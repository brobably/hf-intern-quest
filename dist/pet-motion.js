/* Whole-costume motion art: exactly one opaque generated frame is displayed. */
(()=>{
 'use strict';
 const version='20261008-motion-v3',cache=new Map(),reduced=matchMedia('(prefers-reduced-motion: reduce)');
 let catalogue,active,request=0,attaching=null,flightTime=0,lastTick=0;
 const loaded=fetch(`pet-poses.json?v=${version}`).then(r=>{if(!r.ok)throw Error('Motion manifest unavailable');return r.json();}).then(d=>catalogue=d);
 function preload(stage){
  if(!cache.has(stage))cache.set(stage,loaded.then(()=>Promise.all(Object.values(catalogue.stages[stage]).map(async p=>{const im=new Image();im.src=`${p.url}?v=${version}`;await im.decode();return im;}))).catch(e=>{cache.delete(stage);throw e;}));
  return cache.get(stage);
 }
 function show(a,pose){
  if(a.pose===pose)return;
  const p=catalogue.stages[a.stage][pose],f=p.frames[a.outfit];
  a.frame.style.setProperty('--pet-sheet',`url('${p.url}?v=${version}')`);
  a.frame.style.setProperty('--pet-idle-size',f.size);
  a.frame.style.setProperty('--pet-idle-position',f.position);
  a.frame.style.setProperty('--pet-idle-clip',f.clip);
  a.frame.dataset.animationPose=pose;a.pose=pose;
 }
 function tick(t){
  const delta=lastTick?Math.min(t-lastTick,80):0;lastTick=t;
  request=0;const a=active;if(!a||!a.avatar.isConnected){active=null;return;}
  if(!document.hidden){
   const room=a.character.closest('.pet-room'),reacting=a.character.classList.contains('is-stroked'),playing=room?.classList.contains('is-playing');
   const paused=reduced.matches||reacting||playing||room?.classList.contains('is-layout-editing')||room?.classList.contains('is-napping')||a.character.matches(':hover,:focus-visible,:active');
   if(!paused)flightTime+=delta;
   const phase=flightTime/18000*Math.PI*2,direction=Math.cos(phase)>=0?'right':'left';
   a.character.style.setProperty('--pet-flight-x',`${reduced.matches?0:42*Math.sin(phase)}%`);
   a.character.style.setProperty('--pet-flight-y',`${reduced.matches?0:-10-7*Math.sin(phase*2)}%`);
   a.character.style.setProperty('--pet-flight-lean',`${reduced.matches?0:4*Math.cos(phase)}deg`);
   const cycle=direction==='right'?[0,1,2,3,2,1,0]:[4,5,6,7,6,5,4];
   let pose=reduced.matches?'fly0':`fly${cycle[Math.floor(flightTime/160)%cycle.length]}`;
   if(reacting){pose='happy';a.nextBlink=t+4500;a.blinkStart=0;}
   else if(room?.classList.contains('is-napping'))pose='blink';
   else if(!reduced.matches){
    if(t>=a.nextBlink&&!playing){a.blinkStart=t;a.blinkBase=pose;a.nextBlink=t+4500+Math.random()*4000;}
    const elapsed=t-a.blinkStart;
    if(a.blinkStart&&elapsed<240)pose=elapsed<65||elapsed>=175?'half':'blink';
    else if(a.blinkStart&&elapsed<400)pose=a.blinkBase;
   }
   const qa=document.querySelector('#qa-pose')?.value;if(qa&&catalogue.stages[a.stage][qa])pose=qa;
   show(a,pose);a.character.dataset.flightDirection=direction;
  }
  request=requestAnimationFrame(tick);
 }
 async function attach(){
  const avatar=document.querySelector('.pet-character .pet-avatar'),frame=avatar?.querySelector('.pet-idle-frame');
  if(!frame||active?.avatar===avatar||attaching===avatar)return;
  attaching=avatar;const stage=Number(avatar.dataset.petStage),outfit=Number(frame.dataset.outfit);
  try{await preload(stage);if(!avatar.isConnected||attaching!==avatar)return;
   cancelAnimationFrame(request);const character=avatar.closest('.pet-character');
   avatar.querySelectorAll('.pet-pose-frame,.pet-blink-frame,.pet-face').forEach(el=>el.remove());
   frame.style.setProperty('opacity','1','important');
   active={avatar,frame,character,stage,outfit,pose:null,blinkStart:0,nextBlink:performance.now()+3500+Math.random()*3000};
   show(active,'fly0');lastTick=0;request=requestAnimationFrame(tick);
  }catch(e){console.warn('Bogeumi motion images could not load',e);}finally{if(attaching===avatar)attaching=null;}
 }
 new MutationObserver(attach).observe(document.getElementById('content')||document.body,{childList:true,subtree:true});
 document.addEventListener('visibilitychange',()=>{lastTick=0;});
 attach();
})();
