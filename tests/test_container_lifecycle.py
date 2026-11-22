import importlib.util
from pathlib import Path
import subprocess
import unittest

path = Path(__file__).resolve().parents[1] / 'scripts/container_lifecycle.py'
spec = importlib.util.spec_from_file_location('container_lifecycle', path)
helper = importlib.util.module_from_spec(spec)
spec.loader.exec_module(helper)


class LifecycleTests(unittest.TestCase):
    def running(self):
        return subprocess.CompletedProcess([], 0, '{"Status":"running","Running":true,"Pid":42,"ExitCode":0,"OOMKilled":false,"Error":""}', '')

    def clock(self):
        clock = [0]
        return lambda: clock[0], lambda delay: clock.__setitem__(0, clock[0] + delay)

    def test_transient_exec_128_is_retried_then_verified(self):
        calls = []
        def run(args):
            calls.append(args)
            if args[0] == 'inspect': return self.running()
            if sum(x[0] == 'exec' for x in calls) == 1:
                return subprocess.CompletedProcess([], 128, '', 'FailedPrecondition: init process is not running')
            return subprocess.CompletedProcess([], 0, '', '')
        now, sleep = self.clock()
        helper.wait('cf-ci-test-app', run=run, now=now, sleep=sleep)
        self.assertEqual(sum(x[0] == 'exec' for x in calls), 2)

    def test_exit_is_failure_not_readiness(self):
        def run(args): return subprocess.CompletedProcess([], 0, '{"Status":"exited","Running":false,"ExitCode":1,"OOMKilled":false,"Error":""}', '')
        with self.assertRaisesRegex(helper.ContainerError, 'stopped'):
            helper.wait('cf-ci-test-app', run=run)

    def test_container_created_without_pid_has_bounded_wait(self):
        calls=[]
        def run(args):
            calls.append(args)
            return subprocess.CompletedProcess([], 0, '{"Status":"created","Running":false,"Pid":0}', '')
        now, sleep = self.clock()
        with self.assertRaisesRegex(helper.ContainerError, 'within 3 seconds'):
            helper.wait('cf-ci-test-app', timeout=3, run=run, now=now, sleep=sleep)
        self.assertFalse(any(x[0]=='exec' for x in calls))

    def test_missing_extension_is_failure_not_retry_success(self):
        def run(args):
            return self.running() if args[0]=='inspect' else subprocess.CompletedProcess([], 1, '', '')
        with self.assertRaisesRegex(helper.ContainerError, 'directory check failed'):
            helper.wait('cf-ci-test-app', run=run)

    def test_diagnostic_exposes_state_and_logs_without_full_inspect(self):
        commands=[];output=[]
        def run(args):
            commands.append(args)
            return self.running() if args[0]=='inspect' else subprocess.CompletedProcess([], 0, 'startup failed: missing runtime library', '')
        helper.diagnose(['cf-ci-test-app'], run=run, output=output.append)
        self.assertTrue(any('missing runtime library' in line for line in output))
        self.assertTrue(any('OOMKilled' in line for line in output))
        self.assertEqual(commands[0][2], '{{json .State}}')

    def test_invalid_state_is_rejected(self):
        def run(args): return subprocess.CompletedProcess([], 0, 'not-json', '')
        with self.assertRaisesRegex(helper.ContainerError, 'invalid state'):
            helper.wait('cf-ci-test-app', run=run)


if __name__ == '__main__':
    unittest.main()
