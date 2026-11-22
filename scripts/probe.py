"""Only probes HTTP startup/auth boundaries; never links a WhatsApp account."""
import json,sys,time,urllib.request,urllib.error
base,provider=sys.argv[1:];path='/' if provider=='api' else '/server/ok'
last='no response'
for attempt in range(90):
 try:
  with urllib.request.urlopen(base+path,timeout=3) as response:code=response.status;raw=response.read(65536)
 except urllib.error.HTTPError as error:code=error.code;raw=error.read(65536)
 except (OSError,TimeoutError):time.sleep(2);continue
 if code==200:
  try:data=json.loads(raw)
  except ValueError:raise SystemExit('HTTP 200 was not the expected JSON API health response')
  if provider=='api' and data.get('version')=='2.3.7':break
  if provider=='go' and data.get('status')=='ok':break
  raise SystemExit('Unexpected native API health contract')
 if provider=='go' and code in (402,403,503) and any(x in raw.lower() for x in [b'licens',b'licen',b'activation']):
  print('Native GO licensing gate is active; activation was not attempted. HTTP startup confirmed.')
  break
 last='HTTP '+str(code);time.sleep(2)
else:raise SystemExit('Image startup did not become ready: '+last)
route='/centralflow/capabilities/ci-probe' if provider=='api' else '/centralflow/capabilities'
try:
 with urllib.request.urlopen(base+route,timeout=5) as response:
  raw=response.read(65536)
  if not (provider=='go' and b'licen' in raw.lower() and b'centralflow-publishing/1' not in raw):raise SystemExit('Unauthenticated capability route returned HTTP 200')
except urllib.error.HTTPError as error:
 if error.code not in (401,402,403,404,409,503):raise
print('HTTP startup and unauthenticated route probe passed. No WhatsApp account was connected.')
