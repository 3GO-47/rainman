"""v38 — (a) every player card lists the Weeklies categories he carries into the week and what he carried in each played week;
(b) Weeklies v2 / Category Grid v2 category pop-ups list the qualifying players week by week (v1's signal pane does this; v2 only
showed the numbers). Rerunnable."""
import io, sys
T = 'scripts/dashboard_template.html'
s = io.open(T, encoding='utf-8').read()
if 'function wkPlayerCats(' in s:
    print('already applied'); sys.exit(0)

def rep(old, new, n=1):
    global s
    c = s.count(old); assert c == n, ('match count %d != %d for: %s' % (c, n, old[:100])); s = s.replace(old, new)

# (a) player card
fn = r'''/* v38: the Weeklies categories a player carries — on his card */
function wkPlayerCats(n){try{if(typeof wkFeat!=='function')return '';const S=LAST_SE,F=wkFeat(S),SG=wkSigs();if(!F.rows.length)return '';
  const TR=wkTrust(x=>true,SG,'card38'),W0=J.week||1;
  const ah=wkAhead(u=>u.player===n,TR,W0).find(x=>x.name===n);
  const hist=F.rows.filter(x=>x.name===n&&F.weeks.includes(x.w)).sort((a,b)=>b.w-a.w).slice(0,8);
  const ahead=ah?(ah.on||SG.filter(z=>z.f(ah))):[];
  if(!ahead.length&&!hist.length)return '';
  const chip=z=>`<span class="wkpc ${z.kind==='neg'?'l':'w'}" title="${esc(z.long||'')}">${esc(z.lbl)}</span>`;
  return `<div class="panel" style="margin-top:8px"><h3>categories <span class="f">the Weeklies signals he carries into week ${W0}${ah&&ah.raw?' ('+esc(ah.raw)+')':''}, then what he carried into each played week · red chip = a fade</span></h3>
    <div class="wkpcs" style="margin-bottom:6px">${ahead.map(chip).join('')||'<span class="mini dim">none going into this week</span>'}</div>
    ${hist.length?`<table class="fx"><thead><tr><th>week</th><th>opp</th><th style="text-align:left">carried</th><th>TDs</th></tr></thead><tbody>${hist.map(h=>`<tr><td>${h.w}</td><td>${h.l?tcell(h.l[LOG.opp]):''}</td><td style="text-align:left">${SG.filter(z=>z.f(h)).map(z=>`<span class="${z.kind==='neg'?'dim':''}">${esc(z.lbl)}</span>`).join(' · ')||'<span class="dim">—</span>'}</td><td>${h.td>0?'<b style="color:var(--green)">✓ '+h.td+'</b>':'<span style="color:var(--red)">✗</span>'}</td></tr>`).join('')}</tbody></table>`:''}</div>`}catch(e){return ''}}
'''
rep("window.playerPop=function(n){", fn + "window.playerPop=function(n){")
rep("   <p style=\"margin-top:10px\"><button class=\"mclose\" style=\"position:static\" id=\"ppDeepBtn\">open full deep dive &rarr;</button></p>",
    "   ${wkPlayerCats(n)}\n   <p style=\"margin-top:10px\"><button class=\"mclose\" style=\"position:static\" id=\"ppDeepBtn\">open full deep dive &rarr;</button></p>")

# (b) Weeklies v2: qualifiers week by week in every category pop-up
w2 = r'''    const sigRows2=s=>()=>{const p=sigRows(s)();const Q=[];AL.slice().reverse().forEach(a=>a.P.filter(s.f).sort((x,y)=>y.td-x.td).forEach(x=>Q.push(Object.assign([a.w,pn(x.name,x.team,true),tcell(x.team),slotchip(x.slot),w2opp(x),x.td,x.cs,w2res(x)],{hi:a.w===W}))));
      p.sections=[{cols:p.cols,rows:p.rows},{h:`everyone who carried it, week by week · ${Q.length} player-games`,cols:[{l:'week',g:false},'player','team',{l:'slot',g:false},{l:'opp',g:false},{l:'TDs',g:false},{l:'signals',t:'how many of the eight core signals he carried'},{l:'scored',g:false}],rows:Q}];return p};
'''
rep("    const who=s=>()=>({title:esc(s.lbl)+` · week ${W}`,", w2 + "    const who=s=>()=>({title:esc(s.lbl)+` · week ${W}`,")
rep("[wkRows,pos[0]?sigRows(pos[0]):null,steady?sigRows(steady.s):null,fade?sigRows(fade.s):null].filter(Boolean)",
    "[wkRows,pos[0]?sigRows2(pos[0]):null,steady?sigRows2(steady.s):null,fade?sigRows2(fade.s):null].filter(Boolean)")
rep("return `<div class=\"w2row\" data-th=\"${thReg(sigRows(r.s))}\">", "return `<div class=\"w2row\" data-th=\"${thReg(sigRows2(r.s))}\">")

# (b) Category Grid v2: who carries it into the week + qualifiers per played week
g2 = r'''    const cat2=r=>()=>{const p=cat(r)();const now=R.filter(x=>x.cells[r.s.id]&&x.cells[r.s.id].now).sort((a,b)=>(wgTp(b)??-1)-(wgTp(a)??-1));
      const Q=[];D.Wk.slice().reverse().forEach(w=>{const a=wkStats(F,w,w2keep,SG);a.P.filter(r.s.f).sort((x,y)=>y.td-x.td).forEach(x=>Q.push([w,pn(x.name,x.team,true),tcell(x.team),slotchip(x.slot),w2opp(x),x.td,w2res(x)]))});
      p.sections=[{cols:p.cols,rows:p.rows},{h:`carrying it into week ${W0} · ${now.length} starters`,cols:['player','team',{l:'slot',g:false},{l:'opp',g:false},{l:'TD %',t:'TD Picks chance'},{l:'categories',t:'reliable categories he carries'},{l:'result',g:false}],rows:now.map(x=>[pn(x.name,x.team,true),tcell(x.team),slotchip(x.slot),w2opp(x),x.tp?{v:x.tp.p,h:Math.round(100*x.tp.p)+'%'}:null,x.cat,x.done?w2res(x.done):'—'])},
        {h:`everyone who carried it in a played week · ${Q.length} player-games`,cols:[{l:'week',g:false},'player','team',{l:'slot',g:false},{l:'opp',g:false},{l:'TDs',g:false},{l:'scored',g:false}],rows:Q}];return p};
'''
rep("    const hist=()=>{const wks=F.weeks.concat([Math.max(...F.weeks)+1]).filter(w=>w>=2);", g2 + "    const hist=()=>{const wks=F.weeks.concat([Math.max(...F.weeks)+1]).filter(w=>w>=2);")
rep("      [hist,...(top?[cat(top)]:[]),hist,...(B[0]?[hist]:[]),hist]);", "      [hist,...(top?[cat2(top)]:[]),hist,...(B[0]?[hist]:[]),hist]);")
rep("const cbar=(r,tone)=>`<div class=\"g2cat\" data-th=\"${thReg(cat(r))}\"", "const cbar=(r,tone)=>`<div class=\"g2cat\" data-th=\"${thReg(cat2(r))}\"")
s = s.replace("Object.assign(NOTES,{v37:", "Object.assign(NOTES,{v38:['v38','every player card lists the Weeklies categories he carries into the week and what he carried each played week \\u00b7 the category pop-ups on Weeklies v2 / Category Grid v2 list every qualifying player week by week']});\nObject.assign(NOTES,{v37:", 1)
io.open(T, 'w', encoding='utf-8').write(s)
print('v38 applied', len(s))
