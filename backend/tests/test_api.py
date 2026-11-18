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

client = TestClient(main.app)

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

    def test_invalid_model_rejected(self):
        response=client.post('/chat',json={'message':'hi','model':'../../../not-a-model'})
        self.assertEqual(response.status_code,400)

if __name__=='__main__':unittest.main()
