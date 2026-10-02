import json
from datetime import datetime,timezone,timedelta

def initialize(c):
 c.execute("CREATE TABLE IF NOT EXISTS wiki_documents(id INTEGER PRIMARY KEY,user_id INTEGER NOT NULL,title TEXT NOT NULL,body TEXT NOT NULL,department TEXT NOT NULL,created TEXT NOT NULL)")
 c.execute('CREATE TABLE IF NOT EXISTS wiki_migrations(user_id INTEGER PRIMARY KEY)')
 for user in c.execute('SELECT id,state FROM users').fetchall():
  if c.execute('SELECT user_id FROM wiki_migrations WHERE user_id=?',(user['id'],)).fetchone():continue
  for doc in json.loads(user['state']).get('wiki',[]):
   if isinstance(doc,dict) and isinstance(doc.get('title'),str) and isinstance(doc.get('body'),str):
    c.execute('INSERT INTO wiki_documents(user_id,title,body,department,created) VALUES(?,?,?,?,?)',(user['id'],doc['title'][:120],doc['body'][:5000],'유동화자산처',datetime.now(timezone(timedelta(hours=9))).isoformat()))
  c.execute('INSERT INTO wiki_migrations(user_id) VALUES(?)',(user['id'],))

def get(h,u,db):
 if h.path!='/api/wiki':return False
 with db() as c:rows=c.execute('SELECT wiki_documents.*,users.name AS author FROM wiki_documents JOIN users ON users.id=wiki_documents.user_id ORDER BY wiki_documents.id DESC LIMIT 200').fetchall()
 h.reply(200,{'documents':[dict(r) for r in rows]});return True

def post(h,u,d,db):
 if not h.path.startswith('/api/wiki/'):return False
 if h.path=='/api/wiki/post':
  title=d.get('title');body=d.get('body');department=d.get('department')
  if not isinstance(title,str) or not 1<=len(title.strip())<=120 or not isinstance(body,str) or not 1<=len(body.strip())<=5000 or department!='유동화자산처':
   h.reply(400,{'error':'문서 제목, 내용, 부서를 확인해 주세요.'});return True
  with db() as c:c.execute('INSERT INTO wiki_documents(user_id,title,body,department,created) VALUES(?,?,?,?,?)',(u['id'],title.strip(),body.strip(),department,datetime.now(timezone(timedelta(hours=9))).isoformat()))
  h.reply(201,{'ok':True});return True
 if h.path=='/api/wiki/remove':
  did=d.get('id')
  if type(did)!=int:h.reply(400,{'error':'문서를 확인해 주세요.'});return True
  with db() as c:
   c.execute('BEGIN IMMEDIATE');doc=c.execute('SELECT user_id FROM wiki_documents WHERE id=?',(did,)).fetchone()
   if not doc:h.reply(404,{'error':'문서를 찾을 수 없습니다.'});return True
   if doc['user_id']!=u['id'] and u['role']!='admin':h.reply(403,{'error':'본인이 작성한 문서만 삭제할 수 있습니다.'});return True
   c.execute('DELETE FROM wiki_documents WHERE id=?',(did,))
  h.reply(200,{'ok':True});return True
 h.reply(404,{'error':'찾을 수 없습니다.'});return True
