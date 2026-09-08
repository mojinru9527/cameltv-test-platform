"""Run inside a disposable runner image: real DSH parent plus browser workload.

The LLM is a local deterministic HTTP fixture, so no external AI credentials or
paid calls are used. This measures runtime overlap, not a production team task.
"""
import json
import argparse
import os
from pathlib import Path
import tempfile
import threading
from concurrent.futures import ThreadPoolExecutor
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--members', type=int, choices=(0, 6), default=0)
    parser.add_argument('--include-embedding', action='store_true')
    args = parser.parse_args()
    requested = threading.Event()
    finished = threading.Event()
    members_seen = set()
    member_guard = threading.Lock()

    class CompletionFixture(BaseHTTPRequestHandler):
        def log_message(self, *args):
            pass

        def do_POST(self):
            body = json.loads(self.rfile.read(int(self.headers['Content-Length'])))
            self.server.tools = [*getattr(self.server, 'tools', []), *body.get('tools', [])]
            tool_calls = []
            if args.members and body.get('tools'):
                context = json.dumps([m.get('content') for m in body.get('messages', [])
                                      if m.get('role') in ('system', 'user')])
                member = next((i for i in range(args.members) if f'CAPACITY_MEMBER_{i}' in context), None)
                if member is not None:
                    with member_guard:
                        members_seen.add(member)
                        if len(members_seen) == args.members:
                            requested.set()
                    finished.wait(300)
                else:
                    called = [c.get('function', {}).get('name') for m in body.get('messages', [])
                              for c in m.get('tool_calls', [])]
                    planned = []
                    if 'agent_teams_create' not in called:
                        planned = [('agent_teams_create', {'name': 'capacity-fixture', 'approval': 'automatic'})]
                    elif 'agent_teams_add_member' not in called:
                        planned = [('agent_teams_add_member', {'name': f'member-{i}', 'role': 'capacity-test',
                                    'executionPrompt': f'CAPACITY_MEMBER_{i}: Wait for the local capacity test then reply done.'})
                                   for i in range(args.members)]
                    elif 'agent_teams_send_message' not in called:
                        planned = [('agent_teams_send_message', {'to': f'member-{i}',
                                    'content': f'CAPACITY_MEMBER_{i}: perform the isolated runtime capacity check.'})
                                   for i in range(args.members)]
                    else:
                        finished.wait(300)
                    tool_calls = [{'id': f'capacity-{len(called)}-{i}', 'type': 'function',
                                   'function': {'name': name, 'arguments': json.dumps(arguments)}}
                                  for i, (name, arguments) in enumerate(planned)]
            elif body.get('tools'):
                requested.set()
                finished.wait(300)
            self.send_response(200)
            if body.get('stream'):
                self.send_header('Content-Type', 'text/event-stream')
                self.end_headers()
                response_delta = {'role': 'assistant', 'content': 'Capacity smoke complete.'}
                if tool_calls:
                    response_delta = {'role': 'assistant', 'tool_calls': [dict(index=i, **call) for i, call in enumerate(tool_calls)]}
                for delta, reason in ((response_delta, None), ({}, 'tool_calls' if tool_calls else 'stop')):
                    chunk = {'id': 'capacity-fixture', 'object': 'chat.completion.chunk',
                             'created': 1, 'model': body.get('model', 'capacity'),
                             'choices': [{'index': 0, 'delta': delta, 'finish_reason': reason}]}
                    self.wfile.write(('data: ' + json.dumps(chunk) + '\n\n').encode())
                self.wfile.write(b'data: [DONE]\n\n')
            else:
                self.send_header('Content-Type', 'application/json')
                self.end_headers()
                self.wfile.write(json.dumps({'id': 'capacity-fixture', 'object': 'chat.completion',
                    'created': 1, 'model': body.get('model', 'capacity'),
                    'choices': [{'index': 0, 'message': {'role': 'assistant', 'content': 'Capacity smoke complete.',
                                                       **({'tool_calls': tool_calls} if tool_calls else {})},
                                 'finish_reason': 'tool_calls' if tool_calls else 'stop'}],
                    'usage': {'prompt_tokens': 1, 'completion_tokens': 1, 'total_tokens': 2}}).encode())
            self.wfile.flush()

    server = ThreadingHTTPServer(('127.0.0.1', 0), CompletionFixture)
    threading.Thread(target=server.serve_forever, daemon=True).start()
    with tempfile.TemporaryDirectory(prefix='dsh-capacity-') as temporary:
        os.environ.update({
            'WORKER_EXECUTION_ENABLED': 'true', 'DSH_ENABLED': 'true', 'DSH_RUNTIME': 'node',
            'DSH_API_KEY': 'local-fixture-only', 'DSH_BASE_URL': f'http://127.0.0.1:{server.server_port}/v1',
            'DSH_HARNESS_PATH': '/usr/lib/node_modules/@deepseek-ai/dsh/lib/bin.js',
            'DSH_SESSION_ROOT': temporary, 'HEAVY_TASK_BUDGET_ENABLED': 'true',
            'HEAVY_TASK_BUDGET_CAPACITY': '1', 'ORCHESTRATION_BUDGET_CAPACITY': '1',
            'HEAVY_TASK_BUDGET_DIR': temporary + '/budget',
        })
        from app.core.resource_budget import configured_budget
        from app.services.dsh.dsh_runner import run_dsh_task
        from playwright.sync_api import sync_playwright

        def memory():
            return {key: int((Path('/sys/fs/cgroup') / key).read_text())
                    for key in ('memory.current', 'memory.peak')}

        snapshots = {'before_dsh': memory()}
        try:
            with ThreadPoolExecutor(max_workers=1) as executor:
                pending = executor.submit(run_dsh_task, 'Run the isolated local capacity fixture.',
                                          mode='team', timeout=300)
                if not requested.wait(40):
                    finished.set()
                    result = pending.result(timeout=60)
                    raise RuntimeError(f'Real DSH did not reach expected fixture state; members={sorted(members_seen)}: '
                                       + result.error[-1500:] + result.final_response[-2000:])
                snapshots['dsh_waiting'] = memory()
                orchestration = configured_budget('orchestration').try_acquire('probe', 'second-parent')
                if orchestration is not None:
                    orchestration.release()
                    raise AssertionError('DSH parent did not retain orchestration admission')
                with configured_budget().wait('browser', 'dsh-overlap', timeout=5):
                    with sync_playwright() as playwright:
                        browser = playwright.chromium.launch(headless=True, args=['--no-sandbox'])
                        try:
                            page = browser.new_page()
                            page.set_content('<h1>real browser while DSH parent waits</h1>')
                            assert page.locator('h1').inner_text() == 'real browser while DSH parent waits'
                            snapshots['dsh_and_browser'] = memory()
                        finally:
                            browser.close()
                if args.include_embedding:
                    from app.services.knowledge.embedding_service import EmbeddingService
                    service = EmbeddingService(cache_dir=temporary + '/model-cache')
                    vectors = service.embed(['isolated mixed workload capacity verification'] * 16)
                    assert vectors is not None and vectors.shape == (16, 512)
                    assert service._model is None
                    assert not pending.done(), 'DSH must remain live during embedding'
                    snapshots['dsh_and_embedding'] = memory()
                finished.set()
                result = pending.result(timeout=60)
                assert result.exit_code == 0, result.error[-1500:]
                snapshots['after_dsh'] = memory()
                with configured_budget('orchestration').wait('probe', 'after-parent', timeout=5):
                    pass
            print(json.dumps({'result': 'passed', 'memory': snapshots,
                              'real_runtime_profile': 'agent-team', 'llm': 'local-fixture',
                              'spawned_team_members': len(members_seen), 'production_sizing_proven': False}))
            if os.environ.get('DSH_CAPACITY_DUMP_TOOLS') == '1':
                print(json.dumps({'tool_names': [tool.get('function', {}).get('name')
                                                 for tool in getattr(server, 'tools', [])],
                                  'team_tool_schemas': [tool for tool in getattr(server, 'tools', [])
                                  if 'team' in tool.get('function', {}).get('name', '')]}))
        finally:
            finished.set()
            server.shutdown()
            server.server_close()


if __name__ == '__main__':
    main()
