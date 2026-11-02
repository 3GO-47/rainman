"""v58 — META / META v2: no floating headers. Section titles and column headers are static (scroll with the table)."""
import sys
P='scripts/dashboard_template.html'; s=open(P,encoding='utf-8').read()
if '/* v58 */' in s: print('v58 already applied'); sys.exit(0)
css="/* v58 */ #meta .lgrid .lgcol>h3,#metav2 .lgrid .lgcol>h3{position:static!important}\n#meta .lgrid table.lgt tr.hd th,#metav2 .lgrid table.lgt tr.hd th,#meta .lgrid table.lgt thead th,#metav2 .lgrid table.lgt thead th{position:static!important;box-shadow:none!important;top:auto!important}\n</style>"
i=s.index('</style>'); s=s[:i]+css+s[i+8:]
i=s.index("Object.assign(NOTES,{"); s=s[:i]+"Object.assign(NOTES,{v58:['META and META v2: section titles and column headers no longer float — they scroll with the table'],"+s[i+len("Object.assign(NOTES,{"):]
open(P,'w',encoding='utf-8').write(s); print('v58 applied')
