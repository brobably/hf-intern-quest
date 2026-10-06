"""Fetch publisher RSS headlines, retaining a durable cache for sleeping free services."""
import html,re,time,threading
import xml.etree.ElementTree as ET
from urllib.request import Request,urlopen
from urllib.parse import urlsplit
from email.utils import parsedate_to_datetime
from datetime import datetime,timezone,timedelta
from concurrent.futures import ThreadPoolExecutor
ZONE=timezone(timedelta(hours=9))
FEEDS=[('경제·금융','https://www.mk.co.kr/rss/30100041/'),('부동산','https://www.mk.co.kr/rss/50300009/')]
lock=threading.Lock()
def initialize(c):
 c.execute('CREATE TABLE IF NOT EXISTS news_items(link TEXT PRIMARY KEY,title TEXT NOT NULL,category TEXT NOT NULL,published TEXT NOT NULL)')
 c.execute('CREATE TABLE IF NOT EXISTS news_cache(id INTEGER PRIMARY KEY,updated TEXT NOT NULL,attempt DOUBLE PRECISION NOT NULL,error TEXT NOT NULL)')
def parse_feed(raw,category,now=None):
 now=now or datetime.now(ZONE)
 if len(raw)>2000000 or b'<!DOCTYPE' in raw.upper() or b'<!ENTITY' in raw.upper():raise ValueError('Invalid RSS')
 root=ET.fromstring(raw);result=[]
 for item in root.findall('./channel/item')[:100]:
  title=html.unescape(re.sub('<[^>]*>','',item.findtext('title',''))).strip()[:300];link=item.findtext('link','').strip();url=urlsplit(link)
  try:date=parsedate_to_datetime(item.findtext('pubDate',''));date=date.replace(tzinfo=ZONE) if date.tzinfo is None else date.astimezone(ZONE)
  except (ValueError,TypeError,OverflowError):continue
  if not title or url.scheme!='https' or url.hostname not in ['www.mk.co.kr','mk.co.kr'] or date<now-timedelta(days=7) or date>now+timedelta(minutes=10):continue
  result.append(dict(title=title,link=link,category=category,published=date.isoformat()))
 return result

def fetch_feed(feed):
 category,url=feed
 with urlopen(Request(url,headers={'User-Agent':'HFInternPortal/1.0 RSS Reader'}),timeout=6) as r:raw=r.read(2000001)
 return parse_feed(raw,category)

def refresh(db):
 if not lock.acquire(blocking=False):return
 try:
  with db() as c:
   meta=c.execute('SELECT * FROM news_cache WHERE id=1').fetchone()
   if meta and time.time()-meta['attempt']<300:return
   c.execute('INSERT OR IGNORE INTO news_cache(id,updated,attempt,error) VALUES(1,?,?,?)',('',0,''))
   c.execute('UPDATE news_cache SET attempt=? WHERE id=1',(time.time(),))
  results=[];failed=0
  with ThreadPoolExecutor(max_workers=2) as pool:
   futures=[pool.submit(fetch_feed,f) for f in FEEDS]
   for future in futures:
    try:
     rows=future.result()
     if not rows:failed+=1
     results.extend(rows)
    except Exception:failed+=1
  with db() as c:
   if results:
    for r in results:
     c.execute('INSERT OR IGNORE INTO news_items(link,title,category,published) VALUES(?,?,?,?)',(r['link'],r['title'],r['category'],r['published']))
    c.execute('DELETE FROM news_items WHERE published<?',((datetime.now(ZONE)-timedelta(days=7)).isoformat(),))
    c.execute('UPDATE news_cache SET updated=? WHERE id=1',(datetime.now(ZONE).isoformat(),))
   c.execute('UPDATE news_cache SET error=? WHERE id=1',('일부 기사 소스를 갱신하지 못했습니다. 저장된 기사를 표시합니다.' if failed else '',))
 finally:lock.release()

def get(h,u,db):
 if h.path!='/api/news':return False
 with db() as c:
  meta=c.execute('SELECT * FROM news_cache WHERE id=1').fetchone();count=c.execute('SELECT COUNT(*) FROM news_items').fetchone()[0]
 stale=not meta or not meta['updated'] or meta['updated'][:10]!=datetime.now(ZONE).date().isoformat() or (datetime.now(ZONE)-datetime.fromisoformat(meta['updated'])).total_seconds()>3600
 if stale:
  if count:threading.Thread(target=refresh,args=(db,),daemon=True).start()
  else:refresh(db)
 with db() as c:
  rows=[dict(r) for r in c.execute('SELECT * FROM news_items ORDER BY published DESC LIMIT 100')];meta=c.execute('SELECT * FROM news_cache WHERE id=1').fetchone()
 h.reply(200,{'articles':rows,'updated':meta['updated'] if meta else '', 'notice':meta['error'] if meta else '', 'today':datetime.now(ZONE).date().isoformat()});return True
