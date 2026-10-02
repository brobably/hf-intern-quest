import json,secrets,time
from datetime import datetime,timezone,timedelta
ZONE=timezone(timedelta(hours=9))
def today():return datetime.now(ZONE).date().isoformat()
def week():
 d=datetime.now(ZONE).date();return (d-timedelta(days=d.weekday())).isoformat()
def initialize(c):
 c.execute('CREATE TABLE IF NOT EXISTS reflex_comments(id INTEGER PRIMARY KEY,user_id INTEGER NOT NULL,body TEXT NOT NULL,created TEXT NOT NULL)')
 c.executescript('''CREATE TABLE IF NOT EXISTS points(user_id INTEGER NOT NULL,event_key TEXT NOT NULL,day TEXT NOT NULL,amount INTEGER NOT NULL,PRIMARY KEY(user_id,event_key));CREATE TABLE IF NOT EXISTS reflex_runs(token TEXT PRIMARY KEY,user_id INTEGER NOT NULL,ready DOUBLE PRECISION NOT NULL,used INTEGER NOT NULL DEFAULT 0);CREATE TABLE IF NOT EXISTS reflex_scores(user_id INTEGER NOT NULL,week TEXT NOT NULL,ms INTEGER NOT NULL,PRIMARY KEY(user_id,week));CREATE TABLE IF NOT EXISTS cleaning_jobs(id INTEGER PRIMARY KEY,week TEXT NOT NULL,user_id INTEGER NOT NULL,area TEXT NOT NULL,done INTEGER NOT NULL DEFAULT 0,UNIQUE(week,user_id,area));''')
 c.executescript("CREATE TABLE IF NOT EXISTS announcements(id INTEGER PRIMARY KEY,user_id INTEGER NOT NULL,title TEXT NOT NULL,body TEXT NOT NULL,created TEXT NOT NULL);CREATE TABLE IF NOT EXISTS calendar_events(id INTEGER PRIMARY KEY,user_id INTEGER NOT NULL,day TEXT NOT NULL,body TEXT NOT NULL);")
def award(c,uid,key,amount):c.execute('INSERT OR IGNORE INTO points(user_id,event_key,day,amount) VALUES(?,?,?,?)',(uid,key,today(),amount))
def get(h,u,db):
 if h.path=='/api/reflex/comments':
  with db() as c:rows=c.execute('SELECT reflex_comments.*,users.name AS author FROM reflex_comments JOIN users ON users.id=reflex_comments.user_id ORDER BY reflex_comments.id DESC LIMIT 100').fetchall()
  h.reply(200,{'comments':[dict(r) for r in rows]});return True
 if h.path!='/api/activity':return False
 month=today()[:7]
 with db() as c:
  xp=c.execute('SELECT COALESCE(SUM(amount),0) FROM points WHERE user_id=?',(u['id'],)).fetchone()[0]
  ranking=[dict(r) for r in c.execute("SELECT users.id,users.name,COALESCE(SUM(points.amount),0) AS xp FROM users LEFT JOIN points ON points.user_id=users.id AND points.day LIKE ? WHERE users.status='approved' GROUP BY users.id,users.name ORDER BY xp DESC,users.id",(month+'%',))]
  reflex=[dict(r) for r in c.execute('SELECT users.id,users.name,reflex_scores.ms FROM reflex_scores JOIN users ON users.id=reflex_scores.user_id WHERE week=? AND users.status=? ORDER BY ms,users.id',(week(),'approved'))]
  cleaning=[dict(r) for r in c.execute('SELECT cleaning_jobs.*,users.name FROM cleaning_jobs JOIN users ON users.id=cleaning_jobs.user_id WHERE week=? ORDER BY cleaning_jobs.id',(week(),))]
  members=[dict(r) for r in c.execute("SELECT id,name FROM users WHERE status='approved' ORDER BY name")]
  history=[dict(r) for r in c.execute('SELECT event_key,day,amount FROM points WHERE user_id=? ORDER BY day DESC LIMIT 30',(u['id'],))]
  announcements=[dict(r) for r in c.execute('SELECT id,title,body,created FROM announcements ORDER BY id DESC LIMIT 20')]
  events=[dict(r) for r in c.execute('SELECT id,day,body FROM calendar_events WHERE user_id=? ORDER BY id',(u['id'],))]
  clean_done=c.execute("SELECT COUNT(*) FROM points WHERE user_id=? AND event_key LIKE 'clean:%'",(u['id'],)).fetchone()[0]
 h.reply(200,dict(xp=int(xp),month=month,ranking=ranking,reflex=reflex,cleaning=cleaning,members=members,week=week(),history=history,clean_done=clean_done,announcements=announcements,events=events));return True
def post(h,u,d,db):
 path=h.path
 if path=='/api/reflex/comments/post':
  body=d.get('body')
  if not isinstance(body,str) or not 1<=len(body.strip())<=1000:h.reply(400,{'error':'댓글은 1~1,000자로 작성해 주세요.'});return True
  with db() as c:c.execute('INSERT INTO reflex_comments(user_id,body,created) VALUES(?,?,?)',(u['id'],body.strip(),datetime.now(ZONE).isoformat()))
  h.reply(201,{'ok':True});return True
 if path=='/api/reflex/comments/remove':
  cid=d.get('id')
  if type(cid)!=int:h.reply(400,{'error':'댓글을 확인해 주세요.'});return True
  with db() as c:
   c.execute('BEGIN IMMEDIATE');row=c.execute('SELECT user_id FROM reflex_comments WHERE id=?',(cid,)).fetchone()
   if not row:h.reply(404,{'error':'댓글이 없습니다.'});return True
   if row['user_id']!=u['id'] and u['role']!='admin':h.reply(403,{'error':'본인이 작성한 댓글만 삭제할 수 있습니다.'});return True
   c.execute('DELETE FROM reflex_comments WHERE id=?',(cid,))
  h.reply(200,{'ok':True});return True
 if path=='/api/announcements/post':
  if u['role']!='admin':h.reply(403,{'error':'관리자만 공지할 수 있습니다.'});return True
  title=d.get('title');body=d.get('body')
  if not isinstance(title,str) or not 1<=len(title.strip())<=120 or not isinstance(body,str) or not 1<=len(body.strip())<=5000:h.reply(400,{'error':'공지 제목과 내용을 확인하세요.'});return True
  with db() as c:c.execute('INSERT INTO announcements(user_id,title,body,created) VALUES(?,?,?,?)',(u['id'],title.strip(),body.strip(),datetime.now(ZONE).isoformat()))
  h.reply(201,{'ok':True});return True
 if path in ['/api/announcements/remove','/api/calendar/remove']:
  pid=d.get('id')
  if type(pid)!=int:h.reply(400,{'error':'항목을 확인하세요.'});return True
  with db() as c:
   if path.startswith('/api/announcements'):
    if u['role']!='admin':h.reply(403,{'error':'관리자만 공지를 삭제할 수 있습니다.'});return True
    c.execute('DELETE FROM announcements WHERE id=?',(pid,))
   else:c.execute('DELETE FROM calendar_events WHERE id=? AND user_id=?',(pid,u['id']))
  h.reply(200,{'ok':True});return True
 if path=='/api/calendar/post':
  day=d.get('day');body=d.get('body')
  if not isinstance(day,str) or not isinstance(body,str) or not 1<=len(body.strip())<=1000:h.reply(400,{'error':'날짜와 내용을 확인하세요.'});return True
  try:datetime.strptime(day,'%Y-%m-%d')
  except ValueError:h.reply(400,{'error':'날짜를 확인하세요.'});return True
  with db() as c:c.execute('INSERT INTO calendar_events(user_id,day,body) VALUES(?,?,?)',(u['id'],day,body.strip()))
  h.reply(201,{'ok':True});return True
 if path=='/api/reflex/start':
  token=secrets.token_urlsafe(24);delay=1600+secrets.randbelow(2500)
  with db() as c:c.execute('INSERT INTO reflex_runs(token,user_id,ready) VALUES(?,?,?)',(token,u['id'],time.time()+delay/1000))
  h.reply(200,dict(token=token,delay=delay));return True
 if path=='/api/reflex/result':
  ms=d.get('ms');token=d.get('token')
  if type(ms)!=int or not 100<=ms<=10000 or not isinstance(token,str):h.reply(400,{'error':'유효한 게임 기록이 아닙니다.'});return True
  with db() as c:
   c.execute('BEGIN IMMEDIATE');run=c.execute('SELECT * FROM reflex_runs WHERE token=? AND user_id=?',(token,u['id'])).fetchone()
   elapsed=(time.time()-run['ready'])*1000 if run else -1
   if not run or run['used'] or elapsed<0 or elapsed>60000:h.reply(400,{'error':'게임을 다시 시작해 주세요.'});return True
   c.execute('UPDATE reflex_runs SET used=1 WHERE token=?',(token,))
   old=c.execute('SELECT ms FROM reflex_scores WHERE user_id=? AND week=?',(u['id'],week())).fetchone()
   if not old:c.execute('INSERT INTO reflex_scores(user_id,week,ms) VALUES(?,?,?)',(u['id'],week(),ms))
   elif ms<old['ms']:c.execute('UPDATE reflex_scores SET ms=? WHERE user_id=? AND week=?',(ms,u['id'],week()))
  h.reply(200,{'ok':True});return True
 if path=='/api/cleaning/assign':
  if u['role']!='admin':h.reply(403,{'error':'관리자만 당번을 설정할 수 있습니다.'});return True
  uid=d.get('user_id');area=d.get('area')
  if type(uid)!=int or not isinstance(area,str) or not 1<=len(area.strip())<=80:h.reply(400,{'error':'담당자와 구역을 확인해 주세요.'});return True
  with db() as c:
   if not c.execute("SELECT id FROM users WHERE id=? AND status='approved'",(uid,)).fetchone():h.reply(400,{'error':'승인된 회원을 선택하세요.'});return True
   c.execute('INSERT OR IGNORE INTO cleaning_jobs(week,user_id,area) VALUES(?,?,?)',(week(),uid,area.strip()))
  h.reply(201,{'ok':True});return True
 if path in ['/api/cleaning/complete','/api/cleaning/remove']:
  pid=d.get('id')
  if type(pid)!=int:h.reply(400,{'error':'당번을 확인해 주세요.'});return True
  with db() as c:
   c.execute('BEGIN IMMEDIATE');job=c.execute('SELECT * FROM cleaning_jobs WHERE id=? AND week=?',(pid,week())).fetchone()
   if not job:h.reply(404,{'error':'이번 주 당번을 찾을 수 없습니다.'});return True
   if u['role']!='admin' and (path.endswith('/remove') or job['user_id']!=u['id']):h.reply(403,{'error':'본인 담당 구역만 완료할 수 있습니다.'});return True
   if path.endswith('/remove'):c.execute('DELETE FROM cleaning_jobs WHERE id=?',(pid,))
   else:c.execute('UPDATE cleaning_jobs SET done=1 WHERE id=?',(pid,));award(c,job['user_id'],'clean:'+job['week']+':'+str(job['user_id'])+':'+job['area'],10)
  h.reply(200,{'ok':True});return True
 return False
