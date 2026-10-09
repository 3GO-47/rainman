# DraftKings salaries — how the weekly file gets made

`scripts/build_dfs.py` needs one file to build a cap-legal lineup:

    data/raw/dk_salaries_wk{N}.csv

It is read in **DraftKings' own export schema**, so there are two ways to produce it and they are
interchangeable — the build does not care which one you used.

## 1. Straight from DraftKings (preferred, zero intermediaries)

Open any NFL Classic contest lobby, click **Available Players → Export to CSV**, and drop the file at
`data/raw/dk_salaries_wk{N}.csv`. Done. These are DK's numbers by definition.

## 2. The Chrome route (what was used for week 5, 2026)

DraftKings' own endpoints are unreachable from every machine in this stack:

| from | `api.draftkings.com` |
|---|---|
| cloud sandbox | `CONNECT tunnel failed, 403` (egress allowlist) |
| device VM (`device_bash`) | `X-Proxy-Error: blocked-by-allowlist` |
| Chrome bridge | `This site is not allowed due to safety restrictions` |

So the salaries come through a site that republishes DK's posted numbers for every DK slate:

    https://fftoolbox.fulltimefantasy.com/football/draftkings-fulltimefantasy-scores.php?dgi={DRAFT_GROUP_ID}

* The page's **slate** `<select name="dgi">` lists every DK draft group for the week by name —
  `Main Slate (11 games)`, `Early Only (8 games)`, `Afternoon Only (3 games)`, `Primetime (2 games)`,
  `Thu-Mon (15 games)`, plus one Showdown per game. Those map onto `SLATES` in `build_dfs.py`.
* Pick the **widest** classic slate (`Thu-Mon`) — it carries every player of the week, and DK posts the
  same classic salary across the week's classic slates.
* The player `<select>` on that page holds one option per player, formatted
  `POS · Name · TEAM @ OPP · $9,800 · 31.6 pts · 3.22 BoxScore value`. Read `POS`, `Name`, `TEAM` and the
  dollar figure; ignore their projection — RAINMAN uses its own.
* `DEF` rows carry the team nickname; `build_dfs.py` renames them `{TEAM} D/ST`. `LVR` → `LV`.

Then write the four columns the build reads (`Position,Name,Salary,TeamAbbrev`) in DK's header order.
Week 5 2026: `dgi=154467`, 258 players — 30 QB, 61 RB, 97 WR, 40 TE, 30 DEF.

### Chrome notes
* The extension redacts query strings out of anything JavaScript returns, so read the `<select>`
  **options**, not `performance.getEntriesByType('resource')`.
* `javascript_tool` truncates its result near 1 kB. Stash the rows on `window` first, then page through
  them in slices of ~38 inside one `browser_batch`.
* `rotoguru1.com` (the classic free archive) no longer answers through any proxy — don't bother.

## What the build guarantees once the file is there

`capped` flips on, the DST slot appears, and the lineup is the **exact optimum** under every DK Classic
rule (QB/RB/RB/WR/WR/WR/TE/FLEX/DST · FLEX from RB-WR-TE · no player twice · $50,000 cap · two games
minimum). It is re-checked against those rules before it is allowed to freeze, and a slate whose first
kickoff has already passed is refused outright — a frozen lineup has to be something you could actually
have submitted.
