"""Tests use only local fixtures and never contact destination sites."""
from http.client import HTTPConnection
from pathlib import Path
from tempfile import TemporaryDirectory
from threading import Thread
import sys
import unittest

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / 'scripts'))
import yaml
from build import ConfigurationError, RESERVED, build, cards_html, load_links, validate
from preview import make_server, read_redirects


def entry(**values):
    return dict(slug='test-link', label='Test link', destination='https://example.com/path?x=1&y=2', enabled=True, homepage=True, **values)


class LinkTests(unittest.TestCase):
    def test_initial_configuration(self):
        links = load_links()
        self.assertEqual([x['slug'] for x in links if x['enabled']], ['designs', 'main'])
        self.assertEqual([x['slug'] for x in links if not x['enabled']], ['shop', 'print', 'instagram'])
        self.assertEqual(cards_html(links).count('class="destination"'), 1)

    def test_slug_validation_and_reserved_paths(self):
        for slug in ['/print', 'Print', 'my link', '?foo', '#test', '', '-', 'a--b', '../a', 'a' * 65, 'favicon.ico', 'robots.txt', *RESERVED]:
            with self.subTest(slug=slug), self.assertRaises(ConfigurationError):
                validate({'links': [dict(entry(), slug=slug)]})
        for slug in ['print', '42', 'diorama-kit']:
            self.assertTrue(validate({'links': [dict(entry(), slug=slug)]}))

    def test_duplicates_including_disabled_entries(self):
        with self.assertRaisesRegex(ConfigurationError, 'duplicate slug'):
            validate({'links': [entry(), dict(entry(), enabled=False)]})

    def test_unsafe_and_malformed_destinations(self):
        for url in ['javascript:alert(1)', 'data:text/html,test', 'file:///a', 'http://example.com', '//example.com', 'https://', 'https://a b/', 'https://x/\n/shop', 'https://x/%0d%0a', 'https://user:password@example.com', 'https://bmat.io/print', 'https://www.bmat.io./', 'https://example.com:bad', 'https://example.com/:splat', 'https://example.com/*']:
            with self.subTest(url=url), self.assertRaises(ConfigurationError):
                validate({'links': [dict(entry(), destination=url)]})

    def test_disabled_empty_destination_and_bad_supplied_destination(self):
        self.assertTrue(validate({'links': [dict(entry(), enabled=False, destination=None)]}))
        with self.assertRaises(ConfigurationError):
            validate({'links': [dict(entry(), enabled=False, destination='javascript:bad')]})

    def test_types_and_typos(self):
        for key, value in [('enabled', 'true'), ('homepage', 1), ('order', True), ('new_tab', 'false'), ('icon', []), ('label', ''), ('description', []), ('enabeld', True)]:
            with self.subTest(key=key), self.assertRaises(ConfigurationError):
                validate({'links': [dict(entry(), **{key: value})]})

    def test_order_visibility_escaping_and_new_tab(self):
        links = validate({'links': [
            dict(entry(), slug='later', order=30),
            dict(entry(), slug='hidden', homepage=False),
            dict(entry(), slug='disabled', enabled=False),
            dict(entry(), slug='first', order=10, label='<script>test</script>', description='A & B', new_tab=True, shortlink=False),
        ]})
        html = cards_html(links)
        self.assertLess(html.index('&lt;script&gt;'), html.index('/later'))
        self.assertNotIn('<script>', html)
        self.assertNotIn('/hidden', html)
        self.assertNotIn('/disabled', html)
        self.assertIn('target="_blank" rel="noopener noreferrer"', html)
        self.assertIn('Opens in a new tab', html)
        self.assertIn('A &amp; B', html)
        self.assertIn('href="https://example.com/path?x=1&amp;y=2"', html)

    def test_empty_hub(self):
        self.assertIn('No links are available', cards_html([]))


class BuildTests(unittest.TestCase):
    def setUp(self):
        (ROOT / '.tools').mkdir(exist_ok=True)
        self.temp = TemporaryDirectory(dir=ROOT / '.tools')
        self.root = Path(self.temp.name)
        self.data = self.root / 'links.yaml'
        self.output = self.root / 'dist'

    def tearDown(self):
        self.temp.cleanup()

    def write(self, links):
        self.data.write_text(yaml.safe_dump({'links': links}), encoding='utf-8')

    def test_duplicate_yaml_keys(self):
        self.data.write_text('links: []\nlinks: []\n', encoding='utf-8')
        with self.assertRaisesRegex(ConfigurationError, 'Duplicate'):
            load_links(self.data)

    def test_generated_rules_and_removal(self):
        self.write([entry(), dict(entry(), slug='home-only', shortlink=False), dict(entry(), slug='off', enabled=False, destination=None)])
        build(self.output, self.data)
        rules = read_redirects(self.output)
        self.assertEqual(set(rules), {'/test-link', '/test-link/'})
        self.assertEqual(rules['/test-link'], ('https://example.com/path?x=1&y=2', 302))
        self.assertNotIn('/off', (self.output / 'index.html').read_text())
        self.write([])
        build(self.output, self.data)
        self.assertEqual(read_redirects(self.output), {})

    def test_invalid_configuration_preserves_successful_build(self):
        self.write([entry()])
        build(self.output, self.data)
        previous = (self.output / '_redirects').read_bytes()
        self.write([dict(entry(), slug='Bad')])
        with self.assertRaises(ConfigurationError):
            build(self.output, self.data)
        self.assertEqual(previous, (self.output / '_redirects').read_bytes())

    def test_http_landing_redirects_and_404(self):
        build(self.output)
        server = make_server(self.output, 0)
        thread = Thread(target=server.serve_forever, daemon=True)
        thread.start()
        try:
            for method, route, status in [('GET', '/', 200), ('GET', '/designs', 302), ('HEAD', '/main/', 302), ('GET', '/designs/', 302), ('GET', '/shop', 404), ('GET', '/print', 404), ('GET', '/instagram', 404), ('GET', '/not-a-real-link', 404), ('GET', '/nested/missing', 404), ('GET', '/_redirects', 404), ('GET', '/assets/site.css', 200)]:
                with self.subTest(route=route, method=method):
                    client = HTTPConnection('127.0.0.1', server.server_port)
                    client.request(method, route)
                    response = client.getresponse()
                    body = response.read().decode('utf-8')
                    self.assertEqual(response.status, status)
                    if status == 302:
                        self.assertEqual(response.getheader('Location'), 'https://bmatic.xyz/')
                        self.assertEqual(body, '')
                    elif status == 404:
                        self.assertIn('Back to bmat.io', body)
                        self.assertNotIn('Location', response.headers)
                    elif route == '/':
                        self.assertIn('Dream. Design. Discover.', body)
                        self.assertNotIn('<script', body)
                    client.close()
        finally:
            server.shutdown()
            server.server_close()
            thread.join()


if __name__ == '__main__':
    unittest.main()
