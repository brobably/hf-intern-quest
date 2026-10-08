/* Generated whole-outfit pose player. Art is never stretched or deformed. */
(()=>{
 'use strict';
 const version='20261008-flight',cache=new Map(),reduced=matchMedia('(prefers-reduced-motion: reduce)');
 let catalogue,active,request=0,attaching=null,flightTime=0,lastTick=0;
 const loaded=fetch(`pet-poses.json?v=${version}`).then(r=>{if(!r.ok)throw Error('Pose manifest unavailable');return r.json();}).then(d=>catalogue=d);
 function preload(stage){
  if(!cache.has(stage))cache.set(stage,loaded.then(()=>Promise.all(Object.values(catalogue.stages[stage]).map(async p=>{const im=new Image();im.src=`${p.url}?v=${version}`;await im.decode();return im;}))));
  return cache.get(stage);
 }
 function show(a,pose){
  if(a.pose===pose)return;
  for(const [name,layer] of Object.entries(a.layers))layer.style.setProperty('opacity',name===pose?'1':'0','important');
  a.frame.dataset.animationPose=pose;a.pose=pose;
 }
 function tick(t){
  const delta=lastTick?Math.min(t-lastTick,80):0;lastTick=t;
  request=0;const a=active;if(!a||!a.avatar.isConnected){active=null;return;}
  if(!document.hidden){
   const x=a.character.getBoundingClientRect().x,dt=t-a.sampleTime;
   if(dt>=90){a.moving=Math.abs(x-a.x)>.12;a.x=x;a.sampleTime=t;}
   const reacting=a.character.classList.contains('is-stroked');
   const room=a.character.closest('.pet-room'),playing=room?.classList.contains('is-playing');
   const paused=reduced.matches||reacting||playing||room?.classList.contains('is-layout-editing')||room?.classList.contains('is-napping')||a.character.matches(':hover,:focus-visible,:active');
   if(!paused)flightTime+=delta;
   const phase=flightTime/18000*Math.PI*2;
   a.character.style.setProperty('--pet-flight-x',`${reduced.matches?0:42*Math.sin(phase)}%`);
   a.character.style.setProperty('--pet-flight-y',`${reduced.matches?0:-10-7*Math.sin(phase*2)}%`);
   a.character.style.setProperty('--pet-flight-lean',`${reduced.matches?0:7*Math.cos(phase)}deg`);
   let pose='idle';
   if(reacting){pose='happy';a.nextBlink=t+4500;a.blinkStart=0;}
   else if(room?.classList.contains('is-napping'))pose='blink';
   else if(!reduced.matches){
    if(t>=a.nextBlink&&!playing){a.blinkStart=t;a.nextBlink=t+4500+Math.random()*4000;}
    const elapsed=t-a.blinkStart;
    if(a.blinkStart&&elapsed<240)pose=elapsed<65||elapsed>=175?'half':'blink';
   }
   show(a,pose);
  }
  request=requestAnimationFrame(tick);
 }
 async function attach(){
  const avatar=document.querySelector('.pet-character .pet-avatar'),frame=avatar?.querySelector('.pet-idle-frame');
  if(!frame||active?.avatar===avatar||attaching===avatar)return;
  attaching=avatar;const stage=Number(avatar.dataset.petStage),outfit=Number(frame.dataset.outfit);
  try{await preload(stage);if(!avatar.isConnected||attaching!==avatar)return;
   cancelAnimationFrame(request);const character=avatar.closest('.pet-character');
   const layers={};
   for(const [name,p] of Object.entries(catalogue.stages[stage])){
    const layer=name==='idle'?frame:document.createElement('span'),f=p.frames[outfit];
    if(name!=='idle'){layer.className='pet-integrated-frame pet-pose-frame';layer.setAttribute('aria-hidden','true');avatar.append(layer);}
    layer.style.setProperty('--pet-sheet',`url('${p.url}?v=${version}')`);layer.style.setProperty('--pet-idle-size',f.size);layer.style.setProperty('--pet-idle-position',f.position);layer.style.setProperty('--pet-idle-clip',f.clip);layer.style.setProperty('opacity','0','important');layers[name]=layer;
   }
   active={avatar,frame,layers,character,stage,outfit,x:character.getBoundingClientRect().x,sampleTime:performance.now(),moving:false,pose:null,blinkStart:0,nextBlink:performance.now()+3500+Math.random()*3000};
   show(active,'idle');request=requestAnimationFrame(tick);
  }catch(e){console.warn('Bogeumi pose images could not load',e);}finally{if(attaching===avatar)attaching=null;}
 }
 new MutationObserver(attach).observe(document.getElementById('content')||document.body,{childList:true,subtree:true});
 document.addEventListener('visibilitychange',()=>{lastTick=0;if(!document.hidden&&active){active.sampleTime=performance.now();active.x=active.character.getBoundingClientRect().x;}});
 attach();
})();
