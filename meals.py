import json,os
import activity
from urllib.parse import urlsplit,parse_qs,urlencode
from urllib.request import Request,urlopen
from urllib.error import URLError
from datetime import datetime

def initialize(c):
 c.execute('CREATE TABLE IF NOT EXISTS meal_weekly_status(user_id INTEGER NOT NULL,week TEXT NOT NULL,statuses TEXT NOT NULL,PRIMARY KEY(user_id,week))')
 c.execute('CREATE TABLE IF NOT EXISTS meal_rewards(meal_id INTEGER NOT NULL,user_id INTEGER NOT NULL,PRIMARY KEY(meal_id,user_id))')
 c.execute('CREATE TABLE IF NOT EXISTS meal_confirmations(meal_id INTEGER NOT NULL,user_id INTEGER NOT NULL,PRIMARY KEY(meal_id,user_id))')
 c.execute('CREATE TABLE IF NOT EXISTS meal_days(meal_id INTEGER NOT NULL,user_id INTEGER NOT NULL,days TEXT NOT NULL,PRIMARY KEY(meal_id,user_id))')
 c.execute("CREATE TABLE IF NOT EXISTS meals(id INTEGER PRIMARY KEY,user_id INTEGER NOT NULL,restaurant TEXT NOT NULL,event_time TEXT NOT NULL,capacity INTEGER NOT NULL,members TEXT NOT NULL)")
 c.execute("CREATE TABLE IF NOT EXISTS meal_places(meal_id INTEGER PRIMARY KEY,address TEXT NOT NULL,url TEXT NOT NULL)")
 c.execute("CREATE TABLE IF NOT EXISTS meal_invites(meal_id INTEGER NOT NULL,user_id INTEGER NOT NULL,status TEXT NOT NULL DEFAULT 'pending',PRIMARY KEY(meal_id,user_id))")

def weekly_rows(c,w):
 rows=[]
 for r in c.execute("SELECT meal_weekly_status.* FROM meal_weekly_status JOIN users ON users.id=meal_weekly_status.user_id WHERE week=? AND users.status='approved'",(w,)):
  value=json.loads(r['statuses']);lunch=value if isinstance(value,list) else value['lunch'];dinner=[-1]*5 if isinstance(value,list) else value['dinner']
  rows.append({**dict(r),'statuses':lunch,'lunch':lunch,'dinner':dinner})
 return rows

def get(h,u,db):
 if urlsplit(h.path).path=='/api/meals/weekly':
  w=parse_qs(urlsplit(h.path).query).get('week',[activity.week()])[0]
  try:
   assert datetime.strptime(w,'%Y-%m-%d').weekday()==0
  except (ValueError,AssertionError):h.reply(400,{'error':'주간 날짜를 확인해 주세요.'});return True
  with db() as c:rows=weekly_rows(c,w)
  h.reply(200,{'week':w,'weekly_status':rows});return True

 if h.path=='/api/meals/invitations':
  with db() as c:rows=c.execute("SELECT meals.id,restaurant,event_time,capacity,members,users.name AS author FROM meal_invites JOIN meals ON meals.id=meal_invites.meal_id JOIN users ON users.id=meals.user_id WHERE meal_invites.user_id=? AND meal_invites.status='pending' ORDER BY meals.id DESC",(u['id'],)).fetchall()
  h.reply(200,{'invitations':[{**dict(r),'members':json.loads(r['members'])} for r in rows]});return True
 if urlsplit(h.path).path=='/api/meals/restaurants':
  query=parse_qs(urlsplit(h.path).query).get('q',[''])[0].strip()
  if not 1<=len(query)<=100:h.reply(400,{'error':'식당 이름이나 지역을 입력해 주세요.'});return True
  key=os.environ.get('KAKAO_REST_API_KEY')
  if not key:h.reply(503,{'error':'지도 식당 검색 연결을 준비 중입니다. 식당 이름을 직접 입력해 등록할 수 있습니다.'});return True
  request=Request('https://dapi.kakao.com/v2/local/search/keyword.json?'+urlencode({'query':query,'category_group_code':'FD6','size':10}),headers={'Authorization':'KakaoAK '+key})
  try:
   with urlopen(request,timeout=8) as response:data=json.load(response)
   h.reply(200,{'places':[{'name':p['place_name'],'address':p.get('road_address_name') or p.get('address_name',''),'url':p['place_url']} for p in data.get('documents',[])]})
  except (URLError,ValueError,KeyError):h.reply(502,{'error':'지도 검색에 연결하지 못했습니다. 잠시 후 다시 시도해 주세요.'})
  return True
 if h.path!='/api/meals':return False
 with db() as c:
  rows=c.execute("SELECT meals.*,users.name AS author,COALESCE(meal_places.address,'') AS address,COALESCE(meal_places.url,'') AS url FROM meals JOIN users ON users.id=meals.user_id LEFT JOIN meal_places ON meals.id=meal_places.meal_id ORDER BY event_time DESC LIMIT 100").fetchall()
  weekly_status=weekly_rows(c,activity.week())
  confirmations=[dict(r) for r in c.execute('SELECT meal_id,user_id FROM meal_confirmations')]
  restaurants=[r[0] for r in c.execute('SELECT DISTINCT restaurant FROM meals ORDER BY restaurant LIMIT 500')]
  availability=[dict(r) for r in c.execute('SELECT meal_days.*,users.name FROM meal_days JOIN users ON users.id=meal_days.user_id')]
  members=c.execute("SELECT users.id,name,COALESCE(department,'') AS department FROM users LEFT JOIN user_profiles ON users.id=user_profiles.user_id WHERE status='approved' ORDER BY name").fetchall()
 h.reply(200,{'meals':[{**dict(r),'members':json.loads(r['members'])} for r in rows],'week':activity.week(),'weekly_status':weekly_status,'confirmations':confirmations,'restaurants':restaurants,'users':[dict(r) for r in members],'availability':[{**r,'days':json.loads(r['days'])} for r in availability]});return True

def valid_days(days):return isinstance(days,list) and 1<=len(days)<=5 and all(type(x)==int and 0<=x<=4 for x in days)
def save_days(c,mid,uid,days):
 c.execute('INSERT OR IGNORE INTO meal_days(meal_id,user_id,days) VALUES(?,?,?)',(mid,uid,'[]'))
 c.execute('UPDATE meal_days SET days=? WHERE meal_id=? AND user_id=?',(json.dumps(sorted(set(days))),mid,uid))

def post(h,u,d,db):
 if not h.path.startswith('/api/meals/'):return False
 if 'days' in d and not valid_days(d['days']):h.reply(400,{'error':'월~금 중 가능한 요일을 하나 이상 선택해 주세요.'});return True
 if h.path=='/api/meals/weekly':
  lunch=d.get('lunch',d.get('statuses'));dinner=d.get('dinner',[-1]*5)
  def valid(values):return isinstance(values,list) and len(values)==5 and all(type(x)==int and x in [-1,0,1] for x in values)
  if d.get('week')!=activity.week() or not valid(lunch) or not valid(dinner):h.reply(400,{'error':'이번 주 월~금 점심과 저녁 상태를 확인해 주세요.'});return True
  value=json.dumps({'lunch':lunch,'dinner':dinner})
  with db() as c:
   c.execute('INSERT OR IGNORE INTO meal_weekly_status(user_id,week,statuses) VALUES(?,?,?)',(u['id'],activity.week(),value))
   c.execute('UPDATE meal_weekly_status SET statuses=? WHERE user_id=? AND week=?',(value,u['id'],activity.week()))
  h.reply(200,{'ok':True});return True
 if h.path=='/api/meals/complete':
  mid=d.get('id')
  if type(mid)!=int:h.reply(400,{'error':'식사 제안을 확인해 주세요.'});return True
  with db() as c:
   c.execute('BEGIN IMMEDIATE');meal=c.execute('SELECT * FROM meals WHERE id=?',(mid,)).fetchone()
   if not meal or u['id'] not in json.loads(meal['members']):h.reply(403,{'error':'참여한 식사만 완료할 수 있습니다.'});return True
   if len(json.loads(meal['members']))<2:h.reply(400,{'error':'두 명 이상 함께 참여한 식사만 완료할 수 있습니다.'});return True
   if meal['event_time']>datetime.now(activity.ZONE).strftime('%Y-%m-%dT%H:%M'):h.reply(400,{'error':'예정된 식사 시간 이후에 확인할 수 있습니다.'});return True
   before=c.execute('SELECT COALESCE(SUM(amount),0) FROM points WHERE user_id=?',(u['id'],)).fetchone()[0]
   c.execute('INSERT OR IGNORE INTO meal_confirmations(meal_id,user_id) VALUES(?,?)',(mid,u['id']))
   confirmed=[r[0] for r in c.execute('SELECT user_id FROM meal_confirmations WHERE meal_id=?',(mid,))]
   if len(confirmed)>=2:
    day=activity.today()
    for uid in confirmed:
     if not c.execute('SELECT user_id FROM meal_rewards WHERE meal_id=? AND user_id=?',(mid,uid)).fetchone():
      activity.award(c,uid,'meal-day:'+day,10)
      c.execute('INSERT OR IGNORE INTO meal_rewards(meal_id,user_id) VALUES(?,?)',(mid,uid))
     for other in confirmed:
      if other!=uid:activity.award(c,uid,'meal-new:'+str(other),5)
   after=c.execute('SELECT COALESCE(SUM(amount),0) FROM points WHERE user_id=?',(u['id'],)).fetchone()[0]
  h.reply(200,{'ok':True,'earned':int(after-before),'confirmed':len(confirmed)});return True
 if h.path=='/api/meals/availability':
  mid=d.get('id')
  if type(mid)!=int or not valid_days(d.get('days')):h.reply(400,{'error':'가능한 요일을 선택해 주세요.'});return True
  with db() as c:
   c.execute('BEGIN IMMEDIATE');meal=c.execute('SELECT members FROM meals WHERE id=?',(mid,)).fetchone()
   if not meal or u['id'] not in json.loads(meal['members']):h.reply(403,{'error':'참여한 식사 제안에서만 요일을 설정할 수 있습니다.'});return True
   save_days(c,mid,u['id'],d['days'])
  h.reply(200,{'ok':True});return True
 if h.path=='/api/meals/remove':
  mid=d.get('id')
  if type(mid)!=int:h.reply(400,{'error':'식사 제안을 확인해 주세요.'});return True
  with db() as c:
   c.execute('BEGIN IMMEDIATE');meal=c.execute('SELECT user_id FROM meals WHERE id=?',(mid,)).fetchone()
   if not meal:h.reply(404,{'error':'식사 제안이 없습니다.'});return True
   if meal['user_id']!=u['id']:h.reply(403,{'error':'본인이 만든 식사 제안만 삭제할 수 있습니다.'});return True
   c.execute('DELETE FROM meal_rewards WHERE meal_id=?',(mid,))
   c.execute('DELETE FROM meal_confirmations WHERE meal_id=?',(mid,))
   c.execute('DELETE FROM meal_days WHERE meal_id=?',(mid,));c.execute('DELETE FROM meal_invites WHERE meal_id=?',(mid,));c.execute('DELETE FROM meal_places WHERE meal_id=?',(mid,));c.execute('DELETE FROM meals WHERE id=?',(mid,))
  h.reply(200,{'ok':True});return True
 if h.path=='/api/meals/invite':
  mid=d.get('id');recipients=d.get('recipients')
  if type(mid)!=int or not isinstance(recipients,list) or not 1<=len(recipients)<=30 or any(type(x)!=int for x in recipients):h.reply(400,{'error':'초대할 회원을 선택해 주세요.'});return True
  with db() as c:
   c.execute('BEGIN IMMEDIATE');meal=c.execute('SELECT * FROM meals WHERE id=?',(mid,)).fetchone()
   if not meal or meal['user_id']!=u['id']:h.reply(403,{'error':'본인이 만든 식사 제안에서만 초대할 수 있습니다.'});return True
   if c.execute('SELECT user_id FROM meal_confirmations WHERE meal_id=?',(mid,)).fetchone():h.reply(409,{'error':'식사 완료 확인이 시작되어 참여자를 변경할 수 없습니다.'});return True
   members=json.loads(meal['members'])
   if len(members)>=meal['capacity']:h.reply(409,{'error':'정원이 찼습니다.'});return True
   valid={r[0] for r in c.execute("SELECT id FROM users WHERE status='approved'")}
   if any(x not in valid or x==u['id'] for x in recipients):h.reply(400,{'error':'승인된 다른 회원만 초대할 수 있습니다.'});return True
   for recipient in set(recipients)-set(members):c.execute('INSERT OR IGNORE INTO meal_invites(meal_id,user_id) VALUES(?,?)',(mid,recipient))
  h.reply(200,{'ok':True});return True
 if h.path=='/api/meals/respond':
  mid=d.get('id');action=d.get('action')
  if type(mid)!=int or action not in ['accept','decline']:h.reply(400,{'error':'초대 응답을 확인해 주세요.'});return True
  with db() as c:
   c.execute('BEGIN IMMEDIATE');invite=c.execute("SELECT status FROM meal_invites WHERE meal_id=? AND user_id=?",(mid,u['id'])).fetchone()
   if not invite or invite['status']!='pending':h.reply(404,{'error':'응답할 초대가 없습니다.'});return True
   meal=c.execute('SELECT * FROM meals WHERE id=?',(mid,)).fetchone()
   if not meal:h.reply(404,{'error':'식사 제안이 없습니다.'});return True
   if c.execute('SELECT user_id FROM meal_confirmations WHERE meal_id=?',(mid,)).fetchone():h.reply(409,{'error':'식사 완료 확인이 시작되어 참여자를 변경할 수 없습니다.'});return True
   members=json.loads(meal['members'])
   if action=='accept' and u['id'] not in members:
    if len(members)>=meal['capacity']:h.reply(409,{'error':'정원이 찼습니다. 초대를 거절하거나 제안자에게 문의해 주세요.'});return True
    members.append(u['id']);c.execute('UPDATE meals SET members=? WHERE id=?',(json.dumps(members),mid))
   if action=='accept':save_days(c,mid,u['id'],d.get('days',[]))
   c.execute('UPDATE meal_invites SET status=? WHERE meal_id=? AND user_id=?',('accepted' if action=='accept' else 'declined',mid,u['id']))
  h.reply(200,{'ok':True});return True
 if h.path=='/api/meals/post':
  restaurant=d.get('restaurant','');when=d.get('event_time','');capacity=d.get('capacity')
  if not isinstance(restaurant,str) or not 1<=len(restaurant.strip())<=120 or type(capacity)!=int or not 2<=capacity<=30:
   h.reply(400,{'error':'식당 이름과 정원(본인 포함 2~30명)을 확인해 주세요.'});return True
  try:
   if not isinstance(when,str) or len(when)!=16:raise ValueError()
   datetime.strptime(when,'%Y-%m-%dT%H:%M')
  except ValueError:
   h.reply(400,{'error':'식사 날짜와 시간을 선택해 주세요.'});return True
  address=d.get('address','');url=d.get('url','')
  if not isinstance(address,str) or len(address)>300 or not isinstance(url,str) or len(url)>500 or (url and (urlsplit(url).scheme not in ['http','https'] or urlsplit(url).netloc!='place.map.kakao.com')):
   h.reply(400,{'error':'식당 위치 정보를 확인해 주세요.'});return True
  with db() as c:
   c.execute('BEGIN IMMEDIATE')
   c.execute('INSERT INTO meals(user_id,restaurant,event_time,capacity,members) VALUES(?,?,?,?,?)',(u['id'],restaurant.strip(),when,capacity,json.dumps([u['id']])))
   mid=c.execute('SELECT id FROM meals WHERE user_id=? ORDER BY id DESC LIMIT 1',(u['id'],)).fetchone()[0]
   c.execute('INSERT INTO meal_places(meal_id,address,url) VALUES(?,?,?)',(mid,address,url))
   save_days(c,mid,u['id'],d.get('days',[]))
  h.reply(201,{'ok':True});return True
 if h.path=='/api/meals/join':
  mid=d.get('id')
  if type(mid)!=int:h.reply(400,{'error':'식사 제안을 확인해 주세요.'});return True
  with db() as c:
   c.execute('BEGIN IMMEDIATE');meal=c.execute('SELECT * FROM meals WHERE id=?',(mid,)).fetchone()
   if not meal:h.reply(404,{'error':'식사 제안을 찾을 수 없습니다.'});return True
   if meal['user_id']==u['id']:h.reply(400,{'error':'제안자는 기본으로 참여합니다.'});return True
   if c.execute('SELECT user_id FROM meal_confirmations WHERE meal_id=?',(mid,)).fetchone():h.reply(409,{'error':'식사 완료 확인이 시작되어 참여자를 변경할 수 없습니다.'});return True
   members=json.loads(meal['members'])
   if u['id'] in members:members.remove(u['id'])
   elif len(members)>=meal['capacity']:h.reply(409,{'error':'정원이 찼습니다.'});return True
   else:members.append(u['id'])
   c.execute('UPDATE meals SET members=? WHERE id=?',(json.dumps(members),mid))
   if u['id'] in members:save_days(c,mid,u['id'],d.get('days',[]))
   else:c.execute('DELETE FROM meal_days WHERE meal_id=? AND user_id=?',(mid,u['id']))
   if u['id'] in members:c.execute("UPDATE meal_invites SET status='accepted' WHERE meal_id=? AND user_id=?",(mid,u['id']))
  h.reply(200,{'ok':True});return True
 h.reply(404,{'error':'찾을 수 없습니다.'});return True
