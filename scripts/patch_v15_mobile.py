# -*- coding: utf-8 -*-
"""v15 — mobile mode. ≤760px: one-row header, bottom section bar, scrollable sub-tab row, filters behind one button,
every table a scroll strip with the first column pinned, game view stacked, pop-ups full screen. Same page, same numbers."""
import sys
sys.path.insert(0,'scripts')
from mobile import MOB_CSS, MOB_JS
def patch(path,pairs):
    s=open(path,encoding='utf-8').read()
    for old,new in pairs:
        assert s.count(old)==1,(path,old[:80],s.count(old))
        s=s.replace(old,new)
    open(path,'w',encoding='utf-8').write(s)

DASH_CSS = MOB_CSS + r"""
@media (max-width:760px){
 #top{position:sticky;top:0;z-index:30}
 #hdr{display:flex;flex-wrap:nowrap!important;align-items:center;height:44px!important;padding:0 8px!important;gap:6px!important}
 .brand{height:44px;font-size:13px;flex:1 1 auto;min-width:0;overflow:hidden;border-right:0;padding-right:0;margin-right:0}
 .brand #lgSw{display:none}
 #tnav{display:none!important}
 .hright{height:44px;gap:5px!important;padding:0!important;margin-left:0;flex:none}
 #gFind{padding:0 9px;min-height:30px}#gFind .fl,#gFind kbd{display:none}
 .hright .gl,#gShare,#gHelp{display:none}
 #gWk{min-height:30px;font-size:12px;max-width:92px}
 #mMenu{background:#000;border:1px solid var(--edge2);color:var(--txt);font:600 15px/1 var(--mono);min-height:30px;min-width:34px;padding:0 8px;cursor:pointer;border-radius:3px}
 #sub{display:flex!important;align-items:stretch;height:38px!important;padding:0 0 0 4px!important;gap:0!important;overflow:hidden}
 #sub:has(#snav[hidden]){display:flex!important}
 #snav{flex:1 1 auto!important;max-width:none;overflow-x:auto;scrollbar-width:none;display:flex!important;mask-image:linear-gradient(90deg,#000 92%,transparent)}
 #snav[hidden]{visibility:hidden}
 #snav::-webkit-scrollbar{display:none}
 #snav .sitem{flex:none;padding:0 11px;font-size:12px;height:38px;line-height:38px}#snav .sitem kbd{display:none}
 #crumb{display:none}
 #mFilt{flex:none;background:#000;border:0;border-left:1px solid var(--edge);color:var(--dim);font:600 10.5px var(--ui);letter-spacing:.08em;text-transform:uppercase;padding:0 11px;cursor:pointer;white-space:nowrap}
 #mFilt.on{color:var(--amber)}
 #gbar{display:none!important}
 #gbar.open{display:flex!important;flex-wrap:wrap!important;overflow:auto;max-height:60vh;padding:6px 10px 10px!important;gap:6px 6px!important;border-bottom:1px solid var(--edge2);background:#000}
 #gbar.open>*{flex:none}#gbar.open .gl{flex-basis:100%;margin-top:4px;font-size:9.5px}#gbar.open .chips{flex-wrap:wrap!important;max-width:100%}
 #gbar.open select{max-width:100%}#gSum{display:none}
 main{padding:8px 8px 68px!important}
 #pageIntro .pintro .ph{display:-webkit-box;-webkit-line-clamp:2;-webkit-box-orient:vertical;overflow:hidden;font-size:11px}
 #pageIntro .pintro.exp .ph{display:block}
 #mnav{position:fixed;left:0;right:0;bottom:0;display:flex;height:calc(54px + env(safe-area-inset-bottom));padding-bottom:env(safe-area-inset-bottom);background:rgba(0,0,0,.97);border-top:1px solid var(--edge2);z-index:35}
 #mnav button{flex:1 1 0;min-width:0;background:none;border:0;border-right:1px solid var(--edge);color:var(--dim);font:600 9.5px var(--ui);letter-spacing:.06em;text-transform:uppercase;display:flex;flex-direction:column;align-items:center;justify-content:center;gap:4px;cursor:pointer;padding:0 2px}
 #mnav button:last-child{border-right:0}#mnav button b{font:600 13px/1 var(--mono);color:var(--dim2)}
 #mnav button.on{color:var(--amber);background:#0d0b05}#mnav button.on b{color:var(--amber)}
 #mSheet .modalbox{padding:12px 12px 40px!important}
 #mSheet .msh{font:600 10px var(--ui);letter-spacing:.1em;text-transform:uppercase;color:var(--dim2);margin:12px 0 6px}
 #mSheet .mlinks{display:flex;flex-wrap:wrap;gap:6px}
 #mSheet .mlinks a{display:inline-flex;align-items:center;min-height:34px;padding:0 12px;border:1px solid var(--edge2);border-radius:4px;color:var(--txt);text-decoration:none;font:500 12px var(--ui)}
 #mSheet .mlinks a.on{border-color:var(--amber);color:var(--amber)}
 #mSheet .mlinks a .fk{color:var(--dim2);font:600 10px var(--mono);margin-right:6px}
 .sribbon.g16{grid-template-columns:repeat(2,minmax(0,1fr))!important;gap:5px}
 @media (max-width:400px){.stcomp i{font-size:8px}}
 #gameview .gsides,.gsides{grid-template-columns:1fr!important;gap:10px}
 .gcard{min-height:0}
 #gameview .grow,.grow{grid-template-columns:38px minmax(0,1.1fr) minmax(0,.8fr) minmax(0,1.2fr)!important;gap:4px;padding:3px 4px;min-height:30px}
 .grow>*:nth-child(5){display:none}
 .gvdeep,#gameview .gvdeep{grid-template-columns:1fr!important}
 .hg2,.hg3,.hg2b,.r11wrap,.r11two,.dvpsplit,.sc2,.inj2,.scgrid,.lore3,.volgrid,.standgrid,.standgrid>div,.pkgrid2,.apipol,.hgl{grid-template-columns:1fr!important}
 .r11sum,.kpis{grid-template-columns:repeat(2,minmax(0,1fr))!important}
 .ebgrid,.lgrid,.lgrid.td5,.lgrid.td5.wide{grid-template-columns:1fr!important}
 .injr{grid-template-columns:1fr!important;gap:1px;padding:4px 0}
 .quad{min-width:0}
 .smap{columns:1}
 #ppModal .modalbox.wide{max-width:100%!important}
 #ppModal table.mkt td{max-width:160px}
 .chips{flex-wrap:wrap}
 #devFrame{height:calc(100vh - 150px)!important}
}
"""

DASH_JS = MOB_JS + r"""
/* ---------- mobile nav: bottom section bar from SECTIONS, filters button, league/section sheet ---------- */
(function(){const mq=window.rmMobile;if(!mq)return;
function build(){if(document.getElementById('mnav'))return;
 const n=document.createElement('nav');n.id='mnav';n.setAttribute('aria-label','sections');
 n.innerHTML=SECTIONS.filter(s=>s.items.some(itemOK)).map(s=>`<button data-s="${s.id}"><b>${s.fk}</b><span>${s.label}</span></button>`).join('');
 n.addEventListener('click',e=>{const b=e.target.closest('button');if(!b)return;const sec=SECTIONS.find(s=>s.id===b.dataset.s);if(!sec)return;const cur=ITEMS[CUR_ITEM];if(cur&&cur.sec.id===sec.id){window.scrollTo({top:0,behavior:'smooth'});return}go(SEC_LAST[sec.id]||sec.items.find(itemOK).id)});
 document.body.appendChild(n);
 const f=document.createElement('button');f.id='mFilt';f.type='button';f.textContent='filters';f.onclick=()=>{const g=$('#gbar');g.classList.toggle('open');f.classList.toggle('on',g.classList.contains('open'))};$('#sub').appendChild(f);
 const m=document.createElement('button');m.id='mMenu';m.type='button';m.title='leagues, sections, tracking';m.textContent='☰';
 m.onclick=()=>{let s=document.getElementById('mSheet');if(s){s.remove();return}s=document.createElement('div');s.id='mSheet';s.className='modal';
  const lg=$('#lgSw')?$('#lgSw').innerHTML:'';
  const secs=SECTIONS.filter(x=>x.items.some(itemOK)).map(x=>`<div class="msh">${x.fk} · ${x.label}</div><div class="mlinks">${x.items.filter(itemOK).map(i=>`<a href="#" data-go="${i.id}" class="${i.id===CUR_ITEM?'on':''}">${i.label}</a>`).join('')}</div>`).join('');
  s.innerHTML=`<div class="modalbox"><button class="mclose">✕</button><div class="msh">leagues · pages</div><div class="mlinks">${lg}</div>${secs}<div class="msh">week</div><div class="mlinks"><a href="#" data-help="1">? glossary</a><a href="#" data-share="1">copy link to this view</a></div></div>`;
  s.addEventListener('click',e=>{if(e.target===s||e.target.closest('.mclose')){s.remove();return}const a=e.target.closest('a');if(!a)return;if(a.dataset.go){e.preventDefault();s.remove();go(a.dataset.go);return}if(a.dataset.help){e.preventDefault();s.remove();const h=$('#gHelp');if(h)h.click();return}if(a.dataset.share){e.preventDefault();s.remove();const h=$('#gShare');if(h)h.click();return}});
  document.body.appendChild(s)};
 $('.hright').appendChild(m);
 const pi=$('#pageIntro');if(pi)pi.addEventListener('click',e=>{const p=e.target.closest('.pintro');if(p&&!e.target.closest('.newn'))p.classList.toggle('exp')})}
function sync(){const b=document.getElementById('mnav');if(!b)return;const it=ITEMS[CUR_ITEM];b.querySelectorAll('button').forEach(x=>x.classList.toggle('on',!!it&&x.dataset.s===it.sec.id));
 const n=(G.slates?G.slates.size:0)+(G.pos?G.pos.size:0)+(G.game?1:0)+(G.team?1:0)+(G.owner?1:0)+(G.conf?1:0);const f=document.getElementById('mFilt');if(f){f.textContent=n?`filters · ${n}`:'filters';f.classList.toggle('on',n>0||$('#gbar').classList.contains('open'))}}
let tm;const mo=new MutationObserver(()=>{clearTimeout(tm);tm=setTimeout(sync,120)});
function on(){build();sync();mo.observe($('main'),{childList:true,subtree:true});addEventListener('hashchange',sync)}
function off(){mo.disconnect()}
if(mq.matches)on();mq.addEventListener('change',e=>e.matches?on():off())})();
"""
T='scripts/dashboard_template.html'
patch(T,[
 ("</style>__BRAND_BOOT__", DASH_CSS + "\n</style>__BRAND_BOOT__"),
 ("""addEventListener('hashchange',()=>{const h=new URLSearchParams(location.hash.replace(/^#/,''));const v=h.get('v')||'lab';if(ITEMS[v]&&v!==CUR_ITEM)go(v,{silent:true})});
</script>__BRAND_JS__""",
  """addEventListener('hashchange',()=>{const h=new URLSearchParams(location.hash.replace(/^#/,''));const v=h.get('v')||'lab';if(ITEMS[v]&&v!==CUR_ITEM)go(v,{silent:true})});
""" + DASH_JS + """
</script>__BRAND_JS__"""),
 (""" overview:['v14','slate is three rows of five;""", """ overview:['v15','on a phone: sections live in the bar at the bottom, views scroll across under the header, filters sit behind one button, every table slides sideways with the first column pinned'],
 overview_v14:['v14','slate is three rows of five;"""),
])
# ---- every other page: the shared shim
for p in ['scripts/build_arb.py','scripts/build_social.py','scripts/build_tracking.py','scripts/tennis/build.py','scripts/build_dev.py']:
    s=open(p,encoding='utf-8').read()
    assert s.count('</style>')==1 and s.count('</body>')==1,p
    css=MOB_CSS.replace('{','{{').replace('}','}}') if ('f"""' in s or "f'''" in s) else MOB_CSS
    js=MOB_JS.replace('{','{{').replace('}','}}') if ('f"""' in s or "f'''" in s) else MOB_JS
    s=s.replace('</style>',css+'\n</style>').replace('</body>','<script>'+js+'</script></body>')
    open(p,'w',encoding='utf-8').write(s)
# landing has three f-string templates
p='scripts/build_landing.py';s=open(p,encoding='utf-8').read()
css=MOB_CSS.replace('{','{{').replace('}','}}');js=MOB_JS.replace('{','{{').replace('}','}}')
assert s.count('</style>')==3 and s.count('</body>')==3
s=s.replace('</style>',css+'\n</style>').replace('</body>','<script>'+js+'</script></body>')
open(p,'w',encoding='utf-8').write(s)
# sport template is a plain html file with placeholders
p='scripts/sport_template.html';s=open(p,encoding='utf-8').read()
assert s.count('</style>')==1 and s.count('</body>')==1
s=s.replace('</style>',MOB_CSS+'\n</style>').replace('</body>','<script>'+MOB_JS+'</script></body>')
open(p,'w',encoding='utf-8').write(s)
print('v15 mobile patched')
