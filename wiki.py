import json,base64,binascii
import privacy
from urllib.parse import urlsplit,parse_qs
from datetime import datetime,timezone,timedelta

def initialize(c):
 c.execute('CREATE TABLE IF NOT EXISTS wiki_images(document_id INTEGER NOT NULL,position INTEGER NOT NULL,name TEXT NOT NULL,data TEXT NOT NULL,PRIMARY KEY(document_id,position))')
 c.execute("CREATE TABLE IF NOT EXISTS wiki_documents(id INTEGER PRIMARY KEY,user_id INTEGER NOT NULL,title TEXT NOT NULL,body TEXT NOT NULL,department TEXT NOT NULL,created TEXT NOT NULL)")
 c.execute('CREATE TABLE IF NOT EXISTS wiki_migrations(user_id INTEGER PRIMARY KEY)')
 for user in c.execute('SELECT id,state FROM users').fetchall():
  if c.execute('SELECT user_id FROM wiki_migrations WHERE user_id=?',(user['id'],)).fetchone():continue
  for doc in json.loads(user['state']).get('wiki',[]):
   if isinstance(doc,dict) and isinstance(doc.get('title'),str) and isinstance(doc.get('body'),str):
    c.execute('INSERT INTO wiki_documents(user_id,title,body,department,created) VALUES(?,?,?,?,?)',(user['id'],doc['title'][:120],doc['body'][:5000],'유동화자산처',datetime.now(timezone(timedelta(hours=9))).isoformat()))
  c.execute('INSERT INTO wiki_migrations(user_id) VALUES(?)',(user['id'],))

def departments(c):
 return sorted({'유동화자산처'}|{r[0] for r in c.execute("SELECT DISTINCT department FROM user_profiles JOIN users ON users.id=user_profiles.user_id WHERE users.status='approved' AND department<>''")}|{r[0] for r in c.execute('SELECT DISTINCT department FROM wiki_documents')})

def get(h,u,db):
 path=urlsplit(h.path).path;q=parse_qs(urlsplit(h.path).query)
 if path=='/api/wiki/image':
  try:did=int(q.get('id',[''])[0]);position=int(q.get('position',[''])[0])
  except ValueError:h.reply(400,{'error':'사진을 확인해 주세요.'});return True
  with db() as c:
   owner=c.execute('SELECT user_id FROM wiki_documents WHERE id=?',(did,)).fetchone()
   row=c.execute('SELECT data FROM wiki_images WHERE document_id=? AND position=?',(did,position)).fetchone() if owner and privacy.visible(c,u,owner[0]) else None
  if not row:h.reply(404,{'error':'사진을 찾을 수 없습니다.'});return True
  image=base64.b64decode(row['data']);h.send_response(200);h.send_header('Content-Type','image/jpeg');h.send_header('X-Content-Type-Options','nosniff');h.send_header('Cache-Control','private, no-store');h.send_header('Content-Length',str(len(image)));h.end_headers();h.wfile.write(image);return True
 if path=='/api/wiki/document':
  try:did=int(q.get('id',[''])[0])
  except ValueError:h.reply(400,{'error':'문서를 확인해 주세요.'});return True
  with db() as c:
   row=c.execute('SELECT wiki_documents.*,users.name AS author FROM wiki_documents JOIN users ON users.id=wiki_documents.user_id WHERE wiki_documents.id=?',(did,)).fetchone()
   if row and not privacy.visible(c,u,row['user_id']):row=None
   images=[{'name':r['name'],'url':'/api/wiki/image?id='+str(did)+'&position='+str(r['position'])} for r in c.execute('SELECT name,position FROM wiki_images WHERE document_id=? ORDER BY position',(did,))]
  h.reply(200 if row else 404,{'document':{**dict(row),'images':images}} if row else {'error':'문서를 찾을 수 없습니다.'});return True
 if path!='/api/wiki':return False
 try:page=max(1,int(q.get('page',['1'])[0]))
 except ValueError:page=1
 department=q.get('department',[''])[0];search=q.get('q',[''])[0].strip()[:120];where=' WHERE 1=1';args=[]
 if department:where+=' AND department=?';args.append(department)
 if search:where+=' AND LOWER(title) LIKE ?';args.append('%'+search.lower()+'%')
 with db() as c:
  hidden=privacy.hidden(c,u)
  visibility=''
  hidden_args=[]
  if hidden:
   visibility=' AND wiki_documents.user_id NOT IN ('+','.join('?' for _ in hidden)+')';hidden_args=list(hidden)
   where+=visibility;args+=hidden_args
  total=c.execute('SELECT COUNT(*) FROM wiki_documents'+where,args).fetchone()[0]
  page=min(page,max(1,(total+19)//20))
  rows=c.execute('SELECT wiki_documents.id,user_id,title,department,created,users.name AS author FROM wiki_documents JOIN users ON users.id=wiki_documents.user_id'+where+' ORDER BY wiki_documents.id DESC LIMIT 20 OFFSET ?',tuple(args)+((page-1)*20,)).fetchall()
  groups=[dict(r) for r in c.execute('SELECT department,COUNT(*) AS count FROM wiki_documents WHERE 1=1'+visibility+' GROUP BY department',hidden_args)];options=departments(c)
 h.reply(200,{'documents':[dict(r) for r in rows],'total':total,'page':page,'pages':max(1,(total+19)//20),'departments':options,'groups':groups});return True

def post(h,u,d,db):
 if not h.path.startswith('/api/wiki/'):return False
 if h.path=='/api/wiki/post':
  title=d.get('title');body=d.get('body');department=d.get('department')
  if not isinstance(title,str) or not 1<=len(title.strip())<=120 or not isinstance(body,str) or not 1<=len(body.strip())<=5000 or not isinstance(department,str) or not 1<=len(department)<=80:
   h.reply(400,{'error':'문서 제목, 내용, 부서를 확인해 주세요.'});return True
  images=d.get('images',[])
  if not isinstance(images,list) or len(images)>3:h.reply(400,{'error':'사진은 최대 3장 첨부할 수 있습니다.'});return True
  validated=[]
  for image in images:
   if not isinstance(image,dict) or not isinstance(image.get('name'),str) or not 1<=len(image['name'])<=200 or not isinstance(image.get('data'),str) or len(image['data'])>550000:h.reply(400,{'error':'사진 정보를 확인해 주세요.'});return True
   try:raw=base64.b64decode(image['data'],validate=True)
   except (ValueError,binascii.Error):h.reply(400,{'error':'사진 형식을 확인해 주세요.'});return True
   if len(raw)>400000 or not raw.startswith(b'\xff\xd8\xff') or not raw.endswith(b'\xff\xd9'):h.reply(400,{'error':'유효한 사진을 첨부해 주세요.'});return True
   validated.append(image)
  with db() as c:
   c.execute('BEGIN IMMEDIATE')
   if department not in departments(c):h.reply(400,{'error':'등록된 부서를 선택해 주세요.'});return True
   c.execute('INSERT INTO wiki_documents(user_id,title,body,department,created) VALUES(?,?,?,?,?)',(u['id'],title.strip(),body.strip(),department,datetime.now(timezone(timedelta(hours=9))).isoformat()))
   did=c.execute('SELECT id FROM wiki_documents WHERE user_id=? ORDER BY id DESC LIMIT 1',(u['id'],)).fetchone()[0]
   for position,image in enumerate(validated):c.execute('INSERT INTO wiki_images(document_id,position,name,data) VALUES(?,?,?,?)',(did,position,image['name'],image['data']))
  h.reply(201,{'ok':True});return True
 if h.path=='/api/wiki/remove':
  did=d.get('id')
  if type(did)!=int:h.reply(400,{'error':'문서를 확인해 주세요.'});return True
  with db() as c:
   c.execute('BEGIN IMMEDIATE');doc=c.execute('SELECT user_id FROM wiki_documents WHERE id=?',(did,)).fetchone()
   if not doc:h.reply(404,{'error':'문서를 찾을 수 없습니다.'});return True
   if doc['user_id']!=u['id'] and u['role']!='admin':h.reply(403,{'error':'본인이 작성한 문서만 삭제할 수 있습니다.'});return True
   c.execute('DELETE FROM wiki_images WHERE document_id=?',(did,))
   c.execute('DELETE FROM wiki_documents WHERE id=?',(did,))
  h.reply(200,{'ok':True});return True
 h.reply(404,{'error':'찾을 수 없습니다.'});return True
