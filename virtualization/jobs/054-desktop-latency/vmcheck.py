"""VM-only harness inside the exact RAM root. Never included in native bundle."""
import importlib.util,json,os,subprocess,sys,time
from pathlib import Path
s=Path('/run/d30');o=s/'results'
spec=importlib.util.spec_from_file_location('collector',s/'collect.py')
a=importlib.util.module_from_spec(spec);spec.loader.exec_module(a)
os.sched_setaffinity(0,{0})
end=time.monotonic()+60
while True:
 try:
  pid,ipc,env=a.find_desktop()
  monitors=a.request(ipc,'j/monitors')
  assert len(monitors)==1 and (monitors[0]['width'],monitors[0]['height'],monitors[0]['scale'])==(3456,2160,1)
  assert a.request(ipc,'j/getoption input:repeat_delay')['int']==1000
  break
 except (OSError,ValueError,AssertionError):
  if time.monotonic()>end or not Path('/proc',os.environ['ILINUX_VM_STARTPID']).exists():raise
  time.sleep(1)
(o/'monitors.json').write_text(json.dumps(monitors))
(o/'layers.json').write_text(json.dumps(a.request(ipc,'j/layers')))
(o/'options.json').write_text(json.dumps({n:a.request(ipc,'j/getoption '+n) for n in ('render:cm_enabled','debug:damage_tracking','input:repeat_delay','animations:enabled')}))
time.sleep(5)
with (o/'phases.jsonl').open('w') as f:
 old=sys.stdout;sys.stdout=f
 try:
  a.clock_estimate('vm-before')
  a.phase('vm-exact-root-1',pid,ipc,env,s)
  a.phase('vm-exact-root-2',pid,ipc,env,s)
  a.phase('vm-short-observation',pid,ipc,env,s,human_seconds=2)
  a.clock_estimate('vm-after')
 finally:sys.stdout=old
p=subprocess.run([str(s/'frameprobe-san')],env=env,capture_output=True,text=True,timeout=45,user=1000,group=1000,extra_groups=[])
(o/'sanitizer.jsonl').write_text(p.stdout);(o/'sanitizer.stderr').write_text(p.stderr)
assert p.returncode==0 and not p.stderr,(p.returncode,p.stderr)
a.validate_frames([json.loads(x) for x in p.stdout.splitlines()])
# Expected generic-VM refusal: actual native entrypoint does not reach desktop changes.
assert a.main()==3
assert not Path('/run/ilinux-desktop30.started').exists()
print('PASS exact-root compositor guard, uid1000 client, 3 phases, sanitizer callbacks, native identity refusal')
