"""Keep the explicitly designated test account out of shared user-facing data."""
import json
TEST_EMPLOYEE='1111'
TEST_NAME='테스트계정'
VIEWER_EMPLOYEE='56512'

def hidden(c,u):
 if u and u['employee']==VIEWER_EMPLOYEE:return set()
 return {r[0] for r in c.execute('SELECT id FROM users WHERE employee=? AND name=?',(TEST_EMPLOYEE,TEST_NAME))}

def visible(c,u,owner):return owner not in hidden(c,u)

def sanitize(data,ids,names,key=''):
 if not ids:return data
 if key=='members' and isinstance(data,str):
  try:return json.dumps([uid for uid in json.loads(data) if uid not in ids])
  except (ValueError,TypeError):return data
 if isinstance(data,list):
  result=[]
  for value in data:
   if isinstance(value,dict):
    if value.get('user_id') in ids:continue
    if key in ['ranking','reflex','members','users'] and value.get('id') in ids:continue
   if key=='members' and isinstance(value,int) and value in ids:continue
   if key=='participants' and isinstance(value,str) and value in names:continue
   result.append(sanitize(value,ids,names,key))
  return result
 if isinstance(data,dict):
  if data.get('user_id') in ids:return None
  result={k:sanitize(v,ids,names,k) for k,v in data.items()}
  # Replies under a hidden root are hidden with that thread.
  if key=='comments':return result
  if 'comments' in result:
   original=data['comments'];private_roots={r['id'] for r in original if r.get('user_id') in ids}
   result['comments']=[r for r in result['comments'] if r.get('parent_id') not in private_roots]
  return result
 return data

def filter_response(c,u,data):
 ids=hidden(c,u)
 names={r[0] for r in c.execute('SELECT name FROM users WHERE employee=? AND name=?',(TEST_EMPLOYEE,TEST_NAME))} if ids else set()
 return sanitize(data,ids,names)

def blocked_mutation(c,u,path,data):
 ids=hidden(c,u)
 if not ids:return False
 table=None
 if path.startswith('/api/boards/'):table='posts'
 elif path.startswith('/api/meals/'):table='meals'
 elif path.startswith('/api/reflex/comments/'):table='reflex_comments'
 elif path=='/api/wiki/remove':table='wiki_documents'
 elif path.startswith('/api/admin/'):
  return data.get('user_id') in ids or data.get('id') in ids
 target=data.get('id',data.get('meal_id',data.get('parent_id')))
 if table and type(target)==int:
  row=c.execute('SELECT user_id FROM '+table+' WHERE id=?',(target,)).fetchone()
  return bool(row and row[0] in ids)
 return False
