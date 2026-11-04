import json
import os
import subprocess
import sys

import pytest

from emdash_density import measure, strip_gutenberg

SCRIPT = os.path.join(os.path.dirname(os.path.abspath(__file__)), 'emdash_density.py')
EM = '-'


def test_density_formula():
    # 2 em dashes in 8 words -> 250 per 1,000
    r = measure(f'one two three{EM}four five six seven{EM}eight')
    assert r == {'em_dashes': 2, 'words': 8, 'density': 250.0}


def test_double_hyphen_normalized_to_em_dash():
    r = measure('Call me Ishmael--some years ago--never mind')
    assert r['em_dashes'] == 2
    assert r['words'] == 8


def test_strict_counts_only_u2014():
    text = f'alpha--beta{EM}gamma'
    assert measure(text, strict=True)['em_dashes'] == 1
    assert measure(text)['em_dashes'] == 2
    # Word count is identical in both modes
    assert measure(text, strict=True)['words'] == measure(text)['words'] == 3


def test_dash_runs_count_once():
    assert measure(f'wait{EM}{EM}what')['em_dashes'] == 1
    assert measure('wait----what')['em_dashes'] == 1
    assert measure('wait-what')['em_dashes'] == 1


def test_hyphenated_compounds_and_contractions_are_one_word():
    r = measure("the man-of-war didn't sail")
    assert r['words'] == 4
    assert r['em_dashes'] == 0


def test_empty_text():
    assert measure('') == {'em_dashes': 0, 'words': 0, 'density': 0.0}


def test_gutenberg_boilerplate_stripped():
    text = ('license words--here\n'
            '*** START OF THE PROJECT GUTENBERG EBOOK TEST ***\n'
            f'body{EM}text\n'
            '*** END OF THE PROJECT GUTENBERG EBOOK TEST ***\n'
            'more--license words\n')
    assert strip_gutenberg(text).strip() == f'body{EM}text'
    assert measure(text) == {'em_dashes': 1, 'words': 2, 'density': 500.0}
    assert measure(text, keep_boilerplate=True)['em_dashes'] == 3


def test_cli_json(tmp_path):
    (tmp_path / 'a.txt').write_text(f'one{EM}two three four', encoding='utf-8')
    (tmp_path / 'skip.md').write_text(f'x{EM}y', encoding='utf-8')
    res = subprocess.run([sys.executable, SCRIPT, '--json', str(tmp_path)],
                         capture_output=True, text=True, encoding='utf-8')
    assert res.returncode == 0, res.stderr
    data = json.loads(res.stdout)
    assert [os.path.basename(f['file']) for f in data['files']] == ['a.txt']
    assert data['total'] == {'em_dashes': 1, 'words': 4, 'density': 250.0}


def test_cli_no_files(tmp_path):
    res = subprocess.run([sys.executable, SCRIPT, str(tmp_path)],
                         capture_output=True, text=True, encoding='utf-8')
    assert res.returncode == 2
