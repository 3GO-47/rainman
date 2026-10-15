"""Tracking — the shared star. One localStorage list (rainman.track) every page can add to and read; tracking.html shows it
against the live markets. Every tracked item is a plain record so it survives rebuilds and can be exported:
  id, kind ('game' | 'player'), league, game ('AWAY @ HOME'), away, home, kickoff (ISO), event_id (ESPN id when known),
  market ('moneyline' | 'spread' | 'total' | 'prop' | 'td' | 'game'), stat (prop stat key), player, team, selection (side),
  point (line when saved), price (American when saved), implied, source (book / exchange), label, from (page), saved (ISO), note, parlay (bool)
Insert TRACK_CSS inside a <style> and TRACK_JS inside a <script> on any page; render a star with TRK.btn({...record}) in HTML."""
TRACK_CSS = r""".trk{background:transparent;border:1px solid var(--edge2,#2a2e35);color:var(--dim2,#55606a);border-radius:3px;font:600 11px/16px ui-monospace,Menlo,Consolas,monospace;padding:0 4px;cursor:pointer;vertical-align:middle;margin-left:4px}.trk:hover{color:#ffd600;border-color:#ffd60088}.trk.on{color:#ffd600;border-color:#ffd600aa;background:#ffd60014}
#trkToast{position:fixed;bottom:18px;left:50%;transform:translateX(-50%);background:#111;border:1px solid #ffd60088;color:#ffd600;font:600 12px ui-monospace,Menlo,Consolas,monospace;padding:8px 14px;border-radius:6px;display:none;z-index:9999}#trkToast a{color:#fff;margin-left:8px}"""
TRACK_JS = r"""const TRK={key:'rainman.track',
 all(){try{return JSON.parse(localStorage.getItem(this.key))||[]}catch(e){return []}},
 save(a){try{localStorage.setItem(this.key,JSON.stringify(a))}catch(e){}},
 id(o){return [o.league||'',o.away||'',o.home||'',(o.kickoff||'').slice(0,10),o.market||'',o.stat||'',o.player||'',o.selection||'',o.point??''].join('|')},
 has(o){const id=typeof o==='string'?o:this.id(o);return this.all().some(x=>x.id===id)},
 toggle(o){const a=this.all();const id=this.id(o);const i=a.findIndex(x=>x.id===id);if(i>=0){a.splice(i,1);this.save(a);this.paint();return false}a.push(Object.assign({id,saved:new Date().toISOString(),parlay:false,note:''},o));this.save(a);this.paint();return true},
 btn(o,extra){const on=this.has(o);return `<button class="trk${on?' on':''}${extra?' '+extra:''}" data-trk="${encodeURIComponent(JSON.stringify(o))}" title="${on?'tracked — click to remove from Tracking':'track this — save it to your Tracking page for later and watch the line move'}">★</button>`},
 paint(){const a=new Set(this.all().map(x=>x.id));document.querySelectorAll('.trk[data-trk]').forEach(b=>{let o;try{o=JSON.parse(decodeURIComponent(b.dataset.trk))}catch(e){return}b.classList.toggle('on',a.has(this.id(o)))})},
 toast(m){let t=document.getElementById('trkToast');if(!t){t=document.createElement('div');t.id='trkToast';document.body.appendChild(t)}t.innerHTML=m;t.style.display='block';clearTimeout(t._h);t._h=setTimeout(()=>t.style.display='none',2200)},
 wire(){if(this._w)return;this._w=true;document.addEventListener('click',e=>{const b=e.target.closest('.trk[data-trk]');if(!b)return;e.preventDefault();e.stopPropagation();let o;try{o=JSON.parse(decodeURIComponent(b.dataset.trk))}catch(x){return}const on=this.toggle(o);this.toast(on?`★ tracked · ${this.all().length} on <a href="tracking.html">Tracking</a>`:'removed from Tracking')},true)}};
TRK.wire();"""
