"""Member-only playground, anonymous discussions and aggregate usage metrics."""
import json,secrets,time
from datetime import datetime,timedelta
import activity,privacy,pet

ROUTES=['','manual-ai','glossary','registry-guide','checklist','wiki','cleaning','lunch','study','articles','jobs','games','reflex','pet','stroop','anonymous']
COLORS=[('빨강','#ce3e45'),('파랑','#246dd0'),('초록','#278459'),('보라','#8755bb')]
def initialize(c):
 c.executescript("""CREATE TABLE IF NOT EXISTS page_views(id INTEGER PRIMARY KEY,user_id INTEGER NOT NULL,route TEXT NOT NULL,visited INTEGER NOT NULL);CREATE TABLE IF NOT EXISTS color_runs(token TEXT PRIMARY KEY,user_id INTEGER NOT NULL,answers TEXT NOT NULL,started INTEGER NOT NULL);CREATE TABLE IF NOT EXISTS color_scores(id INTEGER PRIMARY KEY,user_id INTEGER NOT NULL,week TEXT NOT NULL,correct INTEGER NOT NULL,elapsed INTEGER NOT NULL);CREATE TABLE IF NOT EXISTS anonymous_posts(id INTEGER PRIMARY KEY,user_id INTEGER NOT NULL,title TEXT NOT NULL,body TEXT NOT NULL,created TEXT NOT NULL);CREATE TABLE IF NOT EXISTS anonymous_replies(id INTEGER PRIMARY KEY,post_id INTEGER NOT NULL,user_id INTEGER NOT NULL,parent_id INTEGER NOT NULL DEFAULT 0,body TEXT NOT NULL,created TEXT NOT NULL);CREATE TABLE IF NOT EXISTS anonymous_hearts(post_id INTEGER NOT NULL,user_id INTEGER NOT NULL,PRIMARY KEY(post_id,user_id));CREATE TABLE IF NOT EXISTS anonymous_reports(post_id INTEGER NOT NULL,user_id INTEGER NOT NULL,PRIMARY KEY(post_id,user_id));""")
def get(h,u,db):
 if h.path=='/api/jobs':
  with db() as c:
   excluded=privacy.hidden(c,u)
   jobs=[{'title':r['title'],'link':r['link']} for r in c.execute("SELECT user_id,title,link FROM posts WHERE kind='jobs' ORDER BY id DESC") if r['user_id'] not in excluded and r['link'].startswith(('https://','http://'))]
  h.reply(200,{'jobs':jobs,'message':'링커리어와 자소설닷컴의 공개 채용 페이지로 이동할 수 있습니다. 자동 수집은 제공처의 접근 제한으로 현재 지원되지 않습니다. 아래에는 회원이 등록한 공고가 표시됩니다.'});return True
 if h.path=='/api/analytics':
  if u['role']!='admin':h.reply(403,{'error':'관리자 전용 페이지입니다.'});return True
  cutoff=int(time.time())-30*86400
  with db() as c:
   rows=[dict(r) for r in c.execute("SELECT route,COUNT(*) AS views,COUNT(DISTINCT page_views.user_id) AS visitors FROM page_views JOIN users ON users.id=page_views.user_id WHERE visited>=? AND users.role<>'admin' AND users.status='approved' AND users.employee<>? GROUP BY route ORDER BY views DESC",(cutoff,privacy.TEST_EMPLOYEE))]
  h.reply(200,{'rows':rows,'days':30});return True
 if h.path=='/api/stroop':
  with db() as c:
   rows=[dict(r) for r in c.execute("SELECT color_scores.id,color_scores.user_id,users.name,correct,elapsed FROM color_scores JOIN users ON users.id=color_scores.user_id WHERE week=? AND users.status='approved' AND users.employee<>? ORDER BY correct DESC,elapsed,color_scores.id LIMIT 100",(activity.week(),privacy.TEST_EMPLOYEE))]
  best=[];seen=set()
  for r in rows:
   if r['user_id'] not in seen:best.append(r);seen.add(r['user_id'])
  h.reply(200,{'scores':best});return True
 if h.path=='/api/anonymous':
  with db() as c:
   hidden=privacy.hidden(c,u);posts=[]
   for r in c.execute('SELECT * FROM anonymous_posts ORDER BY id DESC LIMIT 100'):
    if r['user_id'] in hidden:continue
    aliases={r['user_id']:'익명(글쓴이)'};replies=[]
    for x in c.execute('SELECT * FROM anonymous_replies WHERE post_id=? ORDER BY id',(r['id'],)):
     if x['user_id'] in hidden:continue
     if x['user_id'] not in aliases:aliases[x['user_id']]='익명'+str(len(aliases))
     replies.append({'id':x['id'],'parent_id':x['parent_id'],'author':aliases[x['user_id']],'body':x['body'],'created':x['created']})
    count=c.execute('SELECT COUNT(*) FROM anonymous_hearts WHERE post_id=?',(r['id'],)).fetchone()[0]
    liked=bool(c.execute('SELECT user_id FROM anonymous_hearts WHERE post_id=? AND user_id=?',(r['id'],u['id'])).fetchone())
    reports=c.execute('SELECT COUNT(*) FROM anonymous_reports WHERE post_id=?',(r['id'],)).fetchone()[0] if u['role']=='admin' else None
    posts.append({'id':r['id'],'title':r['title'],'body':r['body'],'created':r['created'],'owned':r['user_id']==u['id'],'hearts':count,'liked':liked,'replies':replies,'reports':reports})
  h.reply(200,{'posts':posts});return True
 return False
def post(h,u,d,db):
 path=h.path
 if path=='/api/page-view':
  route=d.get('route');now=int(time.time())
  if route not in ROUTES:h.reply(400,{'error':'페이지를 확인해 주세요.'});return True
  if u['role']!='admin' and u['employee']!=privacy.TEST_EMPLOYEE:
   with db() as c:
    last=c.execute('SELECT visited FROM page_views WHERE user_id=? AND route=? ORDER BY id DESC LIMIT 1',(u['id'],route)).fetchone()
    if not last or now-last[0]>=30:c.execute('INSERT INTO page_views(user_id,route,visited) VALUES(?,?,?)',(u['id'],route,now))
  h.reply(200,{'ok':True});return True
 if path=='/api/stroop/start':
  token=secrets.token_urlsafe(24);answers=[secrets.randbelow(4) for _ in range(10)]
  questions=[{'word':COLORS[secrets.randbelow(4)][0],'color':COLORS[i][1]} for i in answers]
  with db() as c:
   c.execute('DELETE FROM color_runs WHERE started<?',(int(time.time()*1000)-600000,))
   c.execute('INSERT INTO color_runs VALUES(?,?,?,?)',(token,u['id'],json.dumps(answers),int(time.time()*1000)))
  h.reply(200,{'token':token,'questions':questions});return True
 if path=='/api/stroop/finish':
  answers=d.get('answers')
  if not isinstance(answers,list) or len(answers)!=10 or any(type(x)!=int or x not in range(4) for x in answers):h.reply(400,{'error':'10문제를 완료해 주세요.'});return True
  with db() as c:
   c.execute('BEGIN IMMEDIATE')
   run=c.execute('SELECT * FROM color_runs WHERE token=? AND user_id=?',(d.get('token',''),u['id'])).fetchone()
   if not run:h.reply(400,{'error':'게임을 다시 시작해 주세요.'});return True
   elapsed=int(time.time()*1000)-run['started']
   if not 1000<=elapsed<=600000:h.reply(400,{'error':'진행 시간을 확인해 주세요.'});return True
   correct=sum(a==b for a,b in zip(answers,json.loads(run['answers'])))
   c.execute('DELETE FROM color_runs WHERE token=?',(run['token'],))
   c.execute('INSERT INTO color_scores(user_id,week,correct,elapsed) VALUES(?,?,?,?)',(u['id'],activity.week(),correct,elapsed))
   if u['employee']!=privacy.TEST_EMPLOYEE:pet.reward(c,u['id'],'game:'+activity.today(),10,('game',10))
  h.reply(200,{'correct':correct,'elapsed':elapsed});return True
 if path.startswith('/api/anonymous/'):
  action=path.rsplit('/',1)[-1];pid=d.get('id');body=d.get('body','');created=datetime.now(activity.ZONE).isoformat(timespec='minutes')
  with db() as c:
   if action=='post':
    title=d.get('title','')
    if not isinstance(title,str) or not 1<=len(title.strip())<=120 or not isinstance(body,str) or not 1<=len(body.strip())<=5000:h.reply(400,{'error':'제목과 내용을 확인해 주세요.'});return True
    c.execute('INSERT INTO anonymous_posts(user_id,title,body,created) VALUES(?,?,?,?)',(u['id'],title.strip(),body.strip(),created))
   else:
    r=c.execute('SELECT * FROM anonymous_posts WHERE id=?',(pid,)).fetchone() if type(pid)==int else None
    if not r or not privacy.visible(c,u,r['user_id']):h.reply(404,{'error':'글을 찾을 수 없습니다.'});return True
    if action=='reply':
     parent=d.get('parent_id',0)
     if not isinstance(body,str) or not 1<=len(body.strip())<=1000 or type(parent)!=int or (parent and not c.execute('SELECT id FROM anonymous_replies WHERE id=? AND post_id=?',(parent,pid)).fetchone()):h.reply(400,{'error':'댓글을 확인해 주세요.'});return True
     c.execute('INSERT INTO anonymous_replies(post_id,user_id,parent_id,body,created) VALUES(?,?,?,?,?)',(pid,u['id'],parent,body.strip(),created))
    elif action=='heart':
     if c.execute('SELECT user_id FROM anonymous_hearts WHERE post_id=? AND user_id=?',(pid,u['id'])).fetchone():c.execute('DELETE FROM anonymous_hearts WHERE post_id=? AND user_id=?',(pid,u['id']))
     else:c.execute('INSERT OR IGNORE INTO anonymous_hearts VALUES(?,?)',(pid,u['id']))
    elif action=='report':c.execute('INSERT OR IGNORE INTO anonymous_reports VALUES(?,?)',(pid,u['id']))
    elif action=='delete':
     if r['user_id']!=u['id'] and u['role']!='admin':h.reply(403,{'error':'작성자와 관리자만 삭제할 수 있습니다.'});return True
     for table in ['anonymous_replies','anonymous_hearts','anonymous_reports']:c.execute('DELETE FROM '+table+' WHERE post_id=?',(pid,))
     c.execute('DELETE FROM anonymous_posts WHERE id=?',(pid,))
    else:h.reply(404,{'error':'요청을 확인해 주세요.'});return True
  h.reply(200,{'ok':True});return True
 return False
