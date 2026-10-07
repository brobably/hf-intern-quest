"""Account-scoped Bogeumi care game. Growth and purchases are server-authoritative."""
import json,time
from datetime import datetime,timezone,timedelta
ZONE=timezone(timedelta(hours=9))
STAGES=[('새싹집',0),('아기 보금이',32),('인턴 보금이',96),('든든한 보금이',192)]
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
 'look-scholar':{'name':'똑똑이 보금이','price':20,'category':'character','icon':'👓','slot':'look','description':'동그란 안경을 쓴 공부 친구'},
 'look-ribbon':{'name':'리본 보금이','price':20,'category':'character','icon':'🎀','slot':'look','description':'분홍 리본을 단 다정한 친구'},
 'look-music':{'name':'멜로디 보금이','price':30,'category':'character','icon':'🎧','slot':'look','description':'헤드폰을 쓴 음악 친구'},
 'look-cozy':{'name':'포근 보금이','price':25,'category':'character','icon':'🧣','slot':'look','description':'따뜻한 목도리를 두른 친구'}
}
ACTIONS={'feed':('밥 먹기',{'hunger':25,'happy':5}),'rest':('쉬기',{'energy':30}),'clean':('방 청소',{'hygiene':30,'happy':5}),'study':('함께 공부',{'happy':15,'energy':-10,'hunger':-5})}
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
def initial(name,now):return dict(name=name,growth=0,coins=0,hunger=75,happy=75,energy=75,hygiene=75,updated=now,last_care=0,reward_day=day(now),rewarded=[],owned=[],equipped=[],history=[])
def settled(data,now):
 p=dict(data);hours=max(0,min(48,(now-p['updated'])/3600))
 for key,rate in [('hunger',2),('happy',1),('energy',1),('hygiene',1.5)]:p[key]=max(25,p[key]-hours*rate)
 p['updated']=now
 if p['reward_day']!=day(now):p['reward_day']=day(now);p['rewarded']=[]
 return p
def public(p,now):
 p=settled(p,now);stage=max(i for i,(_,goal) in enumerate(STAGES) if p['growth']>=goal)
 return {**p,'stage':stage,'stage_name':STAGES[stage][0],'next_growth':STAGES[stage+1][1] if stage<3 else None,'care_wait':max(0,5-int(now-p['last_care'])),'items':ITEMS,'stages':[{'name':name,'growth':goal} for name,goal in STAGES]}
def get(h,u,db):
 if h.path!='/api/pet':return False
 with db() as c:
  c.execute('BEGIN IMMEDIATE');row=c.execute('SELECT data FROM intern_pets WHERE user_id=?',(u['id'],)).fetchone()
  if row:
   p=collect(c,u['id'],json.loads(row['data']));c.execute('UPDATE intern_pets SET data=? WHERE user_id=?',(json.dumps(p,ensure_ascii=False),u['id']))
  rewards=[dict(r) for r in c.execute('SELECT event_key,day,amount FROM pet_coin_rewards WHERE user_id=? ORDER BY day DESC,event_key LIMIT 12',(u['id'],))]
 h.reply(200,{'pet':{**public(p,time.time()),'coin_history':rewards} if row else None});return True
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
   if not isinstance(color,str) or color not in ['', 'color-mint','color-pink','color-lavender','color-sunset']:h.reply(400,{'error':'보금이 색상을 선택해 주세요.'});return True
   p=collect(c,u['id'],initial(name.strip(),now))
   if color:p['owned'].append(color);p['equipped'].append(color)
   c.execute('INSERT INTO intern_pets(user_id,data) VALUES(?,?)',(u['id'],json.dumps(p,ensure_ascii=False)));message='우리의 첫 보금자리가 생겼어요!'
  else:
   if not row:h.reply(404,{'error':'먼저 보금이를 맞이해 주세요.'});return True
   p=collect(c,u['id'],settled(json.loads(row['data']),now))
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
    if item not in p['owned']:
     if p['coins']<ITEMS[item]['price']:h.reply(400,{'error':'보금 코인이 부족해요. 오늘의 돌보기를 해 보세요.'});return True
     p['coins']-=ITEMS[item]['price'];p['owned'].append(item);p['equipped'].append(item);message='새 소품을 방에 놓았어요!'
    elif item in p['equipped']:p['equipped'].remove(item);message='소품을 보관했어요.'
    else:p['equipped'].append(item);message='소품을 방에 놓았어요.'
    slot=ITEMS[item].get('slot')
    if slot and item in p['equipped']:
     p['equipped']=[key for key in p['equipped'] if key==item or ITEMS.get(key,{}).get('slot')!=slot]
    if ITEMS[item]['category']=='character':message='보금이의 모습을 바꿨어요!'
   c.execute('UPDATE intern_pets SET data=? WHERE user_id=?',(json.dumps(p,ensure_ascii=False),u['id']))
 h.reply(200,{'pet':public(p,now),'message':message});return True
