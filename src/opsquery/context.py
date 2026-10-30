"""Allowlisted context corpus, BM25, optional local embeddings, and FK completion."""
from collections import Counter, deque
from dataclasses import dataclass, asdict
from itertools import combinations
import json
import math
import re
from .warehouse import ROOT

EMBEDDING_MODEL = 'sentence-transformers/all-MiniLM-L6-v2'
DEPENDENCIES = {
    'gross-billed-spend': ['billing_items'], 'posted-credits': ['credits'],
    'net-billed-spend': ['billing_items', 'credits'],
    'successful-requests': ['requests'], 'failure-percentage': ['requests'],
    'latency': ['requests'], 'token-counts': ['requests'],
    'budgets': ['budgets', 'billing_items'], 'team-ownership': ['services', 'teams'],
}


def slug(text):
    return re.sub(r'[^a-z0-9]+', '-', text.lower()).strip('-')


def tokens(text):
    return re.findall(r'[a-z0-9]+', text.lower().replace('_', ' '))


@dataclass(frozen=True)
class Document:
    id: str
    text: str
    tables: tuple = ()
    dependencies: tuple = ()
    source: str = ''


def corpus(root=ROOT):
    """Read only these three sources; never glob eval/ or reports/."""
    catalog = json.loads((root / 'docs/catalog.json').read_text())
    schemas = {re.search(r'CREATE TABLE (\w+)', s)[1]: s.strip() + ';'
               for s in (root / 'src/opsquery/schema.sql').read_text().split(';') if s.strip()}
    docs = []
    for table in catalog:
        name = table['table']
        docs.append(Document('table:' + name,
                             json.dumps(table, sort_keys=True) + '\n' + schemas[name],
                             (name,), source='docs/catalog.json + src/opsquery/schema.sql'))
    rules = (root / 'docs/business_rules.md').read_text()
    for line in rules.splitlines():
        if line.startswith('- '):
            label = slug(line[2:].split(':', 1)[0])
            docs.append(Document('rule:' + label, line[2:],
                                 dependencies=tuple(DEPENDENCIES.get(label, ())),
                                 source='docs/business_rules.md'))
    preamble, rest = rules.split('## Join rules', 1)
    docs.append(Document('rules:general', preamble.split('\n- ', 1)[0], source='docs/business_rules.md'))
    docs.append(Document('rules:joins', 'Join rules' + rest, source='docs/business_rules.md'))
    return docs


def bm25(question, docs):
    counts = [Counter(tokens(d.text)) for d in docs]
    avg = sum(map(lambda c: sum(c.values()), counts)) / len(counts)
    scores = []
    for d, count in zip(docs, counts):
        score = 0.0
        for term in set(tokens(question)):
            df = sum(term in c for c in counts)
            freq = count[term]
            score += math.log(1 + (len(docs) - df + .5) / (df + .5)) * (freq * 2.5) / (
                freq + 1.5 * (.25 + .75 * sum(count.values()) / avg))
        if score > 0:
            scores.append((d.id, score))
    return sorted(scores, key=lambda x: (-x[1], x[0]))


def semantic(question, docs):
    # Imported only on explicit opt-in; BM25 requires no model or extra package.
    from sentence_transformers import SentenceTransformer
    model = SentenceTransformer(EMBEDDING_MODEL)
    vectors = model.encode([question] + [d.text for d in docs], normalize_embeddings=True)
    return sorted([(d.id, float(vectors[0] @ vector)) for d, vector in zip(docs, vectors[1:])],
                  key=lambda x: (-x[1], x[0]))


def rrf(*rankings, k=60):
    scores = Counter()
    for ranking in rankings:
        for rank, (doc_id, _) in enumerate(ranking, 1):
            scores[doc_id] += 1 / (k + rank)
    return sorted(scores.items(), key=lambda x: (-x[1], x[0]))


def expand(initial, dependencies, catalog):
    initial = set(initial)
    dependency_added = set(dependencies) - initial
    selected = initial | dependency_added
    graph = {t['table']: set() for t in catalog}
    for t in catalog:
        for key in t['keys']:
            target = key['references_table']
            if target:
                graph[t['table']].add(target)
                graph[target].add(t['table'])
    bridges = set()
    for start, end in combinations(sorted(selected), 2):
        queue = deque([(start, [start])]); seen = {start}
        while queue:
            node, path = queue.popleft()
            if node == end:
                bridges.update(set(path) - selected)
                break
            for nxt in sorted(graph[node] - seen):
                seen.add(nxt); queue.append((nxt, path + [nxt]))
    return {'initial_tables': sorted(initial), 'dependency_added_tables': sorted(dependency_added),
            'bridge_tables': sorted(bridges), 'selected_tables': sorted(selected | bridges)}


def retrieve(question, method='bm25', top_k=5, root=ROOT):
    if method not in ('bm25', 'hybrid') or top_k < 1:
        raise ValueError('method must be bm25/hybrid and top_k must be positive')
    docs = corpus(root); by_id = {d.id: d for d in docs}
    lexical = bm25(question, docs)
    semantic_ranking = semantic(question, docs) if method == 'hybrid' else []
    ranking = rrf(lexical, semantic_ranking) if method == 'hybrid' else lexical
    hits = [by_id[i] for i, _ in ranking[:top_k]]
    initial = {t for d in hits for t in d.tables}
    dependencies = {t for d in hits for t in d.dependencies}
    # Explicit grouping intent supplies team dependencies even if ownership rule misses top-k.
    if set(tokens(question)) & {'team', 'teams'}:
        dependencies.update(('services', 'teams'))
    details = expand(initial, dependencies, json.loads((root / 'docs/catalog.json').read_text()))
    ids = {d.id for d in hits} | {'table:' + t for t in details['selected_tables']}
    ids.update(('rules:general', 'rules:joins'))
    context = [d for d in docs if d.id in ids]
    details.update(method=method, top_k=top_k, lexical_ranking=lexical,
                   semantic_ranking=semantic_ranking, ranking=ranking,
                   retrieved_ids=[d.id for d in hits], context_ids=[d.id for d in context],
                   embedding_model=EMBEDDING_MODEL if method == 'hybrid' else None)
    return context, details
