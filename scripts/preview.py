"""Local-only static preview that reads generated _redirects, not a second link database."""
from functools import partial
from http.server import SimpleHTTPRequestHandler, ThreadingHTTPServer
from pathlib import Path
from urllib.parse import unquote, urlsplit
import argparse

from build import ROOT, build


def read_redirects(directory):
    rules = {}
    for line in (Path(directory) / '_redirects').read_text(encoding='utf-8').splitlines():
        if line and not line.startswith('#'):
            source, destination, code = line.split()
            rules[source] = (destination, int(code))
    return rules


class Handler(SimpleHTTPRequestHandler):
    def __init__(self, *args, directory, **kwargs):
        self.output = Path(directory).resolve()
        super().__init__(*args, directory=str(self.output), **kwargs)

    def do_GET(self):
        self.respond(head=False)

    def do_HEAD(self):
        self.respond(head=True)

    def respond(self, head=False):
        route = unquote(urlsplit(self.path).path)
        redirect = read_redirects(self.output).get(route)
        if redirect:
            target, code = redirect
            self.send_response(code)
            self.send_header('Location', target)
            self.send_header('Content-Length', '0')
            self.end_headers()
            return
        path = (self.output / route.lstrip('/')).resolve()
        if route == '/':
            path = self.output / 'index.html'
        # Only serve intended public files; never expose host control files or listings.
        if not path.is_relative_to(self.output) or path.name.startswith('_') or not path.is_file() or route in ('/404', '/404.html'):
            self.send_response(404)
            self.send_header('Content-Type', 'text/html; charset=utf-8')
            self.send_header('X-Robots-Tag', 'noindex')
            body = (self.output / '404.html').read_bytes()
            self.send_header('Content-Length', str(len(body)))
            self.end_headers()
            if not head:
                self.wfile.write(body)
            return
        if head:
            super().do_HEAD()
        else:
            super().do_GET()


def make_server(directory=ROOT / 'dist', port=4174):
    return ThreadingHTTPServer(('127.0.0.1', port), partial(Handler, directory=directory))


if __name__ == '__main__':
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--port', type=int, default=4174)
    args = parser.parse_args()
    build()
    with make_server(port=args.port) as server:
        print(f'BMatic preview: http://127.0.0.1:{args.port} (Ctrl+C to stop)', flush=True)
        print('Edit YAML, then restart this command to rebuild. Production redirects are handled by Cloudflare Pages.', flush=True)
        try:
            server.serve_forever()
        except KeyboardInterrupt:
            pass
