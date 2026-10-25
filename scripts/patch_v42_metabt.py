"""v42 — META weights come from the walk-forward backtest (data/processed/meta_backtest.json → J.metaBT): Ψ + FORM + ENV carry
weight, the rest stay as columns; gamma / shrink switches follow the chosen recipe; a small "backtest" button in META's controls
opens the audit (grade, calibration bands, every recipe tried, single-signal skill, ablation, out-of-time holdout). Rerunnable."""
import io, sys
T = 'scripts/dashboard_template.html'
s = io.open(T, encoding='utf-8').read()
if 'const MBT=' in s:
    print('already applied'); sys.exit(0)
def rep(old, new, n=1):
    global s
    c = s.count(old); assert c == n, ('match count %d != %d for: %s' % (c, n, old[:100])); s = s.replace(old, new)

rep("const META_W=metaWeights();",
    "/* v42: the backtest decides — weights, bend (gamma) and shrink switches come from meta_backtest.json when it is embedded */\n"
    "const MBT=J.metaBT||null;const META_W=MBT&&MBT.weights?MBT.weights:metaWeights();const META_CFG=Object.assign({gamma:1,cov:true,agree:true},MBT&&MBT.cfg||{});\n"
    "const mbend=c=>{if(c==null||META_CFG.gamma===1)return c;const d=c-.5;return .5+Math.sign(d)*Math.pow(Math.abs(2*d),META_CFG.gamma)/2};")
rep("      let s=0,w=0,soft=0,hard=0,n=0;Object.entries(META_W).forEach(([k,wt])=>{if(c[k]!=null){s+=wt*c[k];w+=wt;n++;if(c[k]>=.65)soft++;else if(c[k]<=.35)hard++}});",
    "      let s=0,w=0,soft=0,hard=0,n=0;Object.entries(META_W).forEach(([k,wt])=>{if(wt>0&&c[k]!=null){const v=mbend(c[k]);s+=wt*v;w+=wt;n++;if(v>=.65)soft++;else if(v<=.35)hard++}});")
rep("      x.meta=w&&x.opp?50+(100*s/w-50)*(.6+.4*w/W)*(.75+.25*agree):null});",
    "      x.meta=w&&x.opp?50+(100*s/w-50)*(META_CFG.cov?(.6+.4*w/W):1)*(META_CFG.agree?(.75+.25*agree):1):null});")
# note + button
rep("<b>META</b> folds every other column into one score, 0–100 (100 = the softest spot on every signal), weighted by each signal's measured lift this season (${Object.entries(META_W).map(([k,v])=>LBL[k].replace('META','')+' '+Math.round(100*v)+'%').join(' · ')})",
    "<b>META</b> = one score, 0–100 (100 = the softest spot). ${MBT?`Its recipe is the walk-forward backtest's pick: ${Object.entries(META_W).filter(([k,v])=>v>0).map(([k,v])=>LBL[k]+' '+Math.round(100*v)+'%').join(' · ')} — the other columns stay for the read but carry no weight (none adds to Ψ out of sample). Over ${MBT.rows} starter-games it ranks production vs the player's own baseline at rho ${MBT.chosen_oos.rho} (v40's hand weights: ${(MBT.variants.find(v=>v.name.startsWith('v40'))||{}).rho}); its top tenth produced ${Math.round(100*(MBT.chosen_oos.dec_top-1))}% over baseline, its bottom tenth ${Math.round(100*(MBT.chosen_oos.dec_bot-1))}%.`:`weighted by each signal's measured lift this season (${Object.entries(META_W).map(([k,v])=>LBL[k].replace('META','')+' '+Math.round(100*v)+'%').join(' · ')})`}")
rep("    <input id=\"${px}Q\" placeholder=\"search player...\" size=\"15\">\n    <span class=\"note\">every board at once.",
    "    <input id=\"${px}Q\" placeholder=\"search player...\" size=\"15\">${MBT?` <span class=\"btnlk\" data-th=\"${thReg(metaBtPane)}\" title=\"how the META recipe was chosen and how it grades out of sample\">backtest</span>`:''}\n    <span class=\"note\">every board at once.")
# the pane
rep("function metaGrid(root='#meta',px='mt'){",
    "function metaBtPane(){const B=MBT;if(!B)return null;const f=(v,d=3)=>v==null?null:{v:+v,h:(+v).toFixed(d)};const pc=v=>v==null?null:{v:+v,h:Math.round(100*v)+'%'};\n"
    "  const W=B.weights||{},SD=B.weights_sd||{};const lbl={psi:'Ψ',td:'TD',sch:'SCH',h2h:'H2H',atd:'ATD',env:'ENV',form:'FORM'};\n"
    "  const sec=[];\n"
    "  sec.push({h:`the recipe · ${esc(B.chosen||'')}`,note:`weights refit on everything after the walk-forward grade · gamma ${B.cfg&&B.cfg.gamma||1} bends each 0–1 component toward its extremes · ± = bootstrap spread of the weight (30 resamples)`,\n"
    "    cols:['signal',{l:'weight',t:'share of META'},{l:'± sd',g:false},{l:'rho alone',t:'Spearman rho of the component alone with actual / baseline'},{l:'rho without',t:'walk-forward rho of the 7-signal NNLS recipe with this signal removed — higher than with = it was not helping',lo:false}],\n"
    "    rows:Object.keys(lbl).map(k=>[lbl[k],W[k]!=null?pc(W[k]):{v:0,h:'<span class=\"dim\">0</span>'},SD[k]!=null?'±'+Math.round(100*SD[k])+'%':'',B.single&&B.single[k]?f(B.single[k].rho,3):null,B.ablation&&B.ablation[k]?f(B.ablation[k].rho_without,4):null])});\n"
    "  sec.push({h:'calibration · walk-forward META band → what happened',note:'actual PPR / his own pre-game baseline · over = share of games above baseline · TD = share with a rushing or receiving TD',\n"
    "    cols:[{l:'META',g:false},{l:'n',g:false},{l:'ratio',t:'mean actual / baseline'},{l:'over',t:'share above baseline'},{l:'TD rate'},{l:'PPR',t:'mean actual PPR'}],\n"
    "    rows:(B.bands||[]).map(b=>[b.band,b.n,f(b.ratio),pc(b.over),pc(b.td),f(b.ppr,1)])});\n"
    "  if(B.holdout)sec.push({h:`out-of-time check · signals chosen on ${B.holdout.selected_on} alone (${(B.holdout.signals||[]).map(k=>lbl[k]||k).join(' + ')}), graded on ${B.holdout.tested_on}`,\n"
    "    cols:['set',{l:'rho'},{l:'lift',t:'mean ratio, top third − bottom third'},{l:'top decile',t:'mean ratio in the top tenth'},{l:'n',g:false}],\n"
    "    rows:[['selected',B.holdout.selected],['all seven',B.holdout.all7],['Ψ alone',B.holdout.psi_only]].filter(r=>r[1]).map(([n,v])=>[n,f(v.rho,4),f(v.lift),f(v.dec_top),v.n])});\n"
    "  sec.push({h:`every recipe tried · ${B.rows} starter-games · walk-forward = weights learned only from earlier weeks · one standard error of rho ≈ ${B.extra&&B.extra.se_rho||''}`,\n"
    "    cols:['recipe',{l:'rho'},{l:'lift'},{l:'top decile'},{l:'bottom decile',lo:true},{l:'over · top decile',t:'share above baseline in the top tenth'},{l:'n',g:false}],\n"
    "    rows:(B.variants||[]).slice().sort((a,b)=>b.rho-a.rho).map(v=>Object.assign([`<span title=\"${esc(v.note||'')}\">${esc(v.name)}</span>`,f(v.rho,4),f(v.lift),f(v.dec_top),f(v.dec_bot),pc(v.over_dec_top),v.n],{hi:v.name===B.chosen}))});\n"
    "  if(B.by_pos)sec.push({h:'the chosen recipe by position (walk-forward)',cols:['pos',{l:'rho'},{l:'lift'},{l:'top decile'},{l:'n',g:false}],rows:Object.entries(B.by_pos).filter(([p,v])=>v).map(([p,v])=>[p,f(v.rho,4),f(v.lift),f(v.dec_top),v.n])});\n"
    "  if(B.forward)sec.push({h:'greedy forward selection (walk-forward rho after each add)',cols:['add',{l:'rho'},{l:'gain'},{l:'kept',g:false}],rows:B.forward.map(x=>[lbl[x.add]||x.add,f(x.rho,4),f(x.gain,4),x.kept?'yes':'no — under +0.002'])});\n"
    "  sec.push({h:'notes',html:`<ul class=\"mini\">${(B.notes||[]).map(n=>`<li>${esc(n)}</li>`).join('')}</ul>`});\n"
    "  return {title:'META backtest',sub:`built ${B.built} · outcome = actual PPR / his pre-game baseline`,sections:sec}}\n"
    "function metaGrid(root='#meta',px='mt'){")
rep("/* v41 META slate panel */", "/* v42 */.btnlk{cursor:pointer;border:1px solid var(--edge);border-radius:4px;padding:2px 7px;font-size:11px;color:var(--fg);background:var(--panel)}.btnlk:hover{border-color:#e8b100;color:#e8b100}\n/* v41 META slate panel */")
rep(" meta:{what:'Every board at once.',how:['META = every signal in one score, 0\u2013100 \u2014 100 = the softest spot on all of them; hover a META cell for the breakdown',",
    " meta:{what:'Every board at once.',how:['META = one score, 0\u2013100 \u2014 100 = the softest spot; its recipe is what the walk-forward backtest picked (\u03a8 56% \u00b7 FORM 34% \u00b7 ENV 10% \u2014 the other columns are reads, not weights) \u00b7 hover a META cell for the breakdown, the backtest chip for the audit','ENV = his team\\'s implied points from the line \u00b7 FORM = his opportunities over the last two games vs his season rate',")
s = s.replace("Object.assign(NOTES,{v41:", "Object.assign(NOTES,{v42:['v42','META is now the walk-forward backtest\\'s recipe: \\u03a8 + FORM + ENV carry the weight, the other columns stay as reads \\u00b7 a backtest button in META\\'s controls opens the audit (grade, calibration, every recipe tried, out-of-time holdout)']});\nObject.assign(NOTES,{v41:", 1)
io.open(T, 'w', encoding='utf-8').write(s)
print('v42 applied', len(s))
