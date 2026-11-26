"""v77 — slate chips: the Wednesday game gets its own WED chip, and a Thursday with more than one game (Thanksgiving) is one
THU chip holding all of that day's games. A lone Thursday night game is still TNF. The grouping itself is in
update_kickoffs.regroup (shared with build_kickoffs); this only teaches the page the new chip. Rerunnable."""
import os, sys
os.chdir(os.path.join(os.path.dirname(os.path.abspath(__file__)), '..'))
P = 'scripts/dashboard_template.html'
s = open(P, encoding='utf-8').read()
if '/* v77 */' in s:
    print('v77 already applied'); sys.exit(0)
def rep(old, new, n=1):
    global s
    assert s.count(old) == n, (s.count(old), old[:110])
    s = s.replace(old, new)
rep("const SLATE_LBL=LG.slateLbl||{TNF:'TNF',THU:'THU DAY',", "/* v77 */const SLATE_LBL=LG.slateLbl||{WED:'WED',TNF:'TNF',THU:'THU',")
rep("const SLATE_TIP=LG.slateTip||{TNF:'Thursday night (incl. the Wednesday opener)',THU:'Thanksgiving-day afternoon games',",
    "const SLATE_TIP=LG.slateTip||{WED:'Wednesday game',TNF:'Thursday night',THU:'Every Thursday game when there is more than one (Thanksgiving)',")
rep("const SLATE_ORDER=LG.slateOrder||['TNF','THU',", "const SLATE_ORDER=LG.slateOrder||['WED','TNF','THU',")
rep("const SLATE_C=LG.slateColor||{TNF:'#c39bff',", "const SLATE_C=LG.slateColor||{WED:'#f78fd6',TNF:'#c39bff',")
rep("['slate chips','TNF / SUN 1P / SUN 4P / SNF / MNF etc.", "['slate chips','WED / TNF / THU / SUN 1P / SUN 4P / SNF / MNF etc.")
open(P, 'w', encoding='utf-8').write(s); print('v77 applied')
