import unittest,json,hashlib,subprocess,tempfile,shutil,re
from pathlib import Path
ROOT=Path(__file__).resolve().parents[1]
class RepositoryTests(unittest.TestCase):
 def test_manifest_pinned(self):
  m=json.loads((ROOT/'upstream.json').read_text());self.assertRegex(m['commit'],r'^[a-f0-9]{40}$');self.assertNotIn('latest',(ROOT/'Dockerfile').read_text())
 def test_workflows_are_cloud_only(self):
  for p in (ROOT/'.github/workflows').glob('*.yml'):
   s=p.read_text();self.assertIn('runs-on: ubuntu-24.04',s);self.assertNotIn('self-hosted',s);self.assertNotIn('pull_request_target',s);self.assertIn('scripts/smoke.sh',s)
   for ref in re.findall(r'uses: [^@]+@([^\s]+)',s):self.assertRegex(ref,r'^[a-f0-9]{40}$')
 def test_publish_is_manual_and_gated(self):
  s=(ROOT/'.github/workflows/publish.yml').read_text();self.assertIn('workflow_dispatch',s);self.assertLess(s.index('scripts/smoke.sh'),s.index('Log in to GHCR'));self.assertNotIn('latest',s)
 def test_no_private_files(self):
  for p in ROOT.rglob('*'):
   if not p.is_file() or 'node_modules' in p.parts or '.git' in p.parts:continue
   self.assertNotIn(p.name,['.env','config.php','id_rsa','id_ed25519']);self.assertNotIn('configuracao',p.relative_to(ROOT).parts)
 def test_all_fixtures_match_manifest(self):
  m=json.loads((ROOT/'upstream.json').read_text())
  for name,digest in m['fixture_sha256'].items():self.assertEqual(hashlib.sha256((ROOT/'tests/fixtures'/name).read_bytes()).hexdigest(),digest,name)

 def fixture(self):
  tmp=tempfile.TemporaryDirectory();self.addCleanup(tmp.cleanup);root=Path(tmp.name)
  for path in json.loads((ROOT/'evolution-centralflow-go/upstream.json').read_text())['sha256']:
   d=root/path;d.parent.mkdir(parents=True,exist_ok=True);shutil.copyfile(ROOT/'tests/fixtures'/path,d)
  d=root/'vendor/go.mau.fi/whatsmeow/newsletter.go';d.parent.mkdir(parents=True);shutil.copyfile(ROOT/'tests/fixtures/sdk.newsletter.go',d);return root
 def apply(self,root):return subprocess.run([__import__('sys').executable,str(ROOT/'evolution-centralflow-go/apply.py'),str(root)],capture_output=True,text=True)
 def test_real_route_install(self):
  root=self.fixture();r=self.apply(root);self.assertEqual(r.returncode,0,r.stderr);routes=(root/'pkg/routes/routes.go').read_text();self.assertIn('eng.Group("/centralflow",r.authMiddleware.Auth)',routes);self.assertTrue((root/'vendor/go.mau.fi/whatsmeow/centralflow.go').is_file())
 def test_modified_upstream_rejected(self):
  root=self.fixture();route=root/'pkg/routes/routes.go';route.write_bytes(route.read_bytes()+b'\n// changed\n');before=route.read_bytes();self.assertNotEqual(self.apply(root).returncode,0);self.assertEqual(route.read_bytes(),before);self.assertFalse((root/'pkg/sendMessage/service/centralflow.go').exists())
 def test_wrong_sdk_rejected(self):
  root=self.fixture();(root/'vendor/go.mau.fi/whatsmeow/newsletter.go').write_text('other SDK');self.assertNotEqual(self.apply(root).returncode,0);self.assertFalse((root/'pkg/sendMessage/service/centralflow.go').exists())
