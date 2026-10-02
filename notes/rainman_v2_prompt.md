# RAINMAN v2 — build prompt (paste this as the first message of the next chat in this Project)

Build **RAINMAN v2**: a new front end for the existing RAINMAN NFL defense-vs-position system with a significantly better
UI — clean, minimalist, dark, with impressive but purposeful motion ("physics": spring-based transitions, inertial
scrolling panels, animated number/rank changes, heatmap cells that settle into place, cards that lift and snap). v2 must
show **everything v1 shows** (full inventory below) while feeling like one product, not nine tabs. v1 stays the live site
and the backup until v2 is signed off.

## Hard constraints (read first)

1. **Repo / paths.** Repo `3GO-47/rainman`, local `C:\Users\jwlar\rainman`, cloud clone `/home/claude/rainman-push`
   (re-clone from GitHub if the cloud workspace is fresh). v1 = `scripts/dashboard_template.html` →
   `dashboard/rainman.html` (served at the root of https://3go-47.github.io/rainman/). **Do not edit the v1 template or
   its build.** v2 lives in `scripts/v2/` (source) and builds to `dashboard/v2/index.html`; the Pages workflow already
   publishes `dashboard/v2/` to **https://3go-47.github.io/rainman/v2/** side-by-side with v1. Only when the user says
   v2 is complete do you (a) copy v2 over the root in `.github/workflows/pages.yml` and (b) keep v1 reachable at
   `/v1/` as the backup.
2. **Same data, same numbers.** v2 is a *view* change. Refactor `scripts/build_dashboard.py` so the payload assembly is a
   function (`build_payload()`), then add `scripts/build_dashboard_v2.py` that imports it and injects the identical JSON
   into `scripts/v2/template.html` at `__DATA__`. Every number in v2 must equal v1's for the same filter state (spot-check
   ≥10 values per view against v1 in Playwright). No hand-entered values; all data still traces to `data/game_logs/`.
   `scripts/refresh.py` must build both v1 and v2.
3. **Single self-contained file.** Inline CSS/JS + embedded JSON (currently ~2.9 MB). CDN libraries allowed
   (cdnjs/jsdelivr): e.g. Chart.js or D3 for charts; a motion library (Motion One / anime.js / GSAP-free CSS springs) is
   fine. Must open from `file://` and from Pages. Must work with JS errors = 0 on every view (Playwright `pageerror`).
4. **Deploy workflow (no credentials exist anywhere; never ask for or store any).** Commit in the cloud clone as
   `Claude <noreply@anthropic.com>`; `git push` is blocked (proxy 403), so deploy by **GitHub web upload in Chrome**:
   navigate `https://github.com/3GO-47/rainman/upload/main/<dir>`, `find` "Choose your files file input button" →
   `file_upload` with the `ref` + `paths` (≤10 MB per call; stage files in `/mnt/user-data/uploads/rainman/_up/`), set
   `#commit-summary-input` via JS (set value, dispatch `input`), click `button.js-blob-submit`. Then `git fetch origin &&
   git diff --stat HEAD origin/main` must be empty; `git reset --hard origin/main`; bundle `git bundle create
   /mnt/user-data/outputs/rainman_<date>.bundle <prev>..origin/main`; SendUserFile → `device_commit_files` to
   `C:\Users\jwlar\rainman\notes\_sync_<date>.bundle` → `device_bash`: remove `.git/*.lock` and `.git/objects/pack/tmp_*`,
   `git fetch -q notes/<bundle> refs/remotes/origin/main:refs/remotes/origin/main; git reset -q --hard origin/main;
   git update-ref refs/heads/main origin/main; rm notes/<bundle>`. `rm`/reset on the device needs
   `device_request_delete_permission` for `C:\Users\jwlar\rainman` once per session. Load `mcp__remote-devices__*` and
   Chrome tools via ToolSearch first; Chrome tab ids change every session (call `tabs_context_mcp`). `_up/` is gitignored.
5. **Working style.** The user wants autonomy: build, verify, commit, deploy, sync — do not ask for permission for things
   you can do. Optimize credits: batch tool calls, keep replies short, no recaps. Log each session in
   `notes/session_log.md`, update `README.md` changelog, keep `notes/scrape_recipe.md` as the source of scraping truth.
   `python3 scripts/verify_data.py` must stay 64/64.

## What v1 shows (v2 must cover all of it)

Payload `J` keys: `built, week, statCols, slots, groupStats, primary, dvp{2024,2025,2026,combined}, blend, weekly
[def,season,week,opp,…statCols], logs [player,pfr_id,season,week,team,opp,h/a,slot,pos,PaYd,PaTD,PaAtt,Cmp,Int,RuAtt,RuYd,
RuTD,Tgt,Rec,RcYd,RcTD,std,ppr,snaps,snap%,tgtShare,aDOT,rushShare,WOPR], matchups (matchups_current.csv rows),
sched26{team:[18 opps]}, games26 [wk,vis,home,date,day,time_et,slate], depth (latest ESPN snapshot), depthDate,
intel{tags,tendencies,turnover,coaching,usage}, bets{games,backtest,ledger,retro,ratings,props,propsLedger,propsWeek}`.
Read `scripts/dashboard_template.html` for every formula before reimplementing — in particular `projection()` and
`MODEL={shrinkK:3,matchMode:'blend',blendK:4,matchW:.2,matchByPos:{QB:.35,RB:.15,WR:.05,TE:.25},trustFloor:.4,schemeW:1,
schemeClamp:[.85,1.15],envW:.1,roleW:.6,roleClamp:.25}`, `trust()`, `envAll()`, `schemeEdge()`, `conv()` (Ψ+),
`USG`, `applyW/rawRatio/inSeasonAllowed/pprAllowedWk`, `runBacktest/tuneModel/btMetrics`. Port the logic verbatim into a
shared `scripts/v2/model.js` section; do not re-derive it.

**Global filter bar (every view):** week · slate chips (TNF/INTL AM/SUN 1P/SUN 4P/SNF/MNF…) · position (ALL/QB/RB/WR/TE/
D/ST) · game · team · roster/owner (Draft Results) · search · clear · ctrl-K palette · URL hash state · summary
"wk N · G games · T teams". Semantics: `inF/inD/inP/inO/inU` predicates (team/defense/player/owner/usage) — keep them.

**Views (v1 nav F1–F9 + "?" glossary):**
- **Home** — intel brief (week narrative), trust gauges per defense, environment (pace/plays/pass-lean, roof/wind), scheme
  edges, Top-projections "Big Board preview", My Lineup (roster-filtered best lineup with Ψ+), smash/avoid board, slate map.
- **Big Board** — full projected-PPR ranking with lift decomposition (baseline → slot shrink → DvP → scheme → env → role),
  CSV export; **Model Lab** — walk-forward backtest over played weeks, metrics (MAE, Spearman, hit rates), parameter
  re-tune with the live MODEL object.
- **Weekly Matchups** — one card per game: field tilt bar, both defenses (DC, scheme tag, trust, env), each offense's slot
  owners with opponent's DvP rank badge + raw allowed per stat; click player → card popup.
- **Players** — Depth Charts (ESPN snapshot, injury flags 1/0/−1), Matchup Lab (multi-position toggle; single-position =
  per-stat rank + raw columns; multi = shared sortable grid PaYd·PaTD·RuYd·Rec·RcYd·TD·P+R/R+Y with blanks, nulls last;
  Ψ, Ψ+, PROJ, ω), Player deep-dive (full game log all seasons, per-game PPR, usage trends snaps/tgt share/aDOT/WOPR,
  next-4 schedule strength for his slot), 1st-string-only / hide-OUT toggles, player card popups.
- **Defenses** — rankings table per slot/stat (rank 1 = most allowed = best matchup, composite * = mean of stat ranks),
  32×slot heatmap matrix with drill-down, season toggle (2024 / 2025 / 2026 / combined blend), Defense Observatory
  (weekly stats-allowed timeline per slot, last-4 vs season trend, improving/collapsing flags).
- **TD Board** — TD-allowed / TD-scored board by slot and team.
- **Schedule** — team × week grid with byes, slot-specific DvP coloring, rest-of-season strength winners/losers.
- **Intel** — scheme tags with evidence (coverage/front/blitz/man-zone/personnel), tendencies, starter turnover
  (returning snap %), coaching changes (HC/OC/DC), usage leaders.
- **Games & Picks** — matchup cards (market line vs model spread/total vs SRS ratings vs env/scheme/trust), picks ledger
  (frozen picks graded vs frozen line; retro; 2024-25 backtest record ATS 106-109, totals 113-94), player props (DK lines
  vs our per-stat projection, edge %, L10 over-rate, DvP rank, leans, props ledger record).
- **Insights** — auto takeaways: top-5 smash / top-5 avoid per position, biggest DvP movers (3 wks), ROS schedule
  winners/losers. **Glossary** ("?") defining Ψ, Ψ+, ω, trust, *, env, scheme edge, lift.

## v2 design brief

- **Shell:** a single scrolling canvas with a left rail (icons + labels, collapses to icons; bottom tab bar on mobile) and
  a persistent slim filter strip; views are *panels* that slide/cross-fade with spring easing, not page swaps. One
  typeface family (e.g. Inter + JetBrains Mono for numbers), 8-pt spacing grid, ≤5 accent colors plus a continuous
  green→amber→red matchup scale used consistently everywhere. Generous whitespace; no boxes-inside-boxes; no emoji.
- **Physics/motion (impressive, not gratuitous):** animated count-up/down on numbers when filters change, rank badges
  that reorder with FLIP transitions, heatmap cells that stagger-settle, cards with subtle parallax/tilt on hover, drag-to-
  reorder lineup slots with inertia, scrubber on the defense timeline, charts that draw in. All motion ≤300 ms, honors
  `prefers-reduced-motion`, 60 fps on an iPhone (Playwright iPhone 13: load ≤1.2 s, filter apply ≤150 ms).
- **Density:** every v1 number remains reachable within 2 taps (progressive disclosure: summary row → expand → raw). Tables
  are virtualized or paginated above ~200 rows; sticky headers; sort on any column; column pickers.
- **Mobile first:** no horizontal page scroll at 390 px, tap targets ≥40 px, filter strip collapses into a sheet.
- **Performance:** lazy per-view rendering (v1 already does this: `RR`/`DIRTY`/`runView`), memoized projections
  (`PCACHE`), payload parsed once; consider splitting `logs` into typed arrays.
- **Accessibility:** keyboard nav (F1–F9, ctrl-K retained), focus rings, ARIA on tabs/tables, contrast ≥4.5:1.

## Plan of record

1. Read `README.md`, `notes/session_log.md` (last 3 entries), `scripts/dashboard_template.html`, `scripts/build_dashboard.py`.
2. Refactor payload into `build_payload()`; add `build_dashboard_v2.py`; wire into `refresh.py`; verify v1 output byte-identical.
3. Build `scripts/v2/template.html` view by view in this order: shell + filter strip + Home → Big Board/Model Lab → Players →
   Defenses → Weekly Matchups → Games & Picks → TD Board/Schedule/Intel/Insights/Glossary. After each view: Playwright
   smoke (0 errors, numbers match v1), mobile screenshot, commit, deploy to `/v2/`, sync device.
4. When all views pass parity + the motion/perf budget, write `notes/v2_parity_report.md` and stop; the user decides the
   cut-over (root ← v2, `/v1/` ← v1).
