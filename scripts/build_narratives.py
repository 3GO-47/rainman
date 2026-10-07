"""Game narratives for every matchup of the season -> data/processed/narratives_2026.csv
kinds: division (same-division game + series record), rivalry (historical, curated list below), rematch (last meeting with score,
       playoff rematches), coach (HC/OC/DC facing the team he came from), revenge (players vs a former team — from connections),
       streak (one side has won the last N meetings)
Usage: python3 scripts/build_narratives.py
Inputs: kickoffs_2026.csv, data/raw/nflverse/games.csv (scores 2024-26), coaching.csv, connections_2026.csv
"""
import os
import pandas as pd
os.chdir(os.path.join(os.path.dirname(__file__), '..'))
P = 'data/processed/'
FIX = {'LA': 'LAR'}
DIV = {'AFC East': ['BUF', 'MIA', 'NE', 'NYJ'], 'AFC North': ['BAL', 'CIN', 'CLE', 'PIT'], 'AFC South': ['HOU', 'IND', 'JAX', 'TEN'], 'AFC West': ['DEN', 'KC', 'LV', 'LAC'],
       'NFC East': ['DAL', 'NYG', 'PHI', 'WAS'], 'NFC North': ['CHI', 'DET', 'GB', 'MIN'], 'NFC South': ['ATL', 'CAR', 'NO', 'TB'], 'NFC West': ['ARI', 'LAR', 'SF', 'SEA']}
DIV_OF = {t: d for d, ts in DIV.items() for t in ts}
# curated historical rivalries (pair -> name, note)
RIV = {('GB', 'CHI'): ('Packers–Bears', 'the oldest rivalry in the NFL, first played in 1921'), ('DAL', 'WAS'): ('Cowboys–Commanders', 'NFC East blood feud since 1960'),
       ('DAL', 'PHI'): ('Cowboys–Eagles', 'the NFC East title fight more often than not'), ('PIT', 'BAL'): ('Steelers–Ravens', 'the most physical game on the calendar'),
       ('PIT', 'CLE'): ('Steelers–Browns', 'Turnpike rivalry'), ('CIN', 'CLE'): ('Battle of Ohio', ''), ('CIN', 'PIT'): ('Bengals–Steelers', 'AFC North grudge match'),
       ('KC', 'LV'): ('Chiefs–Raiders', 'AFL originals, hate since 1960'), ('KC', 'DEN'): ('Chiefs–Broncos', 'AFC West'), ('DEN', 'LV'): ('Broncos–Raiders', 'AFC West'),
       ('LAC', 'LV'): ('Chargers–Raiders', 'AFL originals'), ('NE', 'NYJ'): ('Patriots–Jets', 'Border War'), ('NE', 'MIA'): ('Patriots–Dolphins', 'AFC East'), ('BUF', 'MIA'): ('Bills–Dolphins', 'AFC East'),
       ('BUF', 'NE'): ('Bills–Patriots', 'AFC East'), ('NYJ', 'MIA'): ('Jets–Dolphins', 'AFC East'), ('SF', 'SEA'): ('49ers–Seahawks', 'NFC West heavyweight bout'),
       ('SF', 'LAR'): ('49ers–Rams', 'California classic since 1950'), ('SF', 'DAL'): ('49ers–Cowboys', 'The Catch, five NFC title games'), ('GB', 'MIN'): ('Packers–Vikings', 'Border Battle'),
       ('MIN', 'CHI'): ('Vikings–Bears', 'NFC North'), ('DET', 'GB'): ('Lions–Packers', 'NFC North'), ('DET', 'CHI'): ('Lions–Bears', 'NFC North, Thanksgiving regulars'),
       ('NO', 'ATL'): ('Saints–Falcons', 'the Southern rivalry since 1967'), ('TB', 'NO'): ('Buccaneers–Saints', 'NFC South'), ('CAR', 'ATL'): ('Panthers–Falcons', 'NFC South'),
       ('NYG', 'PHI'): ('Giants–Eagles', 'I-95 rivalry'), ('NYG', 'DAL'): ('Giants–Cowboys', 'NFC East'), ('NYG', 'WAS'): ('Giants–Commanders', 'the oldest NFC East rivalry'),
       ('PHI', 'WAS'): ('Eagles–Commanders', 'NFC East'), ('BAL', 'CLE'): ('Ravens–Browns', 'the franchise that moved vs the city it left'), ('IND', 'TEN'): ('Colts–Titans', 'AFC South'),
       ('HOU', 'IND'): ('Texans–Colts', 'AFC South'), ('JAX', 'TEN'): ('Jaguars–Titans', 'AFC South'), ('HOU', 'TEN'): ('Texans–Titans', 'Houston vs the team that left Houston'),
       ('ARI', 'SEA'): ('Cardinals–Seahawks', 'NFC West'), ('ARI', 'SF'): ('Cardinals–49ers', 'NFC West'), ('ARI', 'LAR'): ('Cardinals–Rams', 'NFC West'), ('LAR', 'SEA'): ('Rams–Seahawks', 'NFC West'),
       ('LAC', 'KC'): ('Chargers–Chiefs', 'AFC West'), ('LAC', 'DEN'): ('Chargers–Broncos', 'AFC West'), ('NYJ', 'BUF'): ('Jets–Bills', 'AFC East'),
       ('IND', 'NE'): ('Colts–Patriots', 'Manning–Brady era rivalry'), ('PIT', 'NE'): ('Steelers–Patriots', 'AFC title-game regulars of the 2000s'), ('KC', 'BUF'): ('Chiefs–Bills', 'Mahomes–Allen, four straight postseason meetings'),
       ('GB', 'SEA'): ('Packers–Seahawks', 'Fail Mary, the 2014 NFC title game'), ('MIN', 'NO'): ('Vikings–Saints', 'Bountygate, the Minneapolis Miracle'), ('ATL', 'NE'): ('Falcons–Patriots', '28–3'),
       ('PHI', 'KC'): ('Eagles–Chiefs', 'two Super Bowls in three years'), ('BAL', 'KC'): ('Ravens–Chiefs', 'Jackson vs Mahomes'), ('DET', 'DAL'): ('Lions–Cowboys', 'Thanksgiving hosts'),
       ('DAL', 'GB'): ('Cowboys–Packers', 'Ice Bowl, Dez caught it'), ('SF', 'NYG'): ('49ers–Giants', 'four playoff meetings in the 80s–90s'), ('PHI', 'SF'): ('Eagles–49ers', 'back-to-back NFC title games'),
       ('CIN', 'KC'): ('Bengals–Chiefs', 'Burrow vs Mahomes, two AFC title games'), ('JAX', 'IND'): ('Jaguars–Colts', 'AFC South'), ('CAR', 'NO'): ('Panthers–Saints', 'NFC South'), ('TB', 'ATL'): ('Buccaneers–Falcons', 'NFC South'),
       ('CAR', 'TB'): ('Panthers–Buccaneers', 'NFC South'), ('DET', 'MIN'): ('Lions–Vikings', 'NFC North'), ('HOU', 'JAX'): ('Texans–Jaguars', 'AFC South'), ('BAL', 'CIN'): ('Ravens–Bengals', 'AFC North')}

def key(a, b): return (a, b) if (a, b) in RIV else (b, a)

def main():
    k = pd.read_csv(P + 'kickoffs_2026.csv')
    g = pd.read_csv('data/raw/nflverse/games.csv'); g = g[g.season >= 2024].copy()
    for c in ('away_team', 'home_team'): g[c] = g[c].map(lambda t: FIX.get(t, t))
    g = g[g.away_score.notna()].sort_values(['season', 'week'])
    co = pd.read_csv(P + 'coaching.csv'); co = co[co.season == 2026]
    cn = pd.read_csv(P + 'connections_2026.csv'); cn = cn[cn.type == 'revenge']
    out = []
    def add(wk, game, kind, team, headline, detail, weight):
        out.append(dict(week=wk, game=game, kind=kind, team=team, headline=headline, detail=detail, weight=weight))
    for r in k.itertuples():
        wk, v, h = int(r.week), r.vis, r.home; game = f'{v}@{h}'
        # division + series
        meets = g[((g.away_team == v) & (g.home_team == h)) | ((g.away_team == h) & (g.home_team == v))]
        meets = meets[~((meets.season == 2026) & (meets.week >= wk))]
        wins = {v: 0, h: 0}
        for m in meets.itertuples():
            w = m.away_team if m.away_score > m.home_score else m.home_team if m.home_score > m.away_score else None
            if w: wins[w] += 1
        series = f'{v} {wins[v]}–{wins[h]} {h} since 2024' if len(meets) else 'first meeting since 2024'
        if DIV_OF.get(v) == DIV_OF.get(h):
            add(wk, game, 'division', '', f'{DIV_OF[v]} game', f'{series}', 3)
        kk = key(v, h)
        if kk in RIV:
            nm, note = RIV[kk]; add(wk, game, 'rivalry', '', nm, (note + ' · ' if note else '') + series, 4)
        if len(meets):
            m = meets.iloc[-1]
            w = m.away_team if m.away_score > m.home_score else m.home_team
            post = '' if m.game_type == 'REG' else f' ({m.game_type} playoff game)'
            add(wk, game, 'rematch', w, f'last meeting: {m.away_team} {int(m.away_score)} @ {m.home_team} {int(m.home_score)}', f'{int(m.season)} wk {int(m.week)}{post} · {series}', 2)
            # streak
            last = []
            for x in meets.itertuples():
                last.append(x.away_team if x.away_score > x.home_score else x.home_team if x.home_score > x.away_score else None)
            n = 0
            for x in reversed(last):
                if x == last[-1]: n += 1
                else: break
            if n >= 3 and last[-1]: add(wk, game, 'streak', last[-1], f'{last[-1]} has won {n} straight in the series', '', 2)
            if (meets.game_type != 'REG').any():
                pg = meets[meets.game_type != 'REG'].iloc[-1]
                add(wk, game, 'rematch', '', f'playoff rematch: {pg.away_team} {int(pg.away_score)} @ {pg.home_team} {int(pg.home_score)} ({int(pg.season)} {pg.game_type})', '', 3)
        # coaches facing a former team
        for t, o in ((v, h), (h, v)):
            c = co[co.team == t]
            if not len(c): continue
            c = c.iloc[0]
            for role, name, frm in (('HC', c.hc, c.hc_from), ('OC', c.oc, c.oc_from), ('DC', c.dc, c.dc_from)):
                if not isinstance(frm, str) or not isinstance(name, str): continue
                src = frm.split('@')[-1]
                if src == o:
                    add(wk, game, 'coach', t, f'{name} ({t} {role}) faces {o}, where he was {frm.split("@")[0] if "@" in frm else "on staff"} last season', '', 3)
        # player revenge
        for x in cn[(cn.week == wk) & (cn.game == game)].itertuples():
            add(wk, game, 'revenge', x.team, f'{x.player} ({x.team}) {x.detail}', '', 2)
    df = pd.DataFrame(out).sort_values(['week', 'game', 'weight'], ascending=[True, True, False])
    df.to_csv(P + 'narratives_2026.csv', index=False)
    print(f"narratives_2026.csv: {len(df)} rows · {df.kind.value_counts().to_dict()}")

if __name__ == '__main__':
    main()
