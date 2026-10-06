# Restore points

Each row is a state the whole site can be put back to. The HTML snapshots are served at /archive/; the template + builder
are in git at the listed commit (the web-upload workflow cannot push tags, so the SHA is the anchor).

| date | label | commit | what it is | how to restore |
|---|---|---|---|---|
| 2026-10-06 | v1.2 NFL + v1.0 NCAA (pre-revamp) | `aedc14c` | original terminal UI, F11 Bets prop-research tab, NFL/NCAA switch, league-aware template; week 4 complete | `git checkout aedc14c -- scripts/dashboard_template.html scripts/build_dashboard.py .github/workflows/pages.yml` then `python3 scripts/refresh.py` and `python3 scripts/ncaa/refresh.py --no-fetch`; or copy `scripts/archive/dashboard_template_v1.2_2026-10-06.html` over the template. Static copies: dashboard/archive/rainman_v1.2_2026-10-06.html, ncaa_v1.0_2026-10-06.html |
| 2026-10-06 | v2 shell (task-based sidebar + restyle) | see git log | sidebar navigation, Inter/JetBrains Mono, amber accent; same data modules | this is the live state after the revamp |
| 2026-10-05 | v1 original | `f13c159` | the terminal as first shipped | `git checkout f13c159 -- scripts/dashboard_template.html` |
