"""Keep data/processed/kickoffs_2026.csv true to the league's current kickoff times.

The kickoff file was written from the schedule release, so a flexed game kept its old window (week 11: PIT@PHI was moved to
1:00 PM but still sat in the 4 PM slate). The newest ESPN scoreboard pull (data/raw/slate_all_<date>.txt, refreshed by the PC
loop) carries the real kickoff of every game in the coming days; this rewrites the date / day / ET time / slate of any game
whose kickoff differs and prints what changed. Rows ESPN does not list are left alone. Run by build_dashboard.py on every build."""
import os, csv, glob, datetime
os.chdir(os.path.join(os.path.dirname(os.path.abspath(__file__)), '..'))
try:
    from zoneinfo import ZoneInfo
    ET = ZoneInfo('America/New_York')
except Exception:
    ET = None
FIX = {'WSH': 'WAS', 'LA': 'LAR', 'JAC': 'JAX'}
KO = 'data/processed/kickoffs_2026.csv'

def slate_of(dt):
    d = dt.strftime('%a'); h = dt.hour + dt.minute / 60
    if d == 'Sun': return 'INTL' if h < 12 else 'EARLY' if h < 15 else 'LATE' if h < 19 else 'SNF'
    if d == 'Mon': return 'MNF'
    if d in ('Thu', 'Wed', 'Tue'): return 'THU' if (d == 'Thu' and h < 19) else 'TNF'
    if d == 'Fri': return 'FRI'
    return 'SAT'

def to_et(iso):
    s = iso.rstrip('Z'); fmt = '%Y-%m-%dT%H:%M' if ':' in s.split('T')[1] else '%Y-%m-%dT%H'
    u = datetime.datetime.strptime(s, fmt).replace(tzinfo=datetime.timezone.utc)
    if ET: return u.astimezone(ET)
    # no tz database: US Eastern by rule (DST from the second Sunday of March to the first Sunday of November)
    y = u.year; mar = datetime.datetime(y, 3, 8, 7, tzinfo=datetime.timezone.utc); mar += datetime.timedelta(days=(6 - mar.weekday()) % 7)
    nov = datetime.datetime(y, 11, 1, 6, tzinfo=datetime.timezone.utc); nov += datetime.timedelta(days=(6 - nov.weekday()) % 7)
    return (u + datetime.timedelta(hours=-4 if mar <= u < nov else -5)).replace(tzinfo=None)

def main(quiet=False):
    files = sorted(glob.glob('data/raw/slate_all_*.txt'))
    if not files or not os.path.exists(KO): return 0
    espn = {}
    for line in open(files[-1], encoding='utf-8'):
        p = line.rstrip('\n').split('|')
        if len(p) < 14 or p[0] != 'G' or p[1] != 'nfl' or 'T' not in p[3]: continue
        try: dt = to_et(p[3])
        except Exception: continue
        espn[(FIX.get(p[6], p[6]), FIX.get(p[12], p[12]), dt.strftime('%Y'))] = dt
    rows = list(csv.DictReader(open(KO, encoding='utf-8'))); cols = list(rows[0].keys()) if rows else []
    changed = []
    for r in rows:
        dt = espn.get((r['vis'], r['home'], r['date'][:4]))
        if dt is None or abs((dt.replace(tzinfo=None) - datetime.datetime.strptime(r['date'], '%Y-%m-%d')).days) > 3: continue   # same matchup, another week
        new = dict(date=dt.strftime('%Y-%m-%d'), day=dt.strftime('%a'), time_et=dt.strftime('%I:%M %p').lstrip('0'), slate=slate_of(dt))
        if any(r[k] != v for k, v in new.items()):
            changed.append(f"wk {r['week']} {r['vis']}@{r['home']}: {r['day']} {r['time_et']} {r['slate']} -> {new['day']} {new['time_et']} {new['slate']}"); r.update(new)
    if changed:
        with open(KO, 'w', newline='', encoding='utf-8') as f:
            w = csv.DictWriter(f, fieldnames=cols); w.writeheader(); w.writerows(rows)
        if not quiet: print(f'kickoffs_2026.csv: {len(changed)} kickoff(s) corrected from {os.path.basename(files[-1])}: ' + ' · '.join(changed))
    elif not quiet: print(f'kickoffs_2026.csv: matches ESPN ({len(espn)} games in {os.path.basename(files[-1])})')
    return len(changed)

if __name__ == '__main__':
    main()
