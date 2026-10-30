import unittest
import json
import tempfile
from pathlib import Path
from unittest.mock import patch
from opsquery.evaluate_retrieval import development_cases, evaluate


class RetrievalEvaluationTests(unittest.TestCase):
    def test_only_dev_inputs(self):
        cases = development_cases()
        self.assertTrue(cases)
        self.assertTrue(all(set(c) == {'id', 'question', 'required_tables'} for c in cases))
        self.assertNotIn('Q18', [c['id'] for c in cases])
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp); (root/'eval').mkdir()
            base = dict(id='dev', question='question', required_tables=['teams'],
                        reference_sql='ANSWER_SENTINEL', split='dev', expected_action='query')
            (root/'eval/cases.json').write_text(json.dumps([
                base, base | dict(id='holdout', split='holdout'),
                base | dict(id='nonquery', expected_action='clarify')]))
            self.assertEqual(development_cases(root), [
                dict(id='dev', question='question', required_tables=['teams'])])

    def test_reports_failure(self):
        with patch('opsquery.evaluate_retrieval.retrieve', return_value=([], dict(
            selected_tables=[], initial_tables=[], dependency_added_tables=[], bridge_tables=[]))):
            result = evaluate()
        self.assertEqual(result['mean_required_table_recall'], 0)
        self.assertEqual(len(result['failures']), result['case_count'])
