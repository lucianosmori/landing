# CLAUDE.md — landing (lucianomori.cloud)

Static personal site. Vanilla HTML + CSS, no build step.

## Deploy

- **Active branch is `v2`.** Default branch `master` is stale v1 — don't deploy from there.
- `git push origin v2` triggers `.github/workflows/pages.yml`:
  1. `deploy` job publishes to GitHub Pages → live at https://lucianomori.cloud/
  2. `lighthouse-live` job (post-deploy, `continue-on-error`) audits the live site, uploads reports as artifacts + temporary public storage URL
- `.github/workflows/lighthouse-pr.yml` runs the same audit on PRs via lhci's `staticDistDir` mode (no preview URL needed).
- Pages source = branch `v2`, path `/`. CNAME = `lucianomori.cloud` (via `CNAME` file at repo root). HTTPS cert auto-renewed.

## Repo layout

- `index.html` — single page, all content
- `style.css` — tokens + theme-aware CSS (light/dark)
- `images/` — assets referenced by CSS and OG meta
- `favicon.svg`
- `robots.txt`, `sitemap.xml`, `llms.txt` — SEO + AI-search descriptors
- `scripts/gsc-pull.py` — GSC analytics pull (OAuth user creds)
- `data/` — gitignored; holds CSVs from `scripts/gsc-pull.py`
- `docs/` — audit log, TODO
- `.lighthouserc.live.json`, `.lighthouserc.pr.json` — Lighthouse CI configs

## SEO / AI search

- Canonical: `https://lucianomori.cloud/`
- JSON-LD `@graph` in `<head>`: `Person` + `WebSite` + `ProfilePage` with `knowsAbout` topical signals and `sameAs` to LinkedIn / GitHub / Credly
- `llms.txt` is spec-aligned (llmstxt.org); update its `Last updated` line when content changes
- **Lighthouse target: 100/100/100** (Accessibility, Best Practices, SEO) on mobile + desktop. Performance is not measured by `lighthouse_audit` MCP. CI runs are warn-only; the manual baseline is 100.

## GSC pulls

- `python scripts/gsc-pull.py` from repo root
- Auth: **OAuth 2.0 user creds** (NOT the service account — GSC's "Add user" UI rejected the SA grant)
  - Client config: `~/.gsc/oauth.json`
  - Refresh token (auto-stored, silent subsequent runs): `~/.gsc/token.json`
- Output: `data/gsc-YYYY-MM-DD/` with queries, pages, countries, devices, dates, query×page CSVs + `summary.json`
- Refresh token stays valid as long as the GCP OAuth consent screen is in **Production**, or the user remains a registered test user

## Don't

- **Don't flip repo visibility without single-purpose confirmation.** Free-tier privacy disables Pages and the site goes down (incident: 2026-04-26).
- **Don't blanket-ignore `*.json`** in `.gitignore` — it'd swallow Lighthouse configs. Use specific patterns: `service-account*.json`, `sa*.json`, `*credentials*.json`, `gen-lang-client*.json`, `.env*`, `*.pem`, `*.key`.
- **Don't regress Lighthouse scores below 100.** The CI workflows are warn-only; the contract is 100/100/100.

## Source attribution

The v2.0.0 design originated from an Anthropic Design API bundle (`landing-v2`, exported 2026-04-26). The handoff was a React + Babel prototype — re-implemented as static vanilla HTML to fit this repo's stack. Matrix and Talks sections are intentionally hidden in v2.0.0 per the design's own `app.jsx` comment.
