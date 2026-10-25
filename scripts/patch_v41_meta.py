"""v41 — META refined + a slate-first picks panel.
Calculations: (1) weights come from the season's measured lift per signal (signals.json → J.signals.overall: dvp, psi, scheme, env,
role) instead of hand-set numbers — clamped to [.04,.30], H2H and ATD keep fixed shares, normalised; (2) ENV: the player's team
implied total from this week's lines (total/2 ± spread/2), percentile within the slot pool — the strongest measured signal; (3) FORM:
opportunities over his last two games vs his season rate (the depth file's l2/se), percentile within his position; (4) consensus —
how many signals lean soft (≥.65) vs hard (≤.35) — shown on every pick, and META is shaded toward 50 when they split.
UI: a "this week's slate" panel above the leaders — picks grouped by kickoff window in time order, games already kicked off hidden
by default, each with META, the two or three reasons that carry it, the ATD price when a book posts one; top avoids beside it.
Rerunnable."""
import io, sys
T = 'scripts/dashboard_template.html'
s = io.open(T, encoding='utf-8').read()
if 'function metaWeights(' in s:
    print('already applied'); sys.exit(0)

def rep(old, new, n=1):
    global s
    c = s.count(old); assert c == n, ('match count %d != %d for: %s' % (c, n, old[:100])); s = s.replace(old, new)

# ---- weights + signal list ----
rep("const META_W={psi:.30,td:.25,sch:.15,h2h:.15,atd:.15};",
    "/* v41: weights follow the measured lift of each signal this season (Intel → signals: top third vs bottom third of actual/baseline),\n"
    "   clamped so no one signal runs the board; H2H (unmeasured, small samples) and the ATD model keep fixed shares */\n"
    "const META_W0={psi:.30,td:.25,sch:.15,h2h:.15,atd:.15};\n"
    "function metaWeights(){const o=(J.signals||{}).overall||{};const L=k=>o[k]&&o[k].lift!=null?Math.max(.04,Math.min(.30,+o[k].lift)):null;\n"
    "  const w={psi:L('psi'),td:L('dvp'),sch:L('scheme'),env:L('env'),form:L('role'),h2h:.06,atd:.12};\n"
    "  if(w.psi==null||w.td==null)return Object.assign({},META_W0,{env:.15,form:.05});\n"
    "  Object.keys(w).forEach(k=>{if(w[k]==null)delete w[k]});const t=Object.values(w).reduce((a,b)=>a+b,0);Object.keys(w).forEach(k=>w[k]=+(w[k]/t).toFixed(3));return w}\n"
    "const META_W=metaWeights();\n"
    "const etKick=g=>{if(!g||!g[GM.date]||!g[GM.time])return null;const m=/(\\d+):(\\d+) (AM|PM)/.exec(g[GM.time]);if(!m)return null;\n"
    "  const h=+m[1]%12+(m[3]==='PM'?12:0);const off=g[GM.date]>='2026-11-01'&&g[GM.date]<'2027-03-08'?'-05:00':'-04:00';return new Date(`${g[GM.date]}T${String(h).padStart(2,'0')}:${m[2]}:00${off}`)};\n"
    "const kickedOff=g=>{const k=etKick(g);return !!k&&k.getTime()<=Date.now()};")
rep("const META_L=[['meta','META','everything together · 0–100, 100 = the softest spot on every signal'],",
    "const META_L=[['meta','META','everything together · 0–100, 100 = the softest spot on every signal'],['env','ENV','his team\\'s implied points this week from the spread and total · the strongest measured signal'],['form','FORM','his opportunities over the last two games vs his season rate'],")
rep("  const LBL=Object.fromEntries(META_L.map(([k,l])=>[k,l])),DESC=new Set(['meta','atd','h2h','sch']);\n  let lens='meta';\n  $(root).innerHTML=`<div class=\"controls\">\n    <span class=\"chips\" id=\"${px}Lens\" title=\"what every column is ranked by — META folds all of them together; click any column header to re-sort just that column\">${META_L.map(",
    "  const LBL=Object.fromEntries(META_L.map(([k,l])=>[k,l])),DESC=new Set(['meta','atd','h2h','sch','env','form']);\n  let lens='meta';\n  $(root).innerHTML=`<div class=\"controls\">\n    <span class=\"chips\" id=\"${px}Lens\" title=\"what every column is ranked by — META folds all of them together; click any column header to re-sort just that column\">${META_L.map(")
# note text: add the new signals + weights
rep("<b>META</b> folds the other five into one score, 0–100 (100 = the softest spot on every signal) &middot; <b>TD</b> = touchdowns this week's opponent allows to his slot, rank of ${NT} (1 = the most)",
    "<b>META</b> folds every other column into one score, 0–100 (100 = the softest spot on every signal), weighted by each signal's measured lift this season (${Object.entries(META_W).map(([k,v])=>LBL[k].replace('META','')+' '+Math.round(100*v)+'%').join(' · ')}) &middot; <b>ENV</b> = his team's implied points from this week's line &middot; <b>FORM</b> = his opportunities over the last two games vs his season rate &middot; <b>TD</b> = touchdowns this week's opponent allows to his slot, rank of ${NT} (1 = the most)")
rep("  <div class=\"mlead\" id=\"${px}Lead\" data-mg=\"1\"></div>\n  <div class=\"lgrid td5 wide full meta\">",
    "  <div class=\"mslate\" id=\"${px}Slate\"></div>\n  <div class=\"mlead\" id=\"${px}Lead\" data-mg=\"1\"></div>\n  <div class=\"lgrid td5 wide full meta\">")
rep("  const SIGS=['meta','td','atd','psi','h2h','sch'],SIGW={meta:9,td:8,atd:8,psi:7,h2h:11,sch:8},sigs=()=>SIGS.filter(k=>HAS[k]);",
    "  const SIGS=['meta','env','td','atd','psi','form','h2h','sch'],SIGW={meta:9,env:7,td:8,atd:8,psi:7,form:7,h2h:11,sch:8},sigs=()=>SIGS.filter(k=>HAS[k]);\n"
    "  const implied=(t,wk)=>{const g=((J.betting||{}).glh||[]).find(r=>r[0]===(J.season||2026)&&r[1]===wk&&(r[2]===t||r[3]===t));if(!g||g[7]==null)return null;const sp=g[6]==null?0:+g[6];return g[3]===t?+g[7]/2+sp/2:+g[7]/2-sp/2};");
rep("      const t=tdOf(u),atd=t&&t.p_model!=null&&t.p_model!==''?+t.p_model:null;\n      return {u,pos,oppRaw,opp,td:avg(tdBy),psi:avg(psiBy),S,n:vs.length,hp,hb,hd,hS:hp==null||hb==null?null:(hp-hb)*Math.min(vs.length,3)/3,",
    "      const t=tdOf(u),atd=t&&t.p_model!=null&&t.p_model!==''?+t.p_model:null;\n      const env=opp?implied(u.team,wk):null,form=u.l2!=null&&u.se>0&&u.gp>=2?u.l2/u.se-1:null,gm=opp?gameOf(u.team,wk):null;\n      return {u,pos,oppRaw,opp,env,form,gm,td:avg(tdBy),psi:avg(psiBy),S,n:vs.length,hp,hb,hd,hS:hp==null||hb==null?null:(hp-hb)*Math.min(vs.length,3)/3,")
rep("    const P=R.filter(x=>x.pool&&x.opp),pH=pct(P.map(x=>x.hS)),pS=pct(P.map(x=>x.sch)),pA={};\n    TPOS.forEach(p=>pA[p]=pct(P.filter(x=>x.pos===p).map(x=>x.atd)));",
    "    const P=R.filter(x=>x.pool&&x.opp),pH=pct(P.map(x=>x.hS)),pS=pct(P.map(x=>x.sch)),pE=pct(P.map(x=>x.env)),pA={},pF={};\n    TPOS.forEach(p=>{pA[p]=pct(P.filter(x=>x.pos===p).map(x=>x.atd));pF[p]=pct(P.filter(x=>x.pos===p).map(x=>x.form))});")
rep("    R.forEach(x=>{const c={psi:x.psi==null?null:clamp((NT-x.psi)/(NT-1)),td:x.td==null?null:clamp((NT-x.td)/(NT-1)),h2h:pH(x.hS),sch:pS(x.sch),atd:pA[x.pos](x.atd)};\n      let s=0,w=0;Object.entries(META_W).forEach(([k,wt])=>{if(c[k]!=null){s+=wt*c[k];w+=wt}});\n      x.c=c;x.cov=w/W;x.meta=w&&x.opp?50+(100*s/w-50)*(.6+.4*w/W):null});",
    "    R.forEach(x=>{const c={psi:x.psi==null?null:clamp((NT-x.psi)/(NT-1)),td:x.td==null?null:clamp((NT-x.td)/(NT-1)),h2h:pH(x.hS),sch:pS(x.sch),atd:pA[x.pos](x.atd),env:pE(x.env),form:pF[x.pos](x.form)};\n"
    "      let s=0,w=0,soft=0,hard=0,n=0;Object.entries(META_W).forEach(([k,wt])=>{if(c[k]!=null){s+=wt*c[k];w+=wt;n++;if(c[k]>=.65)soft++;else if(c[k]<=.35)hard++}});\n"
    "      /* consensus: when the signals split (soft AND hard leans at once) the score is shaded toward 50 — a spot every signal agrees on keeps its full distance */\n"
    "      const agree=n?1-Math.min(soft,hard)/n:1;x.c=c;x.cov=w/W;x.soft=soft;x.hard=hard;x.nsig=n;x.agree=agree;\n"
    "      x.meta=w&&x.opp?50+(100*s/w-50)*(.6+.4*w/W)*(.75+.25*agree):null});")
rep("    ROWS=R;HAS={meta:1,td:R.some(x=>x.td!=null),atd:R.some(x=>x.atd!=null),psi:R.some(x=>x.psi!=null),h2h:R.some(x=>x.hp!=null),sch:R.some(x=>x.sch!=null)};",
    "    ROWS=R;HAS={meta:1,td:R.some(x=>x.td!=null),atd:R.some(x=>x.atd!=null),psi:R.some(x=>x.psi!=null),h2h:R.some(x=>x.hp!=null),sch:R.some(x=>x.sch!=null),env:R.some(x=>x.env!=null),form:R.some(x=>x.form!=null)};")
rep("  const sv=(x,k)=>k==='meta'?x.meta:k==='td'?x.td:k==='atd'?x.atd:k==='psi'?x.psi:k==='h2h'?x.hS:k==='sch'?x.sch:",
    "  const sv=(x,k)=>k==='meta'?x.meta:k==='env'?x.env:k==='form'?x.form:k==='td'?x.td:k==='atd'?x.atd:k==='psi'?x.psi:k==='h2h'?x.hS:k==='sch'?x.sch:")
rep("  const why=x=>[`META ${x.meta==null?'—':Math.round(x.meta)} of 100 · ${Math.round(100*x.cov)}% of the weight has data`,",
    "  const why=x=>[`META ${x.meta==null?'—':Math.round(x.meta)} of 100 · ${Math.round(100*x.cov)}% of the weight has data · ${x.soft} of ${x.nsig} signals lean soft, ${x.hard} lean hard${x.agree<1?' (split — shaded toward 50)':''}`,\n"
    "    `ENV ${x.env==null?'no line':x.env.toFixed(1)+' implied pts'} → ${x.c.env==null?'—':Math.round(100*x.c.env)} (weight ${META_W.env||0})`,\n"
    "    `FORM ${x.form==null?'—':(x.form>=0?'+':'')+Math.round(100*x.form)+'% opps last 2 vs season'} → ${x.c.form==null?'—':Math.round(100*x.c.form)} (weight ${META_W.form||0})`,")
rep("    const o={meta,td,atd,psi,h2h,sch};return sigs().map(k=>o[k]).join('')};",
    "    const env=x.env==null?'<td class=\"md\"><span class=\"dim\">·</span></td>'\n"
    "      :`<td class=\"md\" title=\"${esc(`${x.u.team} implied ${x.env.toFixed(1)} points this week${x.gm&&x.gm[GM.time]?' · '+x.gm[GM.day]+' '+x.gm[GM.time]+' ET':''} · shaded among this week's starters`)}\"><span class=\"badge\" style=\"${x.c.env==null?'':gradeStyle(eq(x.c.env))}\">${x.env.toFixed(1)}</span></td>`;\n"
    "    const form=x.form==null?'<td class=\"md\"><span class=\"dim\">·</span></td>'\n"
    "      :`<td class=\"md\" style=\"color:${x.form>=.15?'#00c853':x.form<=-.15?'#ff5252':'var(--dim)'}\" title=\"${esc(`${x.u.l2} opportunities per game over his last two vs ${x.u.se} on the season (${x.u.gp} gp) · shaded within ${x.pos}s`)}\">${x.form>=0?'+':''}${Math.round(100*x.form)}%</td>`;\n"
    "    const o={meta,env,td,atd,psi,form,h2h,sch};return sigs().map(k=>o[k]).join('')};")
rep("    const TH={meta:th('meta','META','every signal folded into one score · 0–100, 100 = softest on all of them · hover a cell for the breakdown','md gs'),",
    "    const TH={meta:th('meta','META','every signal folded into one score · 0–100, 100 = softest on all of them · hover a cell for the breakdown','md gs'),\n"
    "      env:th('env','ENV','his team\\'s implied points from this week\\'s spread and total · shaded among the week\\'s starters','md'),\n"
    "      form:th('form','FORM','opportunities per game over his last two vs his season rate · ▲ workload rising','md'),")
# ---- slate panel ----
rep("  /* the week's best on each signal, from whatever the board is showing */\n  function lead(){",
    "  /* v41: this week's slate — the best spots by kickoff window, games already kicked off hidden by default */\n"
    "  let hideStarted=true;\n"
    "  const reasons=x=>{const r=[];const c=x.c;\n"
    "    if(c.env!=null&&c.env>=.65)r.push(['ENV',x.env.toFixed(1)+' imp',c.env]);if(c.td!=null&&c.td>=.65)r.push(['TD',`rk ${Math.round(x.td)}`,c.td]);\n"
    "    if(c.psi!=null&&c.psi>=.65)r.push(['Ψ',`${Math.round(x.psi)}`,c.psi]);if(c.atd!=null&&c.atd>=.65)r.push(['ATD',Math.round(100*x.atd)+'%',c.atd]);\n"
    "    if(c.form!=null&&c.form>=.65)r.push(['FORM',(x.form>=0?'+':'')+Math.round(100*x.form)+'%',c.form]);if(c.sch!=null&&c.sch>=.65)r.push(['SCH',(x.sch>=0?'+':'')+Math.round(x.sch),c.sch]);\n"
    "    if(c.h2h!=null&&c.h2h>=.65&&x.n>0)r.push(['H2H',x.hp.toFixed(1)+' ppr',c.h2h]);\n"
    "    return r.sort((a,b)=>b[2]-a[2]).slice(0,3)};\n"
    "  const against=x=>{const r=[];const c=x.c;[['ENV',c.env,x.env==null?'':x.env.toFixed(1)+' imp'],['TD',c.td,x.td==null?'':'rk '+Math.round(x.td)],['Ψ',c.psi,x.psi==null?'':Math.round(x.psi)],['ATD',c.atd,x.atd==null?'':Math.round(100*x.atd)+'%'],['FORM',c.form,x.form==null?'':(x.form>=0?'+':'')+Math.round(100*x.form)+'%'],['SCH',c.sch,x.sch==null?'':(x.sch>=0?'+':'')+Math.round(x.sch)]].forEach(([l,v,t])=>{if(v!=null&&v<=.35)r.push([l,t,v])});return r.sort((a,b)=>a[2]-b[2]).slice(0,3)};\n"
    "  function slate(){\n"
    "    const wk=G.week,R=ROWS.filter(x=>keep(x)&&x.meta!=null&&x.opp&&x.cov>=.5&&x.u.inj!=='-1');\n"
    "    const gs=GAMES(wk).filter(g=>(!ACT||ACT.has(g[GM.vis])||ACT.has(g[GM.home]))&&(!G.slates.size||G.slates.has(g[GM.slate])));\n"
    "    const live=gs.filter(g=>!hideStarted||!kickedOff(g)),started=gs.length-live.length;\n"
    "    const key=g=>g[GM.date]+' '+String(tmin(g[GM.time])).padStart(4,'0');\n"
    "    const wins=[];live.forEach(g=>{const k=g[GM.slate]+'|'+g[GM.date];let w=wins.find(x=>x.k===k);if(!w){w={k,slate:g[GM.slate],date:g[GM.date],day:g[GM.day],first:key(g),teams:new Set(),games:[]};wins.push(w)}w.teams.add(g[GM.vis]);w.teams.add(g[GM.home]);w.games.push(g)});\n"
    "    wins.sort((a,b)=>a.first<b.first?-1:1);\n"
    "    const pick=x=>`<div class=\"msr plink\" data-p=\"${esc(x.u.player)}\" title=\"${esc(why(x))}\">${posIcon(x.pos,10,x.u.dslot||x.u.slot)}<b>${esc(pshort(x.u.player))}</b><span class=\"mini\">${tcell(x.u.team)} ${x.oppRaw&&x.oppRaw[0]==='@'?'@':'v'} ${tcell(x.opp)}${x.gm&&x.gm[GM.time]?' · '+x.gm[GM.time].replace(':00','').replace(' ','')+(kickedOff(x.gm)?' <i class=\"started\">live</i>':''):''}</span>\n"
    "      <span class=\"badge\" style=\"${gradeStyle(eq(x.meta/100))}\">${Math.round(x.meta)}</span><span class=\"msw\">${reasons(x).map(r=>`<i>${r[0]} ${r[1]}</i>`).join('')}${x.t&&x.t.price!=null?`<i class=\"px\">ATD ${mlTxt(+x.t.price)}${x.t.ev!=null&&+x.t.ev>=1?' · EV +'+(+x.t.ev).toFixed(0)+'%':''}</i>`:''}</span></div>`;\n"
    "    const avoid=x=>`<div class=\"msr plink\" data-p=\"${esc(x.u.player)}\" title=\"${esc(why(x))}\">${posIcon(x.pos,10,x.u.dslot||x.u.slot)}<b>${esc(pshort(x.u.player))}</b><span class=\"mini\">${tcell(x.u.team)} ${x.oppRaw&&x.oppRaw[0]==='@'?'@':'v'} ${tcell(x.opp)}</span><span class=\"badge\" style=\"${gradeStyle(eq(x.meta/100))}\">${Math.round(x.meta)}</span><span class=\"msw\">${against(x).map(r=>`<i>${r[0]} ${r[1]}</i>`).join('')}</span></div>`;\n"
    "    const perPos=(L,n)=>{const out=[],seen={};L.forEach(x=>{seen[x.pos]=(seen[x.pos]||0);if(seen[x.pos]<n){out.push(x);seen[x.pos]++}});return out};\n"
    "    const liveTeams=new Set();live.forEach(g=>{liveTeams.add(g[GM.vis]);liveTeams.add(g[GM.home])});\n"
    "    const L=R.filter(x=>liveTeams.has(x.u.team)).sort((a,b)=>b.meta-a.meta);\n"
    "    const best=perPos(L,4).slice(0,12),avoids=L.slice().reverse().filter(x=>x.meta<=40).slice(0,6);\n"
    "    const byWin=wins.map(w=>{const P=R.filter(x=>w.teams.has(x.u.team)).sort((a,b)=>b.meta-a.meta);const top=perPos(P,3).slice(0,8);\n"
    "      return `<div class=\"mlc\"><div class=\"mlh\">${slateChip(w.slate)} <span class=\"mini\">${w.day} · ${w.games.length} game${w.games.length===1?'':'s'}${w.games.some(kickedOff)?' · <i class=\"started\">in progress</i>':''}</span></div>${top.map(pick).join('')||'<div class=\"mini dim\">no starter clears the bar</div>'}</div>`}).join('');\n"
    "    $$('Slate').innerHTML=`<div class=\"mshd\"><b>this week's slate</b> <span class=\"mini\">best spots by kickoff window · META with ≥50% of the signals in · OUT excluded · click a name for the breakdown</span>\n"
    "        <label class=\"mini\"><input type=\"checkbox\" id=\"${px}Hide\" ${hideStarted?'checked':''}> hide games already kicked off${started?` (${started} hidden)`:''}</label></div>\n"
    "      <div class=\"msgrid\"><div class=\"mlc g\"><div class=\"mlh\">best of what's left · top ${best.length}</div>${best.map(pick).join('')||'<div class=\"mini dim\">nothing left on the slate</div>'}</div>${byWin}${avoids.length?`<div class=\"mlc r\"><div class=\"mlh\">avoid</div>${avoids.map(avoid).join('')}</div>`:''}</div>`;\n"
    "    const h=$$('Hide');if(h)h.onchange=()=>{hideStarted=h.checked;slate()};tWire($$('Slate'))}\n"
    "  /* the week's best on each signal, from whatever the board is showing */\n  function lead(){")
rep("      ['best spots · META','g',top(null,'meta',false),x=>B(Math.round(x.meta),gradeStyle(eq(x.meta/100)))],\n      ['TD spots','',top(null,'td',true),x=>B(Math.round(x.td),gradeStyle(x.td))],",
    "      ['best spots · META','g',top(null,'meta',false),x=>B(Math.round(x.meta),gradeStyle(eq(x.meta/100)))],\n      ['implied points · ENV','',top(null,'env',false),x=>B(x.env.toFixed(1),x.c.env==null?'':gradeStyle(eq(x.c.env)))],\n      ['TD spots','',top(null,'td',true),x=>B(Math.round(x.td),gradeStyle(x.td))],")
rep("      ['avoid · META','r',top(null,'meta',true),x=>B(Math.round(x.meta),gradeStyle(eq(x.meta/100)))]].filter((c,i)=>HAS[['meta','td','atd','psi','h2h','sch','meta'][i]]);",
    "      ['avoid · META','r',top(null,'meta',true),x=>B(Math.round(x.meta),gradeStyle(eq(x.meta/100)))]].filter((c,i)=>HAS[['meta','env','td','atd','psi','h2h','sch','meta'][i]]);")
rep("  const cols=()=>{['ALL'].concat(TPOS).forEach(col);lead()};\n  const all=()=>{build();if(!HAS[lens])$$('Lens').querySelector('button[data-l=\"meta\"]').click();cols()};\n  ['Src','QB','Se','Inj'].forEach(i=>$$(i).onchange=all);$$('Q').oninput=cols;",
    "  const cols=()=>{['ALL'].concat(TPOS).forEach(col);slate();lead()};\n  const all=()=>{build();if(!HAS[lens])$$('Lens').querySelector('button[data-l=\"meta\"]').click();cols()};\n  ['Src','QB','Se','Inj'].forEach(i=>$$(i).onchange=all);$$('Q').oninput=cols;")
# CSS
rep("/* v36 position letters */",
    "/* v41 META slate panel */.mslate{margin:0 0 10px}.mshd{display:flex;gap:10px;align-items:center;flex-wrap:wrap;margin:0 0 6px;font-size:12px}.mshd label{margin-left:auto;cursor:pointer}.msgrid{display:grid;grid-template-columns:repeat(auto-fit,minmax(250px,1fr));gap:8px}\n"
    ".msr{display:grid;grid-template-columns:14px minmax(0,1fr) auto;gap:4px 6px;align-items:center;font-size:11.5px;padding:3px 0;border-bottom:1px dashed var(--edge);cursor:pointer}.msr>b{white-space:nowrap;overflow:hidden;text-overflow:ellipsis;text-align:left}.msr>.mini{grid-column:2;white-space:nowrap;text-align:left}.msr>.badge{grid-row:1/3;align-self:center}\n"
    ".msw{grid-column:1/4;display:flex;gap:4px;flex-wrap:wrap}.msw i{font-style:normal;font-size:10px;padding:0 5px;border-radius:9px;background:var(--panel2,#161b22);border:1px solid var(--edge);color:var(--fg)}.msw i.px{color:#e8b100;border-color:#e8b10055}.started{font-style:normal;color:#ff8a65}\n"
    "@media(max-width:760px){.msgrid{grid-template-columns:1fr}}\n/* v36 position letters */")
s = s.replace("Object.assign(NOTES,{v40:", "Object.assign(NOTES,{v41:['v41','META refined: weights follow each signal\\'s measured lift this season, ENV (team implied points) and FORM (last-2 opportunities vs season) join the fold, a split verdict is shaded toward 50 \\u00b7 a this-week\\'s-slate panel groups the best spots by kickoff window and hides games already under way']});\nObject.assign(NOTES,{v40:", 1)
io.open(T, 'w', encoding='utf-8').write(s)
print('v41 applied', len(s))
