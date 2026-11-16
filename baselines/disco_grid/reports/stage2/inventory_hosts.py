"""Read-only hardware inventory; no model jobs or transfers to inventory-only hosts."""
import concurrent.futures, datetime, json, pathlib, subprocess
COMMAND = '''hostname; date -u; uptime; lscpu | head -28; free -m; df -h; nvidia-smi --query-gpu=index,name,driver_version,memory.total,memory.used,utilization.gpu --format=csv; nvidia-smi --query-compute-apps=pid,used_memory --format=csv; ps -eo user,pid,ppid,ni,pcpu,pmem,comm --sort=-pcpu | head -28; tmux list-sessions 2>/dev/null; command -v python3; ls -ld /scratch /data /scratch/nav/disco_grid /scratch/nav/disco_grid/venv/bin/python 2>/dev/null; test -w /scratch/nav/disco_grid && echo DISCO_ROOT_WRITABLE'''
HOSTS={'gvlab':'gvlab','gvlab2':'gvlab2.iiit.ac.in','blackwell':'user1@10.4.25.63','girish-laptop':'girish'}
def inventory(item):
 name,host=item
 try:
  p=subprocess.run(['ssh','-o','BatchMode=yes','-o','ConnectTimeout=10',host,COMMAND],capture_output=True,text=True,timeout=40)
  return name,dict(utc=datetime.datetime.now(datetime.timezone.utc).isoformat(),permission='execution within pilot ceilings' if name=='gvlab' else 'inventory only',returncode=p.returncode,stdout=p.stdout,stderr=p.stderr)
 except Exception as e:return name,dict(error=type(e).__name__)
if __name__=='__main__':
 with concurrent.futures.ThreadPoolExecutor(max_workers=4) as ex: d=dict(ex.map(inventory,HOSTS.items()))
 pathlib.Path(__file__).with_name('host_inventory.json').write_text(json.dumps(d,indent=2)+'\n')
 print({k:v.get('returncode',v.get('error')) for k,v in d.items()})
