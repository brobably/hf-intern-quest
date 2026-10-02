import json,secrets,time
from datetime import datetime,timezone,timedelta
ZONE=timezone(timedelta(hours=9))
def today():return datetime.now(ZONE).date().isoformat()
def week():
 d=datetime.now(ZONE).date();return (d-timedelta(days=d.weekday())).isoformat()
def initialize(c):
 c.executescript('''CREATE TABLE IF NOT EXISTS points(user_id INTEGER NOT NULL,event_key TEXT NOT NULL,day TEXT NOT NULL,amount INTEGER NOT NULL,PRIMARY KEY(user_id,event_key));CREATE TABLE IF NOT EXISTS reflex_runs(token TEXT PRIMARY KEY,user_id INTEGER NOT NULL,ready DOUBLE PRECISION NOT NULL,used INTEGER NOT NULL DEFAULT 0);CREATE TABLE IF NOT EXISTS reflex_scores(user_id INTEGER NOT NULL,week TEXT NOT NULL,ms INTEGER NOT NULL,PRIMARY KEY(user_id,week));CREATE TABLE IF NOT EXISTS cleaning_jobs(id INTEGER PRIMARY KEY,week TEXT NOT NULL,user_id INTEGER NOT NULL,area TEXT NOT NULL,done INTEGER NOT NULL DEFAULT 0,UNIQUE(week,user_id,area));''')
def award(c,uid,key,amount):c.execute('INSERT OR IGNORE INTO points(user_id,event_key,day,amount) VALUES(?,?,?,?)',(uid,key,today(),amount))
def get(h,u,db):
 if h.path!='/api/activity':return False
 month=today()[:7]
 with db() as c:
  xp=c.execute('SELECT COALESCE(SUM(amount),0) FROM points WHERE user_id=?',(u['id'],)).fetchone()[0]
  ranking=[dict(r) for r in c.execute("SELECT users.id,users.name,COALESCE(SUM(points.amount),0) AS xp FROM users LEFT JOIN points ON points.user_id=users.id AND points.day LIKE ? WHERE users.status='approved' GROUP BY users.id,users.name ORDER BY xp DESC,users.id",(month+'%',))]
  reflex=[dict(r) for r in c.execute('SELECT users.id,users.name,reflex_scores.ms FROM reflex_scores JOIN users ON users.id=reflex_scores.user_id WHERE week=? AND users.status=? ORDER BY ms,users.id',(week(),'approved'))]
  cleaning=[dict(r) for r in c.execute('SELECT cleaning_jobs.*,users.name FROM cleaning_jobs JOIN users ON users.id=cleaning_jobs.user_id WHERE week=? ORDER BY cleaning_jobs.id',(week(),))]
  members=[dict(r) for r in c.execute("SELECT id,name FROM users WHERE status='approved' ORDER BY name")]
  history=[dict(r) for r in c.execute('SELECT event_key,day,amount FROM points WHERE user_id=? ORDER BY day DESC LIMIT 30',(u['id'],))]
  clean_done=c.execute("SELECT COUNT(*) FROM points WHERE user_id=? AND event_key LIKE 'clean:%'",(u['id'],)).fetchone()[0]
 h.reply(200,dict(xp=int(xp),month=month,ranking=ranking,reflex=reflex,cleaning=cleaning,members=members,week=week(),history=history,clean_done=clean_done));return True
def post(h,u,d,db):
 path=h.path
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
