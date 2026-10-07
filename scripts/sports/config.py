"""League configs for the non-NFL Layer-1 dashboards (NBA, WNBA, NHL). Data = sportsdataverse GitHub release parquets
(ESPN-sourced for basketball, api-web.nhle.com-sourced for hockey), refreshed daily by their GitHub Actions and reachable
from the sandbox without a browser: https://github.com/sportsdataverse/sportsdataverse-data/releases/download/<tag>/<file>
Season naming follows sportsdataverse: the season is named by its END year (2026 = 2025-26)."""
REL = 'https://github.com/sportsdataverse/sportsdataverse-data/releases/download'

# stat definitions: key, label, decimals, pandas column (or callable on the frame)
BASKETBALL_STATS = [
    ('pts', 'PTS', 1, 'points'), ('reb', 'REB', 1, 'rebounds'), ('ast', 'AST', 1, 'assists'), ('tpm', '3PM', 1, 'three_point_field_goals_made'),
    ('stl', 'STL', 1, 'steals'), ('blk', 'BLK', 1, 'blocks'), ('tov', 'TOV', 1, 'turnovers'), ('fga', 'FGA', 1, 'field_goals_attempted'),
    ('fta', 'FTA', 1, 'free_throws_attempted'), ('min', 'MIN', 1, 'minutes'),
    ('pra', 'P+R+A', 1, lambda d: d.points + d.rebounds + d.assists), ('pr', 'P+R', 1, lambda d: d.points + d.rebounds),
    ('pa', 'P+A', 1, lambda d: d.points + d.assists), ('ra', 'R+A', 1, lambda d: d.rebounds + d.assists)]
BASKETBALL_MARKETS = ['pts', 'reb', 'ast', 'tpm', 'pra', 'pr', 'pa', 'ra', 'stl', 'blk']   # the markets books post
BASKETBALL_SLOTS = ['G', 'F', 'C']   # ESPN box scores carry G / F / C
BASKETBALL_POS = {'PG': 'G', 'SG': 'G', 'G': 'G', 'SF': 'F', 'PF': 'F', 'F': 'F', 'GF': 'F', 'G-F': 'F', 'FC': 'C', 'F-C': 'C', 'C': 'C'}

HOCKEY_STATS = [
    ('g', 'G', 2, 'goals'), ('a', 'A', 2, 'assists'), ('p', 'PTS', 2, 'points'), ('sog', 'SOG', 1, 'shots_on_goal'), ('blk', 'BLK', 1, 'blocked_shots'),
    ('hit', 'HIT', 1, 'hits'), ('pim', 'PIM', 1, 'pim'), ('ppg', 'PPG', 2, 'power_play_goals'), ('toi', 'TOI', 1, 'toi_min'),
    ('sv', 'SV', 1, 'saves'), ('ga', 'GA', 2, 'goals_against'), ('sa', 'SA', 1, 'shots_against')]
HOCKEY_MARKETS = ['sog', 'p', 'g', 'a', 'blk', 'hit', 'sv', 'ga']
HOCKEY_SLOTS = ['C', 'W', 'D', 'G']
HOCKEY_POS = {'C': 'C', 'L': 'W', 'R': 'W', 'W': 'W', 'LW': 'W', 'RW': 'W', 'D': 'D', 'G': 'G'}

LEAGUES = {
    'nba': dict(label='NBA', sport='basketball', seasons=[2025, 2026, 2027], current=2027, logo='https://a.espncdn.com/i/teamlogos/leagues/500-dark/nba.png',
                files=dict(box='espn_nba_player_boxscores/player_box_{y}.parquet', sched='espn_nba_schedules/nba_schedule_{y}.parquet', team='espn_nba_team_boxscores/team_box_{y}.parquet'),
                stats=BASKETBALL_STATS, markets=BASKETBALL_MARKETS, slots=BASKETBALL_SLOTS, posmap=BASKETBALL_POS, slate_key='nba',
                margin_sd=12.0, home_edge=2.5, min_games_current=10, rotation=8, tv=True),
    'wnba': dict(label='WNBA', sport='basketball', seasons=[2025, 2026], current=2026, logo='https://a.espncdn.com/i/teamlogos/leagues/500-dark/wnba.png',
                 files=dict(box='espn_wnba_player_boxscores/player_box_{y}.parquet', sched='espn_wnba_schedules/wnba_schedule_{y}.parquet', team='espn_wnba_team_boxscores/team_box_{y}.parquet'),
                 stats=BASKETBALL_STATS, markets=BASKETBALL_MARKETS, slots=BASKETBALL_SLOTS, posmap=BASKETBALL_POS, slate_key='wnba',
                 margin_sd=11.0, home_edge=2.0, min_games_current=8, rotation=8, tv=True),
    'nhl': dict(label='NHL', sport='hockey', seasons=[2025, 2026, 2027], current=2027, logo='https://a.espncdn.com/i/teamlogos/leagues/500-dark/nhl.png',
                files=dict(box='nhl_player_boxscores/player_box_{y}.parquet', sched='nhl_schedules/nhl_schedule_{y}.parquet', team='nhl_team_boxscores/team_box_{y}.parquet'),
                stats=HOCKEY_STATS, markets=HOCKEY_MARKETS, slots=HOCKEY_SLOTS, posmap=HOCKEY_POS, slate_key='nhl',
                margin_sd=1.9, home_edge=0.2, min_games_current=8, rotation=12, tv=True)}
