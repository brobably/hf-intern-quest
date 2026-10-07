import json,secrets,time
import pet
from datetime import datetime,timezone,timedelta
ZONE=timezone(timedelta(hours=9))
def today():return datetime.now(ZONE).date().isoformat()
def week():
 d=datetime.now(ZONE).date();return (d-timedelta(days=d.weekday())).isoformat()
def initialize(c):
 c.execute('CREATE TABLE IF NOT EXISTS reflex_comment_threads(comment_id INTEGER PRIMARY KEY,parent_id INTEGER NOT NULL)')
 c.execute('CREATE TABLE IF NOT EXISTS reflex_comment_likes(comment_id INTEGER NOT NULL,user_id INTEGER NOT NULL,PRIMARY KEY(comment_id,user_id))')
 c.execute('CREATE TABLE IF NOT EXISTS cleaning_rotation_weeks(department TEXT NOT NULL,week TEXT NOT NULL,PRIMARY KEY(department,week))')
 c.execute('CREATE TABLE IF NOT EXISTS cleaning_rotations(department TEXT PRIMARY KEY,start_week TEXT NOT NULL,area TEXT NOT NULL,members TEXT NOT NULL)')
 c.execute('CREATE TABLE IF NOT EXISTS reflex_comments(id INTEGER PRIMARY KEY,user_id INTEGER NOT NULL,body TEXT NOT NULL,created TEXT NOT NULL)')
 c.executescript('''CREATE TABLE IF NOT EXISTS points(user_id INTEGER NOT NULL,event_key TEXT NOT NULL,day TEXT NOT NULL,amount INTEGER NOT NULL,PRIMARY KEY(user_id,event_key));CREATE TABLE IF NOT EXISTS reflex_runs(token TEXT PRIMARY KEY,user_id INTEGER NOT NULL,ready DOUBLE PRECISION NOT NULL,used INTEGER NOT NULL DEFAULT 0);CREATE TABLE IF NOT EXISTS reflex_scores(user_id INTEGER NOT NULL,week TEXT NOT NULL,ms INTEGER NOT NULL,PRIMARY KEY(user_id,week));CREATE TABLE IF NOT EXISTS cleaning_jobs(id INTEGER PRIMARY KEY,week TEXT NOT NULL,user_id INTEGER NOT NULL,area TEXT NOT NULL,done INTEGER NOT NULL DEFAULT 0,UNIQUE(week,user_id,area));''')
 c.executescript("CREATE TABLE IF NOT EXISTS announcements(id INTEGER PRIMARY KEY,user_id INTEGER NOT NULL,title TEXT NOT NULL,body TEXT NOT NULL,created TEXT NOT NULL);CREATE TABLE IF NOT EXISTS calendar_events(id INTEGER PRIMARY KEY,user_id INTEGER NOT NULL,day TEXT NOT NULL,body TEXT NOT NULL);")
def rotation_member(c,r,target_week):
 ids=json.loads(r['members']);eligible=[]
 for uid in ids:
  if c.execute("SELECT users.id FROM users JOIN user_profiles ON users.id=user_profiles.user_id WHERE users.id=? AND users.status='approved' AND department=?",(uid,r['department'])).fetchone():eligible.append(uid)
 offset=(datetime.strptime(target_week,'%Y-%m-%d')-datetime.strptime(r['start_week'],'%Y-%m-%d')).days//7
 return eligible[offset%len(eligible)] if eligible and offset>=0 else None

def materialize_rotations(c,target_week):
 for r in c.execute('SELECT * FROM cleaning_rotations').fetchall():
  uid=rotation_member(c,r,target_week)
  if uid and not c.execute('SELECT week FROM cleaning_rotation_weeks WHERE department=? AND week=?',(r['department'],target_week)).fetchone():
   c.execute('INSERT OR IGNORE INTO cleaning_jobs(week,user_id,area) VALUES(?,?,?)',(target_week,uid,r['area']))
   c.execute('INSERT OR IGNORE INTO cleaning_rotation_weeks(department,week) VALUES(?,?)',(r['department'],target_week))

def award(c,uid,key,amount):
 c.execute('INSERT OR IGNORE INTO points(user_id,event_key,day,amount) VALUES(?,?,?,?)',(uid,key,today(),amount))
 if key.startswith('attendance:'):pet.reward(c,uid,key,10)
 elif amount>0:pet.reward(c,uid,'activity:'+key,max(1,amount//2),('activity',20))
def get(h,u,db):
 if h.path=='/api/reflex/comments':
  with db() as c:
   roots=c.execute('SELECT id FROM reflex_comments WHERE id NOT IN (SELECT comment_id FROM reflex_comment_threads) ORDER BY id DESC LIMIT 100').fetchall()
   ids=[r['id'] for r in roots];rows=[]
   if ids:
    marks=','.join('?' for _ in ids)
    rows=c.execute(f"SELECT r.*,users.name AS author,t.parent_id,(SELECT COUNT(*) FROM reflex_comment_likes l WHERE l.comment_id=r.id) AS hearts,EXISTS(SELECT 1 FROM reflex_comment_likes l WHERE l.comment_id=r.id AND l.user_id=?) AS liked FROM reflex_comments r JOIN users ON users.id=r.user_id LEFT JOIN reflex_comment_threads t ON t.comment_id=r.id WHERE r.id IN ({marks}) OR t.parent_id IN ({marks}) ORDER BY r.id DESC",(u['id'],*ids,*ids)).fetchall()
   received=c.execute('SELECT COUNT(*) FROM reflex_comment_likes l JOIN reflex_comments r ON r.id=l.comment_id WHERE r.user_id=?',(u['id'],)).fetchone()[0]
  h.reply(200,{'comments':[dict(r) for r in rows],'received_hearts':received});return True
 if h.path!='/api/activity':return False
 month=today()[:7]
 with db() as c:
  materialize_rotations(c,week())
  rotations=[dict(r) for r in c.execute('SELECT * FROM cleaning_rotations')]
  xp=c.execute('SELECT COALESCE(SUM(amount),0) FROM points WHERE user_id=?',(u['id'],)).fetchone()[0]
  ranking=[dict(r) for r in c.execute("SELECT users.id,users.name,COALESCE(SUM(points.amount),0) AS xp FROM users LEFT JOIN points ON points.user_id=users.id AND points.day LIKE ? WHERE users.status='approved' GROUP BY users.id,users.name ORDER BY xp DESC,users.id",(month+'%',))]
  reflex=[dict(r) for r in c.execute('SELECT users.id,users.name,reflex_scores.ms FROM reflex_scores JOIN users ON users.id=reflex_scores.user_id WHERE week=? AND users.status=? ORDER BY ms,users.id',(week(),'approved'))]
  profile=c.execute('SELECT department FROM user_profiles WHERE user_id=?',(u['id'],)).fetchone();department=profile[0] if profile else ''
  members=[dict(r) for r in c.execute("SELECT users.id,name,COALESCE(department,'') AS department FROM users LEFT JOIN user_profiles ON users.id=user_profiles.user_id WHERE status='approved' ORDER BY name")]
  cleaning=[dict(r) for r in c.execute("SELECT cleaning_jobs.*,users.name,COALESCE(department,'') AS department FROM cleaning_jobs JOIN users ON users.id=cleaning_jobs.user_id LEFT JOIN user_profiles ON users.id=user_profiles.user_id WHERE week=? ORDER BY cleaning_jobs.id",(week(),))]
  if u['role']!='admin':
   rotations=[r for r in rotations if department and r['department']==department]
   cleaning=[r for r in cleaning if department and r['department']==department]
   members=[r for r in members if department and r['department']==department]
  history=[dict(r) for r in c.execute('SELECT event_key,day,amount FROM points WHERE user_id=? ORDER BY day DESC LIMIT 30',(u['id'],))]
  announcements=[dict(r) for r in c.execute('SELECT id,title,body,created FROM announcements ORDER BY id DESC LIMIT 20')]
  events=[dict(r) for r in c.execute('SELECT id,day,body FROM calendar_events WHERE user_id=? ORDER BY id',(u['id'],))]
  clean_done=c.execute("SELECT COUNT(*) FROM points WHERE user_id=? AND event_key LIKE 'clean:%'",(u['id'],)).fetchone()[0]
 h.reply(200,dict(xp=int(xp),month=month,ranking=ranking,reflex=reflex,cleaning=cleaning,rotations=rotations,members=members,department=department,week=week(),history=history,clean_done=clean_done,announcements=announcements,events=events));return True
def post(h,u,d,db):
 path=h.path
 if path=='/api/reflex/comments/post':
  body=d.get('body');parent=d.get('parent_id')
  if not isinstance(body,str) or not 1<=len(body.strip())<=1000:h.reply(400,{'error':'댓글은 1~1,000자로 작성해 주세요.'});return True
  if parent is not None and type(parent)!=int:h.reply(400,{'error':'답글 대상을 확인해 주세요.'});return True
  with db() as c:
   c.execute('BEGIN IMMEDIATE')
   if parent is not None:
    root=c.execute('SELECT body FROM reflex_comments WHERE id=?',(parent,)).fetchone()
    if not root or not root['body'] or c.execute('SELECT comment_id FROM reflex_comment_threads WHERE comment_id=?',(parent,)).fetchone():h.reply(400,{'error':'답글을 달 수 없는 댓글입니다.'});return True
   row=c.execute('INSERT INTO reflex_comments(user_id,body,created) VALUES(?,?,?) RETURNING id',(u['id'],body.strip(),datetime.now(ZONE).isoformat())).fetchone()
   if parent is not None:c.execute('INSERT INTO reflex_comment_threads(comment_id,parent_id) VALUES(?,?)',(row['id'],parent))
  h.reply(201,{'ok':True});return True
 if path=='/api/reflex/comments/heart':
  cid=d.get('id');liked=d.get('liked')
  if type(cid)!=int or type(liked)!=bool:h.reply(400,{'error':'하트 요청을 확인해 주세요.'});return True
  with db() as c:
   c.execute('BEGIN IMMEDIATE');row=c.execute('SELECT body FROM reflex_comments WHERE id=?',(cid,)).fetchone()
   if not row or not row['body']:h.reply(404,{'error':'댓글이 없습니다.'});return True
   if liked:c.execute('INSERT OR IGNORE INTO reflex_comment_likes(comment_id,user_id) VALUES(?,?)',(cid,u['id']))
   else:c.execute('DELETE FROM reflex_comment_likes WHERE comment_id=? AND user_id=?',(cid,u['id']))
  h.reply(200,{'ok':True});return True
 if path=='/api/reflex/comments/remove':
  cid=d.get('id')
  if type(cid)!=int:h.reply(400,{'error':'댓글을 확인해 주세요.'});return True
  with db() as c:
   c.execute('BEGIN IMMEDIATE');row=c.execute('SELECT user_id FROM reflex_comments WHERE id=?',(cid,)).fetchone()
   if not row:h.reply(404,{'error':'댓글이 없습니다.'});return True
   if row['user_id']!=u['id'] and u['role']!='admin':h.reply(403,{'error':'본인이 작성한 댓글만 삭제할 수 있습니다.'});return True
   c.execute('DELETE FROM reflex_comment_likes WHERE comment_id=?',(cid,))
   if c.execute('SELECT comment_id FROM reflex_comment_threads WHERE parent_id=?',(cid,)).fetchone():c.execute("UPDATE reflex_comments SET body='' WHERE id=?",(cid,))
   else:
    c.execute('DELETE FROM reflex_comment_threads WHERE comment_id=?',(cid,));c.execute('DELETE FROM reflex_comments WHERE id=?',(cid,))
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
  token=secrets.token_urlsafe(24);delay=1500+secrets.randbelow(6501)
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
   coin_reward=pet.reward(c,u['id'],'game:'+today(),10)
  h.reply(200,{'ok':True,'coin_reward':coin_reward});return True
 if path in ['/api/cleaning/rotation','/api/cleaning/rotation/stop']:
  if u['role']!='admin':h.reply(403,{'error':'관리자만 로테이션을 설정할 수 있습니다.'});return True
  department=d.get('department')
  if not isinstance(department,str) or not 1<=len(department.strip())<=80:h.reply(400,{'error':'부서를 선택해 주세요.'});return True
  with db() as c:
   c.execute('BEGIN IMMEDIATE')
   if path.endswith('/stop'):
    c.execute('DELETE FROM cleaning_rotations WHERE department=?',(department,))
   else:
    ids=d.get('members');area=d.get('area');start=d.get('start_week')
    try:
     date=datetime.strptime(start,'%Y-%m-%d')
     assert date.weekday()==0 and start>=week()
    except (TypeError,ValueError,AssertionError):h.reply(400,{'error':'시작 주는 이번 주 이후의 월요일을 선택해 주세요.'});return True
    if not isinstance(ids,list) or not 1<=len(ids)<=100 or any(type(i)!=int for i in ids) or len(set(ids))!=len(ids) or not isinstance(area,str) or not 1<=len(area.strip())<=80:h.reply(400,{'error':'참여 순서와 담당 구역을 확인해 주세요.'});return True
    for uid in ids:
     if not c.execute("SELECT users.id FROM users JOIN user_profiles ON users.id=user_profiles.user_id WHERE users.id=? AND users.status='approved' AND department=?",(uid,department)).fetchone():h.reply(400,{'error':'선택한 부서의 승인된 회원만 참여할 수 있습니다.'});return True
    c.execute('DELETE FROM cleaning_rotations WHERE department=?',(department,))
    c.execute('INSERT INTO cleaning_rotations(department,start_week,area,members) VALUES(?,?,?,?)',(department,start,area.strip(),json.dumps(ids)))
  h.reply(200,{'ok':True});return True
 if path=='/api/cleaning/assign':
  if u['role']!='admin':h.reply(403,{'error':'관리자만 당번을 설정할 수 있습니다.'});return True
  uid=d.get('user_id');area=d.get('area')
  if type(uid)!=int or not isinstance(area,str) or not 1<=len(area.strip())<=80:h.reply(400,{'error':'담당자와 구역을 확인해 주세요.'});return True
  with db() as c:
   if not c.execute("SELECT id FROM users WHERE id=? AND status='approved'",(uid,)).fetchone():h.reply(400,{'error':'승인된 회원을 선택하세요.'});return True
   target=c.execute('SELECT department FROM user_profiles WHERE user_id=?',(uid,)).fetchone()
   if not target or not target[0]:h.reply(400,{'error':'담당자의 부서를 가입 승인 관리에서 먼저 설정해 주세요.'});return True
   if d.get('department',target[0])!=target[0]:h.reply(400,{'error':'선택한 부서의 회원만 배정할 수 있습니다.'});return True
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
