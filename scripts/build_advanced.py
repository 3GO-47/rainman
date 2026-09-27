"""RAINMAN advanced layer: player usage (snaps / target share / air yards), team scheme tendencies
(offense + defense), data-tagged schemes, starter turnover, coaching changes, scheme x slot effects.

Inputs (data/raw/nflverse/, see fetch_nflverse.py) + data/game_logs/ + data/raw/coordinators.csv
Outputs (data/processed/):
  player_usage.csv        one row per player-game: snaps, snap_pct, targets, target_share, rush_share,
                          air_yards, adot, air_share, wopr            (joins game_logs on season/week/player_id)
  team_off_tendencies.csv one row per season x offense: pass rate, PROE, early-down pass rate, shotgun,
                          under-center, no-huddle, play-action, RPO, motion, screens, aDOT, deep rate,
                          personnel 11/12/21 (2024-25), pace, EPA/success, RB/TE/WR target shares
  team_def_tendencies.csv one row per season x defense: blitz rate, pass rushers, box counts, man/zone,
                          coverage mix (Cover 0/1/2/3/4/6/2-man), single/two-high, base/nickel/dime,
                          pressure, sack rate, EPA/success/explosive allowed, pass rate faced
  scheme_tags.csv         season x team x side: primary tag + descriptors + evidence (numbers + league pct)
  starter_turnover.csv    season x team x side: starters (top-11 by snaps that season) vs prior season,
                          retained / departed / new, turnover %, share of prior-season snaps returning
  coaching.csv            season x team: HC / OC / DC with change flags vs prior season (from PFR)
  scheme_slot_effects.csv coverage-family tag x slot: PPR/game allowed vs league (2024-25 charted seasons)
Every number traces to nflverse pbp/charting/snap files + data/game_logs/. Usage: python3 scripts/build_advanced.py
"""
import os, re, glob, json
import numpy as np, pandas as pd
os.chdir(os.path.join(os.path.dirname(__file__), '..'))
NV = 'data/raw/nflverse'; OUT = 'data/processed'
TEAM_FIX = {'LA': 'LAR', 'WSH': 'WAS', 'JAC': 'JAX', 'OAK': 'LV', 'SD': 'LAC', 'STL': 'LAR'}
T = lambda s: s.map(lambda x: TEAM_FIX.get(x, x) if isinstance(x, str) else x)
SEASONS = sorted(int(re.findall(r'(\d{4})', os.path.basename(f))[0]) for f in glob.glob(f'{NV}/pbp_slim_*.parquet'))

def load(name, s, cols=None):
    p = f'{NV}/{name}_{s}.parquet'
    return pd.read_parquet(p, columns=cols) if os.path.exists(p) else None

def pct_rank(series, higher_is_more=True):
    r = series.rank(pct=True) if higher_is_more else (-series).rank(pct=True)
    return (r * 100).round(0)

# ---------------------------------------------------------------- game logs + snaps -> player usage
def build_usage():
    logs = pd.concat([pd.read_csv(f) for f in sorted(glob.glob('data/game_logs/game_logs_*.csv'))], ignore_index=True)
    snaps = pd.concat([d for d in (load('snap_counts', s) for s in SEASONS) if d is not None], ignore_index=True)
    snaps = snaps[snaps.game_type == 'REG'][['season','week','pfr_player_id','offense_snaps','offense_pct']]
    u = logs.merge(snaps, left_on=['season','week','player_id'], right_on=['season','week','pfr_player_id'], how='left')
    grp = u.groupby(['season','week','team'])
    u['team_targets'] = grp['targets'].transform('sum'); u['team_rush'] = grp['rush_att'].transform('sum')
    u['target_share'] = (u.targets / u.team_targets.replace(0, np.nan)).round(3)
    u['rush_share'] = (u.rush_att / u.team_rush.replace(0, np.nan)).round(3)
    # air yards from pbp via gsis<->pfr crosswalk (rosters); unmapped players stay NaN
    ros = pd.concat([d for d in (load('roster', s, ['gsis_id','pfr_id']) for s in SEASONS) if d is not None]).dropna().drop_duplicates('gsis_id')
    g2p = dict(zip(ros.gsis_id, ros.pfr_id))
    air = []
    for s in SEASONS:
        p = load('pbp_slim', s, ['season','week','posteam','receiver_id','air_yards','pass_attempt'])
        p = p[(p.pass_attempt == 1) & p.receiver_id.notna()]
        a = p.groupby(['season','week','receiver_id']).agg(air_yards=('air_yards','sum')).reset_index()
        a['team_air'] = p.groupby(['season','week','posteam'])['air_yards'].sum().reindex(
            pd.MultiIndex.from_frame(p.drop_duplicates(['season','week','receiver_id'])[['season','week','posteam']])).values if False else np.nan
        air.append(a)
    air = pd.concat(air); air['pfr'] = air.receiver_id.map(g2p)
    u = u.merge(air[['season','week','pfr','air_yards']], left_on=['season','week','player_id'], right_on=['season','week','pfr'], how='left')
    u['team_air'] = u.groupby(['season','week','team'])['air_yards'].transform('sum')
    u['air_share'] = (u.air_yards / u.team_air.replace(0, np.nan)).round(3)
    u['adot'] = (u.air_yards / u.targets.replace(0, np.nan)).round(1)
    u['wopr'] = (1.5 * u.target_share.fillna(0) + 0.7 * u.air_share.fillna(0)).round(3)
    out = u[['season','week','player','player_id','team','opponent','slot','pos','offense_snaps','offense_pct',
             'targets','target_share','rush_att','rush_share','air_yards','air_share','adot','wopr']].rename(
             columns={'offense_snaps':'snaps','offense_pct':'snap_pct'})
    out.to_csv(f'{OUT}/player_usage.csv', index=False)
    print(f'player_usage.csv: {len(out)} rows · snap join {out.snap_pct.notna().mean():.1%} · air-yard join {out.air_yards.notna().mean():.1%}')
    return out

# ---------------------------------------------------------------- personnel parsing helpers
def off_pers(s):
    if not isinstance(s, str): return None
    d = {k: int(v) for v, k in re.findall(r'(\d+) (\w+)', s)}
    rb, te, wr = d.get('RB', 0), d.get('TE', 0), d.get('WR', 0)
    return f'{rb}{te}' if rb + te + wr == 5 else 'other'
def def_dbs(s):
    if not isinstance(s, str): return None
    d = {k: int(v) for v, k in re.findall(r'(\d+) (\w+)', s)}
    return sum(d.get(k, 0) for k in ['CB','FS','SS','S','DB'])
def def_dl(s):
    if not isinstance(s, str): return None
    d = {k: int(v) for v, k in re.findall(r'(\d+) (\w+)', s)}
    return sum(d.get(k, 0) for k in ['DE','DT','NT','DL'])

def plays_frame(s):
    p = load('pbp_slim', s)
    p = p[(p.season_type if 'season_type' in p else p.week <= 18) if False else (p.week <= 18)]
    p = p[(p.special_teams_play == 0) & p.posteam.notna() & ((p['pass'] == 1) | (p['rush'] == 1))].copy()
    p['posteam'] = T(p.posteam); p['defteam'] = T(p.defteam)
    f = load('ftn_charting', s)
    if f is not None:
        f = f.rename(columns={'nflverse_game_id':'game_id','nflverse_play_id':'play_id'})
        p = p.merge(f[['game_id','play_id','n_blitzers','n_pass_rushers','n_defense_box','is_no_huddle','is_motion',
                       'is_play_action','is_screen_pass','is_rpo','qb_location','is_qb_out_of_pocket']], on=['game_id','play_id'], how='left')
    pp = load('pbp_participation', s)
    if pp is not None:
        pp = pp.rename(columns={'nflverse_game_id':'game_id'})
        p = p.merge(pp[['game_id','play_id','offense_personnel','defense_personnel','defenders_in_box','number_of_pass_rushers',
                        'defense_man_zone_type','defense_coverage_type','was_pressure','time_to_throw']], on=['game_id','play_id'], how='left')
        p['op'] = p.offense_personnel.map(off_pers); p['dbs'] = p.defense_personnel.map(def_dbs); p['dl'] = p.defense_personnel.map(def_dl)
    else:
        for c in ['offense_personnel','defense_personnel','defenders_in_box','number_of_pass_rushers','defense_man_zone_type',
                  'defense_coverage_type','was_pressure','time_to_throw','op','dbs','dl']: p[c] = np.nan
    p['neutral'] = (p.wp.between(0.2, 0.8)) & (p.qtr <= 3)
    p['explosive'] = ((p['pass'] == 1) & (p.yards_gained >= 20)) | ((p['rush'] == 1) & (p.yards_gained >= 12))
    p['deep'] = (p.pass_attempt == 1) & (p.air_yards >= 20)
    # seconds per play inside a drive (pace)
    p = p.sort_values(['game_id','play_id'])
    same = (p.game_id == p.game_id.shift()) & (p.fixed_drive == p.fixed_drive.shift())
    p['sec_per_play'] = np.where(same, p.game_seconds_remaining.shift() - p.game_seconds_remaining, np.nan)
    p.loc[(p.sec_per_play <= 0) | (p.sec_per_play > 60), 'sec_per_play'] = np.nan
    return p

def rate(x): return round(float(np.nanmean(x)), 3) if len(x) and np.isfinite(np.nanmean(x)) else np.nan

def build_tendencies(usage):
    offs, defs = [], []
    for s in SEASONS:
        p = plays_frame(s)
        db = p[p['pass'] == 1]
        for team, g in p.groupby('posteam'):
            d = g[g['pass'] == 1]; n = g[g.neutral]
            tg = usage[(usage.season == s) & (usage.team == team)]
            tt = tg.targets.sum() or np.nan
            row = dict(season=s, team=team, games=g.game_id.nunique(), plays=len(g), plays_per_game=round(len(g)/g.game_id.nunique(),1),
                pass_rate=rate(g['pass']), neutral_pass_rate=rate(n['pass']), early_down_pass_rate=rate(n[n.down <= 2]['pass']),
                proe=round(float(np.nanmean(g.pass_oe)), 1), shotgun_rate=rate(g.shotgun), no_huddle_rate=rate(g.no_huddle),
                under_center_rate=rate(g.qb_location.isin(['U']) if 'qb_location' in g else np.nan) if g.qb_location.notna().any() else np.nan,
                play_action_rate=rate(d.is_play_action), rpo_rate=rate(g.is_rpo), motion_rate=rate(g.is_motion),
                screen_rate=rate(d.is_screen_pass), adot=round(float(np.nanmean(d[d.pass_attempt==1].air_yards)),1), deep_rate=rate(d[d.pass_attempt==1].deep),
                sec_per_play=round(float(np.nanmedian(n.sec_per_play)),1), epa_play=round(float(g.epa.mean()),3), success_rate=rate(g.success),
                pass_epa=round(float(d.epa.mean()),3), rush_epa=round(float(g[g['rush']==1].epa.mean()),3), explosive_rate=rate(g.explosive),
                rz_pass_rate=rate(g[g.yardline_100 <= 20]['pass']),
                p11=rate(g.op == '11') if g.op.notna().any() else np.nan, p12=rate(g.op == '12') if g.op.notna().any() else np.nan,
                p21=rate(g.op == '21') if g.op.notna().any() else np.nan, p13=rate(g.op == '13') if g.op.notna().any() else np.nan,
                heavy_pers=rate(g.op.isin(['12','13','21','22'])) if g.op.notna().any() else np.nan,
                rb_tgt_share=round(tg[tg.pos=='RB'].targets.sum()/tt,3), te_tgt_share=round(tg[tg.pos=='TE'].targets.sum()/tt,3),
                wr_tgt_share=round(tg[tg.pos=='WR'].targets.sum()/tt,3))
            offs.append(row)
        for team, g in p.groupby('defteam'):
            d = g[g['pass'] == 1]; cov = d.defense_coverage_type.dropna(); mz = d.defense_man_zone_type.replace('', np.nan).dropna()
            ncov = len(cov) or np.nan; nmz = len(mz) or np.nan
            cv = lambda k: round(float((cov == k).sum()/ncov), 3) if ncov == ncov else np.nan
            row = dict(season=s, team=team, games=g.game_id.nunique(), plays=len(g), pass_rate_faced=rate(g['pass']),
                blitz_rate=rate(d.n_pass_rushers >= 5) if d.n_pass_rushers.notna().any() else np.nan,
                heavy_blitz_rate=rate(d.n_pass_rushers >= 6) if d.n_pass_rushers.notna().any() else np.nan,
                avg_pass_rushers=round(float(np.nanmean(d.n_pass_rushers)),2), avg_box=round(float(np.nanmean(g.n_defense_box)),2),
                light_box_rate=rate(g[g['rush']==1].n_defense_box <= 6), stacked_box_rate=rate(g[g['rush']==1].n_defense_box >= 8),
                man_rate=round(float((mz=='MAN_COVERAGE').sum()/nmz),3) if nmz == nmz else np.nan,
                zone_rate=round(float((mz=='ZONE_COVERAGE').sum()/nmz),3) if nmz == nmz else np.nan,
                cover0=cv('COVER_0'), cover1=cv('COVER_1'), cover2=cv('COVER_2'), cover3=cv('COVER_3'), cover4=cv('COVER_4'),
                cover6=cv('COVER_6'), two_man=cv('2_MAN'), cover_other=cv('COVER_9') if ncov == ncov else np.nan,
                single_high=round(cv('COVER_1')+cv('COVER_3'),3) if ncov == ncov else np.nan,
                two_high=round(cv('COVER_2')+cv('COVER_4')+cv('COVER_6')+cv('2_MAN'),3) if ncov == ncov else np.nan,
                base_rate=rate(g.dbs <= 4) if g.dbs.notna().any() else np.nan, nickel_rate=rate(g.dbs == 5) if g.dbs.notna().any() else np.nan,
                dime_rate=rate(g.dbs >= 6) if g.dbs.notna().any() else np.nan, four_down_rate=rate(g.dl >= 4) if g.dl.notna().any() else np.nan,
                pressure_rate=rate(d.was_pressure) if d.was_pressure.notna().any() else np.nan,
                sack_rate=rate(d.sack), int_rate=rate(d.interception), epa_play_allowed=round(float(g.epa.mean()),3),
                pass_epa_allowed=round(float(d.epa.mean()),3), rush_epa_allowed=round(float(g[g['rush']==1].epa.mean()),3),
                success_allowed=rate(g.success), explosive_allowed=rate(g.explosive), adot_faced=round(float(np.nanmean(d[d.pass_attempt==1].air_yards)),1),
                coverage_charted=bool(ncov == ncov))
            defs.append(row)
    off = pd.DataFrame(offs); de = pd.DataFrame(defs)
    off.to_csv(f'{OUT}/team_off_tendencies.csv', index=False); de.to_csv(f'{OUT}/team_def_tendencies.csv', index=False)
    print(f'team_off_tendencies: {len(off)} · team_def_tendencies: {len(de)} · coverage charted seasons: {sorted(de[de.coverage_charted].season.unique())}')
    return off, de

# ---------------------------------------------------------------- scheme tags (rules -> tag + evidence)
def pctl(df, col, val, higher=True):
    s = df[col].dropna()
    if not len(s) or val != val: return None
    return int(round(100 * ((s < val).mean() if higher else (s > val).mean())))

COV_COLS = ['man_rate','zone_rate','cover0','cover1','cover2','cover3','cover4','cover6','two_man','single_high','two_high',
            'base_rate','nickel_rate','dime_rate','four_down_rate','pressure_rate']
def tag_defense(row, season_df, prev_row=None, dc_same=None, dc_from_row=None, dc_from=''):
    tags, ev = [], []
    r = row.copy()
    cov_src = None
    if r.get('coverage_charted') is not True or r.get('two_high') != r.get('two_high'):
        if dc_same is False and dc_from_row is not None and dc_from_row.get('coverage_charted'):
            for c in COV_COLS: r[c] = dc_from_row[c]
            cov_src = f'{int(dc_from_row["season"])} charting of new DC\'s prior unit ({dc_from})'
        elif prev_row is not None and prev_row.get('coverage_charted'):
            for c in COV_COLS: r[c] = prev_row[c]
            cov_src = f'{int(prev_row["season"])} charting' + (' · same DC' if dc_same else ' · NEW DC (no prior DC unit charted) — verify' if dc_same is False else '')
    th, sh, man, zone = r.get('two_high'), r.get('single_high'), r.get('man_rate'), r.get('zone_rate')
    c3, c2, c4, c6, tm, c1, c0 = ((r.get(k) or 0) for k in ['cover3','cover2','cover4','cover6','two_man','cover1','cover0'])
    if th == th:
        shells = {'Single-high Cover-3 zone (Seattle/Saleh tree)': c3, 'Cover-1 man / single-high pressure looks': c1 + c0,
                  'Two-high quarters & match (Cover-4/6)': c4 + c6, 'Two-high Cover-2 / Tampa-2': c2 + tm}
        fam, share = max(shells.items(), key=lambda kv: kv[1])
        if man >= 0.40: fam = 'Man-heavy · Cover-1 press'
        elif th >= 0.50 and zone >= 0.65: fam = 'Two-high zone shell (Fangio/Staley tree)'
        tags.append(fam)
        mix = 'multiple / disguise' if share < 0.36 and man < 0.40 else 'committed shell'
        tags.append(mix)
        ev.append(f'2-high {th:.0%} · 1-high {sh:.0%} · man {man:.0%} zone {zone:.0%} · C3 {c3:.0%} C1 {c1:.0%} C2 {c2:.0%} C4 {c4:.0%} C6 {c6:.0%} 2M {tm:.0%} C0 {c0:.0%}' + (f' [{cov_src}]' if cov_src else ''))
    else:
        tags.append('Coverage not yet charted')
    b = r.get('blitz_rate')
    if b == b:
        pr = pctl(season_df, 'blitz_rate', b)
        tags.append('Blitz-heavy' if b >= 0.32 else 'Four-man rush' if b <= 0.20 else 'Situational pressure')
        ev.append(f'blitz (5+ rushers) {b:.0%} (lg pct {pr}) · avg rushers {r.get("avg_pass_rushers")}' + (f' · pressure {r["pressure_rate"]:.0%}' if r.get('pressure_rate') == r.get('pressure_rate') else ''))
    bx = r.get('avg_box')
    if bx == bx:
        tags.append('Heavy boxes' if bx >= 6.9 else 'Light boxes' if bx <= 6.3 else 'Neutral boxes')
        ev.append(f'avg box {bx} · light-box vs run {r.get("light_box_rate"):.0%} · stacked {r.get("stacked_box_rate"):.0%}')
    nk, dm, bs = r.get('nickel_rate'), r.get('dime_rate'), r.get('base_rate')
    if nk == nk:
        tags.append('Dime-heavy' if dm >= 0.25 else 'Base-heavy' if bs >= 0.35 else 'Nickel base')
        ev.append(f'base {bs:.0%} / nickel {nk:.0%} / dime {dm:.0%} · 4-down front {r.get("four_down_rate"):.0%}')
    ev.append(f'EPA/play allowed {r.get("epa_play_allowed")} (pass {r.get("pass_epa_allowed")} / rush {r.get("rush_epa_allowed")}) · success {r.get("success_allowed"):.0%} · explosive {r.get("explosive_allowed"):.0%} · sack {r.get("sack_rate"):.1%}')
    return tags[0], ' · '.join(tags[1:]), ' | '.join(ev), cov_src

def tag_offense(row, season_df):
    r = row; tags, ev = [], []
    pr = r.get('proe')
    tags.append('Pass-first (PROE +)' if pr >= 3 else 'Run-first (PROE −)' if pr <= -3 else 'Balanced call sheet')
    ev.append(f'PROE {pr:+.1f} · pass {r.get("pass_rate"):.0%} (neutral {r.get("neutral_pass_rate"):.0%}, early-down {r.get("early_down_pass_rate"):.0%})')
    pa, uc, sg, rpo, mo, nh = (r.get(k) for k in ['play_action_rate','under_center_rate','shotgun_rate','rpo_rate','motion_rate','no_huddle_rate'])
    style = []
    if pa == pa:
        P = lambda col, v, hi=True: pctl(season_df, col, v, hi) or 50
        shan = np.mean([P('play_action_rate', pa), P('under_center_rate', uc), P('motion_rate', mo)])
        spread = np.mean([P('shotgun_rate', sg), P('rpo_rate', rpo), P('no_huddle_rate', nh)])
        air = np.mean([P('adot', r.get('adot')), P('deep_rate', r.get('deep_rate'))])
        tree = max([('Under-center play-action / wide-zone (Shanahan–McVay tree)', shan), ('Shotgun spread / RPO (spread tree)', spread),
                    ('Vertical dropback passing (Coryell/Reid tree)', air)], key=lambda kv: kv[1])
        style.append(tree[0])
        for col, v, lab, hi in [('play_action_rate', pa, 'play-action heavy', True), ('motion_rate', mo, 'motion-heavy', True), ('rpo_rate', rpo, 'RPO-heavy', True),
                                ('no_huddle_rate', nh, 'up-tempo', True), ('screen_rate', r.get('screen_rate'), 'screen game', True), ('deep_rate', r.get('deep_rate'), 'vertical', True),
                                ('adot', r.get('adot'), 'quick game', False), ('sec_per_play', r.get('sec_per_play'), 'slow pace', True)]:
            if v == v and P(col, v, hi) >= 78: style.append(lab)
        ev.append(f'PA {pa:.0%} · under-center {uc:.0%} · shotgun {sg:.0%} · RPO {rpo:.0%} · motion {mo:.0%} · no-huddle {nh:.0%} · screens {r.get("screen_rate"):.0%} · tree scores shan {shan:.0f}/spread {spread:.0f}/air {air:.0f}')
    p11, hv = r.get('p11'), r.get('heavy_pers')
    if p11 == p11:
        style.append('11-personnel base' if p11 >= 0.72 else '12/13/21 heavy personnel' if hv >= 0.35 else 'mixed personnel')
    else:
        style.append('personnel (2026) pending')
        ev.append(f'11 {p11:.0%} · 12 {r.get("p12"):.0%} · 21 {r.get("p21"):.0%} · 13 {r.get("p13"):.0%}')
    ev.append(f'aDOT {r.get("adot")} · deep {r.get("deep_rate"):.0%} · pace {r.get("sec_per_play")}s/play · {r.get("plays_per_game")} plays/gm · EPA/play {r.get("epa_play")} · success {r.get("success_rate"):.0%}')
    ev.append(f'target shares — WR {r.get("wr_tgt_share"):.0%} · TE {r.get("te_tgt_share"):.0%} · RB {r.get("rb_tgt_share"):.0%}')
    return tags[0], ' · '.join(style), ' | '.join(ev)

def build_tags(off, de, coaching):
    rows = []
    for s in SEASONS:
        ds = de[de.season == s]; os_ = off[off.season == s]; dp = de[de.season == s - 1].set_index('team')
        for _, r in ds.iterrows():
            prev = dp.loc[r.team].to_dict() if r.team in dp.index else None
            c = coaching[(coaching.season == s) & (coaching.team == r.team)]
            dc_same = (not bool(c.dc_changed.iloc[0])) if len(c) and c.dc_changed.notna().iloc[0] else None
            dc_from = c.dc_from.iloc[0] if len(c) else ''
            from_row = dp.loc[dc_from].to_dict() if dc_from in dp.index else None
            t1, t2, ev, src = tag_defense(r.to_dict(), ds, prev, dc_same, from_row, dc_from)
            rows.append(dict(season=s, team=r.team, side='DEF', primary_tag=t1, descriptors=t2, evidence=ev, coverage_source=src or (f'{s} charting' if r.coverage_charted else ''),
                             coach=c.dc.iloc[0] if len(c) else '', coach_changed=bool(c.dc_changed.iloc[0]) if len(c) and c.dc_changed.notna().iloc[0] else None, coach_from=dc_from))
        for _, r in os_.iterrows():
            t1, t2, ev = tag_offense(r.to_dict(), os_)
            c = coaching[(coaching.season == s) & (coaching.team == r.team)]
            rows.append(dict(season=s, team=r.team, side='OFF', primary_tag=t1, descriptors=t2, evidence=ev, coverage_source='',
                             coach=c.oc.iloc[0] if len(c) else '', coach_changed=bool(c.oc_changed.iloc[0]) if len(c) and c.oc_changed.notna().iloc[0] else None, coach_from=c.oc_from.iloc[0] if len(c) else ''))
    df = pd.DataFrame(rows); df.to_csv(f'{OUT}/scheme_tags.csv', index=False)
    print(f'scheme_tags: {len(df)} rows'); return df

# ---------------------------------------------------------------- starter turnover
def build_turnover():
    snaps = pd.concat([d for d in (load('snap_counts', s) for s in SEASONS) if d is not None], ignore_index=True)
    snaps = snaps[snaps.game_type == 'REG'].copy(); snaps['team'] = T(snaps.team)
    ros = {}
    for s in SEASONS:
        r = load('roster', s, ['team','pfr_id','full_name','position','rookie_year'])
        if r is not None:
            r = r.dropna(subset=['pfr_id']).drop_duplicates('pfr_id'); r['team'] = T(r.team); ros[s] = r.set_index('pfr_id')
    rows = []
    for side, pc, sc in [('DEF','defense_pct','defense_snaps'), ('OFF','offense_pct','offense_snaps')]:
        per = snaps.groupby(['season','team','pfr_player_id']).agg(player=('player','first'), position=('position','first'),
              games=('week','nunique'), starts=(pc, lambda x: int((x >= 0.5).sum())), snaps=(sc,'sum')).reset_index()
        tg = snaps.groupby(['season','team'])['week'].nunique().rename('team_games').reset_index()
        per = per.merge(tg, on=['season','team']); per = per[per.snaps > 0]
        per['rk'] = per.groupby(['season','team'])['snaps'].rank(ascending=False, method='first')
        per['starter'] = per.rk <= 11
        for s in SEASONS[1:]:
            cur = per[per.season == s]; prv = per[per.season == s - 1]
            for team in sorted(cur.team.unique()):
                c = cur[cur.team == team]; p = prv[prv.team == team]
                cs = c[c.starter]; ps = p[p.starter]
                cur_ids, prv_ids = set(cs.pfr_player_id), set(ps.pfr_player_id)
                retained = cur_ids & prv_ids; departed = prv_ids - cur_ids; new = cur_ids - prv_ids
                still_on_team = set(c.pfr_player_id)
                dep = []
                for pid in departed:
                    nm = ps[ps.pfr_player_id == pid].iloc[0]
                    where = 'bench/injured' if pid in still_on_team else (ros.get(s, pd.DataFrame()).team.get(pid, 'left NFL/FA') if s in ros else '?')
                    dep.append(f'{nm.player} ({nm.position}, {int(nm.snaps)} snaps → {where})')
                nw = []
                for pid in new:
                    nm = cs[cs.pfr_player_id == pid].iloc[0]
                    src = prv[prv.pfr_player_id == pid]
                    frm = src.team.iloc[0] if len(src) and src.team.iloc[0] != team else ('promoted' if pid in set(p.pfr_player_id) else
                          ('rookie' if s in ros and pid in ros[s].index and ros[s].loc[pid].rookie_year == s else 'other'))
                    nw.append(f'{nm.player} ({nm.position}, {frm})')
                prev_snaps_total = p.snaps.sum(); returning = p[p.pfr_player_id.isin(still_on_team)].snaps.sum()
                rows.append(dict(season=s, team=team, side=side, prev_starters=len(prv_ids), cur_starters=len(cur_ids), retained=len(retained),
                    turnover_pct=round(1 - len(retained)/len(prv_ids), 3) if prv_ids else np.nan,
                    prev_snaps_returning_pct=round(returning/prev_snaps_total, 3) if prev_snaps_total else np.nan,
                    departed='; '.join(sorted(dep)), new_starters='; '.join(sorted(nw)),
                    cur_starter_names='; '.join(f'{r.player} ({r.position})' for _, r in cs.sort_values('snaps', ascending=False).iterrows())))
    df = pd.DataFrame(rows); df.to_csv(f'{OUT}/starter_turnover.csv', index=False)
    print(f'starter_turnover: {len(df)} rows · 2026 DEF median turnover {df[(df.season==max(SEASONS))&(df.side=="DEF")].turnover_pct.median():.0%}')
    return df

# ---------------------------------------------------------------- coaching (PFR team pages, scraped via Chrome)
def build_coaching():
    p = 'data/raw/coordinators.csv'
    if not os.path.exists(p):
        print('coaching: data/raw/coordinators.csv missing — skipped'); return pd.DataFrame(columns=['season','team','hc','oc','dc','hc_changed','oc_changed','dc_changed'])
    c = pd.read_csv(p).sort_values(['team','season'])
    key = lambda n: re.split(r'[/(]', str(n))[0].strip().lower()
    for k in ['hc','oc','dc']:
        c[f'{k}_prev'] = c.groupby('team')[k].shift()
        c[f'{k}_changed'] = np.where(c[f'{k}_prev'].isna(), np.nan, (c[k].map(key) != c[f'{k}_prev'].map(key)).astype(float))
        # where did the new coordinator come from (same role, prior season, any team)?
        prior = {(int(r.season) + 1, key(r[k])): r.team for _, r in c.iterrows()}
        prior_hc = {(int(r.season) + 1, key(r.hc)): r.team for _, r in c.iterrows()}
        c[f'{k}_from'] = [('' if ch != 1 else prior.get((int(sn), key(nm))) or (('HC@' + prior_hc[(int(sn), key(nm))]) if (int(sn), key(nm)) in prior_hc else 'new/promoted'))
                          for sn, nm, ch in zip(c.season, c[k], c[f'{k}_changed'])]
    c.to_csv(f'{OUT}/coaching.csv', index=False)
    cur = c[c.season == c.season.max()]
    print(f'coaching: {len(c)} rows · {int(cur.dc_changed.sum())} new DCs, {int(cur.oc_changed.sum())} new OCs, {int(cur.hc_changed.sum())} new HCs in {int(c.season.max())}')
    return c

# ---------------------------------------------------------------- scheme family x slot effects
def build_scheme_slot(tags):
    logs = pd.concat([pd.read_csv(f) for f in sorted(glob.glob('data/game_logs/game_logs_*.csv'))], ignore_index=True)
    fam = tags[(tags.side == 'DEF') & (~tags.primary_tag.str.startswith('Coverage not')) & (tags.coverage_source.str.match(r'^\d{4} charting$'))]
    fam = fam[['season','team','primary_tag']].rename(columns={'team':'opponent','primary_tag':'family'})
    SLOTG = lambda s: 'QB' if s.startswith('QB') else ('RB1' if s == 'RB1' else 'RB2' if s.startswith('RB') or s.startswith('FB') else
             s if s in ('WR1','WR2','WR3') else 'WR4+' if s.startswith('WR') else 'TE1' if s == 'TE1' else 'TE2' if s.startswith('TE') else '')
    logs['grp'] = logs.slot.map(SLOTG)
    per = logs.groupby(['season','week','team','opponent','grp'])['fantasy_pts_ppr'].sum().reset_index()
    lg = per.groupby(['season','grp']).fantasy_pts_ppr.mean().rename('lg').reset_index()
    per = per.merge(fam, on=['season','opponent']).merge(lg, on=['season','grp'])
    out = per.groupby(['family','grp']).agg(ppr_allowed=('fantasy_pts_ppr','mean'), lg_avg=('lg','mean'), games=('fantasy_pts_ppr','size')).reset_index()
    out['index'] = (100 * out.ppr_allowed / out.lg_avg).round(0); out['ppr_allowed'] = out.ppr_allowed.round(2); out['lg_avg'] = out.lg_avg.round(2)
    out = out[out.grp != '']
    out.to_csv(f'{OUT}/scheme_slot_effects.csv', index=False)
    print(f'scheme_slot_effects: {len(out)} cells over {per.drop_duplicates(["season","week","team"]).shape[0]} team-games'); return out

if __name__ == '__main__':
    usage = build_usage()
    off, de = build_tendencies(usage)
    coaching = build_coaching()
    tags = build_tags(off, de, coaching)
    build_turnover()
    build_scheme_slot(tags)
