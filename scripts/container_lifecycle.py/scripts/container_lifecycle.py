"""Bounded CI-only container startup check and diagnostics; no restart or deploy."""
import argparse
import json
import os
import re
import subprocess
import sys
import time


class ContainerError(RuntimeError):
    pass


def docker(args):
    try:
        return subprocess.run(['docker', *args], capture_output=True, text=True, timeout=10)
    except subprocess.TimeoutExpired as error:
        raise ContainerError('Docker command timed out: ' + args[0]) from error


def state(name, run=docker):
    result = run(['inspect', '--format', '{{json .State}}', name])
    if result.returncode:
        raise ContainerError('Cannot inspect container ' + name)
    try:
        value = json.loads(result.stdout)
        if not isinstance(value, dict):
            raise ValueError('state is not an object')
        return value
    except ValueError as error:
        raise ContainerError('Docker returned an invalid state for ' + name) from error


def summary(value):
    return json.dumps({key: value.get(key) for key in ['Status', 'Running', 'ExitCode', 'OOMKilled', 'Error']})


def wait(name, timeout=30, run=docker, now=time.monotonic, sleep=time.sleep):
    deadline = now() + timeout
    while True:
        value = state(name, run)
        status = value.get('Status')
        if status in ('exited', 'dead', 'removing'):
            raise ContainerError(name + ' stopped: ' + summary(value))
        if status == 'running' and value.get('Running') is True and value.get('Pid', 0) > 0:
            result = run(['exec', name, 'test', '-d', '/opt/centralflow-source'])
            if result.returncode == 0:
                return
            error = (result.stderr + result.stdout).lower()
            transient = result.returncode in (125, 126, 128) and any(
                term in error for term in ['not running', 'failedprecondition', 'failed precondition', 'not started']
            )
            if not transient:
                raise ContainerError(name + ': extension directory check failed (exit ' + str(result.returncode) + ')')
        if now() >= deadline:
            raise ContainerError(name + ': container did not become executable within ' + str(timeout) + ' seconds; ' + summary(value))
        sleep(1)


def diagnose(names, run=docker, output=print):
    for name in names:
        output('Container diagnostic: ' + name)
        try:
            output(summary(state(name, run)))
        except ContainerError as error:
            output(str(error))
        try:
            logs = run(['logs', '--tail', '80', name])
            # CI uses disposable credentials only. Never print the full inspect/env.
            output((logs.stdout + logs.stderr).strip() or '(no container logs available)')
        except ContainerError as error:
            output(str(error))


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('operation', choices=['wait', 'diagnose'])
    parser.add_argument('containers', nargs='+')
    args = parser.parse_args()
    if os.environ.get('CI') != 'true' or os.environ.get('GITHUB_ACTIONS') != 'true':
        parser.error('Run only in GitHub Actions with disposable containers.')
    if any(not re.fullmatch(r'cf-ci-[A-Za-z0-9_.-]+', name) for name in args.containers):
        parser.error('Only generated cf-ci- test containers are allowed.')
    if args.operation == 'wait' and len(args.containers) != 1:
        parser.error('wait accepts one container')
    try:
        if args.operation == 'wait':
            wait(args.containers[0])
        else:
            diagnose(args.containers)
    except ContainerError as error:
        message = str(error).replace('%', '%25').replace('\r', '%0D').replace('\n', '%0A')
        print('::error::' + message, file=sys.stderr)
        return 1
    return 0


if __name__ == '__main__':
    sys.exit(main())
