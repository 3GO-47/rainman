/* RAINMAN game simulator — browser port of scripts/sim_engine.py, snap for snap.
   simulate(PR, game, n, seed, onProgress) -> the same summary shape the Python engine writes to sim_games.json.
   PR is the sim_params payload (league tables, team / coordinator profiles, players, calibration). */
(function(root){
const ZONES=['own','mid','plus','rz'],TGS=['s','m','l','x'],SDS=['T2','T1','E','L1','L2'],TS=['H1','H1late','H2','late'];
const GRP={QB1:'QB',QB2:'QB',RB1:'RB1',RB2:'RB2',RB3:'RB2',TE1:'TE1',TE2:'TE2',TE3:'TE2',TE4:'TE2',WR1:'WR1',WR2:'WR2',WR3:'WR3','WR4+':'WR4+'};
function rng(seed){let a=(seed>>>0)||1;return function(){a|=0;a=a+0x6D2B79F5|0;let t=Math.imul(a^a>>>15,1|a);t=t+Math.imul(t^t>>>7,61|t)^t;return((t^t>>>14)>>>0)/4294967296}}
const clip=(v,lo,hi)=>v<lo?lo:v>hi?hi:v,logit=p=>{p=clip(p,1e-4,1-1e-4);return Math.log(p/(1-p))},sig=x=>1/(1+Math.exp(-x));
const zone=yl=>yl<=20?3:yl<=49?2:yl<=79?1:0,tgb=t=>t<=2?0:t<=6?1:t<=10?2:3,sdb=d=>d<=-9?0:d<0?1:d===0?2:d<=8?3:4,tb=s=>s>2100?0:s>1800?1:s>300?2:3,rzb=y=>y<=3?0:y<=6?1:y<=10?2:y<=15?3:4;
function fgp(L,dist){return dist<30?L.fg['<30']:dist<40?L.fg['30-39']:dist<50?L.fg['40-49']:dist<55?L.fg['50-54']:dist<60?L.fg['55-59']:L.fg['60+']}
function tables(L){
  const PP={};for(let d=1;d<=4;d++)for(const tg of TGS)for(const z of ZONES)for(const sd of SDS)for(const t of TS){const k=`${d}|${tg}|${z}|${sd}|${t}`;PP[k]=L.pass_prob[k]!=null?L.pass_prob[k]:(L.pass_by_down[d]!=null?L.pass_by_down[d]:L.pass_rate)}
  return PP}
function Team(PR,team,opp,home){
  const L=PR.league,T=PR.teams[team],D=PR.teams[opp].de,O=T.off,g=(d,k,df)=>d[k]==null?df:d[k];const lgp=L.pass_epa,lgr=L.rush_epa;
  const cfg=PR.cfg||{},KP=cfg.kp!=null?cfg.kp:1.0,KR=cfg.kr!=null?cfg.kr:1.1;this.name=team;this.home=home;
  this.pass_shift=logit(clip(L.pass_rate+g(O,'proe',0)/100,.3,.8))-logit(L.pass_rate);this.rz_pass=g(O,'rz_pass_rate',.55);
  this.mp=clip(1+KP*(g(O,'pass_epa',lgp)-lgp)+KP*(g(D,'pass_epa_allowed',lgp)-lgp),.6,1.5);this.mr=clip(1+KR*(g(O,'rush_epa',lgr)-lgr)+KR*(g(D,'rush_epa_allowed',lgr)-lgr),.6,1.5);
  let edge=L.home_edge;if(cfg.home_team&&L.home_edges){const e=L.home_edges[home?team:opp];if(e!=null)edge=e}
  const hm=1+(edge/2)*.013*(home?1:-1);this.mp*=hm;this.mr*=hm;
  this.def_comp=g(D,'pbp_comp',L.comp_rate);this.def_int=g(D,'pbp_int_rate',L.int_rate);this.def_sack=g(D,'pbp_sack_rate',L.sack_rate);
  this.exp_pass=L.explosive_pass*Math.pow(g(O,'pbp_expl_pass',L.explosive_pass)/L.explosive_pass,.6)*Math.pow(g(D,'pbp_expl_pass',L.explosive_pass)/L.explosive_pass,.6);
  this.exp_rush=L.explosive_rush*Math.pow(g(O,'pbp_expl_rush',L.explosive_rush)/L.explosive_rush,.6)*Math.pow(g(D,'pbp_expl_rush',L.explosive_rush)/L.explosive_rush,.6);
  this.pace=g(O,'pace_factor',1);this.aggr=Math.pow(g(O,'fourth_aggr',1),.5);
  const rates=Object.values(PR.teams).map(v=>v.rz.off_td_rate).filter(v=>v!=null);const rzl=rates.length?rates.reduce((a,b)=>a+b,0)/rates.length:.58;
  const shr=(rz,k,nk)=>(g(rz,k,rzl)*g(rz,nk,0)+rzl*30)/(g(rz,nk,0)+30);
  this.rzf=clip(Math.pow(shr(T.rz,'off_td_rate','off_trips')/rzl,.5)*Math.pow(shr(PR.teams[opp].rz,'def_td_rate','def_trips')/rzl,.5),.85,1.18);
  const slot_idx=D.slot_idx||{},P=PR.players[team].players,pm=L.pos_means;
  const qbs=P.filter(p=>p.pos==='QB');this.qb=qbs[0]||{name:'QB',comp:L.comp_rate,ypa:pm.QB.ypa,int_rate:L.int_rate,sack_rate:L.sack_rate,scramble:L.scramble_rate,ypc:4.5};const q=this.qb;
  this.comp_shift=.8*(g(q,'comp',L.comp_rate)-L.comp_rate)+.7*(this.def_comp-L.comp_rate);
  this.int_rate=clip(L.int_rate*Math.pow(g(q,'int_rate',L.int_rate)/L.int_rate,.6)*Math.pow(this.def_int/L.int_rate,.6),.005,.06);
  this.sack_rate=clip(L.sack_rate*Math.pow(g(q,'sack_rate',L.sack_rate)/L.sack_rate,.7)*Math.pow(this.def_sack/L.sack_rate,.7),.02,.14);
  this.scramble=g(q,'scramble',L.scramble_rate);this.mp*=Math.pow(clip(g(q,'ypa',pm.QB.ypa)/pm.QB.ypa,.8,1.2),.5);
  this.R=P.filter(p=>p.pos!=='QB'&&p.tgt_w>0);let w=this.R.map(p=>p.tgt_w*(slot_idx[GRP[p.slot]||'WR4+']||1));let s=w.reduce((a,b)=>a+b,0);w=w.map(x=>s?x/s:x);
  let rz=this.R.map((p,i)=>p.rz_share!=null?p.rz_share:w[i]);s=rz.reduce((a,b)=>a+b,0);rz=s?rz.map(x=>x/s):w;
  const cum=a=>{let c=0;return a.map(x=>c+=x)};this.w=w;this.tw=cum(w);this.tw_rz=cum(w.map((x,i)=>.5*x+.5*rz[i]));
  this.catch_adj=this.R.map(p=>.8*(p.catch-pm[p.pos].catch));this.ypt_r=this.R.map(p=>Math.pow(clip(p.ypt/pm[p.pos].ypt,.7,1.4),.5));
  const MZ=L.mz||{};if(cfg.mz&&MZ.receivers){let m=D.man_rate;m=m==null?(MZ.man_share||.4):+m;this.ypt_r=this.ypt_r.map((v,i)=>{const z=MZ.receivers[this.R[i].gsis||''];return z?v*Math.pow(clip(m*z.man+(1-m)*z.zone,.8,1.25),.7):v});
    const sy=Math.max(...MZ.seasons);const oz=MZ.offenses[sy+'|'+(O.oc_prior_unit||team)]||MZ.offenses[sy+'|'+team];if(oz)this.mp*=clip(1+KP*(m*oz.man+(1-m)*oz.zone),.9,1.1);this.man_rate=m}
  this.U=P.filter(p=>p.rush_w>0);let rw=this.U.map(p=>p.pos==='QB'?Math.max(0,p.rush_w-this.scramble*36/26):p.rush_w);s=rw.reduce((a,b)=>a+b,0);rw=rw.map(x=>x/s);
  let gl=this.U.map(p=>p.gl_rush||0);s=gl.reduce((a,b)=>a+b,0);gl=s?gl.map(x=>x/s):rw;
  this.rw=cum(rw);this.rw_gl=cum(rw.map((x,i)=>.5*x+.5*gl[i]));this.ypc_r=this.U.map(p=>Math.pow(clip(p.ypc/pm[p.pos].ypc,.75,1.3),.5));
  this.qb_ypc=Math.pow(clip(g(q,'ypc',4.5)/4.5,.7,1.4),.5)}
function pick(cum,u){let i=0;while(i<cum.length-1&&u>cum[i])i++;return i}
function simulate(PR,game,n,seed,onProgress){
  const L=PR.league,R=rng(seed||7),PP=tables(L),CB=PR.calib||{},c_pass=CB.pass_logit||0,c_yard=CB.yard_scale||1,c_td=CB.td_mult||1;
  const TAILP=Math.round(100-100*L.explosive_pass),TAILR=Math.round(100-100*L.explosive_rush),RZP=L.rz_td.pass,RZR=L.rz_td.rush;
  const Y=(k,z,dn)=>L.yards[`${k}|${ZONES[z]}|${dn?'late':'early'}`],YSCR=L.yards.scramble,YSACK=L.yards.sack,PUNT=L.punt_net,KO=L.ko_start,C=(z,dn)=>L.comp[`${ZONES[z]}|${dn?'late':'early'}`],F4=(tg,z)=>L.fourth_go[`${TGS[tg]}|${ZONES[z]}`]!=null?L.fourth_go[`${TGS[tg]}|${ZONES[z]}`]:.05;
  const TM=[new Team(PR,game.away,game.home,false),new Team(PR,game.home,game.away,true)];
  if((PR.cfg||{}).dome&&/^(dome|closed)$/.test(String(game.roof||'')))TM.forEach(tm=>tm.mp*=1.02);
  const PACE2=(PR.cfg||{}).pace2&&L.snap_gap_state?L.snap_gap_state:null;
  if((PR.cfg||{}).rest){[[TM[0],'away_rest'],[TM[1],'home_rest']].forEach(([tm,rk])=>{const rd=game[rk]||7,m=rd<=5?.985:rd>=10?1.015:1;tm.mp*=m;tm.mr*=m})}
  const qi=n=>Math.floor(R()*n),pq=a=>a[qi(101)];
  const box=TM.map(t=>({tgt:t.R.map(()=>[]),rec:t.R.map(()=>[]),recyd:t.R.map(()=>[]),rectd:t.R.map(()=>[]),car:t.U.map(()=>[]),ruyd:t.U.map(()=>[]),rutd:t.U.map(()=>[]),
    att:[],cmp:[],pyd:[],ptd:[],int:[],sk:[],qbru:[],qbryd:[],qbrtd:[],plays:[],yds:[],to:[],drives:[],rzt:[],fga:[],fgm:[],punts:[],top:[],third:[],thirdc:[],fd:[],downs:[],go4:[],otd:[]}));
  const SA=[],SH=[],OT=[];
  for(let s=0;s<n;s++){
    const B=box.map((b,side)=>({tgt:b.tgt.map(()=>0),rec:b.rec.map(()=>0),recyd:b.recyd.map(()=>0),rectd:b.rectd.map(()=>0),car:b.car.map(()=>0),ruyd:b.ruyd.map(()=>0),rutd:b.rutd.map(()=>0),
      att:0,cmp:0,pyd:0,ptd:0,int:0,sk:0,qbru:0,qbryd:0,qbrtd:0,plays:0,yds:0,to:0,drives:0,rzt:0,fga:0,fgm:0,punts:0,top:0,third:0,thirdc:0,fd:0,downs:0,go4:0,otd:0}));
    const sc=[0,0];let poss=qi(2);const recv2=1-poss;let clock=3600,yl=pq(KO),down=1,togo=10,ot=false,half2=false,inrz=false,otPoss=[false,false],done=false;B[poss].drives++;
    const change=(newYl)=>{poss=1-poss;yl=clip(newYl,1,99);down=1;togo=Math.min(10,yl);B[poss].drives++;inrz=false;if(ot)otPoss[poss]=true};
    const kickoff=()=>{yl=pq(KO);down=1;togo=10;inrz=false};
    for(let it=0;it<600&&!done;it++){
      const o=poss,d=1-o,T=TM[o],Bo=B[o],sd=sc[o]-sc[d],z=zone(yl),tg=tgb(togo),dn=down>=3?1:0,dist=yl+17;
      const kneel=sd>0&&clock<=70&&down===1&&!ot;
      let goP=clip(F4(tg,z)*T.aggr,0,.95);const desperate=sd<0&&(clock<150||(sd<=-4&&clock<300)||(sd<=-9&&clock<600));if(desperate&&(dist>55||sd<-3))goP=.95;
      const fgOk=dist<=55||(dist<=62&&sd>=-3&&sd<=0&&clock<120);const is4=down===4;const u=R();
      let go=is4&&u<goP,fgt=is4&&!go&&fgOk,punt=is4&&!go&&!fgOk;
      const last=(clock<=40&&clock>0&&!half2&&dist<=58)||(clock<=40&&half2&&dist<=58&&sd>=-3&&sd<=0);if(last&&!is4&&!go)fgt=true;if(last)punt=false;
      const normal=!fgt&&!punt&&!kneel;
      let p=PP[`${clip(down,1,4)}|${TGS[tg]}|${ZONES[z]}|${SDS[sdb(sd)]}|${TS[tb(clock)]}`];p=sig(logit(p)+T.pass_shift+c_pass);if(z===3)p=.5*p+.5*T.rz_pass;
      const ispass=normal&&R()<p,isrush=normal&&!ispass;
      let yards=0,turnover=false,incomplete=false,tdRet=false,spot=0,fgMade=false,td=false;
      const mp=T.mp*c_yard,mr=T.mr*c_yard,rzf=T.rzf*c_td;
      if(go)Bo.go4++;
      if(ispass){Bo.plays++;const r=R();
        if(r<T.sack_rate){yards=Math.max(pq(YSACK),-(99-yl));Bo.sk++;if(R()<L.fum_sack)turnover=true}
        else if(r<T.sack_rate+T.scramble){let yv=Math.round(pq(YSCR)*T.qb_ypc);const rz=z===3&&R()<clip(RZR[rzb(yl)]*rzf,0,.97);yards=rz?yl:z===3?Math.min(yv,yl-1):Math.min(yv,yl);Bo.qbru++;Bo.qbryd+=yards;if(yards>=yl)Bo.qbrtd++}
        else{Bo.att++;const inr=z===3,tgt=pick(inr?T.tw_rz:T.tw,R());Bo.tgt[tgt]++;
          const cp=clip(C(z,dn)+T.comp_shift+T.catch_adj[tgt],.25,.9),v=R(),picked=v<T.int_rate,comp=!picked&&v<T.int_rate+cp;
          const tail=R()<T.exp_pass,q=tail?TAILP+qi(101-TAILP):qi(TAILP);let yv=Math.round(Y('pass',z,dn)[q]*mp*T.ypt_r[tgt]);
          const rztd=inr&&R()<clip(RZP[rzb(yl)]*rzf*Math.pow(mp,.3),0,.97);yv=rztd?yl:inr?Math.min(yv,yl-1):Math.min(yv,yl);
          if(comp){yards=yv;Bo.rec[tgt]++;Bo.recyd[tgt]+=yv;Bo.cmp++;Bo.pyd+=yv;if(yv>=yl){Bo.rectd[tgt]++;Bo.ptd++}else if(R()<L.fum_rec)turnover=true}
          else if(picked){turnover=true;Bo.int++;spot=clip(yl-3,1,99);if(R()<L.int_ret_td)tdRet=true}
          else incomplete=true}}
      else if(isrush){Bo.plays++;const gl=yl<=5,ru=pick(gl?T.rw_gl:T.rw,R());Bo.car[ru]++;
        const tail=R()<T.exp_rush,q=tail?TAILR+qi(101-TAILR):qi(TAILR);let yv=Math.round(Y('rush',z,dn)[q]*mr*T.ypc_r[ru]);
        const inr=z===3,rztd=inr&&R()<clip(RZR[rzb(yl)]*rzf*Math.pow(mr,.3),0,.97);yv=rztd?yl:inr?Math.min(yv,yl-1):Math.min(yv,yl);
        yards=yv;Bo.ruyd[ru]+=yv;if(yv>=yl)Bo.rutd[ru]++;else if(R()<L.fum_rush)turnover=true}
      else if(fgt){Bo.fga++;Bo.plays++;if(R()<fgp(L,dist)){fgMade=true;Bo.fgm++;sc[o]+=3}}
      else if(punt){Bo.punts++;Bo.plays++}
      if(normal){Bo.yds+=yards;if(down===3){Bo.third++;if(yards>=togo&&!turnover)Bo.thirdc++}}
      td=normal&&yards>=yl&&!turnover;if(td)Bo.otd++;
      if(tdRet)sc[d]+=7;
      if(td){const sa=sd+6,two=sa===-2||sa===-5;sc[o]+=6+(two?(R()<.48?2:0):(R()<.94?1:0))}
      let gap=incomplete?L.snap_gap.incomplete:(PACE2?(PACE2[SDS[sdb(sd)]+'|'+(clock<=1800?1:0)]||L.snap_gap.run_or_complete):L.snap_gap.run_or_complete);const hurry=(sd<0&&clock<240)||(clock>1800&&clock<1920);
      if(hurry)gap=incomplete?L.snap_gap.hurry_incomplete:L.snap_gap.hurry;gap*=T.pace;if(fgt||punt)gap=6;if(td||turnover||tdRet)gap=incomplete?5:12;if(kneel)gap=clock+1;
      Bo.top+=gap;const before=clock;clock=Math.max(0,clock-gap);
      const kick=td||tdRet||fgMade;let newPoss=false,newYl=0;
      if(kick){newPoss=true;newYl=pq(KO);if(R()<L.ko_ret_td){sc[d]+=7;newPoss=false;kickoff()}}
      else if(fgt){newPoss=true;newYl=100-Math.max(yl+7,20)}
      else if(punt){const net=pq(PUNT),land=yl-net;newPoss=true;newYl=land<=0?80:100-land;if(R()<L.punt_ret_td){sc[d]+=7;newPoss=false;kickoff()}}
      else if(turnover){Bo.to++;newPoss=true;newYl=100-clip(spot>0?spot:yl-yards,1,99)}
      else if(normal&&!td){const ylNew=yl-yards,first=yards>=togo;if(first)Bo.fd++;const nd=first?1:down+1;
        if(nd>4){newPoss=true;newYl=100-ylNew;Bo.downs++}else{yl=clip(ylNew,1,99);down=nd;togo=first?Math.min(10,yl):togo-yards;if(yl<=20&&!inrz){Bo.rzt++;inrz=true}}}
      const half=before>1800&&clock<=1800&&!ot;
      if(half){clock=1800;half2=true;poss=recv2;kickoff();B[poss].drives++;newPoss=false}
      if(newPoss)change(newYl);
      if(clock<=0&&!ot){if(sc[0]!==sc[1])done=true;else{ot=true;clock=600;poss=qi(2);otPoss=[false,false];otPoss[poss]=true;kickoff()}}
      else if(ot){const diff=sc[0]-sc[1];if((td||tdRet)||(diff!==0&&otPoss[0]&&otPoss[1])||clock<=0)done=true}
    }
    SA.push(sc[0]);SH.push(sc[1]);OT.push(ot?1:0);
    for(let side=0;side<2;side++){const b=box[side],x=B[side];for(const k of ['att','cmp','pyd','ptd','int','sk','qbru','qbryd','qbrtd','plays','yds','to','drives','rzt','fga','fgm','punts','top','third','thirdc','fd','downs','go4','otd'])b[k].push(x[k]);
      for(const k of ['tgt','rec','recyd','rectd'])x[k].forEach((v,i)=>b[k][i].push(v));for(const k of ['car','ruyd','rutd'])x[k].forEach((v,i)=>b[k][i].push(v))}
    if(onProgress&&(s%500===499||s===n-1))onProgress(s+1,n);
  }
  return summary(game,TM,SA,SH,box,n,OT)}
const mean=a=>a.length?a.reduce((x,y)=>x+y,0)/a.length:0,med=a=>{const s=a.slice().sort((x,y)=>x-y);return s.length?s[Math.floor(s.length/2)]:0},pct=(a,p)=>{const s=a.slice().sort((x,y)=>x-y);return s.length?s[Math.min(s.length-1,Math.floor(p/100*s.length))]:0},sd=a=>{const m=mean(a);return Math.sqrt(mean(a.map(x=>(x-m)*(x-m))))};
function summary(game,TM,SA,SH,box,N,OT){
  const margin=SA.map((a,i)=>SH[i]-a),total=SA.map((a,i)=>a+SH[i]);const pairs={};SA.forEach((a,i)=>{const k=Math.round(a)+'-'+Math.round(SH[i]);pairs[k]=(pairs[k]||0)+1});
  const likely=Object.entries(pairs).sort((a,b)=>b[1]-a[1]).slice(0,8).map(([k,c])=>{const [a,h]=k.split('-').map(Number);return {away:a,home:h,p:c/N}});
  const hw=mean(margin.map(m=>m>0?1:0))>=mean(margin.map(m=>m<0?1:0));const sideP=Object.entries(pairs).map(([k,c])=>{const [a,h]=k.split('-').map(Number);return {away:a,home:h,p:c/N}}).filter(x=>x.away!==x.home&&((x.home>x.away)===hw)).sort((a,b)=>b.p-a.p);const headline=sideP[0]||likely[0];
  const dist=(x,lo,hi)=>{const c=new Array(hi-lo+1).fill(0);x.forEach(v=>{c[clip(Math.round(v)-lo,0,hi-lo)]++});return {lo,counts:c}};
  const teamBox=(side,T,B)=>{const pl=T.R.map((p,i)=>{const j=T.U.findIndex(q=>q.name===p.name);const car=j>=0?B.car[j]:null,ruyd=j>=0?B.ruyd[j]:null,rutd=j>=0?B.rutd[j]:null;
      const tot=B.recyd[i].map((v,k)=>v+(ruyd?ruyd[k]:0)),tds=B.rectd[i].map((v,k)=>v+(rutd?rutd[k]:0));
      return {name:p.name,pos:p.pos,slot:p.slot,inj:p.inj,tgt:mean(B.tgt[i]),rec:mean(B.rec[i]),rec_yds:mean(B.recyd[i]),rec_yds_med:med(B.recyd[i]),rec_yds_p25:pct(B.recyd[i],25),rec_yds_p75:pct(B.recyd[i],75),rec_td:mean(B.rectd[i]),
        car:car?mean(car):null,rush_yds:ruyd?mean(ruyd):null,rush_yds_med:ruyd?med(ruyd):null,rush_yds_p25:ruyd?pct(ruyd,25):null,rush_yds_p75:ruyd?pct(ruyd,75):null,rush_td:rutd?mean(rutd):null,
        p_td:mean(tds.map(v=>v>=1?1:0)),p_100:mean(tot.map(v=>v>=100?1:0)),share:T.w[i]}});
    T.U.forEach((q,j)=>{if(q.pos==='QB'||pl.some(x=>x.name===q.name))return;pl.push({name:q.name,pos:q.pos,slot:q.slot,inj:q.inj,tgt:0,rec:0,rec_yds:0,rec_yds_med:0,rec_yds_p25:0,rec_yds_p75:0,rec_td:0,car:mean(B.car[j]),rush_yds:mean(B.ruyd[j]),rush_yds_med:med(B.ruyd[j]),rush_yds_p25:pct(B.ruyd[j],25),rush_yds_p75:pct(B.ruyd[j],75),rush_td:mean(B.rutd[j]),p_td:mean(B.rutd[j].map(v=>v>=1?1:0)),p_100:mean(B.ruyd[j].map(v=>v>=100?1:0)),share:0})});
    const q=T.qb,j=T.U.findIndex(u=>u.pos==='QB');
    const qb={name:q.name,att:mean(B.att),cmp:mean(B.cmp),pass_yds:mean(B.pyd),pass_yds_med:med(B.pyd),pass_yds_p25:pct(B.pyd,25),pass_yds_p75:pct(B.pyd,75),pass_td:mean(B.ptd),int:mean(B.int),sacks:mean(B.sk),car:mean(B.qbru)+(j>=0?mean(B.car[j]):0),rush_yds:mean(B.qbryd)+(j>=0?mean(B.ruyd[j]):0),rush_td:mean(B.qbrtd)+(j>=0?mean(B.rutd[j]):0),p_300:mean(B.pyd.map(v=>v>=300?1:0)),p_2td:mean(B.ptd.map(v=>v>=2?1:0)),p_int:mean(B.int.map(v=>v>=1?1:0))};
    const pts=side===0?SA:SH;
    const team={plays:mean(B.plays),pass_att:mean(B.att),rush_att:T.U.reduce((a,_,k)=>a+mean(B.car[k]),0)+mean(B.qbru),yds:mean(B.yds),to:mean(B.to),drives:mean(B.drives),rz_trips:mean(B.rzt),fga:mean(B.fga),fgm:mean(B.fgm),punts:mean(B.punts),top:mean(B.top),third:mean(B.third),third_conv:B.thirdc.reduce((a,b)=>a+b,0)/Math.max(1,B.third.reduce((a,b)=>a+b,0)),first_downs:mean(B.fd),downs:mean(B.downs),go4:mean(B.go4),otd:mean(B.otd),
      pts:mean(pts),pts_med:med(pts),pts_p10:pct(pts,10),pts_p90:pct(pts,90)};
    return {team:T.name,qb,players:pl.sort((a,b)=>(b.tgt+(b.car||0))-(a.tgt+(a.car||0))),team_stats:team}};
  const spread=game.spread,tot=game.total;
  return {game_id:game.game_id,week:game.week,away:game.away,home:game.home,date:game.date,time:game.time,n:N,spread,total:tot,roof:game.roof,away_qb:TM[0].qb.name,home_qb:TM[1].qb.name,
    p_home:mean(margin.map(m=>m>0?1:0)),p_away:mean(margin.map(m=>m<0?1:0)),p_tie:mean(margin.map(m=>m===0?1:0)),p_ot:mean(OT),
    mean_away:mean(SA),mean_home:mean(SH),med_away:med(SA),med_home:med(SH),mean_margin:mean(margin),sd_margin:sd(margin),mean_total:mean(total),sd_total:sd(total),likely,headline,
    p_home_cover:spread==null?null:mean(margin.map(m=>m>spread?1:0)),p_push:spread==null?null:mean(margin.map(m=>m===spread?1:0)),p_over:tot==null?null:mean(total.map(t=>t>tot?1:0)),p_total_push:tot==null?null:mean(total.map(t=>t===tot?1:0)),
    margin_dist:dist(margin,-45,45),total_dist:dist(total,10,90),box:[teamBox(0,TM[0],box[0]),teamBox(1,TM[1],box[1])],actual:game.home_score==null?null:{away:game.away_score,home:game.home_score}}}
root.RainmanSim={simulate,Team};
})(typeof self!=='undefined'?self:this);
