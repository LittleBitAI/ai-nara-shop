"""Pilot ledger must identify episodes and avoid counting copied prior results twice."""
import json
from pathlib import Path
import tempfile
from unittest.mock import patch

from tools import build_measurements as builder


def test_pilot_episodes_use_recorded_code_and_skip_archive_duplicates():
    with tempfile.TemporaryDirectory() as directory:
        root = Path(directory)
        (root/'docs').mkdir()
        (root/'docs/runs.md').write_text('', encoding='utf-8')
        (root/'reports').mkdir()
        (root/'reports/submissions.json').write_text('{"submissions": []}', encoding='utf-8')
        for run, canonical, episodes in [('first', ['episode-1'], [1]), ('second', ['episode-2'], [1, 2])]:
            base = root/'reports/runs'/run
            base.mkdir(parents=True)
            (base/'manifest.json').write_text(json.dumps({'canonical_episodes': canonical,
                'registered_at': '2026-09-21T00:00:00Z'}), encoding='utf-8')
            for ep in episodes:
                path = base/f'pilot/episode-{ep}/v18/on-score'
                path.mkdir(parents=True)
                (path/'metrics.json').write_text('{"macro_f1": 0.6}', encoding='utf-8')
                (path.parent.parent/'contract.json').write_text(
                    '{"source_commit": "44f5e4b8c9a9d8b7b0e83b51f546c04be5e3316e"}', encoding='utf-8')
        with patch.object(builder, 'ROOT', root):
            rows = builder.collect()
        assert len(rows) == 2
        assert {r['id'] for r in rows} == {'first/episode-1/v18/on', 'second/episode-2/v18/on'}
        assert {r['code'] for r in rows} == {'44f5e4b'}
