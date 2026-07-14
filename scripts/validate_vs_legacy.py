"""Validate computed 2025 DvP weekly numbers against the legacy NFLLLLL.xlsx Data tab.

Usage: python3 validate_vs_legacy.py [DEF1 DEF2 ...]   (default: ARI ATL BAL KC SF)
Writes notes/validation_2025.md
"""
import sys
import openpyxl, pandas as pd

STAT_COLS = ['QB PY','P TD','QB RY','RB1 RY','RB2+ RY','WR RY','RB1 Recep','RB1 RecY',
 'RB2 Recep','RB2 RecY','WR1 Recep','WR1 RecY','WR2 Recep','WR2 RecY','WR3 Recep','WR3 RecY',
 'WR4+ Recep','WR4+ RecY','TE1 Recep','TE1 RecY','TE2 Recep','TE2 RecY','QB TD','RB1 TD',
 'RB2 TD','WR1 TD','WR2 TD','WR3 TD','WR4+ TD','TE1 TD','TE2 TD','D/ST TD','QB P+R','RB R+R']

def load_legacy():
    wb = openpyxl.load_workbook('NFLLLLL.xlsx', read_only=True, data_only=True)
    ws = wb['Data']
    data = list(ws.iter_rows(values_only=True))
    wb.close()
    blocks = {}
    i = 0
    while i < len(data):
        row = data[i]
        if row[0] and (i+1 < len(data)) and data[i+1][0] == 'Opp':
            team = str(row[0]).strip()
            hdr = [str(c).strip() for c in data[i+1] if c is not None]
            rows = []
            j = i + 2
            while j < len(data) and data[j][0] not in (None, '') and str(data[j][1]).strip() not in ('', 'None'):
                r = data[j]
                if str(r[1]).strip() == 'Average': break
                rows.append(r)
                j += 1
            blocks[team] = (hdr, rows)
            i = j
        else:
            i += 1
    return blocks

def main(defenses):
    legacy = load_legacy()
    mine = pd.read_csv('data/processed/dvp_weekly.csv')
    mine = mine[mine.season == 2025]
    lines = ['# 2025 DvP validation vs legacy NFLLLLL.xlsx Data tab', '',
             'Comparison grain: defense x week x 34 stat columns. Legacy BYE rows skipped.', '']
    grand_cells = grand_exact = 0
    for d in defenses:
        hdr, rows = legacy[d]
        col_ix = {c: hdr.index(c) for c in STAT_COLS if c in hdr}
        md = mine[mine.defense == d].set_index('week')
        cells = exact = 0
        diffs = []
        for r in rows:
            wk = r[1]
            if str(r[0]).strip() == 'BYE' or wk is None: continue
            wk = int(wk)
            if wk not in md.index: continue
            for c, ix in col_ix.items():
                lv = r[ix]
                if lv in (None, 'N/A', ''): continue
                try: lv = float(lv)
                except (TypeError, ValueError): continue
                mv = float(md.loc[wk, c])
                cells += 1
                if abs(lv - mv) < 0.001: exact += 1
                else: diffs.append((wk, c, lv, mv))
        grand_cells += cells; grand_exact += exact
        pct = 100.0 * exact / cells if cells else 0
        lines.append(f'## {d}: {exact}/{cells} cells exact ({pct:.1f}%)')
        diffs.sort(key=lambda x: -abs(x[2]-x[3]))
        for wk, c, lv, mv in diffs[:12]:
            lines.append(f'- wk{wk} {c}: legacy={lv:g} ours={mv:g} (diff {mv-lv:+g})')
        if len(diffs) > 12: lines.append(f'- ... and {len(diffs)-12} more')
        lines.append('')
    pct = 100.0 * grand_exact / grand_cells if grand_cells else 0
    lines.insert(3, f'**Overall: {grand_exact}/{grand_cells} cells exact ({pct:.1f}%)**')
    lines += ['', '## Known causes of differences',
      '- Slot attribution: legacy used hand-maintained weekly depth charts; RAINMAN ranks players',
      '  by cumulative usage through the current week (see notes/slot_method.md). Totals across',
      '  a position group (e.g. QB PY, RB R+R, WR RY) should match almost exactly; per-slot splits',
      '  (RB1 vs RB2+, WR1 vs WR2...) can differ where the two methods disagree on slot.',
      '- Legacy hand-entry errors are possible; PFR box scores are the source of truth here.']
    open('notes/validation_2025.md', 'w', encoding='utf-8').write('\n'.join(lines))
    print('\n'.join(lines[:40]))

if __name__ == '__main__':
    main(sys.argv[1:] or ['ARI','ATL','BAL','KC','SF'])
