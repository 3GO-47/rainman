"""v75b — the depth mark must not cost any names: it is 11px and sits partly in the cell's left padding, and at four-across
(1900px+) the RB table's name column takes 2 points from its opponent column, which had room to spare. Same names fit as
before the mark. Rerunnable."""
import os, sys
os.chdir(os.path.join(os.path.dirname(os.path.abspath(__file__)), '..'))
P = 'scripts/dashboard_template.html'
s = open(P, encoding='utf-8').read()
if '/* v75b */' in s:
    print('v75b already applied'); sys.exit(0)
assert s.count('</style>') == 1
s = s.replace('</style>', """/* v75b */#labgrid .dsl{width:11px;margin-left:-3px;margin-right:3px}
@media(min-width:1900px){#lgBRB col:nth-child(1){width:29%!important}#lgBRB col:nth-child(2){width:13%!important}}
</style>""")
open(P, 'w', encoding='utf-8').write(s); print('v75b applied')
