function formatManualAnswer(answer){
 const inline=text=>safe(text)
  .replace(/\*\*([^*\n]+)\*\*/g,'<strong>$1</strong>')
  .replace(/__([^_\n]+)__/g,'<strong>$1</strong>')
  .replace(/\*([^*\n]+)\*/g,'<em>$1</em>')
  .replace(/`([^`\n]+)`/g,'<code>$1</code>')
  .replace(/\[(\d+(?:\s*,\s*\d+)*)\]/g,'<span class="manual-citation">[$1]</span>');
 const lines=String(answer||'').replace(/\r\n?/g,'\n').split('\n');let pos=0;
 const item=line=>{const m=line.match(/^(\s*)(?:([-*+])\s+|(\d+)[.)]\s+)(.*)$/);return m?{indent:m[1].replace(/\t/g,'    ').length,ordered:!!m[3],number:m[3],text:m[4]}:null};
 const list=(indent,ordered)=>{
  const first=item(lines[pos]),tag=ordered?'ol':'ul';let html=`<${tag}${ordered?` start="${first.number}"`:''}>`;
  while(pos<lines.length){
   const row=item(lines[pos]);if(!row||row.indent!==indent||row.ordered!==ordered)break;
   html+=`<li>${inline(row.text)}`;pos++;
   while(pos<lines.length){const child=item(lines[pos]);if(!child||child.indent<=indent)break;html+=list(child.indent,child.ordered)}
   html+='</li>';
  }
  return html+`</${tag}>`;
 };
 let html='',paragraph=[];
 const flush=()=>{if(paragraph.length){html+=`<p>${paragraph.map(inline).join('<br>')}</p>`;paragraph=[]}};
 while(pos<lines.length){
  const line=lines[pos].trim(),row=item(lines[pos]);
  if(!line||/^([-*_])\1{2,}$/.test(line)){flush();pos++;continue}
  const heading=line.match(/^#{1,6}\s+(.+?)\s*#*$/)||line.match(/^\*\*(.+?)\*\*\s*$/);
  if(heading){flush();html+=`<h4>${inline(heading[1])}</h4>`;pos++;continue}
  if(row){flush();html+=list(row.indent,row.ordered);continue}
  paragraph.push(line);pos++;
 }
 flush();return html;
}

function manualAnswerSections(answer){
 const text=String(answer||'').trim();
 const heading=/^\s*(?:#{1,6}\s*)?(?:\*\*)?\[?자세한\s*내용\]?(?:\*\*)?\s*[:：]?\s*$/m;
 const split=heading.exec(text);
 if(split){
  const summary=text.slice(0,split.index).replace(/^\s*(?:#{1,6}\s*)?(?:\*\*)?\[?핵심\s*요약\]?(?:\*\*)?\s*[:：]?\s*\n/,'').trim();
  if(summary)return {summary,details:text.slice(split.index+split[0].length).trim()};
 }
 // Older or unusually formatted answers still keep the full text available.
 const meaningful=text.split('\n').map(x=>x.trim()).filter(x=>x&&!/^#|^\*\*[^*]+\*\*$/.test(x)&&!/^제시된|^다음은/.test(x));
 const summary=(meaningful.find(x=>/^[-*+]\s+|^\d+[.)]\s+/.test(x))||meaningful[0]||text).replace(/^(?:[-*+]|\d+[.)])\s+/,'');
 return {summary:summary.length>250?summary.slice(0,250)+'…':summary,details:text===summary?'':text};
}

function manualAnswerBody(data){
 if(data.mode!=='ai')return `<div class="manual-answer-text">${formatManualAnswer(data.answer)}</div>`;
 const parts=manualAnswerSections(data.answer);
 return `<section class="manual-brief"><h4>핵심 요약</h4><div class="manual-answer-text">${formatManualAnswer(parts.summary)}</div></section>${parts.details?`<details class="manual-answer-more"><summary><span class="manual-more-closed">자세히 보기</span><span class="manual-more-open">자세한 내용 접기</span></summary><div class="manual-answer-text">${formatManualAnswer(parts.details)}</div></details>`:''}`;
}

async function renderManual(target){
 target.innerHTML+=`<section class="panel manual-panel"><h2>내규에 물어보기</h2><p class="muted" id="manual-coverage">수집한 내규를 확인하고 있습니다…</p><form id="ai-form"><label class="manual-question-label" for="manual-question">궁금한 업무나 규정을 질문하세요</label><div class="toolbar"><input id="manual-question" class="field" name="question" minlength="2" maxlength="500" placeholder="예: 연차휴가 사용 기준은 무엇인가요?" required><button class="primary">질문하기</button></div><label class="manual-history"><input type="checkbox" name="history"> 과거 개정 자료도 검색</label></form><p class="muted">기본 검색은 수집 당시 최신 첨부본을 사용합니다. 답변의 근거와 파일 개정일을 확인해 주세요.</p><div id="messages" aria-live="polite"></div></section><section class="panel"><details><summary>수집한 규정 목록 보기</summary><input class="field" id="manual-document-search" placeholder="규정명 검색" aria-label="수집한 규정명 검색"><div id="manual-document-list" class="manual-document-list"></div></details></section>`;
 try{const d=await api('/api/manual/info');if(!target.querySelector('#manual-coverage'))return;target.querySelector('#manual-coverage').textContent=`ALIO 내부규정 ${d.rules}건 · 첨부 ${d.downloaded}/${d.attachments}개 수집 · 최신본 ${d.indexed_rules}건 검색 가능 · ${d.collected} 수집`;
 if(d.unreadable?.length){const note=document.createElement('p');note.className='muted';note.textContent='과거 첨부 '+d.unreadable.length+'개는 DRM 보호로 본문 검색에서 제외됩니다: '+d.unreadable.map(x=>x.name).join(', ');target.querySelector('#manual-coverage').after(note)}
 const list=target.querySelector('#manual-document-list'),search=target.querySelector('#manual-document-search');
 const draw=()=>{list.innerHTML=d.documents.filter(x=>x.title.includes(search.value.trim())).map(x=>`<a href="${safe(x.url)}" target="_blank" rel="noopener noreferrer"><span>${safe(x.title)}</span><small>제·개정 ${safe(x.amended)}</small></a>`).join('')||'<p class="muted">일치하는 규정이 없습니다.</p>'};search.oninput=draw;draw();
 }catch(e){target.querySelector('#manual-coverage').textContent=e.message}
}
document.addEventListener('submit',async e=>{
 if(e.target.id!=='ai-form')return;e.preventDefault();
 const form=e.target,question=form.elements.question.value.trim(),messages=document.querySelector('#messages'),button=form.querySelector('button');if(button.disabled)return;
 const entry=document.createElement('article');entry.className='manual-answer';entry.innerHTML=`<h3>${safe(question)}</h3><p role="status">내규를 검색하고 답변을 준비하고 있습니다…</p>`;messages.prepend(entry);button.disabled=true;button.textContent='확인 중…';
 try{const d=await api('/api/manual/ask',{question,history:form.elements.history.checked});entry.innerHTML=`<h3>${safe(question)}</h3><span class="cleaning-status">${d.mode==='ai'?'내규 근거 AI 답변':'내규 원문 검색'}</span>${manualAnswerBody(d)}${d.notice?`<p class="manual-notice" role="status">${safe(d.notice)}</p>`:''}<div class="manual-sources">${d.sources.map((s,i)=>`<details><summary>[${i+1}] ${safe(s.title)} · ${s.page?s.page+'쪽':'쪽 정보 없음'}${s.current?'':' · 과거 자료'}</summary><p class="muted">${safe(s.file_name)}<br>규정 목록 제·개정일: ${safe(s.amended)}</p><blockquote>${safe(s.text)}</blockquote><div class="toolbar"><a href="${safe(s.file_url)}" target="_blank" rel="noopener noreferrer">첨부 원문</a><a href="${safe(s.source_url)}" target="_blank" rel="noopener noreferrer">ALIO 규정 상세</a></div></details>`).join('')}</div>`;
 }catch(error){entry.querySelector('[role="status"]').textContent=error.message}finally{button.disabled=false;button.textContent='질문하기'}
});
