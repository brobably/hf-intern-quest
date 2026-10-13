"""Private cleaning groups, explicit memberships and preserved legacy rotation."""
import json
from datetime import datetime
import activity,privacy

def global_admin(u):return u['role']=='admin'
def initialize(c):
 c.execute('CREATE TABLE IF NOT EXISTS cleaning_groups(id INTEGER PRIMARY KEY,name TEXT NOT NULL,legacy_department TEXT UNIQUE,start_week TEXT NOT NULL,area TEXT NOT NULL,rotation TEXT NOT NULL,active INTEGER NOT NULL DEFAULT 1)')
 c.execute('CREATE TABLE IF NOT EXISTS cleaning_group_members(group_id INTEGER NOT NULL,user_id INTEGER NOT NULL,manager INTEGER NOT NULL DEFAULT 0,PRIMARY KEY(group_id,user_id))')
 c.execute('CREATE TABLE IF NOT EXISTS cleaning_group_invites(group_id INTEGER NOT NULL,user_id INTEGER NOT NULL,status TEXT NOT NULL,PRIMARY KEY(group_id,user_id))')
 c.execute('CREATE TABLE IF NOT EXISTS cleaning_group_jobs(id INTEGER PRIMARY KEY,group_id INTEGER NOT NULL,week TEXT NOT NULL,user_id INTEGER NOT NULL,area TEXT NOT NULL,done INTEGER NOT NULL DEFAULT 0,legacy_id INTEGER UNIQUE,UNIQUE(group_id,week,user_id,area))')
 c.execute('CREATE TABLE IF NOT EXISTS cleaning_group_weeks(group_id INTEGER NOT NULL,week TEXT NOT NULL,PRIMARY KEY(group_id,week))')
 # Each legacy department is imported once. Original tables remain intact.
 departments={r[0] for r in c.execute('SELECT department FROM cleaning_rotations')}
 departments.update(r[0] for r in c.execute("SELECT DISTINCT p.department FROM cleaning_jobs j JOIN user_profiles p ON p.user_id=j.user_id WHERE p.department<>''"))
 for dep in departments:
  if c.execute('SELECT id FROM cleaning_groups WHERE legacy_department=?',(dep,)).fetchone():continue
  r=c.execute('SELECT * FROM cleaning_rotations WHERE department=?',(dep,)).fetchone()
  gid=c.execute('INSERT INTO cleaning_groups(name,legacy_department,start_week,area,rotation) VALUES(?,?,?,?,?) RETURNING id',(dep,dep,r['start_week'] if r else activity.week(),r['area'] if r else '공용 공간',r['members'] if r else '[]')).fetchone()[0]
  ids={x[0] for x in c.execute("SELECT u.id FROM users u JOIN user_profiles p ON p.user_id=u.id WHERE p.department=? AND u.status='approved'",(dep,))}
  if r:ids.update(json.loads(r['members']))
  for uid in ids:c.execute('INSERT OR IGNORE INTO cleaning_group_members VALUES(?,?,0)',(gid,uid))
  for j in c.execute('SELECT j.* FROM cleaning_jobs j JOIN user_profiles p ON p.user_id=j.user_id WHERE p.department=?',(dep,)).fetchall():
   c.execute('INSERT OR IGNORE INTO cleaning_group_jobs(group_id,week,user_id,area,done,legacy_id) VALUES(?,?,?,?,?,?)',(gid,j['week'],j['user_id'],j['area'],j['done'],j['id']))
  for w in c.execute('SELECT week FROM cleaning_rotation_weeks WHERE department=?',(dep,)):
   c.execute('INSERT OR IGNORE INTO cleaning_group_weeks VALUES(?,?)',(gid,w[0]))

def access(c,u,gid):
 g=c.execute('SELECT * FROM cleaning_groups WHERE id=? AND active=1',(gid,)).fetchone()
 m=c.execute('SELECT manager FROM cleaning_group_members WHERE group_id=? AND user_id=?',(gid,u['id'])).fetchone()
 return g,bool(g and (global_admin(u) or m)),bool(g and (global_admin(u) or m and m[0]))

def materialize(c):
 w=activity.week()
 for g in c.execute('SELECT * FROM cleaning_groups WHERE active=1').fetchall():
  if c.execute('SELECT week FROM cleaning_group_weeks WHERE group_id=? AND week=?',(g['id'],w)).fetchone():continue
  ids=[uid for uid in json.loads(g['rotation']) if c.execute("SELECT m.user_id FROM cleaning_group_members m JOIN users u ON u.id=m.user_id WHERE m.group_id=? AND m.user_id=? AND u.status='approved'",(g['id'],uid)).fetchone()]
  offset=(datetime.strptime(w,'%Y-%m-%d')-datetime.strptime(g['start_week'],'%Y-%m-%d')).days//7
  if ids and offset>=0:
   c.execute('INSERT OR IGNORE INTO cleaning_group_jobs(group_id,week,user_id,area) VALUES(?,?,?,?)',(g['id'],w,ids[offset%len(ids)],g['area']))
   c.execute('INSERT OR IGNORE INTO cleaning_group_weeks VALUES(?,?)',(g['id'],w))

def visible_jobs(c,u,personal=False):
 materialize(c);rows=[]
 for j in c.execute('SELECT j.*,u.name,g.name AS group_name FROM cleaning_group_jobs j JOIN users u ON u.id=j.user_id JOIN cleaning_groups g ON g.id=j.group_id WHERE j.week=? AND g.active=1 ORDER BY j.id',(activity.week(),)):
  _,visible,_=access(c,u,j['group_id'])
  if visible and (not personal or j['user_id']==u['id']):rows.append(dict(j))
 return rows

def get(h,u,db):
 if h.path not in ('/api/cleaning-groups','/api/cleaning-groups/invitations'):return False
 with db() as c:
  if h.path.endswith('/invitations'):
   rows=[dict(r) for r in c.execute("SELECT g.id,g.name,g.area FROM cleaning_group_invites i JOIN cleaning_groups g ON g.id=i.group_id WHERE i.user_id=? AND i.status='pending' AND g.active=1 AND NOT EXISTS(SELECT 1 FROM cleaning_group_members m WHERE m.group_id=g.id AND m.user_id=?)",(u['id'],u['id']))]
   h.reply(200,{'invitations':rows});return True
  materialize(c);groups=[]
  for r in c.execute('SELECT * FROM cleaning_groups WHERE active=1 ORDER BY id').fetchall():
   g,visible,manage=access(c,u,r['id'])
   if not visible:continue
   v=dict(g);v['manage']=manage;v['rotation']=json.loads(v['rotation']);v['members']=[dict(m) for m in c.execute("SELECT u.id,u.name,m.manager FROM cleaning_group_members m JOIN users u ON u.id=m.user_id WHERE m.group_id=? AND u.status='approved' ORDER BY u.name",(r['id'],))]
   v['jobs']=[j for j in visible_jobs(c,u) if j['group_id']==r['id']]
   v['invitees']=[dict(x) for x in c.execute("SELECT id,name FROM users WHERE status='approved' AND employee<>? AND id NOT IN (SELECT user_id FROM cleaning_group_members WHERE group_id=?) ORDER BY name",(privacy.TEST_EMPLOYEE,r['id']))] if manage else []
   groups.append(v)
 h.reply(200,{'groups':groups,'week':activity.week(),'admin':global_admin(u)});return True

def post(h,u,d,db):
 if not h.path.startswith('/api/cleaning-groups/'):return False
 action=h.path.rsplit('/',1)[-1]
 with db() as c:
  c.execute('BEGIN IMMEDIATE')
  if action=='create':
   name=d.get('name','').strip() if isinstance(d.get('name'),str) else ''
   if not global_admin(u):h.reply(403,{'error':'전체 관리자만 그룹을 만들 수 있습니다.'});return True
   if not 1<=len(name)<=80:h.reply(400,{'error':'그룹 이름을 입력해 주세요.'});return True
   gid=c.execute('INSERT INTO cleaning_groups(name,start_week,area,rotation) VALUES(?,?,?,?) RETURNING id',(name,activity.week(),'공용 공간','[]')).fetchone()[0]
   c.execute('INSERT INTO cleaning_group_members VALUES(?,?,1)',(gid,u['id']))
   h.reply(201,{'ok':True,'id':gid});return True
  gid=d.get('group_id');g,visible,manage=access(c,u,gid) if type(gid)==int else (None,False,False)
  if not g:h.reply(404,{'error':'그룹을 찾을 수 없습니다.'});return True
  if action=='respond':
   inv=c.execute("SELECT status FROM cleaning_group_invites WHERE group_id=? AND user_id=? AND status='pending'",(gid,u['id'])).fetchone()
   if not inv or d.get('action') not in ('accept','decline'):h.reply(403,{'error':'응답할 초대가 없습니다.'});return True
   if d['action']=='accept':c.execute('INSERT OR IGNORE INTO cleaning_group_members VALUES(?,?,0)',(gid,u['id']))
   c.execute('UPDATE cleaning_group_invites SET status=? WHERE group_id=? AND user_id=?',(d['action'],gid,u['id']))
   h.reply(200,{'ok':True});return True
  if not visible:h.reply(403,{'error':'가입한 그룹만 이용할 수 있습니다.'});return True
  if action=='complete':
   job=c.execute('SELECT * FROM cleaning_group_jobs WHERE id=? AND group_id=? AND week=?',(d.get('job_id'),gid,activity.week())).fetchone()
   if not job or not (manage or job['user_id']==u['id']):h.reply(403,{'error':'본인 당번 또는 관리 중인 그룹만 완료할 수 있습니다.'});return True
   c.execute('UPDATE cleaning_group_jobs SET done=1 WHERE id=?',(job['id'],))
   key='clean:'+job['week']+':'+str(job['user_id'])+':'+job['area'] if job['legacy_id'] else 'clean:group:'+str(gid)+':'+str(job['id'])
   activity.award(c,job['user_id'],key,10)
   if job['legacy_id']:c.execute('UPDATE cleaning_jobs SET done=1 WHERE id=?',(job['legacy_id'],))
   h.reply(200,{'ok':True});return True
  if not manage:h.reply(403,{'error':'그룹 관리자만 변경할 수 있습니다.'});return True
  members={r[0] for r in c.execute('SELECT user_id FROM cleaning_group_members WHERE group_id=?',(gid,))}
  if action=='invite':
   ids=d.get('recipients')
   if not isinstance(ids,list) or not 1<=len(ids)<=30 or any(type(x)!=int or x in members or not c.execute("SELECT id FROM users WHERE id=? AND status='approved' AND employee<>?",(x,privacy.TEST_EMPLOYEE)).fetchone() for x in ids):h.reply(400,{'error':'초대할 회원을 확인해 주세요.'});return True
   for uid in set(ids):
    c.execute("INSERT OR IGNORE INTO cleaning_group_invites VALUES(?,?,'pending')",(gid,uid));c.execute("UPDATE cleaning_group_invites SET status='pending' WHERE group_id=? AND user_id=?",(gid,uid))
  elif action=='manager':
   if not global_admin(u):h.reply(403,{'error':'전체 관리자만 그룹 관리자를 지정할 수 있습니다.'});return True
   if d.get('user_id') not in members or type(d.get('manager'))!=bool:h.reply(400,{'error':'그룹 회원을 선택해 주세요.'});return True
   c.execute('UPDATE cleaning_group_members SET manager=? WHERE group_id=? AND user_id=?',(int(d['manager']),gid,d['user_id']))
  elif action=='remove-member':
   uid=d.get('user_id')
   if uid not in members or uid==u['id']:h.reply(400,{'error':'다른 그룹 회원을 선택해 주세요.'});return True
   if not global_admin(u) and c.execute('SELECT manager FROM cleaning_group_members WHERE group_id=? AND user_id=?',(gid,uid)).fetchone()[0]:h.reply(403,{'error':'다른 관리자는 전체 관리자만 제외할 수 있습니다.'});return True
   c.execute('DELETE FROM cleaning_group_members WHERE group_id=? AND user_id=?',(gid,uid));c.execute('DELETE FROM cleaning_group_invites WHERE group_id=? AND user_id=?',(gid,uid))
   c.execute('UPDATE cleaning_groups SET rotation=? WHERE id=?',(json.dumps([x for x in json.loads(g['rotation']) if x!=uid]),gid))
  elif action=='rotation':
   ids=d.get('members');start=d.get('start_week');area=d.get('area','')
   try:assert datetime.strptime(start,'%Y-%m-%d').weekday()==0 and start>=activity.week()
   except (ValueError,TypeError,AssertionError):h.reply(400,{'error':'이번 주 이후 월요일을 선택해 주세요.'});return True
   if not isinstance(ids,list) or any(type(x)!=int for x in ids) or len(ids)!=len(set(ids)) or not set(ids)<=members or not isinstance(area,str) or not 1<=len(area.strip())<=80:h.reply(400,{'error':'그룹 회원 순서와 구역을 확인해 주세요.'});return True
   c.execute('UPDATE cleaning_groups SET rotation=?,start_week=?,area=? WHERE id=?',(json.dumps(ids),start,area.strip(),gid))
  elif action=='assign':
   uid=d.get('user_id');area=d.get('area','')
   if uid not in members or not isinstance(area,str) or not 1<=len(area.strip())<=80:h.reply(400,{'error':'그룹 회원과 구역을 확인해 주세요.'});return True
   c.execute('INSERT OR IGNORE INTO cleaning_group_jobs(group_id,week,user_id,area) VALUES(?,?,?,?)',(gid,activity.week(),uid,area.strip()))
  elif action=='remove-job':c.execute('DELETE FROM cleaning_group_jobs WHERE id=? AND group_id=?',(d.get('job_id'),gid))
  else:h.reply(404,{'error':'요청을 확인해 주세요.'});return True
 h.reply(200,{'ok':True});return True

