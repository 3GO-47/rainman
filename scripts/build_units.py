"""Full-unit depth charts + player bios from nflverse (no scraping needed — refreshed by fetch_nflverse.py).
-> data/processed/units_2026.csv  one row per team × unit × position slot × rank (OFF line + skill, DEF 4-3 / 3-4, ST)
-> data/processed/bios_2026.csv   one row per rostered player: college, jersey, height, weight, exp, age, draft, headshot

Usage: python3 scripts/build_units.py
Inputs: data/raw/nflverse/depth_charts_2026.parquet (latest snapshot date), data/raw/nflverse/roster_2026.parquet (latest week)
The offensive skill slots on the dashboard still come from the effective ESPN depth chart (build_depth_chart.py); this file
adds what that chart lacks: the offensive line, the whole defense with its base front, special teams, and every bio field.
Names are normalised (suffixes / punctuation dropped) so the two sources join; nflverse 'LA' -> LAR, 'WAS' kept.
"""
import os, re
import pandas as pd
os.chdir(os.path.join(os.path.dirname(__file__), '..'))
P = 'data/processed/'
TEAM_FIX = {'LA': 'LAR'}

def norm(n):
    n = re.sub(r"\b(Jr|Sr|II|III|IV|V)\.?$", '', str(n).strip()).strip()
    return re.sub(r"[^a-z0-9]", '', n.lower())

def main():
    d = pd.read_parquet('data/raw/nflverse/depth_charts_2026.parquet')
    snap = d.dt.max(); d = d[d.dt == snap].copy()
    d['team'] = d.team.map(lambda t: TEAM_FIX.get(t, t))
    r = pd.read_parquet('data/raw/nflverse/roster_2026.parquet'); r = r[r.week == r.week.max()].copy()
    r['team'] = r.team.map(lambda t: TEAM_FIX.get(t, t))
    r['key'] = r.full_name.map(norm) + '|' + r.team
    bio = {}
    for x in r.itertuples():
        age = ''
        try:
            bd = pd.Timestamp(x.birth_date)
            if bd == bd: age = round((pd.Timestamp.today() - bd).days / 365.25, 1)
        except Exception: age = ''
        ht = ''
        if x.height == x.height and x.height: ht = f"{int(x.height) // 12}-{int(x.height) % 12}"
        bio[x.key] = dict(player=x.full_name, team=x.team, pos=x.position, jersey='' if x.jersey_number != x.jersey_number else int(x.jersey_number),
                          college=str(x.college if isinstance(x.college, str) else '').split(';')[-1].strip(), colleges=(x.college if isinstance(x.college, str) else ''), height=ht, weight='' if x.weight != x.weight else int(x.weight), years_exp=x.years_exp,
                          age=age, draft_club=(x.draft_club or '') if isinstance(x.draft_club, str) else '', draft_number='' if x.draft_number != x.draft_number else int(x.draft_number),
                          entry_year='' if x.entry_year != x.entry_year else int(x.entry_year), status=x.status, headshot=x.headshot_url if isinstance(x.headshot_url, str) else '', espn_id='' if x.espn_id != x.espn_id else int(x.espn_id))
    UNIT = {'3WR 1TE': 'OFF', 'Base 4-3 D': 'DEF', 'Base 3-4 D': 'DEF', 'Special Teams': 'ST'}
    rows = []
    for x in d.itertuples():
        b = bio.get(norm(x.player_name) + '|' + x.team, {})
        rows.append(dict(team=x.team, unit=UNIT.get(x.pos_grp, x.pos_grp), front=x.pos_grp, pos=x.pos_abb, pos_name=x.pos_name, slot=int(x.pos_slot), rank=int(x.pos_rank),
                         player=x.player_name, jersey=b.get('jersey', ''), college=b.get('college', ''), height=b.get('height', ''), weight=b.get('weight', ''),
                         years_exp=b.get('years_exp', ''), age=b.get('age', ''), status=b.get('status', ''), headshot=b.get('headshot', ''), espn_id=x.espn_id if x.espn_id == x.espn_id else ''))
    u = pd.DataFrame(rows).sort_values(['team', 'unit', 'slot', 'rank'])
    u.to_csv(P + 'units_2026.csv', index=False)
    pd.DataFrame(bio.values()).sort_values(['team', 'player']).to_csv(P + 'bios_2026.csv', index=False)
    fronts = u[u.unit == 'DEF'].groupby('team').front.first().value_counts().to_dict()
    print(f"units_2026.csv: {len(u)} rows · snapshot {snap[:10]} · fronts {fronts} · bios {len(bio)} (college known for {sum(1 for b in bio.values() if b['college'])})")

if __name__ == '__main__':
    main()
