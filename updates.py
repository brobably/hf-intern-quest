"""Per-viewer fingerprints for sidebar activity indicators."""
import hashlib,json
import privacy

def snapshot(c,u):
 hidden=privacy.hidden(c,u)
 groups={k:[] for k in ['wiki','lunch','study','articles','jobs','qna','suggestions','anonymous','reflex','stroop','cleaning']}
 def add(route,row):
  r=dict(row)
  if 'members' in r:r['members']=[uid for uid in json.loads(r['members']) if uid not in hidden]
  if r.get('user_id') not in hidden:groups[route].append(r)
 for r in c.execute('SELECT p.id,p.kind,p.user_id,p.created,p.replies,p.members,v.post_id AS private FROM posts p LEFT JOIN private_posts v ON v.post_id=p.id ORDER BY p.id'):
  if r['kind'] not in groups:continue
  if u['role']!='admin' and ((r['private'] is not None or r['kind']=='qna') and r['user_id']!=u['id']):continue
  # Hidden authors' replies must not leak through the update indicator.
  row=dict(r);row['replies']=[x for x in json.loads(row['replies']) if x.get('user_id') not in hidden]
  add(r['kind'],row)
 for route,table,columns in [('wiki','wiki_documents','id,user_id,created'),('lunch','meals','id,user_id,members'),('study','studys','id,user_id,members'),('anonymous','anonymous_posts','id,user_id,created'),('anonymous','anonymous_replies','id,user_id,created'),('reflex','reflex_comments','id,user_id,created'),('reflex','reflex_scores','user_id,week,ms'),('stroop','color_scores','id,user_id,week,correct,elapsed')]:
  for r in c.execute(f'SELECT {columns} FROM {table} ORDER BY 1'):add(route,r)
 profile=c.execute('SELECT department FROM user_profiles WHERE user_id=?',(u['id'],)).fetchone()
 department=profile[0] if profile else ''
 for r in c.execute('SELECT j.id,j.user_id,j.week,j.area,j.done,p.department FROM cleaning_jobs j LEFT JOIN user_profiles p ON p.user_id=j.user_id ORDER BY j.id'):
  if u['role']=='admin' or (department and r['department']==department):add('cleaning',r)
 return {key:hashlib.sha256(json.dumps(rows,sort_keys=True,ensure_ascii=False).encode()).hexdigest() for key,rows in groups.items()}

