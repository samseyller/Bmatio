# Verification — October 1, 2026

The landing page and YAML-driven short-link implementation are complete for a static Cloudflare Pages deployment. The domain has not been deployed or configured remotely.

## Checks run

| Command | Result |
| --- | --- |
| `python scripts/build.py` | Passed: one visible homepage card and two enabled short links, each with slash/no-slash 302 rules. |
| `python -m unittest discover -s tests -v` | Passed: 12 tests, including invalid/reserved/duplicate slugs, duplicate YAML keys, unsafe URLs, configuration types, ordering, enabled/homepage/shortlink flags, escaping, new-tab behavior, removal, and real local HTTP response checks. |
| `python scripts/check_site.py` | Passed: two HTML pages, local assets, required metadata, headings, duplicate-ID checks, exact homepage ordering and exact YAML-to-redirect agreement. |
| `python scripts/preview.py` | Served the root landing page and generated redirects locally, with branded missing/disabled-link 404 responses. |
| `node scripts/browser_check.cjs` | Passed: homepage and 404 at 320, 390, 768, and 1440 px with JavaScript disabled, 44 px link targets, no horizontal overflow, loaded images, keyboard access and visible focus. |

The HTTP tests verified `/` returns 200; `/designs`, `/designs/`, and `/main/` return 302 with `Location: https://bmatic.xyz/`; disabled `/shop`, `/print`, `/instagram` and unknown/nested routes return 404 rather than redirecting. The homepage-only variant creates a direct homepage link and no redirect. Shortlink-only entries do not appear on the homepage.

Screenshots were inspected for layout and readability: [phone homepage](previews/home-phone.png), [desktop homepage](previews/home-desktop.png), [phone 404](previews/404-phone.png). Skip-link focus moves to `main`, and the next Tab reaches Browse Designs. No production scripts or external fonts are loaded. The copied primary mark files are byte-identical to the official BMatic assets.

Source/output search found no incorrect brand casing, retired brand name, placeholder fragment links, Google Analytics, or Tag Manager. Unknown shop/social destinations remain null and disabled. Test-only example.com URLs are confined to tests; no fabricated destinations enter the deployed output.

## Hosting assumptions

The production artifact uses Cloudflare Pages `_redirects` syntax for actual edge HTTP redirects, not client-side navigation. The local preview verifies the generated rule semantics but does not emulate every Cloudflare URL, header or cache behavior. A real Pages preview/custom-domain test remains necessary before printing permanent QR codes. No deployment, DNS, Cloudflare settings, Git initialization, commit or push was performed.

Cloudflare documentation was checked for [redirect syntax and limits](https://developers.cloudflare.com/pages/configuration/redirects/), [header/redirect precedence](https://developers.cloudflare.com/pages/configuration/headers/), [404 behavior](https://developers.cloudflare.com/pages/configuration/serving-pages/), [custom domains](https://developers.cloudflare.com/pages/configuration/custom-domains/), and [optional Web Analytics](https://developers.cloudflare.com/pages/how-to/web-analytics/). README documents the account configuration still required and the distinction between landing-page analytics and redirect request counts.

## Workspace safety

`Bmatio` was initially empty and is not a Git repository. No governing AGENTS.md files were found. All writes stayed in Bmatio. The adjacent BMatic repository’s original untracked-file status was preserved; SeyllerApps remained clean. The official primary bee images and favicon were copied read-only from BMatic. Generated `dist/` is the intentional deploy-ready artifact and is ignored by the supplied `.gitignore`; browser/test tooling and scratch output are excluded from deployment.

## Dark-mode update — October 1, 2026

Added a shared-header Dark mode toggle with pressed-state semantics, saved per-origin preference, pre-render initialization and system-theme defaults. Official artwork and gold-button text contrast remain unchanged. Theme browser checks passed at 320, 390 and 1440 px for home/supporting pages, including keyboard activation, reload/navigation persistence, cross-tab synchronization, live system changes, blocked storage and CSS fallback with JavaScript disabled. Both site builds and generated-page validators passed. Bmatio’s 12 link tests passed; fixtures now avoid assumptions about the owner’s enabled shop/Printables links.
