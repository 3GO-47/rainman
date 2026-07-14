"""Build weekly depth chart snapshot CSV from an ESPN raw dump (TEAM|POSROW|DEPTH|NAME|TAG lines),
cross-check against Fantasy Master Key, update scrape_state.json.

Usage: python3 build_depth_chart.py <raw_txt> <date YYYY-MM-DD>
Slot convention: QB1/QB2.., RB1/RB2.., TE1/TE2.. by depth; WR rows 1-3 starters = WR1/WR2/WR3,
all non-starter WRs = WR4+. Injury: 1 active, 0 questionable (Q), -1 out (O/IR/PUP/SUSP/NFI/D).
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

def main(raw, date):
    rows = []
    for line in open(raw, encoding='utf-8'):
        line = line.rstrip('\n')
        if not line.strip(): continue
        team, pos, d, name, tag = line.split('|')
        team = TEAM_NORM.get(team, team)
        d = int(d)
        if pos.startswith('WR'):
            slot = pos if d == 1 else 'WR4+'
        else:
            slot = f'{pos}{d}'
        inj = 1
        if tag == 'Q': inj = 0
        elif tag in OUT_TAGS: inj = -1
        rows.append({'player': name, 'team': team, 'slot': slot, 'injury': inj,
                     'pos_row': pos, 'depth': d})
    out = f'data/processed/depth_charts_{date}.csv'
    with open(out, 'w', newline='', encoding='utf-8') as f:
        w = csv.DictWriter(f, fieldnames=['player','team','slot','injury','pos_row','depth'])
        w.writeheader(); w.writerows(rows)
    print(f'wrote {out}: {len(rows)} rows, {len({r["team"] for r in rows})} teams')

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
