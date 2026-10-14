# Restore points

Each row is a state the whole site can be put back to. The HTML snapshots are served at /archive/; the template + builder
are in git at the listed commit (the web-upload workflow cannot push tags, so the SHA is the anchor).

| date | label | commit | what it is | how to restore |
|---|---|---|---|---|
| 2026-10-06 | v1.2 NFL + v1.0 NCAA (pre-revamp) | `aedc14c` | original terminal UI, F11 Bets prop-research tab, NFL/NCAA switch, league-aware template; week 4 complete | `git checkout aedc14c -- scripts/dashboard_template.html scripts/build_dashboard.py .github/workflows/pages.yml` then `python3 scripts/refresh.py` and `python3 scripts/ncaa/refresh.py --no-fetch`; or copy `scripts/archive/dashboard_template_v1.2_2026-10-06.html` over the template. Static copies: dashboard/archive/rainman_v1.2_2026-10-06.html, ncaa_v1.0_2026-10-06.html |
| 2026-10-06 | v2 shell (task-based sidebar + restyle) | see git log | sidebar navigation, Inter/JetBrains Mono, amber accent; same data modules | this is the live state after the revamp |
| 2026-10-05 | v1 original | `f13c159` | the terminal as first shipped | `git checkout f13c159 -- scripts/dashboard_template.html` |

## v5.2 — 2026-10-14 (commit 343c1df, tag v5.2-2026-10-14)
Five-tab layout with the n49–n51 fixes (loop self-sufficient, depth-chart universe, CLV, per-tab notes). Frozen copies: dashboard/archive/rainman_v5.2_2026-10-14.html,
dashboard/archive/ncaa_v1.2_2026-10-14.html, scripts/archive/dashboard_template_v5.2_2026-10-14.html; full backup backups/rainman_backup_v6_2026-10-14.zip.
Revert the template: cp scripts/archive/dashboard_template_v5.2_2026-10-14.html scripts/dashboard_template.html && python3 scripts/build_dashboard.py

## v5.3-live — 2026-10-14 (tag v5.3-live-2026-10-14; the build live on Pages after the revert)
Template = ceb2ef2's (F6 TEST visible, 11-view Intel/Picks layout) + today's data/loop fixes. Frozen: dashboard/archive/rainman_v5.3_live_2026-10-14.html,
scripts/archive/dashboard_template_v5.3_live_2026-10-14.html; backup backups/rainman_backup_v7_live_2026-10-14.zip.
Revert: cp scripts/archive/dashboard_template_v5.3_live_2026-10-14.html scripts/dashboard_template.html && python3 scripts/build_dashboard.py
