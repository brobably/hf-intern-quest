import json
from datetime import datetime

def initialize(c):
 c.execute("CREATE TABLE IF NOT EXISTS meals(id INTEGER PRIMARY KEY,user_id INTEGER NOT NULL,restaurant TEXT NOT NULL,event_time TEXT NOT NULL,capacity INTEGER NOT NULL,members TEXT NOT NULL)")

def get(h,u,db):
 if h.path!='/api/meals':return False
 with db() as c:
  rows=c.execute('SELECT meals.*,users.name AS author FROM meals JOIN users ON users.id=meals.user_id ORDER BY event_time DESC LIMIT 100').fetchall()
  restaurants=[r[0] for r in c.execute('SELECT DISTINCT restaurant FROM meals ORDER BY restaurant LIMIT 500')]
 h.reply(200,{'meals':[{**dict(r),'members':json.loads(r['members'])} for r in rows],'restaurants':restaurants});return True

def post(h,u,d,db):
 if not h.path.startswith('/api/meals/'):return False
 if h.path=='/api/meals/post':
  restaurant=d.get('restaurant','');when=d.get('event_time','');capacity=d.get('capacity')
  if not isinstance(restaurant,str) or not 1<=len(restaurant.strip())<=120 or type(capacity)!=int or not 2<=capacity<=30:
   h.reply(400,{'error':'식당 이름과 정원(본인 포함 2~30명)을 확인해 주세요.'});return True
  try:
   if not isinstance(when,str) or len(when)!=16:raise ValueError()
   datetime.strptime(when,'%Y-%m-%dT%H:%M')
  except ValueError:
   h.reply(400,{'error':'식사 날짜와 시간을 선택해 주세요.'});return True
  with db() as c:c.execute('INSERT INTO meals(user_id,restaurant,event_time,capacity,members) VALUES(?,?,?,?,?)',(u['id'],restaurant.strip(),when,capacity,json.dumps([u['id']])))
  h.reply(201,{'ok':True});return True
 if h.path=='/api/meals/join':
  mid=d.get('id')
  if type(mid)!=int:h.reply(400,{'error':'식사 제안을 확인해 주세요.'});return True
  with db() as c:
   c.execute('BEGIN IMMEDIATE');meal=c.execute('SELECT * FROM meals WHERE id=?',(mid,)).fetchone()
   if not meal:h.reply(404,{'error':'식사 제안을 찾을 수 없습니다.'});return True
   if meal['user_id']==u['id']:h.reply(400,{'error':'제안자는 기본으로 참여합니다.'});return True
   members=json.loads(meal['members'])
   if u['id'] in members:members.remove(u['id'])
   elif len(members)>=meal['capacity']:h.reply(409,{'error':'정원이 찼습니다.'});return True
   else:members.append(u['id'])
   c.execute('UPDATE meals SET members=? WHERE id=?',(json.dumps(members),mid))
  h.reply(200,{'ok':True});return True
 h.reply(404,{'error':'찾을 수 없습니다.'});return True
