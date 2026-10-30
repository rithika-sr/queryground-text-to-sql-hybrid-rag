import json
import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch
from opsquery.context import corpus, expand, retrieve, bm25, rrf
from opsquery.warehouse import ROOT


class ContextTests(unittest.TestCase):
    def test_bridge(self):
        catalog = json.loads((ROOT/'docs/catalog.json').read_text())
        result = expand(['credits', 'teams'], [], catalog)
        self.assertEqual(result['bridge_tables'], ['billing_items', 'services'])
        self.assertEqual(result['dependency_added_tables'], [])

    def test_metric_dependency(self):
        docs = corpus()
        rule = next(d for d in docs if d.id == 'rule:net-billed-spend')
        self.assertEqual(set(rule.dependencies), {'billing_items', 'credits'})
        with patch('opsquery.context.bm25', return_value=[(rule.id, 1)]):
            _, result = retrieve('net billed spend by team', top_k=1)
        self.assertEqual(result['dependency_added_tables'], ['billing_items', 'credits', 'services', 'teams'])

    def test_corpus_allowlist(self):
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            for name in ('docs/catalog.json', 'docs/business_rules.md', 'src/opsquery/schema.sql'):
                target = root/name; target.parent.mkdir(parents=True, exist_ok=True)
                target.write_text((ROOT/name).read_text())
            before = corpus(root)
            (root/'eval').mkdir(); (root/'reports').mkdir()
            (root/'eval/cases.json').write_text('HELD_OUT_REFERENCE_SQL_SENTINEL')
            (root/'reports/reference_answers.json').write_text('SECRET_ANSWER_SENTINEL')
            self.assertEqual(before, corpus(root))
            self.assertEqual(len({d.id for d in before}), len(before))

    def test_ranking_and_hybrid(self):
        docs = corpus()
        self.assertTrue(bm25('net billed spend', docs))
        self.assertEqual(rrf([('a', 10)], [('b', 1), ('a', .1)])[0][0], 'a')
        with patch('opsquery.context.semantic', return_value=[('table:credits', 1)]):
            _, result = retrieve('credits', method='hybrid')
        self.assertTrue(result['semantic_ranking'])
        with self.assertRaises(ValueError): retrieve('x', top_k=0)
