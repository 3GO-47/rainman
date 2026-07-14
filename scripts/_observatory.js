/* ---------- Defense Observatory: comparative field physics ---------- */
let dChart,rChart,phChart;
function defense(){
  const defs=[...new Set(J.weekly.map(r=>r[0]))].sort();
  const seasons=[...new Set(J.weekly.map(r=>r[1]))].sort();
  const latest=Math.max(...seasons);
  $('#defense').innerHTML=`
  <div class="controls">
    <select id="dDef">${defs.map(d=>`<option>${d}</option>`).join('')}</select>
    <span class="mini">⟷ interfere with</span>
    <select id="dCmp">${defs.map(d=>`<option ${d===defs[1]?'selected':''}>${d}</option>`).join('')}</select>
    <select id="dSea">${seasons.map(x=>`<option ${x===latest?'selected':''}>${x}</option>`).join('')}</select>
    <select id="dSlot">${J.slots.map(x=>`<option>${x}</option>`).join('')}</select>
    <select id="dStat">${J.statCols.map(c=>`<option>${c}</option>`).join('')}</select>
  </div>
  <div id="dHero" class="panel"></div>
  <div class="grid2">
    <div class="panel"><h3 id="dTitle"></h3><canvas id="dCanvas" class="chart"></canvas></div>
    <div class="panel"><h3 id="rTitle"></h3><canvas id="rCanvas" class="chart"></canvas></div>
  </div>
  <div class="panel"><h3 id="specTitle"></h3><div id="dSpectrum"></div>
    <div class="specscale"><span>&Psi; 1 &middot; FUSION — leaks everything</span><span>&Psi; 32 &middot; EVENT HORIZON — nothing escapes</span></div></div>
  <div class="grid2">
    <div class="panel"><h3 id="phTitle"></h3><canvas id="phCanvas" class="chart"></canvas></div>
    <div class="panel" id="dTrend"></div>
  </div>`;
  const AX={ticks:{color:'#5d7186'},grid:{color:'#1c2836'}};
  function render(){
    const d=$('#dDef').value,b=$('#dCmp').value,se=+$('#dSea').value,
          slot=$('#dSlot').value,c=$('#dStat').value;
    const D=J.dvp[String(se)]||J.dvp.combined;
    const CA=vivid(d),CB=vivid(b);
    /* hero banner */
    $('#dHero').innerHTML=`<div style="display:flex;align-items:center;gap:16px;flex-wrap:wrap;padding:5px 8px;
      background:linear-gradient(90deg,${hex2rgba(CA,.22)},transparent 65%);border-left:3px solid ${CA}">
      ${tlogo(d,44)}<div><div style="font-size:16px;letter-spacing:2px;color:#fff">${TEAM[d].n.toUpperCase()} DEFENSE</div>
      <div class="mini">season ${se} &middot; &Psi; field strength by slot</div></div>
      <div style="display:flex;gap:8px;flex-wrap:wrap">${J.slots.map(sl=>{
        const v=(D[d]||{comps:{}}).comps[sl];
        return `<span class="mini" style="text-align:center">${sl}<br>${v==null?'—':badge(v)}</span>`}).join('')}</div></div>`;
    /* worldline vs league band vs rival */
    const rows=J.weekly.filter(r=>r[0]===d&&r[1]===se).sort((x,y)=>x[2]-y[2]);
    const lg={};
    [...new Set(J.weekly.filter(r=>r[1]===se).map(r=>r[2]))].forEach(w=>{
      const v=J.weekly.filter(r=>r[1]===se&&r[2]===w).map(r=>r[WCOL[c]]);
      lg[w]={m:mean(v),sd:stdev(v)}});
    const bMap={};J.weekly.filter(r=>r[0]===b&&r[1]===se).forEach(r=>bMap[r[2]]=r[WCOL[c]]);
    const xs=rows.map(r=>'wk'+r[2]),ys=rows.map(r=>r[WCOL[c]]);
    $('#dTitle').innerHTML=`${tlogo(d)} worldline — ${c} <span class="f">vs league μ±σ field and ${b}</span>`;
    if(dChart)dChart.destroy();
    dChart=new Chart($('#dCanvas'),{type:'line',data:{labels:xs,datasets:[
      {label:d,data:ys,borderColor:CA,backgroundColor:hex2rgba(CA,.12),tension:.32,borderWidth:2.6,pointRadius:3},
      {label:b,data:rows.map(r=>bMap[r[2]]??null),borderColor:CB,borderDash:[7,4],tension:.32,pointRadius:2,spanGaps:true},
      {label:'league μ',data:rows.map(r=>+lg[r[2]].m.toFixed(1)),borderColor:'#5d7186',borderDash:[3,4],pointRadius:0},
      {label:'μ+σ',data:rows.map(r=>+(lg[r[2]].m+lg[r[2]].sd).toFixed(1)),borderColor:'transparent',pointRadius:0,fill:'+1',backgroundColor:'rgba(97,220,255,.08)'},
      {label:'μ−σ',data:rows.map(r=>+Math.max(0,lg[r[2]].m-lg[r[2]].sd).toFixed(1)),borderColor:'transparent',pointRadius:0}]},
      options:{plugins:{legend:{labels:{color:'#cfdcea',filter:i=>!i.text.includes('σ')}}},
      scales:{x:AX,y:AX}}});
    /* interference radar */
    $('#rTitle').innerHTML=`interference — ${tlogo(d)}${d} vs ${tlogo(b)}${b} <span class="f">permeability = 33−&Psi; &middot; season ${se}</span>`;
    if(rChart)rChart.destroy();
    const perm=t=>J.slots.map(sl=>{const v=(D[t]||{comps:{}}).comps[sl];return v==null?0:+(33-v).toFixed(1)});
    rChart=new Chart($('#rCanvas'),{type:'radar',data:{labels:J.slots,datasets:[
      {label:d,data:perm(d),borderColor:CA,backgroundColor:hex2rgba(CA,.20),pointBackgroundColor:CA},
      {label:b,data:perm(b),borderColor:CB,backgroundColor:hex2rgba(CB,.14),pointBackgroundColor:CB}]},
      options:{scales:{r:{min:0,max:32,ticks:{display:false},grid:{color:'#1c2836'},
        angleLines:{color:'#1c2836'},pointLabels:{color:'#cfdcea',font:{family:'monospace',size:11}}}},
        plugins:{legend:{labels:{color:'#cfdcea'}}}}});
    /* energy spectrum: all 32 defenses on one axis */
    $('#specTitle').innerHTML=`energy spectrum — every defense vs ${slot} <span class="f">(position = &Psi; composite &middot; hover for value &middot; season ${se})</span>`;
    const list=Object.keys(D).map(t=>({t,v:D[t].comps[slot]})).filter(x=>x.v!=null).sort((x,y)=>x.v-y.v);
    $('#dSpectrum').innerHTML=`<div class="specband">${list.map((x,i)=>{
      const cls=x.t===d?'selA':x.t===b?'selB':'';
      return `<img class="${cls}" title="${x.t} — Ψ ${x.v.toFixed(1)} vs ${slot}" src="${LOGO(x.t)}"
        style="left:${(3+94*(x.v-1)/31).toFixed(2)}%;top:${10+(i%3)*26}px">`}).join('')}</div>`;
    /* phase portrait: season μ vs last-3 μ, every defense */
    const stat2=J.primary[slot];
    const pts=defs.map(t=>{const rw=J.weekly.filter(r=>r[0]===t&&r[1]===se).sort((x,y)=>x[2]-y[2])
        .map(r=>r[WCOL[stat2]]);
      return {t,x:+mean(rw).toFixed(1),y:+mean(rw.slice(-3)).toFixed(1)}});
    const lo=Math.min(...pts.map(p=>Math.min(p.x,p.y))),hi=Math.max(...pts.map(p=>Math.max(p.x,p.y)));
    $('#phTitle').innerHTML=`phase portrait — ${slot} <span class="f">(${stat2}: season μ vs last-3 μ &middot; above diagonal = collapsing &middot; below = tightening)</span>`;
    if(phChart)phChart.destroy();
    phChart=new Chart($('#phCanvas'),{data:{datasets:[
      {type:'scatter',label:'defenses',data:pts,parsing:false,
        pointStyle:pts.map(p=>logoPt(p.t,p.t===d||p.t===b?30:20)),
        borderColor:pts.map(p=>p.t===d?CA:p.t===b?CB:'transparent'),borderWidth:2},
      {type:'line',label:'equilibrium',data:[{x:lo,y:lo},{x:hi,y:hi}],borderColor:'#5d7186',
        borderDash:[5,5],pointRadius:0}]},
      options:{plugins:{legend:{display:false},tooltip:{callbacks:{
        label:ctx=>ctx.raw.t?`${ctx.raw.t}: season ${ctx.raw.x} · last3 ${ctx.raw.y}`:''}}},
      scales:{x:{...AX,title:{display:true,text:'season μ '+stat2,color:'#5d7186'}},
              y:{...AX,title:{display:true,text:'last-3 μ',color:'#5d7186'}}}}});
    /* momentum + uncertainty table */
    $('#dTrend').innerHTML=`<h3>${tlogo(d)} momentum &amp; uncertainty <span class="f">last 4 wks vs season ${se}</span></h3>
      <table><thead><tr><th>slot</th><th>stat</th><th>μ/gm</th><th>last4</th><th>Δp</th><th>σ</th><th>σ/μ</th></tr></thead><tbody>
      ${J.slots.map(sl=>{const c2=J.primary[sl];const all=rows.map(r=>r[WCOL[c2]]);
        const mm=mean(all),m4=mean(all.slice(-4)),sd=stdev(all);
        const pct=mm?100*(m4-mm)/mm:0,cv=mm?100*sd/mm:0;
        const arrow=pct>15?'<span class="up">&#9650;</span>':pct<-15?'<span class="dn">&#9660;</span>':'&middot;';
        return `<tr><td>${sl}</td><td class="mini">${c2}</td><td>${mm.toFixed(1)}</td><td>${m4.toFixed(1)}</td>
        <td>${arrow} <span class="${pct>15?'up':pct<-15?'dn':'mini'}">${pct>=0?'+':''}${pct.toFixed(0)}%</span></td>
        <td class="mini">${sd.toFixed(1)}</td><td class="mini">${cv.toFixed(0)}%</td></tr>`}).join('')}</tbody></table>
      <p class="note">Δp &gt; 0 collapsing (allowing more) &middot; Δp &lt; 0 tightening &middot; σ/μ high = boom/bust, rank less trustworthy</p>`;
  }
  ['dDef','dCmp','dSea','dSlot','dStat'].forEach(id=>$('#'+id).onchange=render);
  render();
}
