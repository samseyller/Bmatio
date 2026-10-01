"""One YAML file -> static homepage and Cloudflare Pages HTTP redirects."""
from html import escape
from pathlib import Path
from string import Template
from urllib.parse import urlsplit
import re
import shutil
import sys

import yaml

ROOT = Path(__file__).resolve().parents[1]
RESERVED = {'404', 'assets', 'css', 'js', 'data', 'images', 'favicon', 'index',
            'robots', 'sitemap', 'admin', 'api', 'cdn-cgi', 'functions'}
FIELDS = {'slug', 'label', 'destination', 'description', 'icon', 'enabled',
          'homepage', 'order', 'new_tab', 'shortlink'}
ICONS = {
    'cube': '<path d="m12 3 9 5v8l-9 5-9-5V8l9-5Zm0 9 9-4M12 12 3 8m9 4v9M7.5 5.5l9 5"/>',
    'bag': '<path d="M5 7h14l1 14H4L5 7Zm3 0V6a4 4 0 0 1 8 0v1"/>',
    'printer': '<path d="M6 9V3h12v6M6 18H3V9h18v9h-3M6 14h12v7H6zM17 11h1"/>',
    'instagram': '<rect x="3" y="3" width="18" height="18" rx="5"/><circle cx="12" cy="12" r="4"/><path d="M17 7h.01"/>',
    'globe': '<circle cx="12" cy="12" r="9"/><ellipse cx="12" cy="12" rx="4" ry="9"/><path d="M3 12h18"/>',
    'link': '<path d="m10 13 4-4m-6 6-1 1a4 4 0 0 1-6-6l4-4a4 4 0 0 1 6 0m2 2 1-1a4 4 0 0 1 6 6l-4 4a4 4 0 0 1-6 0"/>',
}


class ConfigurationError(ValueError):
    pass


class UniqueLoader(yaml.SafeLoader):
    """Also reject duplicate YAML keys, which SafeLoader otherwise overwrites."""


def unique_mapping(loader, node, deep=False):
    mapping = {}
    for key_node, value_node in node.value:
        key = loader.construct_object(key_node, deep=deep)
        if not isinstance(key, str) or key in mapping:
            raise ConfigurationError(f'Duplicate or non-text YAML key: {key!r}')
        mapping[key] = loader.construct_object(value_node, deep=deep)
    return mapping


UniqueLoader.add_constructor(yaml.resolver.BaseResolver.DEFAULT_MAPPING_TAG, unique_mapping)


def validate_url(value):
    if not isinstance(value, str) or not value.startswith('https://'):
        raise ConfigurationError('destination must be an absolute HTTPS URL')
    if not value.isascii() or re.search(r'[\s\\<>"\x00-\x1f\x7f]', value) or re.search(r'%(?:0[0-9a-f]|1[0-9a-f]|7f)', value, re.I):
        raise ConfigurationError('destination contains whitespace/control/unsafe characters; percent-encode URL characters')
    try:
        url = urlsplit(value)
        port = url.port
        hostname = url.hostname
    except ValueError as error:
        raise ConfigurationError(f'invalid destination URL: {error}') from error
    if not hostname or url.username is not None or url.password is not None:
        raise ConfigurationError('destination needs a hostname and cannot contain credentials')
    if hostname.rstrip('.').lower() in {'bmat.io', 'www.bmat.io'}:
        raise ConfigurationError('destination must leave bmat.io; self-links can create redirect loops')
    if not re.fullmatch(r'[a-zA-Z0-9](?:[a-zA-Z0-9.-]*[a-zA-Z0-9])?', hostname) or '..' in hostname:
        raise ConfigurationError('destination hostname must be a valid ASCII DNS name')
    if port is not None and not 1 <= port <= 65535:
        raise ConfigurationError('destination port is invalid')
    if re.search(r':[A-Za-z]|\*', url.path + url.query + url.fragment):
        raise ConfigurationError('percent-encode literal : or * in destination paths/queries to avoid redirect placeholders')
    return value


def validate(document):
    if not isinstance(document, dict) or set(document) != {'links'} or not isinstance(document['links'], list):
        raise ConfigurationError('YAML must contain a single links: list')
    links, seen = [], set()
    for number, original in enumerate(document['links'], 1):
        if not isinstance(original, dict):
            raise ConfigurationError(f'Entry {number}: expected a mapping')
        item = dict(original)
        slug = item.get('slug')
        prefix = f'Entry {number} ({slug!r}): '
        if set(item) - FIELDS:
            raise ConfigurationError(prefix + f'unknown fields: {sorted(set(item) - FIELDS)}')
        if not isinstance(slug, str) or not re.fullmatch(r'[a-z0-9]+(?:-[a-z0-9]+)*', slug) or len(slug) > 64:
            raise ConfigurationError(prefix + 'slug must be 1–64 lowercase letters/numbers with single interior hyphens')
        if slug in RESERVED:
            raise ConfigurationError(prefix + 'reserved slug')
        if slug in seen:
            raise ConfigurationError(prefix + 'duplicate slug')
        seen.add(slug)
        for key in ('enabled', 'homepage'):
            if type(item.get(key)) is not bool:
                raise ConfigurationError(prefix + f'{key} must explicitly be true or false')
        for key, default in (('shortlink', True), ('new_tab', False)):
            item.setdefault(key, default)
            if type(item[key]) is not bool:
                raise ConfigurationError(prefix + f'{key} must be true or false')
        if not isinstance(item.get('label'), str) or not item['label'].strip():
            raise ConfigurationError(prefix + 'label must be nonempty text')
        if 'description' in item and (not isinstance(item['description'], str) or not item['description'].strip()):
            raise ConfigurationError(prefix + 'description must be nonempty text or omitted')
        if item.get('icon') is not None and (not isinstance(item['icon'], str) or item['icon'] not in ICONS):
            raise ConfigurationError(prefix + f'unknown icon; choose {", ".join(ICONS)} or omit')
        item.setdefault('order', 100)
        if type(item['order']) is not int:
            raise ConfigurationError(prefix + 'order must be an integer')
        destination = item.get('destination')
        if item['enabled'] or destination not in (None, ''):
            try:
                validate_url(destination)
            except ConfigurationError as error:
                raise ConfigurationError(prefix + str(error)) from error
        if item['enabled'] and not item['homepage'] and not item['shortlink']:
            raise ConfigurationError(prefix + 'enabled link must have homepage or shortlink enabled')
        if item['enabled'] and item['shortlink'] and len(f'/{slug}/ {destination} 302') > 1000:
            raise ConfigurationError(prefix + 'redirect exceeds Cloudflare’s 1,000-character rule limit')
        links.append(item)
    if sum(item['enabled'] and item['shortlink'] for item in links) > 1000:
        raise ConfigurationError('Maximum 1,000 enabled short links (two rules each)')
    return links


def load_links(path=ROOT / 'data/links.yaml'):
    try:
        return validate(yaml.load(Path(path).read_text(encoding='utf-8'), Loader=UniqueLoader))
    except yaml.YAMLError as error:
        raise ConfigurationError(f'Invalid YAML: {error}') from error


def cards_html(links):
    cards = []
    for item in sorted((x for x in links if x['enabled'] and x['homepage']), key=lambda x: x['order']):
        href = '/' + item['slug'] if item['shortlink'] else item['destination']
        attrs = ' target="_blank" rel="noopener noreferrer"' if item['new_tab'] else ''
        icon = ''
        if item.get('icon'):
            icon = '<span class="card-icon"><svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="1.8" stroke-linecap="round" stroke-linejoin="round" aria-hidden="true" focusable="false">' + ICONS[item['icon']] + '</svg></span>'
        description = '<span class="card-description">' + escape(item['description']) + '</span>' if item.get('description') else ''
        notice = '<span class="new-tab">Opens in a new tab</span>' if item['new_tab'] else ''
        cards.append(f'<a class="destination" href="{escape(href, quote=True)}"{attrs}>{icon}<span class="card-copy"><span class="label">{escape(item["label"])}</span>{description}{notice}</span><span class="arrow" aria-hidden="true">↗</span></a>')
    return '\n'.join(cards) or '<p class="empty-note">No links are available right now. Visit the main BMatic website below.</p>'


def render_page(content, *, title, description, canonical, robots='index, follow'):
    shell = Template((ROOT / 'templates/page.html').read_text(encoding='utf-8'))
    return shell.substitute(content=content, title=escape(title), description=escape(description, quote=True), canonical=canonical, robots=robots)


def build(destination=ROOT / 'dist', links_path=ROOT / 'data/links.yaml'):
    links = load_links(links_path)  # Fail before touching the last successful build.
    home = Template((ROOT / 'templates/home.html').read_text(encoding='utf-8')).substitute(cards=cards_html(links))
    error = (ROOT / 'templates/404.html').read_text(encoding='utf-8')
    redirects = ['# Generated from data/links.yaml. Edit YAML, then rebuild.']
    robots = ['User-agent: *', 'Allow: /$', 'Disallow: /404']
    for item in links:
        if item['enabled'] and item['shortlink']:
            redirects.extend(f'/{item["slug"]}{suffix} {item["destination"]} 302' for suffix in ('', '/'))
        # Exact endpoint paths only; do not accidentally block similarly named routes.
        robots.extend([f'Disallow: /{item["slug"]}$', f'Disallow: /{item["slug"]}/'])
    files = {
        'index.html': render_page(home, title='BMatic — Dream. Design. Discover.', description='Find BMatic designs and the latest configured destinations. Your next stop starts here.', canonical='https://bmat.io/'),
        '404.html': render_page(error, title='Link not found | BMatic', description='This BMatic short link could not be found or is unavailable. Return to bmat.io or visit bmatic.xyz.', canonical='https://bmat.io/404', robots='noindex, follow'),
        '_redirects': '\n'.join(redirects) + '\n',
        '_headers': "/*\n  X-Content-Type-Options: nosniff\n  Referrer-Policy: strict-origin-when-cross-origin\n  X-Frame-Options: DENY\n  Permissions-Policy: camera=(), microphone=(), geolocation=()\n/404\n  X-Robots-Tag: noindex\n/404.html\n  X-Robots-Tag: noindex\n",
        'robots.txt': '\n'.join(robots) + '\n',
    }
    destination = Path(destination).resolve()
    # Fixed build location or test directories under .tools; never delete source.
    if destination != ROOT / 'dist' and not destination.is_relative_to(ROOT / '.tools'):
        raise ConfigurationError('Build output must be dist/ or inside .tools/')
    if destination.exists():
        shutil.rmtree(destination)
    destination.mkdir(parents=True)
    for name, content in files.items():
        (destination / name).write_text(content, encoding='utf-8', newline='\n')
    shutil.copytree(ROOT / 'assets', destination / 'assets')
    shutil.copyfile(ROOT / 'assets/favicon.ico', destination / 'favicon.ico')
    return links


if __name__ == '__main__':
    try:
        result = build()
        print(f'Built dist/: {sum(x["enabled"] and x["homepage"] for x in result)} homepage cards, {sum(x["enabled"] and x["shortlink"] for x in result)} short links (302).')
    except (ConfigurationError, OSError) as error:
        print(f'Build failed: {error}', file=sys.stderr)
        sys.exit(1)
