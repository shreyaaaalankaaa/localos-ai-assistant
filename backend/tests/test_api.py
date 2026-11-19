"""Contract tests. Do not require local Ollama or a physical GPU."""
import os
import sys
import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch, Mock

from fastapi.testclient import TestClient

BACKEND = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(BACKEND))
TEST_DATA = tempfile.TemporaryDirectory(prefix='jarvis_api_test_')
os.environ['LOCALOS_DATA_DIR'] = TEST_DATA.name
import main  # noqa: E402

client = TestClient(main.app, headers={'x-jarvis-token': main.SESSION_TOKEN})
anonymous = TestClient(main.app)

class ApiTests(unittest.TestCase):
    def test_status_when_ollama_unavailable(self):
        with patch.object(main, '_ollama_models', return_value=(False, [])):
            data = client.get('/api/status').json()
        self.assertTrue(data['backend_online'])
        self.assertFalse(data['models_ready'])
        self.assertFalse(data['ollama_online'])

    def test_system_reports_real_numbers_not_fake_gpu(self):
        result = client.get('/api/system')
        self.assertEqual(result.status_code, 200)
        value = result.json()
        self.assertTrue(0 <= value['cpu'] <= 100)
        self.assertTrue(0 <= value['ram'] <= 100)
        self.assertTrue(value['gpu'] is None or 0 <= value['gpu'] <= 100)

    def test_history_get_clear(self):
        main.clear_history()
        main.add_to_history('user', 'Hello')
        self.assertEqual(client.get('/api/history').json()['messages'][0]['content'], 'Hello')
        self.assertEqual(client.delete('/api/history').status_code, 200)
        self.assertEqual(client.get('/api/history').json()['messages'], [])

    def test_memory_notes_and_profile_persist(self):
        self.assertEqual(client.post('/api/memory', json={'fact': 'Prefers monochrome'}).status_code, 200)
        self.assertIn('Prefers monochrome', client.get('/api/memory').json()['memory'])
        self.assertEqual(client.post('/api/notes', json={'title':'Example','content':'Actual content'}).status_code, 200)
        self.assertIn('Actual content', str(client.get('/api/notes').json()['notes']))
        self.assertEqual(client.patch('/api/profile', json={'preferred_name':'Demo'}).json()['preferred_name'],'Demo')
        self.assertEqual(client.patch('/api/profile', json={'preferred_name':''}).json()['preferred_name'],'')

    def test_accessible_files_and_denied_outside(self):
        result = client.get('/api/files', params={'folder':'frontend'})
        self.assertEqual(result.status_code,200)
        self.assertTrue(any(f['name']=='package.json' for f in result.json()['files']))
        self.assertEqual(client.get('/api/files', params={'folder':'/etc'}).status_code,403)
        self.assertEqual(client.get('/api/files/read', params={'path':'/etc/passwd'}).status_code,403)

    def test_apps_allowlist(self):
        self.assertEqual(client.post('/api/apps/launch', json={'name':'danger','kind':'app'}).status_code,400)
        self.assertTrue(isinstance(client.get('/api/apps').json()['apps'],list))

    def test_chat_uses_selected_model(self):
        main.clear_history()
        response = Mock()
        response.json.return_value={'message':{'content':'Hello from local model'}}
        with patch.object(main.requests, 'post', return_value=response) as post:
            result = client.post('/chat', json={'message':'hi there','mode':'coding','model':'qwen2.5-coder:7b'})
        self.assertEqual(result.status_code,200)
        self.assertEqual(result.json()['model_used'],'qwen2.5-coder:7b')
        self.assertEqual(post.call_args.kwargs['json']['model'],'qwen2.5-coder:7b')
        self.assertEqual(len(client.get('/api/history').json()['messages']),2)

    def test_requests_without_token_are_rejected(self):
        self.assertEqual(anonymous.get('/api/files/read', params={'path': str(BACKEND / 'main.py')}).status_code, 401)
        self.assertEqual(anonymous.post('/tool', json={'tool_name': 'list_notes', 'params': {}}).status_code, 401)
        wrong = {'x-jarvis-token': 'not-the-token'}
        self.assertEqual(anonymous.get('/api/status', headers=wrong).status_code, 401)

    def test_null_origin_page_cannot_use_api_without_token(self):
        # A sandboxed iframe on any website sends Origin: null. CORS allows that
        # origin for the packaged app, so the token is what must stop it.
        result = anonymous.get('/api/files', params={'folder': 'project'}, headers={'Origin': 'null'})
        self.assertEqual(result.status_code, 401)

    def test_health_check_is_public_and_preflight_passes(self):
        self.assertEqual(anonymous.get('/').status_code, 200)
        preflight = anonymous.options('/chat', headers={
            'Origin': 'http://127.0.0.1:5173',
            'Access-Control-Request-Method': 'POST',
            'Access-Control-Request-Headers': 'content-type,x-jarvis-token',
        })
        self.assertEqual(preflight.status_code, 200)

    def test_token_file_is_created_owner_only(self):
        token_path = Path(TEST_DATA.name) / '.jarvis_token'
        self.assertTrue(token_path.exists())
        self.assertEqual(token_path.read_text().strip(), main.SESSION_TOKEN)
        if os.name != 'nt':
            self.assertEqual(token_path.stat().st_mode & 0o777, 0o600)

    def test_app_aliases_shown_once(self):
        apps = client.get('/api/apps').json()['apps']
        self.assertEqual(len(apps), len(set(apps)))
        self.assertNotIn('calc', apps)
        self.assertIn('calculator', apps)

    def test_ollama_error_is_friendly(self):
        with patch.object(main.requests, 'post', side_effect=main.requests.ConnectionError('refused')):
            data = client.post('/chat', json={'message': 'tell me a joke please'}).json()
        self.assertEqual(data['model_used'], 'ollama-error')
        self.assertNotIn('HTTPConnectionPool', data['reply'])
        self.assertIn('refused', data['error_detail'])

    def test_invalid_model_rejected(self):
        response=client.post('/chat',json={'message':'hi','model':'../../../not-a-model'})
        self.assertEqual(response.status_code,400)

if __name__=='__main__':unittest.main()
