"""Execute the existing dependency chain with the installed Python kernel, preserving logs."""
from pathlib import Path
import sys,subprocess,json
import nbformat
from nbclient import NotebookClient
R=Path(__file__).resolve().parents[1]
E=R/'outputs/paper_integrity/20260929_phases1_3/phase2'
# Use this exact venv; do not trust a globally installed python3 kernelspec.
kdir=R/'work/integrity-kernel/kernels/integrity';kdir.mkdir(parents=True,exist_ok=True)
(kdir/'kernel.json').write_text(json.dumps({'argv':[sys.executable,'-m','ipykernel_launcher','-f','{connection_file}'],'display_name':'Integrity local venv','language':'python'}))
import os
os.environ['JUPYTER_PATH']=str(kdir.parents[1])
for p in sorted((R/'notebooks').glob('*.ipynb')):
 if len(sys.argv)>1 and p.name < sys.argv[1]:continue
 if p.name.startswith('01_'):continue # data access exploratory downloads are not a scientific dependency
 if p.name.startswith('05c'):
  subprocess.run([sys.executable,'scripts/generate_cp6a_summary.py'],cwd=R,check=True)
 print('EXECUTE',p.name,flush=True)
 nb=nbformat.read(p,as_version=4)
 try:
  NotebookClient(nb,timeout=600,kernel_name='integrity',resources={'metadata':{'path':str(R)}}).execute()
 except Exception:
  nbformat.write(nb,E/('FAILED_'+p.name));raise
 nbformat.write(nb,p)
 outputs=[]
 for c in nb.cells:
  for out in c.get('outputs',[]):
   if 'text' in out:outputs.append(out.text)
   elif 'data' in out and 'text/plain' in out.data:outputs.append(out.data['text/plain'])
 (E/(p.stem+'.log')).write_text('\n'.join(outputs))
 print('OK',p.name,flush=True)
subprocess.run([sys.executable,'scripts/generate_cp6a_summary.py'],cwd=R,check=True)
