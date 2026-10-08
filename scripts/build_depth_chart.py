"""Build weekly depth chart snapshot CSV from an ESPN raw dump (TEAM|POSROW|DEPTH|NAME|TAG lines),
derive the EFFECTIVE depth chart (who actually holds each slot this week), cross-check against the
Fantasy Master Key, update scrape_state.json.

Usage: python3 build_depth_chart.py <raw_txt> <date YYYY-MM-DD>

ESPN lists injured starters in their old spot (Baker Mayfield QB1 with an "O" tag for weeks), so the raw
chart alone mis-slots the actual starter. Effective slotting, per team and position row:
  1. players tagged OUT / IR / PUP / SUSP / NFI / D drop to the bottom of the row; everyone else moves up
  2. usage check (RB, TE, FB and the three WR rows): if the man directly below has at least 25% more
     opportunities (RB: carries + targets, WR/TE: targets) over the team's last two games AND a real
     workload (>= 10 RB, >= 8 WR/TE), he moves above — one adjacent pass, so a committee cannot leapfrog
     two spots on one hot week. QBs never swap on usage (QB changes are injury / benching, visible in ESPN).
  3. WR starters (the top of rows WR1/WR2/WR3) are then ordered by the same last-two-games targets rule, so
     the DvP slot "WR1" is the receiver actually being fed, not ESPN's row label
Slot convention: QB1/QB2.., RB1/RB2.., TE1/TE2.. by effective depth; WR starters = WR1/WR2/WR3, the rest WR4+.
Injury: 1 active, 0 questionable (Q), -1 out.
Extra columns: espn_depth (raw listing), note (why a player moved), trend (+1 rising / 0 / -1 fading:
last-2-games opportunities per game vs his season rate), l2 (opps per game, last 2 team games), se (season
opps per game), gp (games with a log this season), log_name (the game-log spelling of his name, so the
dashboard can join his averages — "Kenny Gainwell" -> "Kenneth Gainwell").
"""
import sys, csv, json, re, unicodedata
import pandas as pd

TEAM_NORM = {'WSH': 'WAS'}
OUT_TAGS = {'O','IR','PUP','SUSP','NFI','D','IR-R'}

def norm_name(n):
    n = unicodedata.normalize('NFKD', n).encode('ascii','ignore').decode()
    n = re.sub(r"[.'\-]", '', n).lower()
    n = re.sub(r'\s+(jr|sr|ii|iii|iv|v)$', '', n.strip())
    return n

def load_usage():
    """per (team, log_name): season opps/gm, last-2-team-games opps/gm, gp; plus a name index for joining."""
    import glob
    files = sorted(glob.glob('data/game_logs/game_logs_*.csv'))
    if not files: return {}, {}, {}
    season = max(int(re.findall(r'(\d{4})', f)[-1]) for f in files)
    rows = [r for r in csv.DictReader(open(f'data/game_logs/game_logs_{season}.csv', encoding='utf-8'))]
    team_weeks = {}
    for r in rows: team_weeks.setdefault(r['team'], set()).add(int(r['week']))
    last2 = {t: sorted(w)[-2:] for t, w in team_weeks.items()}
    opps = lambda r: (int(float(r['rush_att'] or 0)) + int(float(r['targets'] or 0)), int(float(r['targets'] or 0)), int(float(r['pass_att'] or 0)))
    per = {}
    for r in rows:
        k = (r['team'], r['player']); a = per.setdefault(k, {'gp': 0, 'se': [0, 0, 0], 'l2': [0, 0, 0], 'pos': r['pos']})
        o = opps(r); a['gp'] += 1
        for i in range(3): a['se'][i] += o[i]
        if int(r['week']) in last2.get(r['team'], []):
            for i in range(3): a['l2'][i] += o[i]
    names = {}
    for (t, n) in per: names.setdefault(t, []).append(n)
    all_names = {}
    for f in files:
        for r in csv.DictReader(open(f, encoding='utf-8')): all_names.setdefault(r['team'], set()).add(r['player'])
    return per, names, {t: sorted(v) for t, v in all_names.items()}, last2

def match_log_name(name, team, names, all_names):
    pool = names.get(team, []); pool_all = all_names.get(team, [])
    for cands in (pool, pool_all):
        if name in cands: return name
        nn = norm_name(name); hit = [c for c in cands if norm_name(c) == nn]
        if hit: return hit[0]
        last = norm_name(name.split()[-1]); fi = name[0].lower()
        hit = [c for c in cands if norm_name(c.split()[-1]) == last and c[0].lower() == fi]
        if len(hit) == 1: return hit[0]
    return name

def main(raw, date):
    rows = []
    for line in open(raw, encoding='utf-8'):
        line = line.rstrip('\n')
        if not line.strip(): continue
        team, pos, d, name, tag = line.split('|')
        team = TEAM_NORM.get(team, team)
        inj = 1
        if tag == 'Q': inj = 0
        elif tag in OUT_TAGS: inj = -1
        rows.append({'player': name, 'team': team, 'pos_row': pos, 'espn_depth': int(d), 'injury': inj, 'tag': tag})
    # de-dup (ESPN pages repeat WR rows)
    seen = set(); rows = [r for r in rows if not ((r['team'], r['pos_row'], r['player']) in seen or seen.add((r['team'], r['pos_row'], r['player'])))]

    per, names, all_names, last2 = load_usage()
    for r in rows:
        r['log_name'] = match_log_name(r['player'], r['team'], names, all_names)
        u = per.get((r['team'], r['log_name']))
        kind = 0 if r['pos_row'] in ('RB', 'FB') else 2 if r['pos_row'] == 'QB' else 1
        n2 = len(last2.get(r['team'], [])) or 1
        r['gp'] = u['gp'] if u else 0
        r['se'] = round(u['se'][kind] / u['gp'], 1) if u and u['gp'] else 0.0
        r['l2'] = round(u['l2'][kind] / n2, 1) if u else 0.0
        r['trend'] = 0
        if u and u['gp'] >= 2 and max(r['se'], r['l2']) >= 4:
            if r['l2'] >= 1.2 * r['se'] and r['l2'] - r['se'] >= 2: r['trend'] = 1
            elif r['l2'] <= 0.8 * r['se'] and r['se'] - r['l2'] >= 2: r['trend'] = -1
        r['note'] = ''

    def settle(group, kind):
        """group: rows of one team+pos_row in ESPN order -> effective order (OUT last, usage-adjacent swaps)."""
        act = [r for r in group if r['injury'] != -1]; out = [r for r in group if r['injury'] == -1]
        for r in act:
            ahead_out = [o['player'].split()[-1] for o in out if o['espn_depth'] < r['espn_depth']]
            if ahead_out: r['note'] = 'promoted — ' + ', '.join(ahead_out) + ' out'
        if kind != 'QB':
            floor = 10 if kind == 'RB' else 8
            for i in range(len(act) - 1):
                a, b = act[i], act[i + 1]
                n2 = len(last2.get(a['team'], [])) or 1
                la, lb = a['l2'] * n2, b['l2'] * n2
                if lb >= 1.25 * la and lb >= floor:
                    act[i], act[i + 1] = b, a
                    b['note'] = (b['note'] + ' · ' if b['note'] else '') + f'usage — {lb:g} vs {la:g} opps last {n2} gms'
                    a['note'] = (a['note'] + ' · ' if a['note'] else '') + f'passed by {b["player"].split()[-1]} ({lb:g} vs {la:g} opps)'
        return act + out

    out_rows = []
    teams = sorted({r['team'] for r in rows})
    for t in teams:
        T = [r for r in rows if r['team'] == t]
        for pos in ('QB', 'RB', 'FB', 'TE'):
            g = sorted([r for r in T if r['pos_row'] == pos], key=lambda r: r['espn_depth'])
            if not g: continue
            for i, r in enumerate(settle(g, 'QB' if pos == 'QB' else 'RB' if pos in ('RB', 'FB') else 'TE'), 1):
                r['depth'] = i; r['slot'] = f'{pos}{i}'; out_rows.append(r)
        # WR: settle each row, then order the three starters by last-2 targets
        wr_rows = {}
        for pos in ('WR1', 'WR2', 'WR3'):
            g = sorted([r for r in T if r['pos_row'] == pos], key=lambda r: r['espn_depth'])
            if g: wr_rows[pos] = settle(g, 'WR')
        starters = [v[0] for v in wr_rows.values() if v]
        # pecking order = targets per game this season (shrunk toward 3/gm over 2 games of prior) blended 70/30 with the last two games;
        # ESPN's WR1/WR2/WR3 rows are alignments (X / Z / slot), not a pecking order, and a single hot week should not flip them
        def wr_rate(r):
            se = (float(r.get('se') or 0) * int(r.get('gp') or 0) + 2 * 3.0) / (int(r.get('gp') or 0) + 2)
            return 0.7 * se + 0.3 * float(r.get('l2') or 0) if int(r.get('gp') or 0) else 0.0
        order = sorted(starters, key=lambda r: -wr_rate(r))
        for i, (a, b) in enumerate(zip(starters, order)):
            if a is not b: b['note'] = (b['note'] + ' · ' if b['note'] else '') + f'usage — {wr_rate(b):.1f} vs {wr_rate(a):.1f} tgt/gm (ESPN row {b["pos_row"]})'
        starters = order
        for i, r in enumerate(starters, 1):
            r['depth'] = 1; r['slot'] = f'WR{i}'; out_rows.append(r)
        for pos, v in wr_rows.items():
            for j, r in enumerate(v[1:], 2):
                r['depth'] = j; r['slot'] = 'WR4+'; out_rows.append(r)

    out = f'data/processed/depth_charts_{date}.csv'
    cols = ['player', 'team', 'slot', 'injury', 'pos_row', 'depth', 'espn_depth', 'note', 'trend', 'l2', 'se', 'gp', 'log_name']
    with open(out, 'w', newline='', encoding='utf-8') as f:
        w = csv.DictWriter(f, fieldnames=cols, extrasaction='ignore'); w.writeheader(); w.writerows(out_rows)
    rows = out_rows
    moved = [r for r in rows if r['note']]
    print(f'wrote {out}: {len(rows)} rows, {len({r["team"] for r in rows})} teams · {len(moved)} effective-depth changes')
    for r in moved: print(f"  {r['team']} {r['slot']:4} {r['player']:24} {r['note']}")

    # cross-check vs Fantasy Master Key
    mk = pd.read_excel('Fantasy Master Key 2026 2027.xlsx', sheet_name='Overall Rankings',
                       header=1).rename(columns=str.strip)
    mk = mk.dropna(subset=['Player'])
    mk['Team'] = mk['Team'].astype(str).str.upper().str.strip()
    check_teams = ['KC','PHI','DET','WAS','SF']
    dc = {(r['team'],): None for r in rows}
    flags = [f'# Depth chart cross-check vs Fantasy Master Key — {date}', '']
    def key_last_first(nm):  # "D. Henry" -> ('henry','d')
        parts = nm.replace('.',' ').split()
        return (norm_name(parts[-1]), parts[0][0].lower()) if len(parts)>=2 else (norm_name(nm),'')
    for t in check_teams:
        mk_t = mk[mk['Team']==t]
        dc_t = [r for r in rows if r['team']==t]
        dc_keys = {(norm_name(r['player'].split()[-1]), r['player'][0].lower()) for r in dc_t}
        dc_keys |= {(norm_name(r['player'].split()[-2]) if len(r['player'].split())>2 else norm_name(r['player'].split()[-1]), r['player'][0].lower()) for r in dc_t}
        missing = []
        for _, m in mk_t.iterrows():
            if str(m.get('Pos.','')).upper() not in ('QB','RB','WR','TE'): continue
            if key_last_first(str(m['Player'])) not in dc_keys:
                missing.append(f"{m['Player']} ({m['Pos.']}, owner: {m.get('Owner','?')})")
        flags.append(f'## {t}')
        if missing:
            flags.append('Master Key players NOT on ESPN offense depth chart for this team '
                         '(traded, cut, renamed, or depth-chart lag):')
            flags += [f'- {x}' for x in missing]
        else:
            flags.append('All Master Key offensive players found on ESPN depth chart. OK.')
        flags.append('')
    open(f'notes/depth_chart_flags_{date}.md','w',encoding='utf-8').write('\n'.join(flags))
    print(f'wrote notes/depth_chart_flags_{date}.md')

    st = json.load(open('notes/scrape_state.json'))
    st['depth_charts'] = {'last_pull': date, 'teams_done': sorted({r['team'] for r in rows})}
    json.dump(st, open('notes/scrape_state.json','w'), indent=2)

if __name__ == '__main__':
    main(sys.argv[1], sys.argv[2])
