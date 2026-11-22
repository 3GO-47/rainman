"""v67 — Category Grid check-off: a box beside every player on the Category Grid (table, lead cards and their pop-ups), in the
category pane's "carrying it in" list, and on Category Grid v2. Click it when he has scored today: the box turns green, the
row is tinted and the name struck through. Kept per week in the browser (localStorage); a counter with 'clear' sits in the
grid controls. Clicking the name still opens his card. Rerunnable."""
import os, sys
os.chdir(os.path.join(os.path.dirname(os.path.abspath(__file__)), '..'))
P = 'scripts/dashboard_template.html'
s = open(P, encoding='utf-8').read()
if '/* v67 */' in s:
    print('v67 already applied'); sys.exit(0)
def rep(old, new, n=1):
    global s
    assert s.count(old) == n, (s.count(old), old[:110])
    s = s.replace(old, new)

# helpers (before wgName, which uses them)
rep("""const wgName=x=>`<span class="plink" data-p="${esc(x.name)}" title="${esc(x.name)} · ${esc(x.slot)} · ${esc(x.team)}">${esc(pshort(x.name))}""",
    """/* v67 */const SCM={};const scKey=w=>'rm_scored_'+LAST_SE+'_'+w;
const scSet=w=>SCM[w]||(SCM[w]=(()=>{try{return new Set(JSON.parse(localStorage.getItem(scKey(w))||'[]'))}catch(e){return new Set()}})());
const scHas=(n,w=G.week)=>scSet(w).has(n);
const scBox=(n,w=G.week)=>`<i class="scb${scHas(n,w)?' on':''}" data-sc="${esc(n)}" data-scw="${w}" title="click when he has scored today · click again to undo"></i>`;
const scSave=w=>{try{localStorage.setItem(scKey(w),JSON.stringify([...scSet(w)]))}catch(e){}};
function scPaint(){document.querySelectorAll('[data-sc]').forEach(b=>{const on=scHas(b.dataset.sc,+b.dataset.scw);b.classList.toggle('on',on);const r=b.closest('tr,.mlr,.wgpc,.wkpc');if(r)r.classList.toggle('scored',on)});
  document.querySelectorAll('.scc').forEach(c=>{const n=scSet(G.week).size;c.innerHTML=n?`<b style="color:var(--green)">✓ ${n}</b> scored today · <a data-scclear="${G.week}" style="cursor:pointer;text-decoration:underline">clear</a>`:'click the box beside a player when he scores'})}
document.addEventListener('click',e=>{const c=e.target.closest('[data-scclear]');if(c){e.preventDefault();e.stopPropagation();const w=+c.dataset.scclear;scSet(w).clear();scSave(w);scPaint();return}
  const t=e.target.closest('[data-sc]');if(!t)return;e.preventDefault();e.stopPropagation();const n=t.dataset.sc,w=+t.dataset.scw,S=scSet(w);S.has(n)?S.delete(n):S.add(n);scSave(w);scPaint()},true);
const wgName=x=>`<span class="plink" data-p="${esc(x.name)}" title="${esc(x.name)} · ${esc(x.slot)} · ${esc(x.team)}">${scBox(x.name)}${esc(pshort(x.name))}""")
# Category Grid (v1): the table rows + the counter in the controls
rep("""      ${R.map(x=>`<tr><td class="plink" data-p="${esc(x.name)}" title="${esc(x.name)} · ${esc(x.slot)} · ${esc(x.team)}">${esc(pshort(x.name))}""",
    """      ${R.map(x=>`<tr${scHas(x.name,CS.W0)?' class="scored"':''}><td class="plink" data-p="${esc(x.name)}" title="${esc(x.name)} · ${esc(x.slot)} · ${esc(x.team)}">${scBox(x.name,CS.W0)}<span class="scn">${esc(pshort(x.name))}</span>""")
rep("""    <input id="${px}Q" placeholder="search player..." size="15">
    <span class="note">every recorded week at once, for the week picked up top.""",
    """    <input id="${px}Q" placeholder="search player..." size="15">
    <span class="mini scc"></span>
    <span class="note">every recorded week at once, for the week picked up top.""")
rep("  const cols=()=>{['ALL'].concat(TPOS).forEach(col);lead()};\n  const all=()=>{build();cols()};\n  el.addEventListener('click',e=>{const t=e.target.closest('[data-sig]');if(!t||!el.contains(t)||!window.wkSigPopG)return;",
    "  const cols=()=>{['ALL'].concat(TPOS).forEach(col);lead();scPaint()};\n  const all=()=>{build();cols()};\n  el.addEventListener('click',e=>{const t=e.target.closest('[data-sig]');if(!t||!el.contains(t)||!window.wkSigPopG)return;")
# the category pane: the players carrying it into the week
rep("""      ${A.map(x=>`<tr><td>${pn(x.name,x.team,true)}${x.u&&x.u.inj==='0'?' <span class="inj0">Q</span>':''}""",
    """      ${A.map(x=>`<tr${scHas(x.name,W0)?' class="scored"':''}><td>${scBox(x.name,W0)}${pn(x.name,x.team,true)}${x.u&&x.u.inj==='0'?' <span class="inj0">Q</span>':''}""")
# Category Grid v2: the picks strip and the table
rep("""${B.slice(0,16).map(x=>`<span class="wkpc ${x.done?(x.done.td>0?'w':'l'):''}">${pn(x.name,x.team,true)}""",
    """${B.slice(0,16).map(x=>`<span class="wkpc ${x.done?(x.done.td>0?'w':'l'):''}${scHas(x.name)?' scored':''}">${scBox(x.name)}${pn(x.name,x.team,true)}""")
rep("""      ${L.map(x=>`<tr><td>${pn(x.name,x.team,true)}</td><td>${tcell(x.team)}</td><td style="color:${POSC[x.pos]||'inherit'}">${x.pos}</td><td>${w2opp(x)}</td><td class="n" data-v="${x.cat}"><b>${x.cat}</b></td>${PKs.map(r=>ccell(x,r)).join('')}""",
    """      ${L.map(x=>`<tr${scHas(x.name)?' class="scored"':''}><td>${scBox(x.name)}${pn(x.name,x.team,true)}</td><td>${tcell(x.team)}</td><td style="color:${POSC[x.pos]||'inherit'}">${x.pos}</td><td>${w2opp(x)}</td><td class="n" data-v="${x.cat}"><b>${x.cat}</b></td>${PKs.map(r=>ccell(x,r)).join('')}""")
rep("</style>", """/* v67 */.scb{display:inline-block;width:12px;height:12px;border:1.5px solid var(--dim);border-radius:3px;margin-right:4px;vertical-align:-2px;cursor:pointer;flex:none;box-sizing:border-box}.scb:hover{border-color:var(--green)}
.scb.on{background:var(--green);border-color:var(--green)}.scb.on::after{content:'\\2713';display:block;color:#000;font:700 9px/9px var(--mono);text-align:center}
tr.scored>td{background:rgba(46,204,113,.10)!important}.scored .plink,.scored .scn,.scored .pp{text-decoration:line-through;opacity:.75}.mlr.scored,.wgpc.scored,.wkpc.scored{background:rgba(46,204,113,.10)}
</style>""")
open(P, 'w', encoding='utf-8').write(s); print('v67 applied')
