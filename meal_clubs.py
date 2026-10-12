"""Recurring weekday meal groups with per-week attendance and daily confirmations."""
import json,re
from datetime import datetime,timedelta
import activity

def initialize(c):
 c.execute('CREATE TABLE IF NOT EXISTS meal_clubs(id INTEGER PRIMARY KEY,owner_id INTEGER NOT NULL,name TEXT NOT NULL,restaurant TEXT NOT NULL,slot TEXT NOT NULL,meal_time TEXT NOT NULL,capacity INTEGER NOT NULL,active INTEGER NOT NULL DEFAULT 1)')
 c.execute('CREATE TABLE IF NOT EXISTS meal_club_members(club_id INTEGER NOT NULL,user_id INTEGER NOT NULL,days TEXT NOT NULL,joined_on TEXT NOT NULL,PRIMARY KEY(club_id,user_id))')
 c.execute('CREATE TABLE IF NOT EXISTS meal_club_overrides(club_id INTEGER NOT NULL,user_id INTEGER NOT NULL,week TEXT NOT NULL,days TEXT NOT NULL,PRIMARY KEY(club_id,user_id,week))')
 c.execute('CREATE TABLE IF NOT EXISTS meal_club_dates(club_id INTEGER NOT NULL,day TEXT NOT NULL,members TEXT NOT NULL,rewarded INTEGER NOT NULL DEFAULT 0,PRIMARY KEY(club_id,day))')
 c.execute('CREATE TABLE IF NOT EXISTS meal_club_confirmations(club_id INTEGER NOT NULL,day TEXT NOT NULL,user_id INTEGER NOT NULL,PRIMARY KEY(club_id,day,user_id))')

def valid_days(days,empty=False):
 return isinstance(days,list) and (empty or len(days)>0) and len(days)<=5 and all(type(x)==int and 0<=x<5 for x in days)

def roster(c,cid,day):
 saved=c.execute('SELECT members FROM meal_club_dates WHERE club_id=? AND day=?',(cid,day)).fetchone()
 if saved:return json.loads(saved[0])
 date=datetime.strptime(day,'%Y-%m-%d');week=(date-timedelta(days=date.weekday())).date().isoformat()
 rows=c.execute("SELECT m.user_id,m.days,m.joined_on,o.days AS override_days FROM meal_club_members m JOIN users u ON u.id=m.user_id LEFT JOIN meal_club_overrides o ON o.club_id=m.club_id AND o.user_id=m.user_id AND o.week=? WHERE m.club_id=? AND u.status='approved' ORDER BY u.name,u.id",(week,cid))
 return [r['user_id'] for r in rows if r['joined_on']<=day and date.weekday() in json.loads(r['override_days'] if r['override_days'] is not None else r['days'])]

def list_clubs(c,u):
 week=activity.week();today=activity.today();names={r['id']:r['name'] for r in c.execute('SELECT id,name FROM users')};items=[]
 for row in c.execute('SELECT * FROM meal_clubs WHERE active=1 ORDER BY id DESC').fetchall():
  club=dict(row);members=[dict(r) for r in c.execute("SELECT m.*,u.name FROM meal_club_members m JOIN users u ON u.id=m.user_id WHERE club_id=? AND u.status='approved' ORDER BY u.name,u.id",(club['id'],))]
  club['members']=[{'id':r['user_id'],'name':r['name']} for r in members];club['author']=names.get(club['owner_id'],'');club['schedule']=[]
  mine=next((r for r in members if r['user_id']==u['id']),None)
  override=c.execute('SELECT days FROM meal_club_overrides WHERE club_id=? AND user_id=? AND week=?',(club['id'],u['id'],week)).fetchone()
  club['my_days']=json.loads(mine['days']) if mine else [];club['my_week_days']=json.loads(override[0]) if override else club['my_days'];club['has_override']=override is not None
  for i in range(5):
   day=(datetime.strptime(week,'%Y-%m-%d')+timedelta(days=i)).date().isoformat();ids=roster(c,club['id'],day)
   confirmed=[r[0] for r in c.execute('SELECT user_id FROM meal_club_confirmations WHERE club_id=? AND day=?',(club['id'],day))]
   done=len(ids)>=2 and set(ids)<=set(confirmed)
   can=day==today and day+'T'+club['meal_time']<=datetime.now(activity.ZONE).strftime('%Y-%m-%dT%H:%M') and u['id'] in ids and len(ids)>=2 and u['id'] not in confirmed
   club['schedule'].append({'day':day,'weekday':i,'members':[{'id':uid,'name':names.get(uid,'회원')} for uid in ids],'confirmed':confirmed,'complete':done,'can_confirm':can,'locked':bool(confirmed)})
  items.append(club)
 return {'clubs':items,'week':week,'today':today}

def get(h,u,db):
 if h.path!='/api/meal-clubs':return False
 with db() as c:data=list_clubs(c,u)
 h.reply(200,data);return True

def today_meals(c,uid):
 day=activity.today();items=[]
 for club in c.execute('SELECT * FROM meal_clubs WHERE active=1').fetchall():
  ids=roster(c,club['id'],day)
  if uid not in ids or len(ids)<2:continue
  names=[c.execute('SELECT name FROM users WHERE id=?',(person,)).fetchone()[0] for person in ids]
  items.append({'id':'club-'+str(club['id']),'restaurant':club['restaurant']+' · '+club['name'],'event_time':day+'T'+club['meal_time'],'slot':club['slot'],'participants':names,'members':ids,'kind':'recurring'})
 return items

def post(h,u,d,db):
 if not h.path.startswith('/api/meal-clubs/'):return False
 action=h.path.rsplit('/',1)[-1];uid=u['id']
 if action not in ('create','join','days','leave','archive','complete'):h.reply(404,{'error':'요청을 확인해 주세요.'});return True
 if action=='create':
  name=d.get('name','');restaurant=d.get('restaurant','');slot=d.get('slot','lunch');time=d.get('meal_time','');capacity=d.get('capacity');days=d.get('days')
  if not isinstance(name,str) or not 1<=len(name.strip())<=80 or not isinstance(restaurant,str) or not 1<=len(restaurant.strip())<=120 or slot not in ('lunch','dinner') or type(capacity)!=int or not 2<=capacity<=30 or not isinstance(time,str) or not re.fullmatch(r'(?:[01]\d|2[0-3]):[0-5]\d',time) or not valid_days(days):
   h.reply(400,{'error':'모임 이름, 식당, 시간, 정원(2~30명), 참여 요일을 확인해 주세요.'});return True
  with db() as c:
   c.execute('BEGIN IMMEDIATE')
   cid=c.execute('INSERT INTO meal_clubs(owner_id,name,restaurant,slot,meal_time,capacity) VALUES(?,?,?,?,?,?) RETURNING id',(uid,name.strip(),restaurant.strip(),slot,time,capacity)).fetchone()[0]
   c.execute('INSERT INTO meal_club_members VALUES(?,?,?,?)',(cid,uid,json.dumps(sorted(set(days))),activity.today()))
  h.reply(201,{'ok':True,'id':cid});return True
 cid=d.get('id')
 if type(cid)!=int:h.reply(400,{'error':'모임을 확인해 주세요.'});return True
 with db() as c:
  c.execute('BEGIN IMMEDIATE');club=c.execute('SELECT * FROM meal_clubs WHERE id=? AND active=1',(cid,)).fetchone()
  if not club:h.reply(404,{'error':'진행 중인 모임이 없습니다.'});return True
  member=c.execute('SELECT * FROM meal_club_members WHERE club_id=? AND user_id=?',(cid,uid)).fetchone()
  if action=='archive':
   if club['owner_id']!=uid:h.reply(403,{'error':'모임장만 모임을 종료할 수 있습니다.'});return True
   c.execute('UPDATE meal_clubs SET active=0 WHERE id=?',(cid,));h.reply(200,{'ok':True});return True
  if action=='join':
   if not valid_days(d.get('days')):h.reply(400,{'error':'매주 참여할 요일을 선택해 주세요.'});return True
   if member:h.reply(409,{'error':'이미 참여 중입니다. 요일 수정에서 변경해 주세요.'});return True
   count=c.execute("SELECT COUNT(*) FROM meal_club_members m JOIN users u ON u.id=m.user_id WHERE club_id=? AND u.status='approved'",(cid,)).fetchone()[0]
   if count>=club['capacity']:h.reply(409,{'error':'모임 정원이 찼습니다.'});return True
   c.execute('INSERT INTO meal_club_members VALUES(?,?,?,?)',(cid,uid,json.dumps(sorted(set(d['days']))),activity.today()))
  elif action in ('days','leave'):
   if not member:h.reply(403,{'error':'참여 중인 모임에서만 변경할 수 있습니다.'});return True
   if action=='leave':
    if club['owner_id']==uid:h.reply(400,{'error':'모임장은 이번 주 불참을 설정하거나 모임을 종료해 주세요.'});return True
    c.execute('DELETE FROM meal_club_members WHERE club_id=? AND user_id=?',(cid,uid))
    c.execute('DELETE FROM meal_club_overrides WHERE club_id=? AND user_id=?',(cid,uid))
   else:
    scope=d.get('scope');days=d.get('days')
    if scope not in ('default','week') or not valid_days(days,empty=scope=='week'):h.reply(400,{'error':'변경 범위와 월~금 요일을 확인해 주세요.'});return True
    value=json.dumps(sorted(set(days)))
    if scope=='week':
     if d.get('week')!=activity.week():h.reply(409,{'error':'주간이 변경되었습니다. 새로고침 후 다시 설정해 주세요.'});return True
     c.execute('INSERT OR IGNORE INTO meal_club_overrides VALUES(?,?,?,?)',(cid,uid,activity.week(),value))
     c.execute('UPDATE meal_club_overrides SET days=? WHERE club_id=? AND user_id=? AND week=?',(value,cid,uid,activity.week()))
    else:c.execute('UPDATE meal_club_members SET days=? WHERE club_id=? AND user_id=?',(value,cid,uid))
  elif action=='complete':
   day=d.get('day');now=datetime.now(activity.ZONE)
   if day!=activity.today() or now.weekday()>4 or now.strftime('%H:%M')<club['meal_time']:h.reply(400,{'error':'오늘 예정된 식사 시간 이후에 완료를 확인해 주세요.'});return True
   ids=roster(c,cid,day)
   if uid not in ids:h.reply(403,{'error':'오늘 참석자로 등록된 회원만 확인할 수 있습니다.'});return True
   if len(ids)<2:h.reply(400,{'error':'두 명 이상 함께 식사해야 완료할 수 있습니다.'});return True
   c.execute('INSERT OR IGNORE INTO meal_club_dates(club_id,day,members) VALUES(?,?,?)',(cid,day,json.dumps(ids)))
   c.execute('INSERT OR IGNORE INTO meal_club_confirmations VALUES(?,?,?)',(cid,day,uid))
   confirmed=[r[0] for r in c.execute('SELECT user_id FROM meal_club_confirmations WHERE club_id=? AND day=?',(cid,day))]
   before=c.execute('SELECT COALESCE(SUM(amount),0) FROM points WHERE user_id=?',(uid,)).fetchone()[0]
   if set(ids)<=set(confirmed):
    for person in ids:
     activity.award(c,person,'meal-day:'+day,10)
     for other in ids:
      if other!=person:activity.award(c,person,'meal-new:'+str(other),5)
    c.execute('UPDATE meal_club_dates SET rewarded=1 WHERE club_id=? AND day=?',(cid,day))
   after=c.execute('SELECT COALESCE(SUM(amount),0) FROM points WHERE user_id=?',(uid,)).fetchone()[0]
   h.reply(200,{'ok':True,'earned':int(after-before),'complete':set(ids)<=set(confirmed),'confirmed':len(confirmed),'total':len(ids)});return True
 h.reply(200,{'ok':True});return True
