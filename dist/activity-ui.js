let activityState=null,activityLoading=false,gameRun=null,gameTimer=null,gameStart=0;
const levelSteps=[0,100,250,450,700,950,1200,1800,2500,3300];
const levelNames=['인턴 새내기','업무 입문자','자료 수집가','체크리스트 실천가','용어 학습자','문서 탐색가','등기부 탐험가','업무 숙련가','인턴 길잡이','퀘스트 마스터'];
function levelOf(xp){return Math.max(0,levelSteps.findLastIndex(x=>xp>=x));}
async function activityRequest(path,data){const r=await fetch('/api/'+path,{credentials:'same-origin',...(data?{method:'POST',headers:{'Content-Type':'application/json'},body:JSON.stringify(data)}:{})});const result=await r.json();if(!r.ok)throw Error(result.error||'연결을 확인해 주세요.');return result;}
async function loadActivity(){if(activityLoading||!window.hfAuth)return;activityLoading=true;try{activityState=await activityRequest('activity');paintActivity();}catch(e){const note=document.querySelector('.notice');if(note)note.textContent=e.message;}finally{activityLoading=false;}}
function memberRows(rows,type){return rows.length?rows.map((r,i)=>`<div class="row ${r.id===window.hfAuth.user.id?'my-ranking':''}"><strong>${i+1}</strong><span>${esc(r.name)}</span><small>${type==='reflex'?r.ms+' ms':Number(r.xp)+' XP'}</small></div>`).join(''):'<p class="muted">아직 기록이 없습니다.</p>';}
function cleaningMarkup(full=false){
 if(!activityState)return '<p>담당 구역을 확인 중입니다…</p>';
 const admin=window.hfAuth.user.role==='admin',a=activityState;
 return `<p class="muted">${a.week} 시작 주간</p>`+a.cleaning.map(j=>`<div class="row"><span><strong>${esc(j.name)}</strong><br><small>${esc(j.area)}</small></span><small>${j.done?'완료':'진행 전'}</small>${!j.done&&(admin||j.user_id===window.hfAuth.user.id)?`<button type="button" class="primary cleaning-action" data-id="${j.id}" data-action="complete">완료</button>`:''}${admin&&full?`<button type="button" class="auth-link cleaning-action" data-id="${j.id}" data-action="remove">배정 삭제</button>`:''}</div>`).join('')+(a.cleaning.length?'':'<p>이번 주 청소 당번이 아직 설정되지 않았습니다.</p>')+(full&&admin?`<form id="cleaning-form" class="toolbar"><label>담당자<select class="field" name="user_id">${a.members.map(m=>`<option value="${m.id}">${esc(m.name)}</option>`).join('')}</select></label><label>담당 구역<input class="field" name="area" maxlength="80" placeholder="예: 탕비실" required></label><button class="primary">이번 주 배정 추가</button><p class="board-status" role="status"></p></form>`:full?'':`<a href="#cleaning" class="board-source">주간 당번 관리 →</a>`);
}
function paintActivity(){
 const content=document.querySelector('#content');if(!content)return;
 const route=location.hash.slice(1);const a=activityState;
 if(route==='cleaning'){content.innerHTML=`<h1 class="view-title">금주 청소 담당자</h1>${panel('이번 주 청소 배정',cleaningMarkup(true))}`;return;}
 if(route==='reflex'){
  if(!content.querySelector('#reflex-play'))content.innerHTML=`<h1 class="view-title">순발력 대결</h1>${panel('반응속도 테스트','<p>시작 후 버튼이 노란색으로 바뀌면 누르세요. 너무 빨리 누르면 기록되지 않습니다.</p><button type="button" id="reflex-play">눌러서 시작</button><p id="reflex-message" role="status"></p>')}${panel('이번 주 참여자 랭킹','<div id="reflex-ranking"></div>')}`;
  content.querySelector('#reflex-ranking').innerHTML=a?memberRows(a.reflex,'reflex'):'기록을 불러오는 중…';return;
 }
 if(route)return;
 const hero=content.firstElementChild;hero.classList.add('live-hero');const xp=Number(a?.xp||0),level=levelOf(xp),next=levelSteps[level+1],progress=next?Math.min(100,(xp-levelSteps[level])/(next-levelSteps[level])*100):100;
 const badges=[['첫 출석',(attendance?.total||0)>=1],['7일 연속 출석',(attendance?.streak||0)>=7],['100 XP 달성',xp>=100],['첫 청소 완료',(a?.clean_done||0)>0]];
 hero.innerHTML=`<div class="hero-summary"><p>HF 인턴 포털</p><h1>${esc(window.hfAuth.user.name)} 인턴님, 오늘도 함께 성장해요!</h1><div class="hero-tags"><button class="progress-link" data-progress="level">Lv.${level+1} ${levelNames[level]}</button><button class="progress-link" data-progress="attendance">${attendance?.streak||0}일 연속 출석</button><button class="progress-link" data-progress="badges">뱃지 ${badges.filter(x=>x[1]).length}개</button></div><div class="xp-label"><span>경험치</span><span>${xp} / ${next||'최고 레벨'} XP</span></div><div class="xp-track" role="progressbar" aria-label="다음 레벨까지 경험치" aria-valuemin="0" aria-valuemax="100" aria-valuenow="${Math.round(progress)}"><div style="width:${progress}%"></div></div><p>${next?`Lv.${level+2}까지 ${next-xp} XP 남았어요`:'최고 레벨에 도달했어요!'}</p></div><div class="hero-milestones">${badges.map(([name,on])=>`<button type="button" data-progress="badges" class="milestone ${on?'earned':''}"><span aria-hidden="true">${on?'✓':'○'}</span>${name}</button>`).join('')}</div>`;
 for(const section of content.querySelectorAll('section')){
  const heading=section.querySelector('h2');if(!heading)continue;const title=heading.textContent.trim();
  if(title==='이번 달 랭킹')section.innerHTML='<h2>이번 달 랭킹</h2>'+ (a?`<p class="muted">${a.month} · 15초마다 갱신</p>`+memberRows(a.ranking,'xp'):'기록 확인 중…');
  if(title==='금주 청소 당번')section.innerHTML='<h2>금주 청소 당번</h2>'+cleaningMarkup();
  if(title==='순발력 대결'){const mine=a?.reflex.find(r=>r.id===window.hfAuth.user.id);section.innerHTML='<h2>순발력 대결</h2>'+`<p>내 이번 주 최고 기록: ${mine?mine.ms+' ms':'아직 기록 없음'}</p>`+(a?memberRows(a.reflex,'reflex'):'기록 확인 중…')+'<a href="#reflex" class="primary">도전하기</a>';}
 }
 for(const span of content.querySelectorAll('a span'))if(/^\+\d+ XP/.test(span.textContent.trim()))span.textContent='메뉴 바로가기';
 for(const span of content.querySelectorAll('a span'))if(span.textContent.trim()==='최고 기록 시 보너스')span.textContent='이번 주 기록 경쟁';
 const calendar=content.querySelector('#dashboard-calendar');if(calendar)calendar.innerHTML=calendarMarkup();
}
function activityProgress(type){
 const xp=Number(activityState?.xp||0),level=levelOf(xp);let dialog=document.querySelector('#progress-dialog');if(!dialog){dialog=document.createElement('dialog');dialog.id='progress-dialog';document.body.append(dialog);}dialog.setAttribute('aria-labelledby','progress-title');
 const badges=[['첫 출석',(attendance?.total||0)>=1,'출석체크 1회'],['7일 연속 출석',(attendance?.streak||0)>=7,'7일 연속 출석'],['100 XP 달성',xp>=100,'누적 포인트 100점'],['첫 청소 완료',(activityState?.clean_done||0)>0,'이번 주 배정 구역 완료']];
 dialog.innerHTML=`<div class="progress-dialog-head"><h2 id="progress-title">${type==='level'?'레벨과 포인트':'내 뱃지'}</h2><button class="auth-link">닫기</button></div>`+(type==='level'?`<p>현재 ${xp} XP · Lv.${level+1}</p><p class="muted">출석 10점 · 업무 완료 5점(하루 최대 5건) · 공부 모임 개설 10점(하루 1회) · 모임 참여 5점(모임당 1회) · 건의 5점(하루 1회) · 청소 완료 10점</p>`+levelNames.map((n,i)=>`<div class="progress-row ${i===level?'current-stage':''}"><strong>Lv.${i+1} ${n}</strong><span>${levelSteps[i]} XP</span></div>`).join(''):badges.map(([name,on,rule])=>`<div class="progress-row ${on?'current-stage':''}"><strong>${name}</strong><span>${on?'획득':'미획득'} · ${rule}</span></div>`).join(''));
 dialog.querySelector('button').onclick=()=>dialog.close();dialog.showModal();
}
document.addEventListener('submit',async e=>{if(e.target.id!=='cleaning-form')return;e.preventDefault();const form=e.target,d=Object.fromEntries(new FormData(form)),button=form.querySelector('button');button.disabled=true;try{await activityRequest('cleaning/assign',{user_id:Number(d.user_id),area:d.area});await loadActivity();}catch(error){form.querySelector('.board-status').textContent=error.message;button.disabled=false;}});
document.addEventListener('click',async e=>{
 const b=e.target.closest('button');if(!b)return;
 if(b.classList.contains('cleaning-action')){b.disabled=true;try{await activityRequest('cleaning/'+b.dataset.action,{id:Number(b.dataset.id)});await loadActivity();}catch(error){b.disabled=false;note.textContent=error.message;}return;}
 if(b.id!=='reflex-play')return;const msg=document.querySelector('#reflex-message');
 if(gameRun?.ready){const ms=Math.round(performance.now()-gameStart),token=gameRun.token;gameRun=null;b.classList.remove('ready');b.disabled=true;try{await activityRequest('reflex/result',{token,ms});msg.textContent=`이번 기록 ${ms} ms`;await loadActivity();}catch(error){msg.textContent=error.message;}finally{b.disabled=false;b.textContent='다시 도전하기';}return;}
 if(gameRun){clearTimeout(gameTimer);gameRun=null;b.textContent='너무 빨라요! 다시 시작';msg.textContent='노란색으로 바뀐 뒤 눌러 주세요.';return;}
 b.disabled=true;try{gameRun=await activityRequest('reflex/start');b.disabled=false;b.textContent='기다려 주세요…';gameTimer=setTimeout(()=>{if(!b.isConnected||!gameRun)return;gameRun.ready=true;gameStart=performance.now();b.classList.add('ready');b.textContent='지금!';},gameRun.delay);}catch(error){b.disabled=false;msg.textContent=error.message;}
});
window.addEventListener('hashchange',()=>{clearTimeout(gameTimer);gameRun=null;});
setInterval(()=>{if(!document.hidden)loadActivity();},15000);
