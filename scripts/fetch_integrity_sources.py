from concurrent.futures import ThreadPoolExecutor,as_completed
from pathlib import Path
import sys,json,time
sys.path.insert(0,'src')
from saa.load_poes import download_poes_file,file_sha256
r=Path('outputs/paper_integrity/20260929_phases1_3/phase1')
def get(task):
 sat,day=task
 for attempt in range(3):
  try:
   p=download_poes_file(f'2024-01-{day:02}',sat,timeout=45)
   return dict(satellite=sat,day=day,path=p,sha256=file_sha256(p))
  except Exception as e: err=str(e)
 return dict(satellite=sat,day=day,error=err)
tasks=[('noaa15',19)]+[(s,d) for s in ['noaa15','noaa18','metop01','metop03'] for d in range(1,32) if (s,d)!=('noaa15',19)]
rows=[]
with ThreadPoolExecutor(max_workers=4) as pool:
 for f in as_completed([pool.submit(get,t) for t in tasks]):
  row=f.result(); rows.append(row);print(json.dumps(row),flush=True)
  (r/'retrieval.json').write_text(json.dumps(sorted(rows,key=lambda x:(x['satellite'],x['day'])),indent=2))
