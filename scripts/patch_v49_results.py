"""v49 — Results, rebuilt to say something. The category view is now:
  1. "who the categories point at" — this week's players ranked by the reliable categories they carry (each category weighted by
     how far above the field it has hit this season), with the categories as chips, TD Picks chance and the result as it lands;
  2. "the categories, ranked" — one table: verdict (trust / lean / noise / fade), season hit rate vs the field (×), weeks beaten,
     this week's carriers and scored-so-far, and the best six names — click a row for everyone carrying it.
The 27 blocks of 30-50 names are gone (they live behind the click). The scorers-mapped table and board scorecard move under a
"how it went" chip once games have been played. Filters, the table view and the global bar are unchanged. Rerunnable."""
import io, sys
T = 'scripts/dashboard_template.html'
s = io.open(T, encoding='utf-8').read()
if 'v49 results' in s:
    print('already applied'); sys.exit(0)
A = "    if(st.view==='cat'){const base=gr?sc/gr:null;"
B = "    const show=R.slice(0,st.lim);"
i = s.index(A); j = s.index(B, i)
new = r'''    if(st.view==='cat'){   /* v49 results */
      const base=gr?sc/gr:null,W0=G.week,TR=(()=>{try{return wkTrust(x=>true,SG,'card38')}catch(e){return null}})();
      const TI={};(TR?TR.sig:[]).forEach(t=>TI[t.id]=t);
      const tp=x=>x.t&&x.t.p!=null?+x.t.p:(x.tp&&x.tp.p!=null?+x.tp.p:null);
      const wgt=id=>{const t=TI[id];if(!t||t.kind==='neg')return 0;if(t.tier==='trust')return Math.max(.3,(t.lift||1)-1);if(t.tier==='lean')return Math.max(.15,(t.lift||1)-1);return 0};
      R.forEach(x=>{x.rel=[...x.ids].filter(id=>wgt(id)>0);x.sc=x.rel.reduce((a,id)=>a+wgt(id),0);x.fade=[...x.ids].filter(id=>TI[id]&&TI[id].kind==='neg'&&TI[id].tier==='fade')});
      const vTxt={trust:'trust',lean:'lean on',noise:'noise',fade:'fade'},vCls={trust:'g',lean:'a',noise:'dim',fade:'r'};
      const catChip2=id=>{const t=TI[id],z=BYID[id];if(!z)return '';return `<span class="wkpc ${t&&t.kind==='neg'?'l':t&&t.tier==='trust'?'w':''}${st.cats.has(id)?' on':''}" data-c="${id}" title="${esc(z.long)}${t&&t.lift?' · hits '+wkX(t.lift)+' the field this season':''} · click to filter on it">${esc(z.lbl)}</span>`};
      const resTxt=x=>x.res==null?(x.open?'<span class="dim" title="in play, no TD yet">· live</span>':'<span class="dim">—</span>'):x.res>0?`<b style="color:var(--green)">✓${x.res>1?' '+x.res:''}</b>`:'<b style="color:var(--red)">✗</b>';
      /* 1. who the categories point at */
      const top=R.filter(x=>x.sc>0&&(!st.cats.size||[...st.cats].every(c=>x.ids.has(c))||(st.mode==='any'&&[...st.cats].some(c=>x.ids.has(c))))).sort((a,b)=>b.sc-a.sc||(tp(b)??-1)-(tp(a)??-1)).slice(0,20);
      const tg=top.filter(x=>x.res!=null).length,tk=top.filter(x=>x.res>0).length;
      const pointed=`<div class="panel"><h3>who the categories point at — week ${W0} <span class="f">ranked by the reliable categories he carries, each weighted by how far above the field it hits this season · TD % = the TD Picks model${tg?` · ${tk} of ${tg} played have scored (${Math.round(100*tk/tg)}%${base!=null?' · field '+Math.round(100*base)+'%':''})`:''}</span></h3>
        <div class="tscroll"><table class="fx wrp"><colgroup><col style="width:34px"><col style="width:160px"><col style="width:52px"><col style="width:52px"><col style="width:58px"><col style="width:56px"><col style="width:46px"><col><col style="width:70px"></colgroup><thead><tr><th>#</th><th style="text-align:left">player</th><th>team</th><th>slot</th><th>opp</th><th title="the TD Picks model">TD %</th><th title="reliable categories carried">cats</th><th style="text-align:left">the categories he carries (trusted ones lit · fades dimmed)</th><th>res</th></tr></thead><tbody>
        ${top.map((x,i)=>`<tr><td class="dim">${i+1}</td><td style="text-align:left">${pn(x.name,x.team,true)}</td><td>${tcell(x.team)}</td><td>${slotchip(x.slot)}</td><td>${x.raw?oppcell(x.raw):(x.l?tcell(x.l[LOG.opp]):'')}</td><td data-v="${tp(x)??-1}">${tp(x)!=null?`<span class="badge" style="${gradeStyle(1+(1-tp(x))*(NT-1))}">${Math.round(100*tp(x))}%</span>`:''}</td><td data-v="${x.rel.length}"><b>${x.rel.length}</b></td><td style="text-align:left"><span class="wkpcs">${x.rel.map(catChip2).join('')}${x.fade.map(catChip2).join('')}</span></td><td>${resTxt(x)}</td></tr>`).join('')||'<tr><td colspan="9" class="dim">nothing in view carries a reliable category</td></tr>'}</tbody></table></div></div>`;
      /* 2. the categories, ranked */
      const ord={trust:0,lean:1,noise:2,fade:3};
      const cats=SG.map(z=>{const t=TI[z.id]||{},L=R.filter(x=>x.ids.has(z.id)),g=L.filter(x=>x.res!=null).length,k=L.filter(x=>x.res>0).length;
        const tier=t.tier||(z.kind==='neg'?'noise':'noise');return {z,t,tier,L,g,k,best:L.slice().sort((a,b)=>(b.res??-1)-(a.res??-1)||(tp(b)??-1)-(tp(a)??-1)).slice(0,6)}})
        .filter(c=>c.L.length||st.cats.has(c.z.id)).sort((a,b)=>(ord[a.tier]??9)-(ord[b.tier]??9)||(b.t.lift||0)-(a.t.lift||0));
      const who=c=>()=>({title:esc(c.z.lbl)+` · week ${W0}`,sub:esc(c.z.long||'')+` · everyone carrying it in, scorers first · season: ${c.t.hr!=null?wkPct(c.t.hr)+' scored, '+wkX(c.t.lift)+' the field':'no record yet'}`,
        cols:['player','team',{l:'slot',g:false},{l:'opp',g:false},{l:'TD %',t:'TD Picks model'},{l:'signals',t:'how many of the eight core signals he carries'},{l:'result',g:false}],
        rows:c.L.slice().sort((a,b)=>(b.res??-1)-(a.res??-1)||(tp(b)??-1)-(tp(a)??-1)).map(x=>[pn(x.name,x.team,true),tcell(x.team),slotchip(x.slot),x.raw?oppcell(x.raw):(x.l?tcell(x.l[LOG.opp]):''),tp(x)!=null?{v:tp(x),h:Math.round(100*tp(x))+'%'}:null,x.cs,resTxt(x)])});
      const ranked=`<div class="panel"><h3>the categories, ranked <span class="f">verdict and record are the season to date (every graded week); this week = who carries it into the games ahead · click a row for everyone carrying it, a chip to filter the page on it</span></h3>
        <div class="tscroll"><table class="fx wrc"><colgroup><col style="width:190px"><col style="width:70px"><col style="width:64px"><col style="width:64px"><col style="width:70px"><col style="width:60px"><col style="width:70px"><col></colgroup><thead><tr><th style="text-align:left">category</th><th title="trust = beat the field 75%+ of weeks and 1.3× overall · lean = 1.1× and half the weeks · fade = carrying it meant fewer touchdowns">verdict</th><th title="share of carriers who scored, season to date">hit rate</th><th title="vs the field: 1.5× = carriers scored half again as often as everyone">× field</th><th title="weeks it beat the field by 10%+ / weeks qualified">weeks</th><th title="players carrying it into this week's games">this wk</th><th title="of those played, how many scored">scored</th><th style="text-align:left">best names (TD Picks order · scorers first)</th></tr></thead><tbody>
        ${cats.map(c=>`<tr data-th="${thReg(who(c))}" style="cursor:pointer"><td style="text-align:left"><span class="wkpc ${c.z.kind==='neg'?'l':c.tier==='trust'?'w':''}${st.cats.has(c.z.id)?' on':''}" data-c="${c.z.id}" title="${esc(c.z.long)} · click to filter">${esc(c.z.lbl)}</span></td><td><span class="${vCls[c.tier]||'dim'}">${vTxt[c.tier]||'—'}</span></td><td data-v="${c.t.hr??-1}">${c.t.hr!=null?wkPct(c.t.hr):'—'}</td><td data-v="${c.t.lift??-1}">${c.t.lift!=null?`<span class="badge" style="${wkLiftS(c.z.kind==='neg'?(c.t.lift?1/c.t.lift:null):c.t.lift)}">${wkX(c.t.lift)}</span>`:'—'}</td><td data-v="${c.t.qw?c.t.bw/c.t.qw:-1}">${c.t.qw?`${c.t.bw} / ${c.t.qw}`:'—'}</td><td data-v="${c.L.length}">${c.L.length}</td><td data-v="${c.g?c.k/c.g:-1}">${c.g?`${c.k} / ${c.g}`:'<span class="dim">—</span>'}</td><td style="text-align:left"><span class="wkpcs">${c.best.map(x=>`<span class="wkpc ${x.res==null?'':x.res>0?'w':'l'}">${pn(x.name,x.team,true)}<i>${tp(x)!=null?Math.round(100*tp(x))+'%':''}</i>${x.res==null?'':`<b>${x.res>0?'✓':'✗'}</b>`}</span>`).join('')}</span></td></tr>`).join('')}</tbody></table></div></div>`;
      $('#wrBy').innerHTML=pointed+ranked;tWire($('#wrBy'));logoize($('#wrBy'));sortableAll($('#wrBy'));
      $('#wrBy').querySelectorAll('.wkpc[data-c]').forEach(c=>c.onclick=e=>{e.stopPropagation();toggleCat(c.dataset.c)})}
'''
s = s[:i] + new + s[j:]
# the scorers panel becomes a chip-opened modal, not a wall above the page
A2 = "    $('#wrSc').innerHTML=st.scope==='ahead'?scorerPanel():'';tWire($('#wrSc'));sortableAll($('#wrSc'));"
B2 = ("    {const html=st.scope==='ahead'&&typeof scorerPanel==='function'?scorerPanel():'';const nS=typeof liveScorers==='function'?liveScorers().length:0;\n"
      "      $('#wrSc').innerHTML=html?`<div class=\"mshd\" style=\"margin:0 0 8px\"><span class=\"btnlk\" data-th=\"${thReg(()=>({title:`how it went — week ${G.week}`,sub:`${nS} scorers so far · where each was ranked highest before kickoff · the board scorecard`,sections:[{html}]}))}\">how it went · ${nS} scorers · scorers mapped & board scorecard →</span></div>`:'';tWire($('#wrSc'))}")
assert s.count(A2) == 1; s = s.replace(A2, B2)
s = s.replace("/* v47 */th.nw{", "/* v49 */.wrp td,.wrc td{white-space:nowrap}.wrp td:nth-child(8),.wrc td:last-child{white-space:normal}.wrc tr:hover td{background:rgba(255,255,255,.03)}.wrc .wkpc,.wrp .wkpc{cursor:pointer}.wrc .a,.wrp .a{color:#e8b100}.wrc .g{color:var(--green)}.wrc .r{color:var(--red)}\n/* v47 */th.nw{", 1)
s = s.replace(" wkres:{what:'The Weeklies picks, by category, for the games ahead.',how:['opens on this week\\'s slate: one block per category with every player carrying it into his game (TD Picks chance, core-signal count; ✓ / ✗ land as games finish) — switch to the table for one row per player-game',",
              " wkres:{what:'What the categories say — and whether they were right.',how:['top: this week\\'s players ranked by the RELIABLE categories they carry (each weighted by how far above the field it hits this season) — the names at the top are the ones the categories agree on; ✓ / ✗ land as games finish','then every category ranked: verdict (trust / lean / noise / fade), season hit rate and × the field, weeks beaten, who carries it this week and how many scored — click a row for everyone, a chip to filter the page',", 1)
s = s.replace("Object.assign(NOTES,{v48:", "Object.assign(NOTES,{v49:['v49','Results rebuilt: who the reliable categories point at this week (ranked), then every category ranked by verdict and record with this week\\'s carriers and scorers \\u2014 the 27 name-walls are gone; the scorers-mapped table sits behind a chip']});\nObject.assign(NOTES,{v48:", 1)
io.open(T, 'w', encoding='utf-8').write(s)
print('v49 applied', len(s))
