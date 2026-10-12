/* Canonical cutout rig: body and equipment pixels stay fixed during motion. */
(()=>{
 'use strict';
 const version='20261012-rig-v5',reduced=matchMedia('(prefers-reduced-motion: reduce)'),images=new Map();
 let active,attaching,request=0,last=0,clock=0;const previewLoading=new WeakSet();
 const metadata=fetch(`pet-rig.json?v=${version}`).then(r=>{if(!r.ok)throw Error('Rig metadata unavailable');return r.json();});
 function image(url){if(!images.has(url))images.set(url,new Promise((resolve,reject)=>{const im=new Image();im.onload=()=>resolve(im);im.onerror=reject;im.src=`${url}?v=${version}`;}));return images.get(url);}
 function draw(a,t){
  const c=a.ctx,m=a.meta,rect=m.bodies[a.stage][a.outfit%20],scale=82/Math.max(rect[2],rect[3]),w=rect[2]*scale,h=rect[3]*scale,x=50-w/2,y=7+(82-h)/2;
  const happy=a.character.classList.contains('is-stroked'),room=a.character.closest('.pet-room'),sleep=room?.classList.contains('is-napping');
  if(t>a.nextBlink){a.blink=t;a.nextBlink=t+4200+Math.random()*3800;}
  const closed=happy||sleep||(a.blink&&t-a.blink<140),motion=reduced.matches||sleep?0:Math.sin(clock/650),swing=motion*(happy?12:6);
  c.clearRect(0,0,400,400);c.save();c.scale(4,4);c.imageSmoothingEnabled=true;c.imageSmoothingQuality='high';
  const part=(index,px,py,pw,ph,angle=0,ox=.5,oy=0)=>{c.save();c.translate(px,py);c.rotate(angle*Math.PI/180);c.drawImage(a.parts,...m.parts[index],-pw*ox,-ph*oy,pw,ph);c.restore();};
  // Two hip feet and one arm on each side; proximal joints are behind the torso.
  part(2,50-w*.16,y+h*.90,w*.15,h*.18,-swing*.45,.5,.12);
  part(3,50+w*.16,y+h*.90,w*.15,h*.18,swing*.45,.5,.12);
  part(0,50-w*.28,y+h*.73,w*.16,h*.20,60+swing,.25,0);
  part(1,50+w*.37,y+h*.67,w*.16,h*.20,-65-swing,.75,0);
  c.save();c.beginPath();
  m.bodyHulls[a.stage][a.outfit%20].forEach(([px,py],i)=>{const dx=x+(px-rect[0])*scale,dy=y+(py-rect[1])*scale;i?c.lineTo(dx,dy):c.moveTo(dx,dy);});
  c.closePath();c.clip();c.drawImage(a.body,...rect,x,y,w,h);c.restore();
  const eyeY=y+h*.565;
  for(let side=0;side<2;side++){
   const r=m.eyes[(closed?2:0)+side],ew=w*(closed?.095:.075),eh=ew*r[3]/r[2];
   c.drawImage(a.parts,...r,50+(side?1:-1)*w*.13-ew/2,eyeY-eh/2,ew,eh);
  }
  if(a.stage!==0)part(happy?7:6,50,y+h*.65,w*(happy?.105:.11),h*(happy?.085:.038),0,.5,.5);
  if(a.outfit>=20){const gw=w*.64,gh=gw*m.glasses[3]/m.glasses[2];c.drawImage(a.glasses,...m.glasses,50-gw/2,eyeY-gh/2,gw,gh);}
  c.restore();a.canvas.dataset.expression=closed?'closed':'open';
 }
 function tick(t){
  request=0;const a=active;if(!a||!a.avatar.isConnected){active=null;return;}
  const dt=last?Math.min(t-last,64):0;last=t;
  if(!document.hidden){
   const room=a.character.closest('.pet-room'),pause=reduced.matches||room?.matches('.is-playing,.is-layout-editing,.is-napping')||a.character.matches(':hover,:focus-visible,:active,.is-stroked');
   if(!pause)clock+=dt;
   const phase=clock/18000*Math.PI*2;
   a.character.style.setProperty('--pet-flight-x',`${reduced.matches?0:35*Math.sin(phase)}%`);
   a.character.style.setProperty('--pet-flight-y',`${reduced.matches?0:-8-3*Math.sin(phase*2)}%`);
   a.character.style.setProperty('--pet-flight-lean',`${reduced.matches?0:5*Math.cos(phase)}deg`);
   draw(a,t);
  }
  request=requestAnimationFrame(tick);
 }
 function previews(){
  document.querySelectorAll('.pet-avatar[data-pet-stage]:not(.has-pet-rig)').forEach(async avatar=>{
   if(avatar.closest('.pet-character')||previewLoading.has(avatar))return;
   const frame=avatar.querySelector('.pet-idle-frame');if(!frame)return;
   previewLoading.add(avatar);const stage=Number(avatar.dataset.petStage),outfit=Number(frame.dataset.outfit);
   try{
    const [meta,body,parts,glasses]=await Promise.all([metadata,image(`bogeumi-rig-body-${stage}.png`),image('bogeumi-rig-parts.png'),image('bogeumi-rig-glasses.png')]);
    if(!avatar.isConnected)return;
    const canvas=document.createElement('canvas');canvas.className='pet-integrated-frame pet-rig-canvas';canvas.width=400;canvas.height=400;canvas.setAttribute('aria-hidden','true');
    draw({canvas,ctx:canvas.getContext('2d'),meta,body,parts,glasses,stage,outfit,nextBlink:Infinity,blink:0,character:{classList:{contains:()=>false},closest:()=>null}},0);
    avatar.append(canvas);avatar.classList.add('has-pet-rig');
   }catch(e){console.warn('Bogeumi preview could not load',e);previewLoading.delete(avatar);}
  });
 }
 async function attach(){
  previews();
  const avatar=document.querySelector('.pet-character .pet-avatar'),frame=avatar?.querySelector('.pet-idle-frame');
  if(!frame||active?.avatar===avatar||attaching===avatar)return;
  attaching=avatar;const stage=Number(avatar.dataset.petStage),outfit=Number(frame.dataset.outfit);
  if(!Number.isInteger(stage)||stage<0||stage>3||!Number.isInteger(outfit)||outfit<0||outfit>39){attaching=null;return;}
  try{
   const [meta,body,parts,glasses]=await Promise.all([metadata,image(`bogeumi-rig-body-${stage}.png`),image('bogeumi-rig-parts.png'),image('bogeumi-rig-glasses.png')]);
   if(!avatar.isConnected||attaching!==avatar)return;
   const canvas=document.createElement('canvas');canvas.className='pet-integrated-frame pet-rig-canvas';canvas.width=400;canvas.height=400;canvas.setAttribute('aria-hidden','true');
   avatar.querySelectorAll('.pet-rig-canvas,.pet-pose-frame,.pet-blink-frame,.pet-face').forEach(el=>el.remove());avatar.append(canvas);
   active={avatar,character:avatar.closest('.pet-character'),canvas,ctx:canvas.getContext('2d'),stage,outfit,meta,body,parts,glasses,nextBlink:performance.now()+3000,blink:0};
   draw(active,performance.now());avatar.classList.add('has-pet-rig');cancelAnimationFrame(request);last=0;request=requestAnimationFrame(tick);
  }catch(e){console.warn('Bogeumi rig could not load',e);}finally{if(attaching===avatar)attaching=null;}
 }
 new MutationObserver(attach).observe(document.getElementById('content')||document.body,{childList:true,subtree:true});
 document.addEventListener('visibilitychange',()=>last=0);attach();
})();
