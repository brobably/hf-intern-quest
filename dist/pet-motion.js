/* Animate one original texture: expressions never swap a repainted character. */
(()=>{
 const assets=new Map(),reduced=matchMedia('(prefers-reduced-motion: reduce)');
 let active=null,sequence=0,anchors=null;
 const imageFor=url=>{if(!assets.has(url))assets.set(url,new Promise((resolve,reject)=>{const im=new Image();im.onload=()=>resolve(im);im.onerror=reject;im.src=url;}));return assets.get(url);};
 const vertex=`precision highp float;
 attribute vec2 uv;varying vec2 tex;uniform vec4 eyeL,eyeR;uniform vec2 mouth;uniform float blink,happy,time,moving,baby;
 float local(vec2 p,vec2 center,vec2 radius){return 1.-smoothstep(1.,1.8,max(abs((p.x-center.x)/radius.x),abs((p.y-center.y)/radius.y)));}
 vec2 closeEye(vec2 p,vec4 eye){float w=local(uv,eye.xy,eye.zw);p.y-=(uv.y-eye.y)*max(blink,happy*.86)*.96*w;p.y+=happy*.006*pow((uv.x-eye.x)/eye.z,2.)*w;return p;}
 void main(){vec2 p=uv;tex=uv;
 p=closeEye(p,eyeL);p=closeEye(p,eyeR);
 float expression=mix(.36+.035*sin(time*.9),1.,happy);
 if(baby<.5)p.y-=(uv.y-mouth.y)*(1.-expression)*local(uv,mouth,vec2(.064,.052));
 else p.y+=(uv.y-mouth.y)*.025*sin(time*2.)*local(uv,mouth,vec2(.055,.06));
 float armY=min(.83,mouth.y+.16);float footY=min(.94,mouth.y+.27);
 for(int i=0;i<2;i++){float side=float(i)*2.-1.;vec2 hand=vec2(.5+side*.18,armY);
 float wave=sin(time*1.5+float(i)*1.7)*(.006+happy*.014+moving*.006);
 float weight=exp(-pow((uv.x-hand.x)/.075,4.)-pow((uv.y-hand.y)/.072,4.));
 p.y+=wave*weight;p.x+=side*wave*.3*weight;
 vec2 foot=vec2(.5+side*.125,footY);float step=sin(time*3.+float(i)*3.14159)*moving;
 float fw=exp(-pow((uv.x-foot.x)/.075,4.)-pow((uv.y-foot.y)/.043,4.));
 p.y-=max(0.,step)*.014*fw;p.x+=step*.009*fw;
 }
 gl_Position=vec4(p.x*2.-1.,1.-p.y*2.,0.,1.);}`;
 const fragment=`precision mediump float;varying vec2 tex;uniform sampler2D art;void main(){gl_FragColor=texture2D(art,tex);}`;
 function release(){if(!active)return;cancelAnimationFrame(active.raf);active.gl.deleteTexture(active.texture);active.gl.deleteBuffer(active.buffer);active.gl.deleteProgram(active.program);active=null;}
 async function mount(){
  const avatar=document.querySelector('.pet-character .pet-avatar');if(avatar===active?.avatar)return;
  release();const token=++sequence;if(!avatar||!anchors)return;
  const stage=Number(avatar.dataset.petStage),frame=Number(avatar.querySelector('[data-outfit]')?.dataset.outfit||0),meta=petSceneFrames[stage][frame][0];
  let image;try{image=await imageFor(stage===0?'bogeumi-baby-idle.png':`bogeumi-integrated-${stage}.webp`);}catch{return;}
  if(token!==sequence||!avatar.isConnected)return;
  const source=document.createElement('canvas');source.width=source.height=512;const ctx=source.getContext('2d');
  const size=meta.size.split(' ').map(parseFloat),position=meta.position.split(' ').map(parseFloat),side=image.width/(size[0]/100),x=position[0]/100*(image.width-side),y=position[1]/100*(image.height-side);
  const polygon=meta.clip.match(/[-\d.]+% [-\d.]+%/g).map(pair=>pair.split(' ').map(parseFloat));
  ctx.beginPath();polygon.forEach(([a,b],i)=>i?ctx.lineTo(a/100*512,b/100*512):ctx.moveTo(a/100*512,b/100*512));ctx.closePath();ctx.clip();ctx.drawImage(image,-x/side*512,-y/side*512,image.width/side*512,image.height/side*512);
  const canvas=document.createElement('canvas');canvas.className='pet-integrated-frame pet-rig-canvas';canvas.width=canvas.height=512;canvas.setAttribute('aria-hidden','true');
  const gl=canvas.getContext('webgl',{alpha:true,premultipliedAlpha:true,antialias:true});if(!gl)return;
  function shader(type,code){const s=gl.createShader(type);gl.shaderSource(s,code);gl.compileShader(s);if(!gl.getShaderParameter(s,gl.COMPILE_STATUS))throw Error(gl.getShaderInfoLog(s));return s;}
  let program;try{program=gl.createProgram();const vs=shader(gl.VERTEX_SHADER,vertex),fs=shader(gl.FRAGMENT_SHADER,fragment);gl.attachShader(program,vs);gl.attachShader(program,fs);gl.linkProgram(program);gl.deleteShader(vs);gl.deleteShader(fs);if(!gl.getProgramParameter(program,gl.LINK_STATUS))throw Error('Pet motion shader could not link');}catch(error){console.warn(error);return;}
  gl.useProgram(program);const vertices=[],n=96;
  for(let row=0;row<n;row++)for(let col=0;col<n;col++){const x=col/n,y=row/n,a=1/n;vertices.push(x,y,x+a,y,x,y+a,x+a,y,x+a,y+a,x,y+a);}
  const buffer=gl.createBuffer();gl.bindBuffer(gl.ARRAY_BUFFER,buffer);gl.bufferData(gl.ARRAY_BUFFER,new Float32Array(vertices),gl.STATIC_DRAW);const attr=gl.getAttribLocation(program,'uv');gl.enableVertexAttribArray(attr);gl.vertexAttribPointer(attr,2,gl.FLOAT,false,0,0);
  const texture=gl.createTexture();gl.bindTexture(gl.TEXTURE_2D,texture);gl.pixelStorei(gl.UNPACK_PREMULTIPLY_ALPHA_WEBGL,true);gl.texImage2D(gl.TEXTURE_2D,0,gl.RGBA,gl.RGBA,gl.UNSIGNED_BYTE,source);gl.texParameteri(gl.TEXTURE_2D,gl.TEXTURE_MIN_FILTER,gl.LINEAR);gl.texParameteri(gl.TEXTURE_2D,gl.TEXTURE_MAG_FILTER,gl.LINEAR);gl.texParameteri(gl.TEXTURE_2D,gl.TEXTURE_WRAP_S,gl.CLAMP_TO_EDGE);gl.texParameteri(gl.TEXTURE_2D,gl.TEXTURE_WRAP_T,gl.CLAMP_TO_EDGE);
  const uniform=name=>gl.getUniformLocation(program,name),rig=anchors[stage][frame];gl.uniform4fv(uniform('eyeL'),rig.eyes[0]);gl.uniform4fv(uniform('eyeR'),rig.eyes[1]);gl.uniform2fv(uniform('mouth'),rig.mouth);gl.uniform1f(uniform('baby'),stage===0?1:0);
  const u={blink:uniform('blink'),happy:uniform('happy'),time:uniform('time'),moving:uniform('moving')};
  avatar.append(canvas);avatar.classList.add('has-pet-rig');avatar.removeAttribute('data-blink');
  canvas.addEventListener('webglcontextlost',e=>{e.preventDefault();cancelAnimationFrame(active?.raf);avatar.classList.remove('has-pet-rig');canvas.style.visibility='hidden';});
  const a=active={avatar,canvas,gl,buffer,texture,program,raf:0,blinkStart:0,nextBlink:performance.now()+3500+Math.random()*4000,happy:0,moving:0,last:0,lastX:null};
  function draw(now){if(active!==a||!avatar.isConnected)return;a.raf=requestAnimationFrame(draw);if(document.hidden||now-a.last<32)return;
   const dt=Math.min(.1,(now-a.last)/1000||.032);a.last=now;const character=avatar.closest('.pet-character'),room=character.closest('.pet-room');
   const happy=character.classList.contains('is-stroked')?1:0;a.happy+=(happy-a.happy)*Math.min(1,dt*7);
   const x=character.getBoundingClientRect().x;const speed=a.lastX==null?0:Math.min(1,Math.abs(x-a.lastX)/(dt*18));a.lastX=x;a.moving+=(speed-a.moving)*Math.min(1,dt*5);
   let blink=room.classList.contains('is-napping')?1:0;if(!reduced.matches&&!happy&&!room.classList.contains('is-playing')&&!room.classList.contains('is-layout-editing')){
    if(now>a.nextBlink&&!a.blinkStart){a.blinkStart=now;a.nextBlink=now+4000+Math.random()*4500;}
    if(a.blinkStart){const t=now-a.blinkStart;blink=t<75?t/75:t<125?1:t<225?1-(t-125)/100:0;if(t>=225)a.blinkStart=0;}
   }else a.blinkStart=0;
   if(room.classList.contains('is-napping'))blink=1;
   gl.uniform1f(u.blink,blink);gl.uniform1f(u.happy,a.happy);gl.uniform1f(u.time,reduced.matches?0:now/1000);gl.uniform1f(u.moving,reduced.matches?0:a.moving);gl.clearColor(0,0,0,0);gl.clear(gl.COLOR_BUFFER_BIT);gl.drawArrays(gl.TRIANGLES,0,vertices.length/2);
   canvas.dataset.blink=blink.toFixed(3);canvas.dataset.happy=a.happy.toFixed(3);canvas.dataset.moving=a.moving.toFixed(3);canvas.dataset.motion='rig';canvas.dataset.expression=happy?'happy':blink>.05?'blink':'idle';
  }draw(performance.now());
 }
 fetch('pet-rig.json?v=20261008-rig').then(r=>r.json()).then(data=>{anchors=data;mount();}).catch(()=>{});
 new MutationObserver(()=>{const avatar=document.querySelector('.pet-character .pet-avatar');if(avatar!==active?.avatar)mount();}).observe(document.querySelector('#content')||document.body,{childList:true,subtree:true});
 addEventListener('pagehide',release);
})();
