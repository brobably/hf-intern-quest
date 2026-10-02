const main=document.querySelector('main'),header=main.querySelector('header');
const signedName=window.hfAuth.user.name;
const dashboard=[...main.children].filter(x=>x!==header).map(x=>x.outerHTML).join('').replaceAll('김하늘 인턴님',signedName.replace(/[&<>"']/g,c=>({'&':'&amp;','<':'&lt;','>':'&gt;','"':'&quot;',"'":'&#39;'}[c]))+' 인턴님');
const titles={'':'대시보드','manual-ai':'업무 매뉴얼 AI',glossary:'HF 금융상품 용어사전','registry-guide':'등기부등본 확인 방법',checklist:'업무 체크리스트',cleaning:'금주 청소 담당자',lunch:'같이 밥 먹을래?',reflex:'순발력 대결',wiki:'인턴 위키',study:'같이 공부할래?',articles:'오늘의 기사',jobs:'오늘의 채용 소식',qna:'Q&A',suggestions:'건의사항'};
const boardKinds=['study','articles','jobs','qna','suggestions'];
const nav=document.querySelector('aside nav');
const navModel=nav.querySelector('a');
for(const kind of boardKinds){const a=document.createElement('a');a.href='#'+kind;a.className=navModel.className.replace('bg-primary-500','').replace('text-background-50','');a.innerHTML='<span class="board-icon" aria-hidden="true">'+({study:'◎',articles:'▤',jobs:'▣',qna:'?',suggestions:'◇'}[kind])+'</span><span>'+titles[kind]+'</span>';nav.append(a);}
const esc=s=>String(s).replace(/[&<>"']/g,c=>({'&':'&amp;','<':'&lt;','>':'&gt;','"':'&quot;',"'":'&#39;'}[c]));
const defaults={tasks:[['오전 9시 MBS 발행 현황 메일 확인',false,5],['유동화증권 발행공시 자료 취합 (DART)',false,5],['담보주택 등기부등본 3건 확인',false,30],['용어사전에서 신탁원본 학습하기',false,10],['주간 회의록 초안 작성',false,20]],clean:[false,true,false],lunch:[],wiki:[],best:null,favorites:[]};
let state={...structuredClone(defaults),...window.hfAuth.state};
let saving=Promise.resolve();
function save(){const snapshot=JSON.stringify({state});saving=saving.catch(()=>{}).then(async()=>{const response=await fetch('/api/state',{method:'POST',credentials:'same-origin',headers:{'Content-Type':'application/json'},body:snapshot});if(!response.ok)throw Error('저장 실패');loadActivity();}).catch(()=>{document.querySelector('.notice').textContent='계정 데이터 저장에 실패했습니다. 로그인과 서버 연결 상태를 확인해 주세요.'});}
const select=document.createElement('select');select.className='mobile-nav';select.setAttribute('aria-label','메뉴 이동');select.innerHTML=Object.entries(titles).map(([k,v])=>`<option value="${k}">${v}</option>`).join('');header.before(select);select.onchange=()=>location.hash=select.value;
const note=document.createElement('p');note.className='notice';note.textContent='활동 포인트와 출석은 내 계정에 저장되며 회원 랭킹은 15초마다 갱신됩니다.';header.after(note);
header.querySelector('input').setAttribute('aria-label','포털 메뉴 검색');header.querySelector('input').placeholder='메뉴 검색 후 Enter';header.querySelector('input').onkeydown=e=>{if(e.key==='Enter'){const q=e.target.value.trim();const found=Object.entries(titles).find(([k,v])=>v.includes(q)&&q);if(found){location.hash=found[0];e.target.value=''}else{note.textContent='일치하는 메뉴가 없습니다. 업무, 용어, 위키 등의 이름으로 검색해 주세요.'}}};
let timer,stage='idle',started=0;
const calendarToday=new Intl.DateTimeFormat('en-CA',{timeZone:'Asia/Seoul',year:'numeric',month:'2-digit',day:'2-digit'}).format(new Date());
const calendarParts=calendarToday.split('-').map(Number);
let calendarYear=calendarParts[0],calendarMonth=calendarParts[1]-1;
let attendance=null,attendanceError='',attendanceBusy=false;
function attendanceMarkup(){return `<div><h2>오늘의 출석</h2><p class="muted" role="status">${attendanceError?esc(attendanceError):attendance?`${attendance.today} · 총 ${attendance.total}일 · ${attendance.streak}일 연속 출석`:'출석 기록을 확인하고 있어요…'}</p></div><button type="button" class="primary" id="attendance-button" ${!attendance||attendance.checked||attendanceBusy?'disabled':''}>${attendanceBusy?'확인 중…':attendance?.checked?'오늘 출석 완료':'출석체크'}</button>`}
function updateAttendance(){const card=document.querySelector('#attendance-card');if(card)card.innerHTML=attendanceMarkup();updateProgressAttendance(document.querySelector('#content'));paintActivity();}
async function loadAttendance(){try{const response=await fetch('/api/attendance',{credentials:'same-origin'});if(!response.ok)throw Error('출석 기록을 불러오지 못했습니다. 새로고침해 주세요.');attendance=await response.json();attendanceError=''}catch(error){attendanceError=error.message}updateAttendance()}
document.addEventListener('click',async e=>{if(!e.target.closest('#attendance-button')||!attendance||attendance.checked||attendanceBusy)return;attendanceBusy=true;updateAttendance();try{const response=await fetch('/api/attendance',{method:'POST',credentials:'same-origin',headers:{'Content-Type':'application/json'},body:'{}'});if(!response.ok)throw Error('출석체크에 실패했습니다. 다시 시도해 주세요.');attendance=await response.json();attendanceError='';loadActivity();}catch(error){attendanceError=error.message}finally{attendanceBusy=false;updateAttendance()}});
loadAttendance();
function calendarMarkup(){
 const first=new Date(calendarYear,calendarMonth,1).getDay(),days=new Date(calendarYear,calendarMonth+1,0).getDate();
 const cells=Array.from({length:Math.ceil((first+days)/7)*7},(_,i)=>{const day=i-first+1;if(day<1||day>days)return '<div class="calendar-empty" aria-hidden="true"></div>';const dateKey=`${calendarYear}-${String(calendarMonth+1).padStart(2,'0')}-${String(day).padStart(2,'0')}`,checked=attendance?.days.includes(dateKey);const today=calendarYear===calendarParts[0]&&calendarMonth===calendarParts[1]-1&&day===calendarParts[2];return `<button type="button" data-event-day="${dateKey}" aria-label="${dateKey} 일정 보기" class="calendar-day ${i%7===0?'sunday':i%7===6?'saturday':''} ${today?'is-today':''} ${checked?'is-attended':''}" ${today?'aria-current="date"':''}><span>${day}</span>${today?'<small>오늘</small>':''}${checked?'<small class="attendance-mark">✓ 출석</small>':''}${activityState?.events?.some(x=>x.day===dateKey)?'<small class="event-mark">● 일정</small>':''}</button>`}).join('');
 return `<div class="calendar-heading"><h2>달력 <span>${calendarYear}년 ${calendarMonth+1}월</span></h2><div class="calendar-controls"><button type="button" data-calendar="-1" aria-label="이전 달">이전 달</button><button type="button" data-calendar="today">오늘</button><button type="button" data-calendar="1" aria-label="다음 달">다음 달</button></div></div><div class="calendar-week" aria-hidden="true">${['일','월','화','수','목','금','토'].map(d=>`<span>${d}</span>`).join('')}</div><div class="calendar-grid" aria-label="${calendarYear}년 ${calendarMonth+1}월 달력">${cells}</div>`;
}
let calendarPreviewTarget=null;
function hideCalendarPreview(){document.querySelector('#calendar-preview')?.remove();calendarPreviewTarget?.removeAttribute('aria-describedby');calendarPreviewTarget=null;}
function showCalendarPreview(cell){
 if(calendarPreviewTarget===cell&&document.querySelector('#calendar-preview'))return;
 hideCalendarPreview();const day=cell.dataset.eventDay,events=(activityState?.events||[]).filter(e=>e.day===day),tip=document.createElement('div');
 tip.id='calendar-preview';tip.setAttribute('role','tooltip');tip.innerHTML=`<strong>${esc(day)} 일정</strong>`+(events.length?events.map(e=>`<p>${esc(e.body)}</p>`).join(''):'<p class="muted">등록된 일정이 없습니다.</p>')+'<small>날짜를 클릭하면 추가·삭제할 수 있어요.</small>';
 document.body.append(tip);calendarPreviewTarget=cell;cell.setAttribute('aria-describedby',tip.id);
 const r=cell.getBoundingClientRect(),t=tip.getBoundingClientRect();tip.style.left=Math.max(8,Math.min(r.left,window.innerWidth-t.width-8))+'px';tip.style.top=(r.bottom+t.height+8<=window.innerHeight?r.bottom+6:Math.max(8,r.top-t.height-6))+'px';
 tip.onmouseleave=hideCalendarPreview;
}
document.addEventListener('mouseover',e=>{const cell=e.target.closest('[data-event-day]');if(cell)showCalendarPreview(cell);else if(!e.target.closest('#calendar-preview'))hideCalendarPreview();});
document.addEventListener('mouseout',e=>{if(!e.target.closest('[data-event-day]'))return;const next=e.relatedTarget;if(next?.closest?.('[data-event-day],#calendar-preview'))return;hideCalendarPreview();});
document.addEventListener('focusin',e=>{const cell=e.target.closest('[data-event-day]');if(cell)showCalendarPreview(cell);else hideCalendarPreview();});
document.addEventListener('focusout',e=>{if(e.target.closest('[data-event-day]'))hideCalendarPreview();});
document.addEventListener('keydown',e=>{if(e.key==='Escape')hideCalendarPreview();});
document.addEventListener('click',e=>{if(e.target.closest('[data-event-day],[data-calendar]'))hideCalendarPreview();});
window.addEventListener('hashchange',hideCalendarPreview);window.addEventListener('resize',hideCalendarPreview);window.addEventListener('scroll',hideCalendarPreview);
document.addEventListener('click',e=>{const button=e.target.closest('[data-calendar]');if(!button)return;if(button.dataset.calendar==='today'){calendarYear=calendarParts[0];calendarMonth=calendarParts[1]-1}else{const date=new Date(calendarYear,calendarMonth+Number(button.dataset.calendar),1);calendarYear=date.getFullYear();calendarMonth=date.getMonth()}document.querySelector('#dashboard-calendar').innerHTML=calendarMarkup();});
function taskRows(){return state.tasks.map((t,i)=>`<div class="task-row"><label class="task-check"><input type="checkbox" data-task="${i}" ${t[1]?'checked':''}><span>${esc(t[0])}</span></label><small>+5 XP</small><button type="button" class="task-delete" data-delete-task="${i}" aria-label="${esc(t[0])} 삭제">삭제</button></div>`).join('')}

function panel(title,body){return `<section class="panel"><h2>${title}</h2>${body}</section>`}
function render(){renderOriginal();paintActivity();}
function renderOriginal(){clearTimeout(timer);stage='idle';let route=location.hash.slice(1);if(!(route in titles))route='';select.value=route;[...main.children].forEach(x=>{if(![header,note,select].includes(x))x.remove()});document.querySelectorAll('aside nav a').forEach(a=>{const active=a.hash==='#'+route||(!route&&!a.hash);a.classList.toggle('bg-primary-500',active);a.classList.toggle('text-background-50',active);a.parentElement.classList.toggle('nav-active',active);if(active)a.setAttribute('aria-current','page');else a.removeAttribute('aria-current')});
const content=document.createElement('div');content.id='content';main.append(content);
if(!route){content.innerHTML=dashboard;wireProgress(content);const calendar=document.createElement('section');calendar.id='dashboard-calendar';calendar.className='dashboard-calendar';calendar.innerHTML=calendarMarkup();content.firstElementChild.after(calendar);const attendanceCard=document.createElement('section');attendanceCard.id='attendance-card';attendanceCard.className='attendance-card';attendanceCard.innerHTML=attendanceMarkup();calendar.before(attendanceCard);updateProgressAttendance(content);const sections=[...content.querySelectorAll('section')];const quest=sections.find(x=>x.textContent.includes('오늘의 퀘스트'));if(quest)quest.innerHTML=`<h2 class="font-heading text-xl mb-3">오늘의 퀘스트 <small>${state.tasks.filter(t=>t[1]).length}/${state.tasks.length} 완료</small></h2>${taskRows()}`;return}
content.innerHTML=`<h1 class="view-title">${titles[route]}</h1><p class="muted" style="margin-bottom:24px">HF 인턴 퀘스트</p>`;
if(boardKinds.includes(route)){renderBoard(route,content);return;}
if(route==='checklist')content.innerHTML+=panel('오늘 해야 할 일',`<form id="task-form" class="toolbar"><input class="field" name="task" maxlength="150" placeholder="새 업무를 입력하세요" aria-label="새 업무" required><button class="primary">업무 추가</button></form>${taskRows()}`);
if(route==='manual-ai')content.innerHTML+=panel('매뉴얼에 물어보기','<p>업무 매뉴얼과 AI 연결을 준비 중입니다. 연결 후에는 확인된 매뉴얼을 바탕으로 답변과 근거를 제공합니다.</p><div id="messages" aria-live="polite"></div><form id="ai-form" class="toolbar"><input class="field" name="question" maxlength="500" placeholder="예: 발행 현황 자료는 어디에서 확인하나요?" aria-label="매뉴얼 질문" required><button class="primary">질문 입력</button></form><p class="muted">현재는 질문 입력 화면을 확인할 수 있습니다. 실제 AI 답변은 생성하지 않습니다.</p>');
if(route==='glossary'){content.innerHTML+=panel('찾아볼 용어','<input id="term-search" class="field" placeholder="MBS, 보금자리론, 주택연금, 신탁원본" aria-label="용어 검색"><div id="terms" class="cards" style="margin-top:18px"></div><p class="muted">용어 설명은 검토된 자료를 연결한 뒤 채워집니다.</p>');showTerms('')}
if(route==='registry-guide')content.innerHTML+=panel('등기부 확인 가이드',`<div class="cards">${['표제부','갑구','을구','근저당 확인'].map((t,i)=>`<article class="panel"><h2>${i+1}. ${t}</h2><p>담당자가 확인한 업무 매뉴얼과 예시 자료를 등록할 자리입니다.</p></article>`).join('')}</div><p class="muted">현재 업무 판단에 사용할 수 있는 검토된 가이드는 등록되지 않았습니다.</p>`);
if(route==='cleaning')content.innerHTML+=panel('이번 주 담당 구역',`<p class="muted">10월 1주차 · 예시 배정</p>${['김하늘 · 탕비실','박지훈 · 회의실 A·B','이서연 · 분리수거'].map((n,i)=>`<label class="row"><input type="checkbox" data-clean="${i}" ${state.clean[i]?'checked':''}><span>${n}</span><small>${state.clean[i]?'완료':'진행 전'}</small></label>`).join('')}`);
if(route==='lunch')renderMeals(content);
if(route==='wiki')renderWiki(content);
if(route==='reflex')content.innerHTML+=panel('반응속도 테스트',`<p>시작한 뒤 화면이 노란색으로 바뀌면 누르세요. 키보드 Enter 또는 Space로도 참여할 수 있어요.</p><button id="game">눌러서 시작</button><p id="result" aria-live="polite" style="margin-top:16px">내 최고 기록: ${state.best?state.best+' ms':'아직 기록 없음'}</p><p class="muted">업무 외 놀이 · 내 기록은 이 브라우저에 저장됩니다.</p>`);
}
function showTerms(q){document.querySelector('#terms').innerHTML=['MBS','보금자리론','주택연금','신탁원본'].filter(t=>t.toLowerCase().includes(q.toLowerCase())).map(t=>`<article class="panel"><h2>${t}</h2><p class="muted">설명 등록 준비 중</p></article>`).join('')||'<p>검색 결과가 없습니다.</p>'}
document.addEventListener('change',e=>{if(e.target.dataset.task!==undefined){state.tasks[+e.target.dataset.task][1]=e.target.checked;save();render()}if(e.target.dataset.clean!==undefined){state.clean[+e.target.dataset.clean]=e.target.checked;save();render()}});
document.addEventListener('input',e=>{if(e.target.id==='term-search')showTerms(e.target.value)});
document.addEventListener('submit',e=>{const id=e.target.id;if(!['task-form','lunch-form','wiki-form','ai-form'].includes(id))return;e.preventDefault();const d=new FormData(e.target);if(id==='task-form'&&d.get('task').trim())state.tasks.push([d.get('task').trim(),false,5]);if(id==='lunch-form'&&d.get('title').trim())state.lunch.unshift({title:d.get('title').trim(),joined:false});if(id==='wiki-form'&&d.get('title').trim()&&d.get('body').trim())state.wiki.unshift({title:d.get('title').trim(),body:d.get('body').trim()});if(id==='ai-form'){const m=document.createElement('p');m.className='message';m.textContent='질문: '+d.get('question')+'\n매뉴얼과 AI가 아직 연결되지 않았습니다. 자료 연결 후 답변을 제공할 수 있습니다.';document.querySelector('#messages').append(m);e.target.reset();return}save();render()});
document.addEventListener('click',e=>{const b=e.target.closest('button');if(!b)return;if(b.dataset.join!==undefined){const x=state.lunch[+b.dataset.join];x.joined=!x.joined;save();render()}if(b.id==='game'){const r=document.querySelector('#result');if(stage==='idle'){stage='waiting';b.textContent='기다려 주세요…';b.classList.remove('ready');timer=setTimeout(()=>{stage='ready';b.textContent='지금!';b.classList.add('ready');started=performance.now()},1600+Math.random()*2500)}else if(stage==='waiting'){clearTimeout(timer);stage='idle';b.textContent='너무 빨라요! 다시 시작';r.textContent='노란색으로 바뀐 뒤 눌러 주세요.'}else{const ms=Math.round(performance.now()-started);state.best=state.best?Math.min(state.best,ms):ms;save();stage='idle';b.classList.remove('ready');b.textContent='다시 도전하기';r.textContent=`이번 기록: ${ms} ms · 내 최고: ${state.best} ms`}}});
window.addEventListener('hashchange',render);render();
if(document.modelContext?.registerTool){try{Promise.resolve(document.modelContext.registerTool({name:'navigate_hf_portal',description:'Open an HF intern portal menu without changing stored data.',inputSchema:{type:'object',properties:{menu:{type:'string',enum:Object.keys(titles)}},required:['menu'],additionalProperties:false},annotations:{readOnlyHint:true},execute:({menu})=>{if(typeof menu!=='string'||!(menu in titles))throw Error('Unknown menu');location.hash=menu;render();return {menu,title:titles[menu]}}})).catch(()=>{})}catch{}}

function wireProgress(content){
 for(const span of content.querySelectorAll('span')){
  const text=span.textContent.trim();let type;
  if(text==='Lv.7 등기부 탐험가')type='level';
  if(text==='12일 연속 출석')type='attendance';
  if(text==='뱃지 9개')type='badges';
  if(!type)continue;
  const button=document.createElement('button');button.type='button';button.className=span.className+' progress-link';button.dataset.progress=type;button.innerHTML=span.innerHTML;button.setAttribute('aria-haspopup','dialog');span.replaceWith(button);
 }
}
function updateProgressAttendance(content){const button=content?.querySelector('[data-progress="attendance"]');if(button)button.textContent=attendance?attendance.streak+'일 연속 출석':'출석 기록 확인 중';}
const favoriteSection=document.createElement('details');favoriteSection.open=true;favoriteSection.className='favorite-section';document.querySelector('aside nav').before(favoriteSection);
function refreshFavorites(){
 const favorites=state.favorites||[];
 favoriteSection.innerHTML='<summary>즐겨찾기</summary>'+(favorites.length?favorites.map(k=>`<a href="#${k}" class="favorite-item">${esc(titles[k])}</a>`).join(''):'<p>메뉴 옆 별을 눌러 추가하세요.</p>');
 document.querySelectorAll('aside nav a').forEach(a=>{const menu=a.hash.slice(1);let button=a.parentElement.classList.contains('nav-favorite-row')?a.parentElement.querySelector('button'):null;if(!button){const row=document.createElement('div');row.className='nav-favorite-row';a.before(row);row.append(a);button=document.createElement('button');button.type='button';button.className='favorite-toggle';button.dataset.favorite=menu;row.append(button)}const on=favorites.includes(menu);button.textContent=on?'★':'☆';a.parentElement.classList.toggle('nav-active',a.hash==='#'+location.hash.slice(1)||(!location.hash.slice(1)&&!a.hash));button.setAttribute('aria-pressed',String(on));button.setAttribute('aria-label',titles[menu]+(on?' 즐겨찾기 해제':' 즐겨찾기 추가'));});
}
refreshFavorites();
document.addEventListener('click',e=>{
 const star=e.target.closest('[data-favorite]');if(star){const k=star.dataset.favorite;state.favorites=state.favorites||[];state.favorites=state.favorites.includes(k)?state.favorites.filter(x=>x!==k):[...state.favorites,k];refreshFavorites();save();return;}
 const progress=e.target.closest('[data-progress]');if(progress)showProgress(progress.dataset.progress);
});
function showProgress(type){
 if(type==='level'||type==='badges'){activityProgress(type);return;}
 let dialog=document.querySelector('#progress-dialog');if(!dialog){dialog=document.createElement('dialog');dialog.id='progress-dialog';dialog.setAttribute('aria-labelledby','progress-title');document.body.append(dialog)}
 let title='',body='';
 if(type==='level'){
  title='레벨 성장 단계';const levels=[['인턴 새내기',0],['업무 입문자',100],['자료 수집가',250],['체크리스트 실천가',450],['용어 학습자',700],['문서 탐색가',950],['등기부 탐험가',1200],['업무 숙련가',1800],['인턴 길잡이',2500],['퀘스트 마스터',3300]];
  body='<p class="progress-notice">레벨과 경험치는 현재 예시입니다. 아래 단계 기준은 첫 버전의 제안이며 실제 활동 점수와는 아직 연결되지 않았습니다.</p><p class="progress-summary">예시 현재 레벨: Lv.7 · 1,340 XP / 다음 단계: 1,800 XP</p>'+levels.map(([n,x],i)=>`<div class="progress-row ${i===6?'current-stage':''}"><strong>Lv.${i+1} ${n}</strong><span>${x.toLocaleString()} XP${i===6?' · 현재 예시':''}</span></div>`).join('');
 }else if(type==='attendance'){
  title='출석 기록과 단계';const streak=attendance?.streak||0;body=`<p class="progress-summary">총 ${attendance?.total||0}일 출석 · ${streak}일 연속 출석</p><p class="muted">한국 시간 기준 하루 한 번 출석할 수 있어요. 날짜가 하루라도 비면 연속 기록이 다시 시작됩니다.</p>`+[1,3,7,14,30].map(n=>`<div class="progress-row ${streak>=n?'current-stage':''}"><strong>${n}일 연속 출석</strong><span>${streak>=n?'달성':'도전 중'}</span></div>`).join('')+'<h3>출석한 날짜</h3><div class="attendance-dates">'+(attendance?.days.length?attendance.days.slice().reverse().map(d=>`<span>${esc(d)}</span>`).join(''):'<p>아직 출석 기록이 없어요. 메인 화면에서 출석체크를 해 주세요.</p>')+'</div>';
 }else{
  title='뱃지 도감';const badges=[['첫 등기부 해독','등기부 가이드 첫 학습 완료'],['7일 연속 출석','7일 연속 출석체크'],['용어 마스터 Lv.1','용어 10개 학습'],['청소 MVP','청소 담당 업무 5회 완료'],['첫 퀘스트','업무 체크리스트 첫 완료'],['꾸준한 실천가','업무 체크리스트 20개 완료'],['점심 친구','점심 초대 3회 참여'],['지식 나눔','위키 문서 첫 작성'],['순발력 챔피언','순발력 게임 개인 최고 기록 갱신']];
  body='<p class="progress-notice">대시보드의 뱃지 9개는 예시입니다. 획득 조건은 제안 단계이며 자동 지급은 아직 연결되지 않았습니다.</p><div class="badge-grid">'+badges.map(([n,c],i)=>`<article><span class="badge-number">${i+1}</span><h3>${n}</h3><p>${c}</p><small>획득 조건 예시</small></article>`).join('')+'</div>';
 }
 dialog.innerHTML=`<div class="progress-dialog-head"><h2 id="progress-title">${title}</h2><button type="button" id="progress-close" class="auth-link">닫기</button></div>${body}`;dialog.querySelector('#progress-close').onclick=()=>dialog.close();if(!dialog.open)dialog.showModal();
}

const logoIcon=document.querySelector('aside > a svg');if(logoIcon)logoIcon.innerHTML='<path d="M3 4h7a3 3 0 0 1 2 1 3 3 0 0 1 2-1h7v16h-7a3 3 0 0 0-2 1 3 3 0 0 0-2-1H3zM12 5v16"/>';document.querySelector('aside > .mt-auto')?.remove();loadActivity();

function organizeSidebar(){
 const menu=document.querySelector('aside nav');
 const groups=[['업무용',['manual-ai','glossary','registry-guide','checklist','cleaning','wiki']],['그 외',['lunch','study','articles','jobs','reflex']],['기타',['qna','suggestions']]];
 for(const [name,keys] of groups){
  const group=document.createElement('details');group.className='sidebar-group';group.open=true;
  const heading=document.createElement('summary');heading.textContent=name;group.append(heading);
  const items=document.createElement('div');items.className='sidebar-group-items';group.append(items);
  for(const key of keys){const link=[...menu.querySelectorAll('a')].find(a=>a.hash==='#'+key);if(link)items.append(link.closest('.nav-favorite-row')||link);}
  menu.append(group);
 }
}
organizeSidebar();

document.addEventListener('click',e=>{const button=e.target.closest('[data-delete-task]');if(!button)return;const index=Number(button.dataset.deleteTask);if(!Number.isInteger(index)||!state.tasks[index])return;state.tasks.splice(index,1);save();render();});
