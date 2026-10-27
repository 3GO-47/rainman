"""sport template v4c: the signal backtest carries last season in as the prior (so the first weeks of a season grade),
and the reused views render into the section they now live in. Rerunnable (guarded)."""
import os, sys
P = os.path.join(os.path.dirname(os.path.abspath(__file__)), 'sport_template.html')
s = open(P, encoding='utf-8').read()
if 'const PRIOR_W=5' in s:
    print('already applied'); sys.exit()
def rep(old, new):
    global s
    assert s.count(old) == 1, (s.count(old), old[:90])
    s = s.replace(old, new)
a = s.index('let _BT=null;function BT(){'); b = s.index('  return _BT=out}', a) + len('  return _BT=out}')
s = s[:a] + r"""const PRIOR_W=5;   /* a season's first games grade against last season's average blended in with the weight of five games */
let _BT=null;function BT(){if(_BT)return _BT;const out=[];const byP={};J.logs.forEach(l=>{(byP[l[LC.pid]]=byP[l[LC.pid]]||[]).push(l)});
  Object.entries(byP).forEach(([pid,L])=>{L.sort((a,b)=>a[LC.date]<b[LC.date]?-1:1);const V={};MK.forEach(mk=>V[mk.k]=L.map(l=>lval(l,mk.k)));const M=L.map(l=>+l[LC.min]);const SE=L.map(l=>l[LC.season]);
    const avg=a=>a.length?a.reduce((x,y)=>x+y,0)/a.length:null;
    const seOf=(arr,i)=>{const sn=SE[i];let j=i;while(j>0&&SE[j-1]===sn)j--;const cur=arr.slice(j,i);const pr=[];for(let q=j-1;q>=0&&SE[q]===sn-1;q--)pr.push(arr[q]);const pm=avg(pr);
      if(cur.length>=PRIOR_W||pm==null)return cur.length>=PRIOR_W?avg(cur):null;return (cur.reduce((x,y)=>x+y,0)+pm*(PRIOR_W-cur.length))/PRIOR_W};
    L.forEach((l,i)=>{const opp=l[LC.opp],slot=l[LC.slot],season=String(l[LC.season]);const mse=seOf(M,i);if(mse==null)return;const m5=avg(M.slice(Math.max(0,i-5),i));
      const prevAll=[];for(let q=0;q<i;q++)if(L[q][LC.opp]===opp)prevAll.push(L[q]);const dv=J.dvp[season]&&J.dvp[season][opp]&&J.dvp[season][opp][slot];
      MK.forEach(mk=>{const k=mk.k;const se=seOf(V[k],i);if(se==null)return;const S={rank:dv&&dv[k]?dv[k].rank:null,se,l5:avg(V[k].slice(Math.max(0,i-5),i)),mse,m5,h2n:prevAll.length,h2:avg(prevAll.map(x=>lval(x,k))),home:l[LC.ha]==='H',pace:PACE_RK[opp],edge:null};
        out.push({date:l[LC.date],season:+season,pid,team:l[LC.team],opp,slot,k,v:V[k][i],se,hit:V[k][i]>se,on:sigOn(S)})})})});
  return _BT=out}""" + s[b:]
rep("function lab(){const el=$('#players');", "function lab(){const el=$('#match');")
rep("function bestpicks(){const el=$('#home');", "function bestpicks(){const el=$('#'+ITEMS[G.sub].sec.id);")
rep("these lifts are the META weights','opponent rank uses that season\\'s final ranks — a small look-ahead']}",
    "these lifts are the META weights','opponent rank uses that season\\'s final ranks — a small look-ahead','a season\\'s first games grade against last season\\'s average, blended in with the weight of five games']}")
open(P, 'w', encoding='utf-8').write(s)
print('applied')
