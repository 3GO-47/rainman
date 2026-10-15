"""Mobile mode — the one shim every page gets (≤760px). CSS inside <style>, JS before </body>.
It never changes a number: it wraps every data table in a horizontal-scroll strip with the first column pinned, folds the header
to one row, drops wide grids to one column, and keeps touch targets ≥32px. Pages with their own nav (the NFL/CFB dashboard) add
their bottom bar on top of this."""
MOB_CSS = r"""
@media (max-width:760px){
 html,body{overflow-x:hidden;max-width:100vw}
 body{font-size:12px}
 #hdr{flex-wrap:wrap;height:auto!important;min-height:0;padding:6px 10px!important;gap:6px 10px!important;row-gap:4px}
 #hdr .brand{font-size:13px}#hdr .brand small{display:none}
 #hdr .tag,#hdr .mini{display:none}
 #hdr .hl,#hdr .tabs,#hdr nav{flex-wrap:wrap;gap:3px;margin-left:0}
 #hdr .hl a,#hdr .tabs a,#hdr .tabs button,#hdr nav a{padding:5px 8px;min-height:30px;display:inline-flex;align-items:center;font-size:11.5px}
 main{padding:8px!important}
 .panel{padding:8px!important;border-radius:5px}
 h1{font-size:15px}h2{font-size:13px}h3{font-size:12px}
 .mscroll{overflow-x:auto;width:0;min-width:100%;max-width:100%;-webkit-overflow-scrolling:touch;overscroll-behavior-x:contain;position:relative}
 .mgrid1>*,.panel,main>*{min-width:0}
 header{flex-wrap:wrap;height:auto;padding:6px 10px;gap:6px 10px}header nav{flex-wrap:wrap}
 .mscroll>table{font-size:11px;width:max-content;min-width:100%}
 .mscroll>table th,.mscroll>table td{white-space:nowrap;max-width:220px;overflow:hidden;text-overflow:ellipsis}
 .mscroll>table th:first-child,.mscroll>table td:first-child{position:sticky;left:0;z-index:2;background:#000;box-shadow:1px 0 0 var(--edge2,#222)}
 .mscroll>table thead th{position:sticky;top:0;z-index:3}
 .mscroll>table thead th:first-child{z-index:4}
 .mscroll.one>table th:first-child,.mscroll.one>table td:first-child{position:static;box-shadow:none}
 .mgrid1{grid-template-columns:1fr!important}
 select,input[type=text],input[type=search],input[type=number]{min-height:32px;font-size:13px}
 .chips button,button.sw,.chip{min-height:30px;padding:5px 9px}
 .modal{padding:0!important;align-items:stretch!important}
 .modal .modalbox,.modal .modalbox.wide,.modalbox{max-width:100%!important;width:100%;min-height:100%;padding:10px 10px 40px!important;border-left:0;border-right:0}
 .mclose{position:sticky!important;top:0;float:right;z-index:5;min-height:32px;padding:4px 12px}
 .sfoot{flex-wrap:wrap;gap:8px}
 .trk{min-width:26px;line-height:22px}
}"""
MOB_JS = r"""(function(){const mq=matchMedia('(max-width:760px)');let mo,tm;
function wrap(){document.querySelectorAll('table').forEach(t=>{if(t.closest('.mscroll,.tw,.tscroll,#mnav'))return;if(t.parentElement&&t.parentElement.closest('table'))return;const w=document.createElement('div');w.className='mscroll';t.parentNode.insertBefore(w,t);w.appendChild(t);const f=t.querySelector('tr');if(f&&f.children.length<=2)w.classList.add('one')})}
function grids(){document.querySelectorAll('main *,body>div *').forEach(e=>{if(e.classList.contains('mgrid1')||e.dataset.mg)return;const cs=getComputedStyle(e);if(cs.display!=='grid')return;const tr=cs.gridTemplateColumns.split(' ').filter(Boolean);e.dataset.mg='1';if(tr.length<2)return;const row=tr.some(x=>/^\d+(\.\d+)?px$/.test(x)&&parseFloat(x)<90);if(row)return;if(e.scrollWidth>e.clientWidth+2||tr.length>=3)e.classList.add('mgrid1')})}
function pass(){wrap();grids()}
function on(){document.documentElement.classList.add('mob');pass();mo=new MutationObserver(()=>{clearTimeout(tm);tm=setTimeout(pass,150)});mo.observe(document.body,{childList:true,subtree:true})}
function off(){document.documentElement.classList.remove('mob');if(mo)mo.disconnect()}
if(mq.matches)on();mq.addEventListener('change',e=>e.matches?on():off());window.rmMobile=mq})();"""
