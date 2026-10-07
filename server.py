"""Local authentication server. Bind to loopback; deploy behind HTTPS for shared use."""
import hashlib,hmac,json,os,re,secrets,sqlite3,time
from pathlib import Path
from http.server import ThreadingHTTPServer,SimpleHTTPRequestHandler
from http.cookies import SimpleCookie
from contextlib import contextmanager
from datetime import datetime,timezone,timedelta
from storage import connect,IntegrityError
import activity
import pet
import meals
import wiki
import news
import privacy
BASE=Path(__file__).resolve().parent
DATA=Path(os.environ.get('HF_DATA',str(BASE/'data')));DATA.mkdir(exist_ok=True)
DB=DATA/'accounts.sqlite3'
PORT=int(os.environ.get('PORT',os.environ.get('HF_PORT','8765')))
BIND=os.environ.get('HF_BIND','127.0.0.1')
SECURE=os.environ.get('HF_HTTPS')=='1'
attempts={}
@contextmanager
def db():
 with connect(DB) as c:yield c
with db() as c:
 c.executescript('''CREATE TABLE IF NOT EXISTS users(id INTEGER PRIMARY KEY,employee TEXT UNIQUE NOT NULL,name TEXT NOT NULL,salt TEXT NOT NULL,hash TEXT NOT NULL,status TEXT NOT NULL,role TEXT NOT NULL DEFAULT 'intern',state TEXT NOT NULL DEFAULT '{}');CREATE TABLE IF NOT EXISTS sessions(token TEXT PRIMARY KEY,user_id INTEGER NOT NULL,expires INTEGER NOT NULL);''')
 c.execute('CREATE TABLE IF NOT EXISTS attendance(user_id INTEGER NOT NULL,day TEXT NOT NULL,PRIMARY KEY(user_id,day))')
 c.execute("CREATE TABLE IF NOT EXISTS posts(id INTEGER PRIMARY KEY,kind TEXT NOT NULL,user_id INTEGER NOT NULL,title TEXT NOT NULL,body TEXT NOT NULL,link TEXT NOT NULL DEFAULT '',event_day TEXT NOT NULL DEFAULT '',created TEXT NOT NULL,members TEXT NOT NULL DEFAULT '[]',replies TEXT NOT NULL DEFAULT '[]')")
 c.execute("CREATE TABLE IF NOT EXISTS user_profiles(user_id INTEGER PRIMARY KEY,department TEXT NOT NULL DEFAULT '',rejection_reason TEXT NOT NULL DEFAULT '')")
 pet.initialize(c)
 activity.initialize(c)
 meals.initialize(c)
 wiki.initialize(c)
 news.initialize(c)
 # Apply the explicitly requested account promotions once, preserving later role changes.
 c.execute('CREATE TABLE IF NOT EXISTS account_changes(change_key TEXT PRIMARY KEY)')
 if not c.execute('SELECT change_key FROM account_changes WHERE change_key=?',('admin-promotion-20261007',)).fetchone():
  targets=[('김태욱','56512'),('이강인','1234')]
  if all(c.execute("SELECT id FROM users WHERE name=? AND employee=? AND status='approved'",target).fetchone() for target in targets):
   for target in targets:c.execute("UPDATE users SET role='admin' WHERE name=? AND employee=? AND status='approved'",target)
   c.execute('INSERT OR IGNORE INTO account_changes(change_key) VALUES(?)',('admin-promotion-20261007',))
 # Admin bootstrap is a private runtime secret, never a committed database.
 seed=os.environ.get('HF_ADMIN_SEED')
 if seed and not c.execute("SELECT COUNT(*) FROM users WHERE role='admin'").fetchone()[0]:
  admin=json.loads(seed)
  if not re.fullmatch(r'[a-f0-9]{32}',admin.get('salt','')) or not re.fullmatch(r'[a-f0-9]{128}',admin.get('hash','')):raise ValueError('Invalid administrator seed')
  c.execute('INSERT INTO users(employee,name,salt,hash,status,role) VALUES(?,?,?,?,?,?)',(admin['employee'],admin['name'],admin['salt'],admin['hash'],'approved','admin'))
def attendance_info(uid):
 today=datetime.now(timezone(timedelta(hours=9))).date()
 with db() as c:days=[x[0] for x in c.execute('SELECT day FROM attendance WHERE user_id=? ORDER BY day',(uid,))]
 cursor=today if today.isoformat() in days else today-timedelta(days=1);streak=0;known=set(days)
 while cursor.isoformat() in known:streak+=1;cursor-=timedelta(days=1)
 return {'today':today.isoformat(),'checked':today.isoformat() in days,'days':days,'total':len(days),'streak':streak}
def digest(p,s):return hashlib.scrypt(p.encode(),salt=bytes.fromhex(s),n=16384,r=8,p=1).hex()
def public(u):return {k:u[k] for k in ['id','employee','name','status','role']}
class Handler(SimpleHTTPRequestHandler):
 def __init__(self,*a,**kw):super().__init__(*a,directory=str(BASE/'dist'),**kw)
 def log_message(self,*a):pass
 def end_headers(self):
  if not self.path.startswith('/api/'):self.send_header('Cache-Control','no-cache')
  self.send_header('X-Content-Type-Options','nosniff');self.send_header('Referrer-Policy','same-origin');self.send_header('X-Frame-Options','DENY');super().end_headers()
 def reply(self,status,obj,cookie=None):
  if self.path.startswith('/api/') and self.path not in ['/api/me','/api/state','/api/attendance','/api/pet'] and not self.path.startswith('/api/pet/'):
   viewer=self.user()
   if viewer:
    with db() as c:obj=privacy.filter_response(c,viewer,obj)
  b=json.dumps(obj,ensure_ascii=False).encode();self.send_response(status);self.send_header('Content-Type','application/json; charset=utf-8');self.send_header('Cache-Control','no-store');self.send_header('Content-Length',str(len(b)))
  if cookie:self.send_header('Set-Cookie',cookie)
  self.end_headers();self.wfile.write(b)
 def token(self):
  try:
   c=SimpleCookie();c.load(self.headers.get('Cookie',''));return c['hf_session'].value if 'hf_session' in c else ''
  except:return ''
 def user(self):
  with db() as c:return c.execute("SELECT users.* FROM sessions JOIN users ON users.id=sessions.user_id WHERE token=? AND expires>? AND status='approved'",(hashlib.sha256(self.token().encode()).hexdigest(),int(time.time()))).fetchone()
 def do_GET(self):
  if not self.path.startswith('/api/'):
   if self.path.startswith(('/data/','/.')):return self.reply(404,{'error':'찾을 수 없습니다.'})
   return super().do_GET()
  if self.path=='/api/me':
   u=self.user()
   with db() as c:setup=c.execute("SELECT COUNT(*) FROM users WHERE role='admin'").fetchone()[0]==0
   return self.reply(200,{'user':public(u) if u else None,'setup':setup})
  u=self.user()
  if not u:return self.reply(401,{'error':'로그인이 필요합니다.'})
  if pet.get(self,u,db):return
  if activity.get(self,u,db):return
  if meals.get(self,u,db):return
  if wiki.get(self,u,db):return
  if news.get(self,u,db):return
  if self.path.startswith('/api/boards/'):
   kind=self.path.split('/')[-1]
   if kind not in ['study','articles','jobs','qna','suggestions']:return self.reply(404,{'error':'게시판이 없습니다.'})
   sql='SELECT posts.*,users.name AS author FROM posts JOIN users ON users.id=posts.user_id WHERE kind=?';params=[kind]
   if kind=='qna' and u['role']!='admin':sql+=' AND user_id=?';params.append(u['id'])
   with db() as c:rows=c.execute(sql+' ORDER BY posts.id DESC LIMIT 100',params).fetchall()
   return self.reply(200,{'posts':[{**dict(x),'members':json.loads(x['members']),'replies':json.loads(x['replies'])} for x in rows]})
  if self.path=='/api/state':return self.reply(200,{'state':json.loads(u['state'])})
  if self.path=='/api/attendance':return self.reply(200,attendance_info(u['id']))
  if self.path=='/api/admin/users' and u['role']=='admin':
   with db() as c:rows=c.execute("SELECT users.id,employee,name,status,role,COALESCE(department,'') AS department,COALESCE(rejection_reason,'') AS rejection_reason FROM users LEFT JOIN user_profiles ON users.id=user_profiles.user_id ORDER BY users.id DESC").fetchall()
   return self.reply(200,{'users':[dict(x) for x in rows]})
  self.reply(404,{'error':'찾을 수 없습니다.'})
 def do_POST(self):
  # Require same-origin JSON for every mutation, including sign-in and setup.
  expected=('https' if SECURE else 'http')+'://'+self.headers.get('Host','')
  if self.headers.get('Origin')!=expected:return self.reply(403,{'error':'잘못된 요청 출처입니다.'})
  if self.headers.get('Content-Type','').split(';')[0]!='application/json':return self.reply(415,{'error':'JSON 요청이 필요합니다.'})
  try:
   n=int(self.headers.get('Content-Length','0'))
   if n<1 or n>(1800000 if self.path=='/api/wiki/post' else 100000):return self.reply(413,{'error':'요청 크기를 확인해 주세요.'})
   d=json.loads(self.rfile.read(n))
   if not isinstance(d,dict):raise ValueError()
  except:return self.reply(400,{'error':'요청 내용을 확인해 주세요.'})
  path=self.path
  if path in ['/api/register','/api/login','/api/setup']:
   key=self.client_address[0]+path;now=time.time();history=[t for t in attempts.get(key,[]) if now-t<600]
   if len(history)>=20:return self.reply(429,{'error':'시도가 많습니다. 10분 뒤 다시 시도해 주세요.'})
   history.append(now);attempts[key]=history
   employee=d.get('employee','');password=d.get('password','')
   if not isinstance(employee,str) or not re.fullmatch(r'[A-Za-z0-9_-]{2,30}',employee) or not isinstance(password,str) or len(password)>128:return self.reply(400,{'error':'사원번호와 비밀번호를 확인해 주세요.'})
   if path in ['/api/register','/api/setup']:
    name=d.get('name','')
    if not isinstance(name,str) or not 1<=len(name.strip())<=40 or len(password)<10:return self.reply(400,{'error':'이름과 10자 이상의 비밀번호를 입력해 주세요.'})
    is_admin=path=='/api/setup'
    if is_admin and self.client_address[0] not in ('127.0.0.1','::1'):return self.reply(403,{'error':'관리자 초기 설정은 서버 컴퓨터에서만 가능합니다.'})
    department=d.get('department','')
    if not is_admin and (not isinstance(department,str) or not 1<=len(department.strip())<=80):return self.reply(400,{'error':'부서를 입력해 주세요.'})
    salt=secrets.token_hex(16);hashed=digest(password,salt)
    try:
     with db() as c:
      c.execute('BEGIN IMMEDIATE')
      if is_admin and c.execute("SELECT COUNT(*) FROM users WHERE role='admin'").fetchone()[0]:return self.reply(409,{'error':'관리자 설정이 완료되어 있습니다.'})
      existing=c.execute('SELECT * FROM users WHERE employee=?',(employee,)).fetchone()
      if not is_admin and existing and existing['status']=='rejected' and existing['role']=='intern':
       if not hmac.compare_digest(digest(password,existing['salt']),existing['hash']):return self.reply(403,{'error':'재신청하려면 이전 가입 신청에 사용한 비밀번호를 입력해 주세요. 기억나지 않으면 관리자에게 문의해 주세요.'})
       c.execute("UPDATE users SET name=?,salt=?,hash=?,status='pending' WHERE id=?",(name.strip(),salt,hashed,existing['id']))
       c.execute('INSERT OR IGNORE INTO user_profiles(user_id) VALUES(?)',(existing['id'],))
       c.execute("UPDATE user_profiles SET department=?,rejection_reason='' WHERE user_id=?",(department.strip(),existing['id']))
       c.execute('DELETE FROM sessions WHERE user_id=?',(existing['id'],))
       return self.reply(201,{'message':'가입 재신청이 완료되었습니다. 관리자 승인 후 로그인할 수 있습니다.'})
      c.execute('INSERT INTO users(employee,name,salt,hash,status,role) VALUES(?,?,?,?,?,?)',(employee,name.strip(),salt,hashed,'approved' if is_admin else 'pending','admin' if is_admin else 'intern'))
      uid=c.execute('SELECT id FROM users WHERE employee=?',(employee,)).fetchone()[0]
      c.execute('INSERT INTO user_profiles(user_id,department) VALUES(?,?)',(uid,department.strip()))
    except IntegrityError:return self.reply(409,{'error':'이미 등록된 사원번호입니다. 관리자에게 문의해 주세요.'})
    return self.reply(201,{'message':'관리자 계정이 생성되었습니다. 로그인해 주세요.' if is_admin else '가입 신청이 완료되었습니다. 관리자 승인 후 로그인할 수 있습니다.'})
   with db() as c:u=c.execute('SELECT * FROM users WHERE employee=?',(employee,)).fetchone()
   salt=u['salt'] if u else '00'*16;computed=digest(password,salt)
   if not u or not hmac.compare_digest(computed,u['hash']):return self.reply(401,{'error':'사원번호 또는 비밀번호가 맞지 않습니다.'})
   if u['status']=='rejected':
    with db() as c:profile=c.execute('SELECT rejection_reason FROM user_profiles WHERE user_id=?',(u['id'],)).fetchone()
    return self.reply(403,{'error':'가입 신청이 거절되었습니다. 사유: '+(profile[0] if profile and profile[0] else '관리자에게 문의해 주세요.')+' 회원가입에서 정보를 수정하고 기존 비밀번호로 다시 신청할 수 있습니다.'})
   if u['status']!='approved':return self.reply(403,{'error':'관리자 승인 대기 중입니다.' if u['status']=='pending' else '가입 신청이 거절되었습니다. 관리자에게 문의해 주세요.'})
   raw=secrets.token_urlsafe(32)
   with db() as c:
    c.execute('DELETE FROM sessions WHERE expires<=?',(int(time.time()),));c.execute('INSERT INTO sessions VALUES(?,?,?)',(hashlib.sha256(raw.encode()).hexdigest(),u['id'],int(time.time())+28800))
   return self.reply(200,{'user':public(u)},f'hf_session={raw}; Path=/; HttpOnly; SameSite=Strict; Max-Age=28800'+('; Secure' if SECURE else ''))
  u=self.user()
  if not u:return self.reply(401,{'error':'로그인이 필요합니다.'})
  with db() as c:private_block=privacy.blocked_mutation(c,u,path,d)
  if private_block:return self.reply(404,{'error':'요청한 항목을 찾을 수 없습니다.'})
  if pet.post(self,u,d,db):return
  if activity.post(self,u,d,db):return
  if news.post(self,u,d,db):return
  if path=='/api/admin/department':
   if u['role']!='admin':return self.reply(403,{'error':'관리자만 부서를 변경할 수 있습니다.'})
   uid=d.get('id');department=d.get('department')
   if type(uid)!=int or not isinstance(department,str) or not 1<=len(department.strip())<=80:return self.reply(400,{'error':'회원과 부서를 확인해 주세요.'})
   with db() as c:
    if not c.execute('SELECT id FROM users WHERE id=?',(uid,)).fetchone():return self.reply(404,{'error':'회원이 없습니다.'})
    c.execute('INSERT OR IGNORE INTO user_profiles(user_id) VALUES(?)',(uid,));c.execute('UPDATE user_profiles SET department=? WHERE user_id=?',(department.strip(),uid))
   return self.reply(200,{'ok':True})
  if meals.post(self,u,d,db):return
  if wiki.post(self,u,d,db):return
  if path=='/api/boards/post':
   kind=d.get('kind');title=d.get('title');body=d.get('body');link=d.get('link','');day=d.get('event_day','')
   if kind not in ['study','articles','jobs','qna','suggestions'] or not isinstance(title,str) or not 1<=len(title.strip())<=120 or not isinstance(body,str) or not 1<=len(body.strip())<=5000:return self.reply(400,{'error':'제목과 내용을 확인해 주세요.'})
   if kind in ['articles','jobs'] and u['role']!='admin':return self.reply(403,{'error':'기사와 채용 소식은 관리자가 등록합니다.'})
   if not isinstance(link,str) or len(link)>1000 or (link and not re.fullmatch(r'https?://[^\s]+',link)) or not isinstance(day,str) or (day and not re.fullmatch(r'\d{4}-\d{2}-\d{2}',day)):return self.reply(400,{'error':'주소와 날짜를 확인해 주세요.'})
   if kind=='study':
    try:datetime.strptime(day,'%Y-%m-%d')
    except ValueError:return self.reply(400,{'error':'모임 날짜를 선택해 주세요.'})
   with db() as c:
    if kind in ['study','suggestions']:activity.award(c,u['id'],kind+':'+activity.today(),10 if kind=='study' else 5)
    c.execute('INSERT INTO posts(kind,user_id,title,body,link,event_day,created,members) VALUES(?,?,?,?,?,?,?,?)',(kind,u['id'],title.strip(),body.strip(),link,day,datetime.now(timezone(timedelta(hours=9))).isoformat(),json.dumps([u['id']] if kind=='study' else [])))
   return self.reply(201,{'ok':True})
  if path in ['/api/boards/reply','/api/boards/join']:
   pid=d.get('id')
   if not isinstance(pid,int):return self.reply(400,{'error':'게시글을 확인해 주세요.'})
   with db() as c:
    c.execute('BEGIN IMMEDIATE')
    post=c.execute('SELECT * FROM posts WHERE id=?',(pid,)).fetchone()
    if not post or (post['kind']=='qna' and u['role']!='admin' and post['user_id']!=u['id']):return self.reply(404,{'error':'게시글을 찾을 수 없습니다.'})
    if path.endswith('/join'):
     if post['kind']!='study':return self.reply(400,{'error':'공부 모임에서만 참여할 수 있습니다.'})
     members=json.loads(post['members'])
     if post['user_id']==u['id']:return self.reply(400,{'error':'모임 작성자는 기본으로 참여합니다.'})
     if u['id'] not in members:activity.award(c,u['id'],'join:'+str(pid),5)
     members.remove(u['id']) if u['id'] in members else members.append(u['id'])
     c.execute('UPDATE posts SET members=? WHERE id=?',(json.dumps(members),pid))
    else:
     body=d.get('body')
     if not isinstance(body,str) or not 1<=len(body.strip())<=2000:return self.reply(400,{'error':'답변 내용을 입력해 주세요.'})
     replies=json.loads(post['replies'])
     if len(replies)>=100:return self.reply(400,{'error':'댓글은 게시글당 100개까지 등록할 수 있습니다.'})
     replies.append({'name':u['name'],'user_id':u['id'],'admin':u['role']=='admin','body':body.strip(),'created':datetime.now(timezone(timedelta(hours=9))).isoformat()})
     c.execute('UPDATE posts SET replies=? WHERE id=?',(json.dumps(replies,ensure_ascii=False),pid))
   return self.reply(200,{'ok':True})
  if path=='/api/attendance':
   day=datetime.now(timezone(timedelta(hours=9))).date().isoformat()
   with db() as c:
    c.execute('BEGIN IMMEDIATE')
    c.execute('INSERT OR IGNORE INTO attendance(user_id,day) VALUES(?,?)',(u['id'],day))
    activity.award(c,u['id'],'attendance:'+day,10)
   return self.reply(200,attendance_info(u['id']))
  if path=='/api/logout':
   with db() as c:c.execute('DELETE FROM sessions WHERE token=?',(hashlib.sha256(self.token().encode()).hexdigest(),))
   return self.reply(200,{'ok':True},'hf_session=; Path=/; HttpOnly; SameSite=Strict; Max-Age=0'+('; Secure' if SECURE else ''))
  if path=='/api/state':
   s=d.get('state');allowed={'tasks','clean','lunch','wiki','best','favorites'}
   if not isinstance(s,dict) or set(s)-allowed:return self.reply(400,{'error':'저장 내용을 확인해 주세요.'})
   if any(not isinstance(s.get(k,[]),list) for k in ['tasks','clean','lunch','wiki']):return self.reply(400,{'error':'저장 형식이 올바르지 않습니다.'})
   if 'favorites' in s and (not isinstance(s['favorites'],list) or len(s['favorites'])>16 or any(x not in ['','games','pet','manual-ai','glossary','registry-guide','checklist','cleaning','lunch','reflex','wiki','study','articles','jobs','qna','suggestions'] for x in s['favorites'])):return self.reply(400,{'error':'즐겨찾기 목록을 확인해 주세요.'})
   with db() as c:
    c.execute('BEGIN IMMEDIATE')
    previous=json.loads(c.execute('SELECT state FROM users WHERE id=?',(u['id'],)).fetchone()[0])
    old={t[0]:bool(t[1]) and (len(t)<5 or not (t[3]=='daily' or isinstance(t[3],list) and len(t[3])>0) or t[4]==activity.today()) for t in previous.get('tasks',[]) if isinstance(t,list) and len(t)>=2}
    for t in s.get('tasks',[]):
     if not isinstance(t,list) or len(t) not in (3,5) or not isinstance(t[0],str) or len(t[0])>150 or type(t[1])!=bool:return self.reply(400,{'error':'업무 형식을 확인하세요.'})
     if len(t)==5 and (not (t[3] in ['daily','occasional'] or isinstance(t[3],list) and len(t[3])<=5 and all(type(day)==int and 1<=day<=5 for day in t[3]) and len(set(t[3]))==len(t[3])) or not isinstance(t[4],str) or not re.fullmatch(r'\d{4}-\d{2}-\d{2}',t[4])):return self.reply(400,{'error':'업무 구분을 확인해 주세요.'})
     if t[1] and (len(t)<5 or not (t[3]=='daily' or isinstance(t[3],list) and len(t[3])>0) or t[4]==activity.today()) and not old.get(t[0],False):
      count=c.execute("SELECT COUNT(*) FROM points WHERE user_id=? AND day=? AND event_key LIKE 'task:%'",(u['id'],activity.today())).fetchone()[0]
      if count<5:activity.award(c,u['id'],'task:'+activity.today()+':'+hashlib.sha256(t[0].encode()).hexdigest(),5)
    c.execute('UPDATE users SET state=? WHERE id=?',(json.dumps(s,ensure_ascii=False),u['id']))
   return self.reply(200,{'ok':True})
  if path=='/api/admin/review':
   if u['role']!='admin':return self.reply(403,{'error':'관리자만 사용할 수 있습니다.'})
   status=d.get('status');uid=d.get('id')
   if status not in ['approved','rejected'] or not isinstance(uid,int):return self.reply(400,{'error':'승인 정보를 확인해 주세요.'})
   reason=d.get('reason','')
   if not isinstance(reason,str) or len(reason)>1000 or (status=='rejected' and not reason.strip()):return self.reply(400,{'error':'거절 사유를 입력해 주세요.'})
   with db() as c:
    target=c.execute("SELECT id FROM users WHERE id=? AND role='intern' AND status='pending'",(uid,)).fetchone()
    if not target:return self.reply(409,{'error':'처리할 승인 대기 신청이 없습니다.'})
    if status=='approved' and c.execute("SELECT COUNT(*) FROM users WHERE role='intern' AND status='approved'").fetchone()[0]>=30:return self.reply(409,{'error':'승인된 인턴이 30명입니다. 인원 설정을 확인해 주세요.'})
    c.execute('UPDATE users SET status=? WHERE id=?',(status,uid))
    c.execute('INSERT OR IGNORE INTO user_profiles(user_id) VALUES(?)',(uid,))
    c.execute('UPDATE user_profiles SET rejection_reason=? WHERE user_id=?',(reason.strip() if status=='rejected' else '',uid))
   return self.reply(200,{'ok':True})
  self.reply(404,{'error':'찾을 수 없습니다.'})
if __name__=='__main__':
 print(f'HF 로그인 서버: http://127.0.0.1:{PORT}/',flush=True)
 ThreadingHTTPServer((BIND,PORT),Handler).serve_forever()
