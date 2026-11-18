"""Workflow river 0.1.0 over Console blocks 0.2.0; no command retries."""
import json
from pathlib import Path
import shlex
import time
from urllib.request import HTTPRedirectHandler, ProxyHandler, build_opener
from uuid import uuid4

from . import ConfigError
from .console_records import Records


class NoRedirect(HTTPRedirectHandler):
    def redirect_request(self, request, fp, code, msg, headers, newurl):
        return None


def uid():
    return str(uuid4())


class WorkflowRiver:
    def __init__(self, records, *, profile, host_id, title, reference, run_id, origin):
        self.records = records
        self.session_id = uid()
        self.target_id = profile + ' / ' + host_id
        self.reader_url = origin.rstrip('/') + '/console/' + self.session_id
        self.history_url = self.reader_url + '/history'
        self.phase = None
        self.records.create({'session_id': self.session_id, 'title': title,
            'host_id': self.target_id, 'work_id': None,
            'targets': [{'profile': profile, 'host_id': host_id, 'icon': '🖥'}]})
        self.text('status', 'Recipe execution', json.dumps({'reference': reference,
            'source_observation_id': run_id, 'host': host_id, 'profile': profile}, ensure_ascii=False))

    def start(self, kind, title, text=''):
        block = uid()
        self.records.add_block(self.session_id, {'event_id': uid(), 'block_id': block,
            'kind': kind, 'title': title, 'text': text, 'form': None, 'target_id': self.target_id})
        return block

    def append(self, block, offset, text):
        # Use small character chunks so each UTF-8 append is below 32 KiB.
        for index in range(0, len(text), 4096):
            chunk = text[index:index + 4096]
            self.records.append(self.session_id, block, {'event_id': uid(), 'offset': offset, 'text': chunk})
            offset += len(chunk.encode('utf-8'))
        return offset

    def finish(self, block, status='completed'):
        self.records.finish(self.session_id, block, {'event_id': uid(), 'status': status})

    def text(self, kind, title, text, status='completed'):
        block = self.start(kind, title)
        self.append(block, 0, text)
        self.finish(block, status)
        return block

    def progress(self, message):
        if self.phase:
            self.finish(self.phase)
        self.phase = self.start('status', 'Workflow progress', message)

    def execute(self, session, argv, *, timeout):
        """Stream public SSHScript managed-job buffers; never open another Session."""
        if not isinstance(argv, list) or not argv or any(not isinstance(v, str) or not v or '\x00' in v for v in argv):
            raise ConfigError('river requires reviewed nonempty argv')
        command = self.start('command', 'Remote command', shlex.join(argv))
        blocks = {name: self.start(name, name) for name in ('stdout', 'stderr')}
        previous = dict.fromkeys(blocks, '')
        offsets = dict.fromkeys(blocks, 0)
        gaps = dict.fromkeys(blocks, False)
        job = None
        result = None
        outcome = 'failed'
        failure = None

        def drain():
            for name in blocks:
                value = getattr(job, name)
                if value.startswith(previous[name]):
                    delta = value[len(previous[name]):]
                else:
                    # The bounded source tail rotated. Never present it as a complete stream.
                    if not gaps[name]:
                        self.text('error', 'Output coverage gap', name + ' capture tail rotated; output is incomplete.', 'failed')
                    gaps[name] = True
                    delta = value
                if delta:
                    offsets[name] = self.append(blocks[name], offsets[name], delta)
                previous[name] = value

        try:
            job = session.start(argv, timeout=timeout, check=False)
            while not job.done:
                drain()
                time.sleep(0.05)
            drain()
            result = job.wait()
            outcome = 'completed' if result.exitcode == 0 else 'failed'
            self.text('status', 'Command result', json.dumps({'exitcode': result.exitcode,
                'stop_reason': result.stop_reason, 'termination_status': result.termination_status}, ensure_ascii=False))
            return result
        except BaseException as error:
            failure = error
            outcome = 'interrupted' if isinstance(error, (KeyboardInterrupt, SystemExit)) else 'failed'
            try:
                self.text('error', 'Command interrupted or failed', type(error).__name__ + '; no automatic retry.', outcome)
            except Exception as recording_error:
                error.add_note('River recording failed: ' + type(recording_error).__name__)
            raise
        finally:
            cleanup_errors = []
            try:
                if job is not None:
                    job.stop()  # Owned job cleanup only; never replay the command.
            except BaseException as cleanup_error:
                cleanup_errors.append(cleanup_error)
            finishes = [(command, outcome)]
            for name, block in blocks.items():
                truncated = bool(getattr(result, name + '_truncated', False))
                finishes.append((block, 'failed' if gaps[name] or truncated or result is None else 'completed'))
            for block, state in finishes:
                try:
                    self.finish(block, state)
                except Exception as recording_error:
                    cleanup_errors.append(recording_error)
            if cleanup_errors:
                if failure is None:
                    raise cleanup_errors[0]
                for error in cleanup_errors:
                    failure.add_note('Owned cleanup/recording failed: ' + type(error).__name__)

    def complete(self, report, result_path):
        if self.phase:
            self.finish(self.phase, 'failed' if report['status'] == 'failed' else 'completed')
            self.phase = None
        self.text('status', 'Final recipe result', json.dumps({
            'status': report['status'], 'reason_code': report['reason_code'],
            'result_path': str(result_path), 'connected': report.get('connected', False),
            'cleanup_error': report.get('cleanup_error'),
            'business_outcome': report.get('data', {}).get('business_outcome'),
            'mail_delivery': report.get('data', {}).get('mail_delivery')}, ensure_ascii=False),
            'failed' if report['status'] == 'failed' else 'completed')


def create(installation, config, *, host_id, title, reference, run_id):
    """Require the existing registered Profile/data root and a running local Web."""
    from .core import Instance, Profile
    from .storage import resolve_data_root
    from .web_settings import read_port
    instance = Instance.open(installation)
    profile = Profile._from_config(instance, config)
    if profile.name is None:
        raise ConfigError('workflow river requires a registered Profile')
    root = resolve_data_root(instance.root, required=True)
    port = read_port(instance.root, data_root=root)
    if port is None:
        raise ConfigError('workflow river requires an existing Web endpoint')
    try:
        with build_opener(ProxyHandler({}), NoRedirect()).open('http://127.0.0.1:' + str(port) + '/api/v1/setup', timeout=3) as response:
            if response.status != 200:
                raise ValueError('Web unavailable')
    except Exception as error:
        raise ConfigError('workflow river Web unavailable; no command dispatched') from error
    return WorkflowRiver(Records(root / 'console-records'), profile=profile.name,
        host_id=host_id, title=title, reference=reference,
        run_id=run_id, origin='http://localhost:' + str(port))
