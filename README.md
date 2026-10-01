# bmat.io — BMatic quick links

BMatic’s small landing page and durable short-link domain. The full brand/catalog site lives at **https://bmatic.xyz/**. This companion is for social profiles, QR codes, packaging, and printed objects.

**One YAML file → homepage cards + HTTP short links.** No browser JavaScript, backend, database, tracking, or application framework. Python and one pinned build dependency (PyYAML) generate deployable static files for Cloudflare Pages.

## Architecture

```text
data/links.yaml + templates/ + assets/
                 │
          scripts/build.py
                 │
                 ▼
dist/index.html      landing page, never redirects
dist/_redirects      /slug and /slug/ → destination, HTTP 302
dist/404.html        missing/disabled-link page
dist/_headers        static response headers
dist/robots.txt      discourages crawling short-link endpoints
dist/assets/         small CSS + official BMatic primary mark
```

`dist/` is generated and ignored; edit source, not output. There are no individual redirect HTML pages. The official primary bee artwork was copied unchanged from the adjacent BMatic site; that site was not modified. No Verti assets/code are used here.

## Build and preview (Windows PowerShell)

Requires Python 3.10+ (tested with 3.13). From this folder:

```powershell
python -m venv .venv
.\.venv\Scripts\python.exe -m pip install -r requirements.txt
.\.venv\Scripts\python.exe scripts/build.py
.\.venv\Scripts\python.exe -m unittest discover -s tests -v
.\.venv\Scripts\python.exe scripts/check_site.py
.\.venv\Scripts\python.exe scripts/preview.py
```

Open **http://127.0.0.1:4174/**. Ctrl+C stops the server. After editing YAML, restart the preview command to rebuild. If Python already has the pinned requirements installed, `python scripts/build.py` and `python scripts/preview.py` suffice.

The local-only preview reads the generated `_redirects` and returns real HTTP 302 responses. It returns the branded page with status 404 for unavailable routes. It is not deployed and is not a full Cloudflare emulator: platform-specific URL normalization, incoming query-string forwarding, cache behavior, and `_headers` processing must be checked on a Pages preview before printing QR codes. A plain `python -m http.server` cannot emulate `_redirects`.

## Manage links

Edit **`data/links.yaml`**. Each entry supports:

| Field | Behavior |
| --- | --- |
| `slug` | Required unique short path, such as `print` or `diorama-kit`. 1–64 lowercase letters/numbers, with single interior hyphens. No slash, spaces, dots, uppercase, or query/fragment text. Quote numeric-only values, e.g. `"42"`. |
| `label` | Required nonempty visible name; independent of the slug. |
| `destination` | Absolute HTTPS URL; required when enabled. Leave null for an unknown disabled destination. |
| `enabled` | Required boolean. False removes both the redirect and homepage card. |
| `homepage` | Required boolean. True shows an enabled entry on the homepage. |
| `shortlink` | Optional boolean, default true. False makes a homepage-only link pointing directly to its destination; its slug still remains unique/reserved. |
| `description` | Optional nonempty text displayed below the label. Omit when unnecessary. |
| `icon` | Optional: `cube`, `bag`, `printer`, `instagram`, `globe`, or `link`. Local decorative inline SVG; labels always remain visible. |
| `order` | Optional integer, default 100. Lower values appear first. Ties keep YAML file order. |
| `new_tab` | Optional boolean, default false. True opens a homepage card in a new tab, adds a visible notice and `noopener noreferrer`. A manually visited short URL cannot force a new tab. |

Complete working example using the known BMatic website:

```yaml
links:
  - slug: main
    label: Visit BMatic
    destination: https://bmatic.xyz/
    description: The main BMatic website.
    icon: globe
    enabled: true
    homepage: true
    shortlink: true
    order: 10
    new_tab: false
```

This produces a homepage card linked to `/main`, plus `/main` and `/main/` redirects. Change only YAML and rebuild/deploy:

- **Add:** append a new entry with a unique slug and verified destination.
- **Change target:** edit `destination`. The printed short URL stays the same.
- **Show/hide on the homepage:** set `homepage: true/false`; redirects keep working if enabled and `shortlink: true`.
- **Homepage only:** use `homepage: true` and `shortlink: false`.
- **Disable:** set `enabled: false`; the URL becomes a branded 404 after deployment.
- **Remove:** delete the entry and rebuild; old rules are removed, not left behind.
- **Rename:** change the slug. For URLs already printed on objects, keep the old entry as a hidden alias (`homepage: false`) pointing to the same destination instead of breaking it.

Unknown shop/social destinations are deliberately disabled. The first visible card receives the gold accent; all later cards use white. If no links are enabled for the homepage, a brief empty state still points visitors to the main-site footer.

## Initial configuration

| Path | Destination / state | On homepage |
| --- | --- | --- |
| `/designs` | `https://bmatic.xyz/` as requested in the seed brief | Yes |
| `/main` | `https://bmatic.xyz/` | No; avoids two identical homepage destinations |
| `/shop` | Disabled; actual BMatic / Slant 3D Portals URL needed | Hidden until enabled |
| `/print` | Disabled; exact Printables profile URL needed | Hidden until enabled |
| `/instagram` | Disabled; exact Instagram profile URL needed | Hidden until enabled |

Once appropriate, `/designs` can be pointed to `https://bmatic.xyz/designs/` by changing that single YAML value. No profile names, shop addresses, credentials, or product claims have been invented.

## Validation and limits

Build errors clearly identify invalid/duplicate slugs (including disabled ones), duplicate YAML keys, unknown/misspelled fields, incorrect types, missing labels, unknown icons, and unsafe destinations. Text is HTML-escaped. HTTPS only; credentials, control characters, invalid hostnames, self-links back to bmat.io, and redirect-template placeholders are rejected. Percent-encode literal `:`/`*` in paths or queries where needed. A supplied disabled URL is validated too; a missing one is allowed. Validation happens before replacing a successful build.

Reserved slugs: `404`, `assets`, `css`, `js`, `data`, `images`, `favicon`, `index`, `robots`, `sitemap`, `admin`, `api`, `cdn-cgi`, `functions`. Root `/`, filenames such as `favicon.ico`, and hosting controls such as `_redirects` are already rejected by the slug grammar.

Each enabled short link generates two exact 302 rules, one with a trailing slash and one without. No wildcard catch-all redirect is used. The build limits output to 1,000 short links (2,000 static rules) and 1,000 characters per rule, matching [Cloudflare’s documented limits](https://developers.cloudflare.com/pages/configuration/redirects/). 302 makes destinations changeable without introducing a permanent 301/308 by default. Do not add a “cache everything” rule over this domain.

`_headers` applies to static pages, **not the redirect responses**, since [Cloudflare executes redirects before headers](https://developers.cloudflare.com/pages/configuration/headers/). The project does not claim to set no-store or noindex headers on 302 responses. `robots.txt` discourages endpoint crawling, redirects contain no indexable content pages, and 404 HTML has `noindex` metadata.

## Cloudflare Pages deployment

Assumption: **Cloudflare Pages**, static hosting with `_redirects` support. Generic static file hosts and GitHub Pages do not interpret this file. No Pages Function or Worker is required.

For Git-integrated Pages, create/connect the repository when ready, then configure:

- Framework preset: **None**.
- Root directory: repository root if publishing Bmatio alone; `Bmatio` if using a parent repository.
- Build command: `pip install -r requirements.txt && python -m unittest discover -s tests -v && python scripts/build.py && python scripts/check_site.py`.
- Build output directory: **`dist`**.
- Python: 3.13 (set `PYTHON_VERSION` in the build environment if needed).
- Add **bmat.io** under the Pages project’s **Custom domains**. For an apex domain, follow Cloudflare’s zone/nameserver and DNS instructions; add the domain through Pages before creating unrelated DNS records. Wait for active domain/TLS status.

Alternatively, run the local build/checks and upload the **contents of `dist`** through a Pages Direct Upload project. Never upload the whole source folder. No `CNAME` file or copied GitHub Pages workflow is needed for this architecture. The top-level `404.html` ensures Pages uses the [custom not-found page instead of SPA fallback](https://developers.cloudflare.com/pages/configuration/serving-pages/).

Before printing short URLs, check `/` (200), `/designs` (302 plus correct Location), `/main/` (302), `/shop` (404), an unknown nested path (404), and target updates on the actual Pages deployment. Also test any query strings you intend to use. Keep long-lived printed slugs stable.

See [Cloudflare custom-domain setup](https://developers.cloudflare.com/pages/configuration/custom-domains/). This build does not create a Cloudflare project, change DNS, initialize Git, commit, push, or deploy.

## Privacy and future analytics

No analytics script or credentials are present. The integration point is documented in `templates/page.html`. If wanted, enable [Cloudflare Web Analytics for Pages](https://developers.cloudflare.com/pages/how-to/web-analytics/) in the dashboard after deployment; do not invent a token or paste a placeholder beacon into production.

A page-view beacon measures the landing page, not visitors who immediately receive HTTP redirects. For future short-link usage, investigate Cloudflare request/path analytics or logs available on the account’s plan. No custom tracking database is needed now. Preserve exact slug routes so later path-based measurement remains possible. Do not assume the free page-view dashboard provides per-short-link counts.

## Browser checks and visual evidence

Optional local checks use installed Chrome and a development-only driver:

```powershell
npm.cmd install --prefix .tools/browser --no-audit --no-fund --package-lock=false playwright-core@1.63.0
# Start python scripts/preview.py in another terminal, then:
node scripts/browser_check.cjs
```

This checks the landing page and branded 404 with JavaScript disabled at 320, 390, 768 and 1440 px, plus keyboard focus, skip link, image loading, and overflow. Test output goes to ignored `.tools/`. See `docs/verification.md` and the saved previews for the completed verification record.
