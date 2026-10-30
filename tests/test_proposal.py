import io
import json
import unittest
from unittest.mock import patch
from opsquery.proposal import preview, validate, openai_propose


class ProposalTests(unittest.TestCase):
    def test_shared_system_and_full_context(self):
        full = preview('spend', 'full'); retrieval = preview('spend')
        self.assertEqual(full['prompt']['system'], retrieval['prompt']['system'])
        self.assertEqual(len(full['retrieval']['selected_tables']), 8)
        self.assertIn('rule:net-billed-spend', full['retrieval']['context_ids'])

    def test_validation(self):
        valid = dict(action='query', sql='SELECT 1', explanation='example', source_ids=['table:teams'])
        self.assertEqual(validate(valid, ['table:teams']), valid)
        for change in ({'action': 'bad'}, {'sql': None}, {'sql': ''}, {'source_ids': ['unknown']},
                       {'explanation': 1}, {'source_ids': 'table:teams'}, {'extra': True}):
            with self.subTest(change=change), self.assertRaises(ValueError):
                validate(valid | change, ['table:teams'])
        for action in ('clarify', 'unsupported', 'reject'):
            validate(valid | dict(action=action, sql=None), ['table:teams'])
            with self.assertRaises(ValueError): validate(valid | dict(action=action), ['table:teams'])

    @patch.dict('os.environ', {'OPENAI_API_KEY': 'test-secret', 'OPENAI_MODEL': 'test-model'})
    def test_adapter(self):
        run = preview('spend')
        proposal = dict(action='clarify', sql=None, explanation='Which period?', source_ids=[])
        def opener(request, timeout):
            payload = json.loads(request.data)
            self.assertEqual(payload['model'], 'test-model')
            self.assertFalse(payload['store'])
            self.assertTrue(payload['text']['format']['strict'])
            self.assertEqual(request.full_url, 'https://api.openai.com/v1/responses')
            return io.StringIO(json.dumps(dict(status='completed', model='resolved-model', usage={'input_tokens': 20},
                output=[{'type': 'message', 'content': [{'type': 'output_text', 'text': json.dumps(proposal)}]}])))
        result = openai_propose(run, opener)
        self.assertEqual(result['proposal'], proposal)
        self.assertEqual(result['model'], 'resolved-model')
        self.assertGreaterEqual(result['latency_seconds'], 0)
        self.assertNotIn('test-secret', json.dumps(result))
        for data in ({'status': 'incomplete'}, {'status': 'completed', 'output': []},
                     {'status': 'completed', 'output': [{'type': 'message', 'content': [{'type': 'refusal'}]}]}):
            with self.assertRaises(ValueError):
                openai_propose(preview('x'), lambda *a, **k: io.StringIO(json.dumps(data)))

    @patch.dict('os.environ', {}, clear=True)
    def test_credentials_required_only_live(self):
        run = preview('x')
        self.assertEqual(run['status'], 'preview')
        with self.assertRaises(ValueError): openai_propose(run)
