# RAINMAN autoloop — the standing runbook for every scheduled run

Every scheduled task starts a fresh session and reads this file first. Follow it literally; the recipes it points to are
in `notes/scrape_recipe.md`. Nothing here needs credentials: data comes through Josh's signed-in Chrome, the push is a
GitHub web upload in that Chrome, and the device sync is a git bundle written into the connected folder.

## 0. Setup (every run)
1. `cd /home/claude && git clone -q https://github.com/3GO-47/rainman rainman-push && cd rainman-push` (the repo is public).
   If the clone already exists: `git fetch -q origin && git reset -q --hard origin/main`.
2. Device: `device_request_folder_access` is already granted for `C:\Users\jwlar\rainman`; call
   `device_request_delete_permission(["C:\\Users\\jwlar\\rainman"])` once (git needs it to replace files).
3. Chrome: `tabs_context_mcp`, create one tab for the pulls. If Chrome is unreachable, retry once after 60 s; if it is still
   unreachable, `send_later` yourself +90 min and stop (the device is asleep).

## 1. Pulls (which ones depends on the day — see §5)
- **Box scores** of the finished week (Tue): PFR recipe → `data/raw/box_lines_2026.txt` (append) + `notes/scrape_state.json`.
- **Depth charts** (every run): ESPN recipe → `data/raw/espn_depth_<today>.txt`, then
  `python3 scripts/build_depth_chart.py data/raw/espn_depth_<today>.txt <today>` (effective slots: OUT players drop,
  usage swaps; see the script header).
- **DraftKings props** (Thu / Sat / Sun): ESPN core API recipe → `data/raw/props_2026_wk<W>_<today>.txt`.
- **Kalshi** (Thu / Sat / Sun): recipe "Kalshi NFL markets" → `data/raw/kalshi_<today>.txt`.
- **NCAA** (Sat): `scripts/ncaa/refresh.py` after the ESPN scoreboard/pickcenter odds pull (NCAA recipe).
Never re-scrape a page already cached in data/raw; respect the pacing in the recipes.

## 2. Build
`python3 scripts/refresh.py` (Tue: full, including `build_signals.py`; other days add `--no-signals` to save a minute).
This rebuilds game logs → DvP → matchups → advanced → games → props → adjusted DvP → prop model → bets → Kalshi → DFS entries →
unified picks (`data/processed/picks_all.csv`, frozen on first build, graded afterwards) → dashboards. Then
`python3 scripts/build_dashboard.py --league ncaa` when NCAA data changed. Sanity: `grep -c . data/processed/picks_all.csv`
grows or holds, never shrinks; `python3 scripts/verify_data.py` passes.

## 3. Commit + deploy (GitHub web upload — the only push path)
1. Commit locally with `-c user.name=Claude -c user.email=noreply@anthropic.com`; end the message with
   `Co-Authored-By: Claude Fable 5.1 <noreply@anthropic.com>` and the session line.
2. Mirror every changed file to `/mnt/user-data/uploads/rainman/_up/<same path>` (`_up/` is git-ignored).
3. Per directory: navigate the Chrome tab to `https://github.com/3GO-47/rainman/upload/main/<dir>`, `find` "Choose your files
   file input button", `file_upload` the mirrored files of that directory (< 10 MB per call), wait 3 s (8 s for the 4–10 MB
   dashboards), then `javascript_tool`: set `#commit-summary-input`.value, dispatch `input`, `setTimeout(()=>button.js-blob-submit.click(),300)`.
   Do not sleep across the navigation in the same call. Order: scripts, data/raw, data/processed, notes, dashboard, README.
4. Verify: `git fetch -q origin && git diff --stat HEAD origin/main` prints nothing. Then `git reset -q --hard origin/main`.
5. Sync the device: `git bundle create /mnt/user-data/outputs/_sync_<tag>.bundle <device_head>..origin/main`;
   `device_commit_files` it to `C:\Users\jwlar\rainman\notes\_sync_<tag>.bundle`; `device_bash`:
   `cd $HOME/mnt/rainman && rm -f .git/index.lock .git/objects/maintenance.lock && git fetch -q notes/_sync_<tag>.bundle refs/remotes/origin/main:refs/remotes/origin/main && git reset -q --hard origin/main && git update-ref refs/heads/main origin/main && rm -f notes/_sync_<tag>.bundle && git log --oneline -1`.
   (`<device_head>` = the device's current `git rev-parse HEAD`; if the bundle is refused for a missing base, bundle from the
   merge-base or copy the changed files with device_commit_files instead.)
6. Pages deploys from `.github/workflows/pages.yml` within ~2 min; spot-check https://3go-47.github.io/rainman/ renders.

## 4. Report (SendUserMessage, short)
Data only — what changed: box scores added, depth-chart moves (promotions, usage swaps, OUT list), new lines posted
(DK / Kalshi counts), biggest DvP movers, graded results (record by type from picks_all.csv — ML / ATS / TOTAL / PROP / TD and
DFS actual vs projected). **Never post picks in the summary**; the Games & Picks tab holds them.

## 5. Calendar (America/Chicago)
| run | when | pulls | build |
|---|---|---|---|
| weekly refresh | Tue 09:00 | box scores of the finished week, depth charts | full refresh (grades every position + DFS entries) |
| midweek lines | Thu 14:00 | depth charts, DK props, Kalshi | refresh --no-signals (TNF lines frozen) |
| Saturday slate | Sat 11:00 | depth charts, DK props, Kalshi, NCAA odds + NCAA refresh | refresh --no-signals + ncaa dashboard |
| pregame freeze | Sun 10:30 | Kalshi (near-closing), depth charts (inactives) | refresh --no-signals (last chance to freeze week positions) |

## 6. Guardrails
- Keys live only in `.env` (git-ignored). `_up/` and root `*.png` stay out of git. Never add credentials anywhere.
- The UI is Josh's: do not restyle or rename tabs in a scheduled run — data, builds, grading and deploys only.
- If a pull source changes shape, stop that pull, build with what exists, and say so in the report with the failing URL.
- Log the run as a dated entry in `notes/session_log.md` (one paragraph).
