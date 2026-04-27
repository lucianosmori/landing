# Roadmap / TODO

Items not blocking, sorted by severity. Add new ones at the top of their bucket.

## Low severity

- **Explore PWA / service-worker viability** — Lighthouse v12+ no longer scores a PWA category, so installability isn't a free win. The site has no offline content worth caching. Worth keeping on the list because:
  - If we add a `/blog` or `/talks` index later, a service worker could pre-cache the homepage shell and feel snappy on repeat visits.
  - If we ever publish a CV or downloadable artifact, "Add to home screen" + offline could be a small but distinctive touch.
  - **Effort if pursued**: ~30–60 min — `site.webmanifest`, two PNG icons (192px, 512px), 30-line `sw.js` doing offline-first cache, registration in `index.html`. Maintenance cost: cache-busting discipline on every deploy.
  - **When to revisit**: when content grows beyond the current single-page profile, OR when there's a clear UX reason ("install this as an app for offline reference").

## Done — kept for context

- Lighthouse 100/100/100 mobile + desktop on Accessibility, Best Practices, SEO — see commits `c389d39`, `e221b76`, `1504a85`.
- CI Lighthouse audits wired: `lighthouse-pr.yml` (PR preview, static-dist-dir), `lighthouse-post-deploy.yml` (live, async, non-blocking). Reports upload to Lighthouse CI's temporary public storage; links surface as workflow artifacts and PR comments.
- Service-account GSC pull script at `scripts/gsc-pull.py`. Pending one-click GSC permission grant for the SA email.
