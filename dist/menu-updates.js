// Last-seen state is scoped to the signed-in account on this browser.
(()=>{
 let signals={},seen={},busy=false,storageKey='',ready=false;
 const route=()=>location.hash.slice(1);
 function save(){try{localStorage.setItem(storageKey,JSON.stringify(seen))}catch{}}
 function paint(){
  if(!ready)return;
  document.querySelectorAll('aside a[href^="#"]').forEach(a=>{
   const key=a.hash.slice(1),fresh=signals[key]&&seen[key]!==signals[key];
   let badge=a.querySelector('.menu-update-badge');
   if(fresh&&!badge){badge=document.createElement('span');badge.className='menu-update-badge';badge.textContent='N';badge.setAttribute('aria-label','새 소식');badge.title='새 글 또는 활동이 있어요';a.append(badge)}
   if(!fresh&&badge)badge.remove();
  });
  document.querySelectorAll('.mobile-nav option').forEach(option=>{
   const base=option.dataset.updateLabel||(option.dataset.updateLabel=option.textContent);
   option.textContent=base+(signals[option.value]&&seen[option.value]!==signals[option.value]?' · 새 소식':'');
  });
 }
 async function refresh(){
  const user=window.hfAuth?.user;if(!user||document.hidden||busy)return;
  busy=true;
  try{
   if(storageKey!=='hf-menu-seen:'+user.id){storageKey='hf-menu-seen:'+user.id;try{seen=JSON.parse(localStorage.getItem(storageKey)||'{}')||{}}catch{seen={}}ready=false}
   const response=await fetch('/api/menu-updates',{credentials:'same-origin',cache:'no-store'});if(!response.ok)return;
   signals=(await response.json()).signals;
   // Existing activity is the baseline on first use, avoiding a wall of alerts.
   for(const key of Object.keys(signals))if(!(key in seen))seen[key]=signals[key];
   if(signals[route()])seen[route()]=signals[route()];
   ready=true;save();paint();
  }catch{}finally{busy=false}
 }
 window.addEventListener('hashchange',()=>{if(signals[route()]){seen[route()]=signals[route()];save();paint()}refresh()});
 document.addEventListener('visibilitychange',refresh);
 window.addEventListener('storage',e=>{if(e.key===storageKey){try{seen=JSON.parse(e.newValue||'{}');paint()}catch{}}});
 new MutationObserver(()=>paint()).observe(document.querySelector('aside'),{childList:true,subtree:true});
 const startup=setInterval(()=>{if(ready)clearInterval(startup);else refresh()},2000);
 setInterval(refresh,30000);refresh();
})();

