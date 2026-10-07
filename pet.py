"""Account-scoped Bogeumi care game. Growth and purchases are server-authoritative."""
import json,time
from datetime import datetime,timezone,timedelta
ZONE=timezone(timedelta(hours=9))
STAGES=[('새싹집',0),('아기 보금이',64),('인턴 보금이',192),('든든한 보금이',384)]
INTERNSHIP_END='2027-02-26'
ITEMS={
 'color-mint':{'name':'민트 보금이','price':15,'category':'color','icon':'🌿','slot':'color'},
 'color-pink':{'name':'분홍 보금이','price':15,'category':'color','icon':'🌸','slot':'color'},
 'color-lavender':{'name':'라벤더 보금이','price':15,'category':'color','icon':'🪻','slot':'color'},
 'color-sunset':{'name':'살구 보금이','price':15,'category':'color','icon':'🍑','slot':'color'},
 'plant':{'name':'작은 화분','price':12,'category':'furniture','icon':'🪴'},
 'books':{'name':'인턴 책장','price':18,'category':'furniture','icon':'📚'},
 'lamp':{'name':'포근한 조명','price':24,'category':'furniture','icon':'💡'},
 'sofa':{'name':'구름 소파','price':30,'category':'furniture','icon':'🛋️'},
 'clock':{'name':'곰돌이 시계','price':16,'category':'furniture','icon':'🕰️'},
 'flowers':{'name':'봄날 꽃병','price':20,'category':'furniture','icon':'🌷'},
 'cat':{'name':'고양이 인형','price':25,'category':'furniture','icon':'🐱'},
 'stars':{'name':'별빛 가랜드','price':22,'category':'furniture','icon':'⭐'},
 'wall-mint':{'name':'민트 벽지','price':20,'category':'room','icon':'🌿','slot':'wall'},
 'wall-peach':{'name':'복숭아 벽지','price':20,'category':'room','icon':'🍑','slot':'wall'},
 'wall-night':{'name':'밤하늘 벽지','price':28,'category':'room','icon':'🌌','slot':'wall'},
 'rug-pink':{'name':'딸기 우유 러그','price':15,'category':'room','icon':'🩷','slot':'rug'},
 'rug-mint':{'name':'민트 구름 러그','price':15,'category':'room','icon':'🟢','slot':'rug'},
 'floor-white':{'name':'화이트 우드 바닥','price':25,'category':'room','icon':'🪵','slot':'floor'},
 'look-scholar':{'name':'똑똑이 보금이','price':20,'category':'character','icon':'👓','slot':'eyewear','description':'동그란 안경 · 다른 소품과 함께 착용 가능'},
 'look-ribbon':{'name':'리본 보금이','price':20,'category':'character','icon':'🎀','slot':'hairwear','description':'분홍 리본 · 다른 소품과 함께 착용 가능'},
 'look-music':{'name':'멜로디 보금이','price':30,'category':'character','icon':'🎧','slot':'earwear','description':'헤드폰 · 다른 소품과 함께 착용 가능'},
 'look-cozy':{'name':'포근 보금이','price':25,'category':'character','icon':'🧣','slot':'neckwear','description':'포근한 목도리 · 다른 소품과 함께 착용 가능'}
}
ACTIONS={'feed':('밥 먹기',{'hunger':25,'happy':5}),'rest':('쉬기',{'energy':30}),'clean':('방 청소',{'hygiene':30,'happy':5}),'study':('함께 공부',{'happy':15,'energy':-10,'hunger':-5})}
for key,price in {'plant':5,'books':10,'lamp':8,'sofa':18,'clock':7,'flowers':6,'cat':8,'stars':7,'look-scholar':8,'look-ribbon':6,'look-music':12,'look-cozy':10}.items():ITEMS[key]['price']=price
for key,item in ITEMS.items():
 if item['category'] in ['color','room']:item['price']=10 if item['category']=='color' else 12
for key,name,price in [('desk','인턴 공부 책상',15),('pillow','구름 쿠션',5),('piggy','보금 저금통',7),('watering','민트 물뿌리개',5),('tea','작은 티 테이블',10),('painting','우리 집 액자',6),('basket','포근한 수납 바구니',8)]:
 ITEMS[key]={'name':name,'price':price,'category':'furniture','icon':''}
for key,name,price,slot in [('look-star','별빛 브로치',5,'badge'),('look-beret','민트 베레모',10,'hat'),('look-bag','인턴 가방',12,'bag'),('look-charm','보금 열쇠고리',6,'charm')]:
 ITEMS[key]={'name':name,'price':price,'category':'character','icon':'','slot':slot,'description':'다른 부위 소품과 함께 착용 가능'}

def coin_progress(c,uid,p,now):
 earned={'attendance':0,'game':0,'activity':0,'care':len(set(settled(p,now)['rewarded']))}
 for row in c.execute('SELECT event_key,amount FROM pet_coin_rewards WHERE user_id=? AND day=?',(uid,day(now))):
  group=row['event_key'].split(':')[0]
  if group in earned:earned[group]+=row['amount']
 return [{'key':key,'earned':min(limit,earned[key]),'limit':limit} for key,limit in [('attendance',10),('game',10),('activity',20),('care',4)]]
for key,item in ITEMS.items():
 item['price']={'plant':15,'books':25,'lamp':22,'sofa':45,'clock':20,'flowers':18,'cat':24,'stars':25,'desk':40,'pillow':12,'piggy':20,'watering':16,'tea':30,'painting':18,'basket':24,'look-scholar':20,'look-ribbon':18,'look-music':35,'look-cozy':28,'look-star':16,'look-beret':25,'look-bag':30,'look-charm':18}.get(key,20 if item['category']=='color' else 25)

ITEMS['color-blue']={'name':'기본 파랑 보금이','price':0,'category':'color','icon':'','slot':'color'}
ITEMS['look-star']['name']='별빛 지붕 핀'
SLOT_NAMES={'head':'머리','eyewear':'얼굴','body':'몸통·손','color':'색상'}
for key in ['look-ribbon','look-music','look-beret','look-star']:ITEMS[key]['slot']='head'
for key in ['look-cozy','look-bag','look-charm']:ITEMS[key]['slot']='body'
for key,item in ITEMS.items():
 if item['category']=='character':
  item['description']=SLOT_NAMES[item['slot']]+' 착용 · 같은 부위는 하나씩'
  item['equipment_region']=SLOT_NAMES[item['slot']]

def normalize_equipment(p):
 # Keep the most recently equipped item in each slot; ownership never changes.
 p['owned']=list(dict.fromkeys(['color-blue']+p.get('owned',[])))
 selected=[];slots=set()
 for key in reversed(p.get('equipped',[])):
  if key not in ITEMS or key in selected:continue
  slot=ITEMS[key].get('slot')
  if slot and slot in slots:continue
  selected.append(key)
  if slot:slots.add(slot)
 p['equipped']=list(reversed(selected))
 if 'color' not in slots:p['equipped'].append('color-blue')
 return p

def initialize(c):
 c.execute('CREATE TABLE IF NOT EXISTS intern_pets(user_id INTEGER PRIMARY KEY,data TEXT NOT NULL)')
 c.execute('CREATE TABLE IF NOT EXISTS pet_coin_wallet(user_id INTEGER PRIMARY KEY,balance INTEGER NOT NULL DEFAULT 0)')
 c.execute('CREATE TABLE IF NOT EXISTS pet_coin_rewards(user_id INTEGER NOT NULL,event_key TEXT NOT NULL,day TEXT NOT NULL,amount INTEGER NOT NULL,PRIMARY KEY(user_id,event_key))')

def reward(c,uid,key,amount,limit=None):
 stamp=day(time.time())
 if c.execute('SELECT event_key FROM pet_coin_rewards WHERE user_id=? AND event_key=?',(uid,key)).fetchone():return 0
 if limit:
  used=c.execute('SELECT COALESCE(SUM(amount),0) FROM pet_coin_rewards WHERE user_id=? AND day=? AND event_key LIKE ?',(uid,stamp,limit[0]+':%')).fetchone()[0]
  amount=min(amount,max(0,limit[1]-used))
 if amount<=0:return 0
 inserted=c.execute('INSERT OR IGNORE INTO pet_coin_rewards(user_id,event_key,day,amount) VALUES(?,?,?,?) RETURNING event_key',(uid,key,stamp,amount)).fetchone()
 if not inserted:return 0
 c.execute('INSERT OR IGNORE INTO pet_coin_wallet(user_id,balance) VALUES(?,0)',(uid,))
 c.execute('UPDATE pet_coin_wallet SET balance=balance+? WHERE user_id=?',(amount,uid))
 return amount

def collect(c,uid,p):
 row=c.execute('SELECT balance FROM pet_coin_wallet WHERE user_id=?',(uid,)).fetchone()
 if row and row['balance']:
  p['coins']+=row['balance'];c.execute('UPDATE pet_coin_wallet SET balance=0 WHERE user_id=?',(uid,))
 return p
def day(now):return datetime.fromtimestamp(now,ZONE).date().isoformat()
def initial(name,now):return dict(name=name,growth=0,growth_version=2,coins=0,hunger=75,happy=75,energy=75,hygiene=75,updated=now,last_care=0,reward_day=day(now),rewarded=[],owned=['color-blue'],equipped=['color-blue'],history=[])
def settled(data,now):
 p=dict(data);hours=max(0,min(48,(now-p['updated'])/3600))
 if p.get('growth_version',1)<2:p['growth']*=2;p['growth_version']=2
 for key,rate in [('hunger',2),('happy',1),('energy',1),('hygiene',1.5)]:p[key]=max(25,p[key]-hours*rate)
 p['updated']=now
 if p['reward_day']!=day(now):p['reward_day']=day(now);p['rewarded']=[]
 return normalize_equipment(p)
def public(p,now,admin=False):
 p=settled(p,now);stage=max(i for i,(_,goal) in enumerate(STAGES) if p['growth']>=goal)
 return {**p,'admin_shop':admin,'internship_end':INTERNSHIP_END,'stage':stage,'stage_name':STAGES[stage][0],'next_growth':STAGES[stage+1][1] if stage<3 else None,'care_wait':max(0,5-int(now-p['last_care'])),'items':ITEMS,'stages':[{'name':name,'growth':goal} for name,goal in STAGES]}
def get(h,u,db):
 if h.path!='/api/pet':return False
 with db() as c:
  c.execute('BEGIN IMMEDIATE');row=c.execute('SELECT data FROM intern_pets WHERE user_id=?',(u['id'],)).fetchone()
  if row:
   p=collect(c,u['id'],settled(json.loads(row['data']),time.time()));c.execute('UPDATE intern_pets SET data=? WHERE user_id=?',(json.dumps(p,ensure_ascii=False),u['id']))
  rewards=[dict(r) for r in c.execute('SELECT event_key,day,amount FROM pet_coin_rewards WHERE user_id=? ORDER BY day DESC,event_key LIMIT 12',(u['id'],))]
  progress=coin_progress(c,u['id'],p,time.time()) if row else []
 h.reply(200,{'pet':{**public(p,time.time(),u['role']=='admin'),'coin_history':rewards,'coin_progress':progress} if row else None});return True
def post(h,u,d,db):
 if h.path not in ['/api/pet/adopt','/api/pet/care','/api/pet/decorate','/api/pet/rename','/api/pet/stroke']:return False
 now=time.time();message=''
 with db() as c:
  c.execute('BEGIN IMMEDIATE');row=c.execute('SELECT data FROM intern_pets WHERE user_id=?',(u['id'],)).fetchone()
  if h.path=='/api/pet/adopt':
   if row:h.reply(409,{'error':'이미 함께 지내는 보금이가 있어요.'});return True
   name=d.get('name','보금이')
   if not isinstance(name,str) or not 1<=len(name.strip())<=12:h.reply(400,{'error':'이름은 1~12자로 입력해 주세요.'});return True
   color=d.get('color','')
   if not isinstance(color,str) or color not in ['', 'color-blue','color-mint','color-pink','color-lavender','color-sunset']:h.reply(400,{'error':'보금이 색상을 선택해 주세요.'});return True
   p=collect(c,u['id'],initial(name.strip(),now))
   if color:p['owned'].append(color);p['equipped'].append(color)
   normalize_equipment(p)
   c.execute('INSERT INTO intern_pets(user_id,data) VALUES(?,?)',(u['id'],json.dumps(p,ensure_ascii=False)));message='우리의 첫 보금자리가 생겼어요!'
  else:
   if not row:h.reply(404,{'error':'먼저 보금이를 맞이해 주세요.'});return True
   p=collect(c,u['id'],settled(json.loads(row['data']),now))
   normalize_equipment(p)
   c.execute('UPDATE intern_pets SET data=? WHERE user_id=?',(json.dumps(p,ensure_ascii=False),u['id']))
   if h.path=='/api/pet/care':
    action=d.get('action')
    if action not in ACTIONS:h.reply(400,{'error':'돌보기 방법을 확인해 주세요.'});return True
    if now-p['last_care']<5:h.reply(429,{'error':'잠깐만요! 5초 뒤 다시 돌볼 수 있어요.'});return True
    title,effects=ACTIONS[action]
    for key,amount in effects.items():p[key]=max(25,min(100,p[key]+amount))
    reward=action not in p['rewarded'];before=max(i for i,(_,goal) in enumerate(STAGES) if p['growth']>=goal)
    if reward:p['growth']+=8;p['coins']+=1;p['rewarded'].append(action)
    p['last_care']=now;message=title+' 완료! '+('성장 +8 · 보금 코인 +1' if reward else '기분이 좋아졌어요. 오늘의 성장 보상은 이미 받았어요.')
    after=max(i for i,(_,goal) in enumerate(STAGES) if p['growth']>=goal)
    if after>before:message+=' · '+STAGES[after][0]+'로 성장했어요!'
    p['history']=([{'text':title+(' · 성장 +8' if reward else ''),'time':datetime.fromtimestamp(now,ZONE).isoformat()}]+p['history'])[:12]
   elif h.path=='/api/pet/stroke':
    if now-p.get('last_stroke',0)<10:h.reply(429,{'error':'보금이가 아직 좋아하고 있어요. 잠깐 뒤 다시 쓰다듬어 주세요.'});return True
    p['happy']=min(100,p['happy']+3);p['last_stroke']=now;message='쓰담쓰담, 고마워요! 행복 +3 ♥'
   elif h.path=='/api/pet/rename':
    name=d.get('name')
    if not isinstance(name,str) or not 1<=len(name.strip())<=12:h.reply(400,{'error':'이름은 1~12자로 입력해 주세요.'});return True
    p['name']=name.strip();message='새 이름을 저장했어요.'
   else:
    item=d.get('item')
    if item not in ITEMS:h.reply(400,{'error':'소품을 확인해 주세요.'});return True
    action=d.get('action','toggle')
    if action not in ['buy','equip','unequip','toggle']:h.reply(400,{'error':'아이템 이용 방법을 확인해 주세요.'});return True
    if action=='buy' and item in p['owned']:h.reply(409,{'error':'이미 소장한 아이템입니다.'});return True
    if item not in p['owned']:
     if action=='unequip' or (action=='equip' and u['role']!='admin'):h.reply(400,{'error':'먼저 아이템을 소장해 주세요.'});return True
     price=0 if u['role']=='admin' else ITEMS[item]['price']
     if p['coins']<price:h.reply(400,{'error':'보금 코인이 부족해요. 출석과 게임으로 코인을 모아 보세요.'});return True
     p['coins']-=price;p['owned'].append(item)
    if action=='buy':message='내 소장함에 추가했어요. 언제든 장착할 수 있어요!'
    elif action=='unequip' or (action=='toggle' and item in p['equipped']):
     if item in p['equipped']:p['equipped'].remove(item)
     message='장착을 해제했어요. 아이템은 소장함에 남아 있어요.'
    else:
     if item not in p['equipped']:p['equipped'].append(item)
     message=(SLOT_NAMES.get(ITEMS[item].get('slot'),'아이템')+'에 '+ITEMS[item]['name']+' 착용 완료! 같은 부위의 기존 소품은 소장함에 보관돼요.')
    slot=ITEMS[item].get('slot')
    if slot and item in p['equipped']:
     p['equipped']=[key for key in p['equipped'] if key==item or ITEMS.get(key,{}).get('slot')!=slot]
   normalize_equipment(p)
   c.execute('UPDATE intern_pets SET data=? WHERE user_id=?',(json.dumps(p,ensure_ascii=False),u['id']))
 with db() as c:progress=coin_progress(c,u['id'],p,now)
 h.reply(200,{'pet':{**public(p,now,u['role']=='admin'),'coin_progress':progress},'message':message});return True
