"""Check generated HTML, assets, metadata, and exact agreement with YAML."""
from collections import Counter
from html.parser import HTMLParser
from urllib.parse import urlsplit
import sys

from build import ROOT, load_links
from preview import read_redirects


class Page(HTMLParser):
    def __init__(self, source):
        super().__init__()
        self.ids, self.refs, self.cards, self.errors = [], [], [], []
        self.meta, self.canonical, self.title = {}, None, ''
        self.in_title, self.h1, self.scripts = False, 0, []
        self.feed(source)

    def handle_starttag(self, tag, pairs):
        attrs = dict(pairs)
        if 'id' in attrs:
            self.ids.append(attrs['id'])
        if tag == 'h1':
            self.h1 += 1
        if tag == 'script':
            self.scripts.append(attrs.get('src'))
        if tag == 'title':
            self.in_title = True
        if tag == 'meta':
            self.meta[attrs.get('name', attrs.get('property'))] = attrs.get('content')
        if tag == 'link' and attrs.get('rel') == 'canonical':
            self.canonical = attrs.get('href')
        for key in ('src', 'href'):
            if key in attrs:
                if not attrs[key] or attrs[key] == '#':
                    self.errors.append(f'empty {key}')
                else:
                    self.refs.append(attrs[key])
        if attrs.get('srcset'):
            self.refs.extend(x.strip().split()[0] for x in attrs['srcset'].split(','))
        if tag == 'img' and 'alt' not in attrs:
            self.errors.append('missing image alt')
        if tag == 'a' and attrs.get('class') == 'destination':
            self.cards.append(attrs['href'])

    def handle_endtag(self, tag):
        if tag == 'title':
            self.in_title = False

    def handle_data(self, data):
        if self.in_title:
            self.title += data


def check():
    output = ROOT / 'dist'
    errors = []
    links = load_links()
    rules = read_redirects(output)
    expected_rules = {f'/{x["slug"]}{suffix}': (x['destination'], 302) for x in links if x['enabled'] and x['shortlink'] for suffix in ('', '/')}
    if rules != expected_rules:
        errors.append('Redirect rules do not match YAML')
    for name, canonical in [('index.html', 'https://bmat.io/'), ('404.html', 'https://bmat.io/404')]:
        source = (output / name).read_text(encoding='utf-8')
        page = Page(source)
        errors.extend(f'{name}: {x}' for x in page.errors)
        if not page.title or page.h1 != 1 or page.canonical != canonical or page.scripts != ['/assets/theme.js']:
            errors.append(f'{name}: title, heading, canonical, or script check failed')
        for field in ('description', 'og:title', 'og:description', 'og:url', 'og:image', 'og:image:alt'):
            if not page.meta.get(field):
                errors.append(f'{name}: missing {field}')
        if any(n > 1 for n in Counter(page.ids).values()):
            errors.append(f'{name}: duplicate IDs')
        for ref in page.refs:
            url = urlsplit(ref)
            if url.scheme or url.netloc:
                continue
            if url.fragment and not url.path and url.fragment not in page.ids:
                errors.append(f'{name}: missing anchor {ref}')
            if url.path and url.path != '/' and url.path not in rules and not (output / url.path.lstrip('/')).is_file():
                errors.append(f'{name}: missing local asset/route {ref}')
        if name == 'index.html':
            expected = ['/' + x['slug'] if x['shortlink'] else x['destination'] for x in sorted(links, key=lambda x: x['order']) if x['enabled'] and x['homepage']]
            if page.cards != expected:
                errors.append('Homepage cards/order do not match YAML')
    print('\n'.join(errors))
    print(f'Checked 2 HTML pages, assets, metadata, homepage ordering and {len(rules)} redirect rules: {len(errors)} errors.')
    return bool(errors)


if __name__ == '__main__':
    sys.exit(check())
