"""Per-user daily checklist snapshots; historical corrections do not award XP."""
import json,hashlib
from datetime import datetime
from urllib.parse import urlsplit,parse_qs
import activity

def initialize(c):
 c.execute('CREATE TABLE IF NOT EXISTS task_history(user_id INTEGER NOT NULL,day TEXT NOT NULL,title TEXT NOT NULL,done INTEGER NOT NULL,PRIMARY KEY(user_id,day,title))')

def due(t,day):
 days=t[3] if len(t)>3 else []
 if days=='daily':days=[1,2,3,4,5]
 return not isinstance(days,list) or not days or datetime.strptime(day,'%Y-%m-%d').isoweekday() in days

def capture(c,uid,tasks):
 day=activity.today()
 for t in tasks:
  if not isinstance(t,list) or len(t)<3 or not isinstance(t[0],str):continue
  if due(t,day):
   recurring=len(t)>3 and (t[3]=='daily' or isinstance(t[3],list) and bool(t[3]))
   done=bool(t[1]) and (not recurring or len(t)>4 and t[4]==day)
   c.execute('INSERT OR IGNORE INTO task_history VALUES(?,?,?,?)',(uid,day,t[0],int(done)))
   c.execute('UPDATE task_history SET done=? WHERE user_id=? AND day=? AND title=?',(int(done),uid,day,t[0]))
  if len(t)>4 and t[1] and t[4]<day:
   c.execute('INSERT OR IGNORE INTO task_history VALUES(?,?,?,1)',(uid,t[4],t[0]))

def get(h,u,db):
 if urlsplit(h.path).path!='/api/task-history':return False
 day=parse_qs(urlsplit(h.path).query).get('day',[activity.today()])[0]
 try:datetime.strptime(day,'%Y-%m-%d')
 except ValueError:h.reply(400,{'error':'날짜를 확인해 주세요.'});return True
 if day>activity.today():h.reply(400,{'error':'오늘 또는 지난 날짜를 선택해 주세요.'});return True
 with db() as c:
  tasks=json.loads(c.execute('SELECT state FROM users WHERE id=?',(u['id'],)).fetchone()[0]).get('tasks',[])
  capture(c,u['id'],tasks)
  rows=[dict(r) for r in c.execute('SELECT title,done FROM task_history WHERE user_id=? AND day=? ORDER BY title',(u['id'],day))]
  saved=bool(rows)
  if not rows:
   keys={r[0] for r in c.execute("SELECT event_key FROM points WHERE user_id=? AND day=? AND event_key LIKE 'task:%'",(u['id'],day))}
   rows=[{'title':t[0],'done':int('task:'+day+':'+hashlib.sha256(t[0].encode()).hexdigest() in keys)} for t in tasks if due(t,day)]
 h.reply(200,{'day':day,'tasks':rows,'saved':saved});return True

def post(h,u,d,db):
 if h.path!='/api/task-history':return False
 day=d.get('day','');title=d.get('title');done=d.get('done')
 try:datetime.strptime(day,'%Y-%m-%d')
 except (TypeError,ValueError):h.reply(400,{'error':'날짜를 확인해 주세요.'});return True
 if day>=activity.today() or not isinstance(title,str) or not 1<=len(title)<=150 or type(done)!=bool:h.reply(400,{'error':'지난 날짜의 업무 기록을 확인해 주세요.'});return True
 with db() as c:
  c.execute('BEGIN IMMEDIATE')
  if not c.execute('SELECT title FROM task_history WHERE user_id=? AND day=?',(u['id'],day)).fetchone():
   tasks=json.loads(c.execute('SELECT state FROM users WHERE id=?',(u['id'],)).fetchone()[0]).get('tasks',[])
   keys={r[0] for r in c.execute("SELECT event_key FROM points WHERE user_id=? AND day=? AND event_key LIKE 'task:%'",(u['id'],day))}
   for t in tasks:
    if due(t,day):c.execute('INSERT OR IGNORE INTO task_history VALUES(?,?,?,?)',(u['id'],day,t[0],int('task:'+day+':'+hashlib.sha256(t[0].encode()).hexdigest() in keys)))
  c.execute('INSERT OR IGNORE INTO task_history VALUES(?,?,?,?)',(u['id'],day,title,int(done)))
  c.execute('UPDATE task_history SET done=? WHERE user_id=? AND day=? AND title=?',(int(done),u['id'],day,title))
 h.reply(200,{'ok':True});return True

