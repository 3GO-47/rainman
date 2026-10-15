# -*- coding: utf-8 -*-
"""v15b — mobile follow-ups: scroll strips never widen their parent, slate tiles one per row on phones,
game view columns stack cleanly, scheme rows and depth charts slide sideways, dev header wraps."""
import re
FILES=['scripts/mobile.py','scripts/build_arb.py','scripts/build_social.py','scripts/build_tracking.py','scripts/tennis/build.py','scripts/build_dev.py','scripts/build_landing.py','scripts/sport_template.html','scripts/dashboard_template.html']
def sub(s,old,new,dbl):
    if dbl: old=old.replace('{','{{').replace('}','}}'); new=new.replace('{','{{').replace('}','}}')
    assert old in s,(old[:60]);return s.replace(old,new)
for p in FILES:
    s=open(p,encoding='utf-8').read()
    dbl=p not in ('scripts/mobile.py','scripts/sport_template.html','scripts/dashboard_template.html')
    s=sub(s," .mscroll{overflow-x:auto;max-width:100%;-webkit-overflow-scrolling:touch;overscroll-behavior-x:contain;position:relative}",
            " .mscroll{overflow-x:auto;width:0;min-width:100%;max-width:100%;-webkit-overflow-scrolling:touch;overscroll-behavior-x:contain;position:relative}\n .mgrid1>*,.panel,main>*{min-width:0}\n header{flex-wrap:wrap;height:auto;padding:6px 10px;gap:6px 10px}header nav{flex-wrap:wrap}",dbl)
    open(p,'w',encoding='utf-8').write(s)
# dashboard-only
p='scripts/dashboard_template.html';s=open(p,encoding='utf-8').read()
s=sub(s," .sribbon.g16{grid-template-columns:repeat(2,minmax(0,1fr))!important;gap:5px}\n @media (max-width:400px){.stcomp i{font-size:8px}}",
        " .sribbon.g16{grid-template-columns:repeat(2,minmax(0,1fr))!important;gap:5px}\n @media (max-width:540px){.sribbon.g16{grid-template-columns:1fr!important}}\n .stile{min-width:0}.stile .stcomp i{font-size:9px}\n .gsides>*,.gside,.gcol{min-width:0;max-width:100%;overflow:hidden}\n .scgrid>div{overflow-x:auto;width:0;min-width:100%}.scr{min-width:560px}\n .dcgrid>*,.dcteam{min-width:0;max-width:100%}.dcteam .dcstrip,.dcteam .dcsr{min-width:0}.dcsr .dcwrap{min-width:0}\n .dcsr{grid-template-columns:44px minmax(0,1fr)}",False)
open(p,'w',encoding='utf-8').write(s)
print('v15b ok')
