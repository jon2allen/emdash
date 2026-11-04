import json
import os
import subprocess
import tempfile
import pytest

SCRIPT_PATH = os.path.abspath(os.path.join(os.path.dirname(__file__), "detect_emdash.py"))


def run_emdash(*args):
    return subprocess.run([sys.executable, SCRIPT_PATH, *args],
                          capture_output=True, text=True, encoding="utf-8")


import sys

def test_permissions_preserved():
    with tempfile.NamedTemporaryFile(mode="w", delete=False, suffix=".sh") as f:
        f.write("#!/bin/sh\necho '— dash'\n")
        path = f.name
    try:
        os.chmod(path, 0o755)
        res = run_emdash("--fix", path)
        assert res.returncode == 0
        mode = os.stat(path).st_mode & 0o777
        assert mode == 0o755, f"Expected 0755, got {oct(mode)}"
        with open(path, "r") as f:
            assert "echo '- dash'" in f.read()
    finally:
        os.remove(path)


def test_crlf_preserved():
    with tempfile.NamedTemporaryFile(mode="wb", delete=False, suffix=".txt") as f:
        f.write(b"Line 1: em \xe2\x80\x94 dash\r\nLine 2: normal\r\n")
        path = f.name
    try:
        res = run_emdash("--fix", path)
        assert res.returncode == 0
        with open(path, "rb") as f:
            content = f.read()
        assert b"\r\n" in content
        assert b"\xe2\x80\x94" not in content
        assert b"Line 1: em - dash\r\n" in content
    finally:
        os.remove(path)


def test_symlink_skipped():
    with tempfile.NamedTemporaryFile(mode="w", delete=False, suffix=".txt") as f:
        f.write("target with — dash\n")
        real_file = f.name
    link_path = real_file + ".symlink"
    os.symlink(real_file, link_path)
    try:
        res = run_emdash("--fix", link_path)
        assert res.returncode == 0
        assert os.path.islink(link_path)
    finally:
        os.remove(link_path)
        os.remove(real_file)


def test_quiet_mode_silence():
    with tempfile.NamedTemporaryFile(mode="w", delete=False, suffix=".txt") as f:
        f.write("Clean file without dashes\n")
        path = f.name
    try:
        res = run_emdash("-q", path)
        assert res.returncode == 0
        assert res.stdout == ""
    finally:
        os.remove(path)


def test_detection_reports_each_line_once():
    with tempfile.NamedTemporaryFile(mode="w", delete=False, suffix=".txt", encoding="utf-8") as f:
        f.write("a \u2014 b \u2010\nclean\nlast \u2013\n")
        path = f.name
    try:
        res = run_emdash(path)
        assert res.returncode == 0
        assert res.stdout.count(":1:") == 1
        assert ":3:" in res.stdout
        assert ":2:" not in res.stdout
    finally:
        os.remove(path)


def test_dry_run_implies_fix():
    with tempfile.NamedTemporaryFile(mode="w", delete=False, suffix=".txt") as f:
        f.write("File with — dash\n")
        path = f.name
    try:
        res = run_emdash("--dry-run", path)
        assert res.returncode == 0
        assert "Would replace 1 dash" in res.stdout
        with open(path, "r") as f:
            assert "—" in f.read()
    finally:
        os.remove(path)



# --density: dashes per 1,000 words
from detect_emdash import count_words, dash_density

EM = chr(0x2014)
EN = chr(0x2013)


def test_count_words_splits_on_dashes():
    assert count_words(f"one two{EM}three") == 3
    assert count_words(f"pages 10{EN}20") == 3
    # Hyphenated compounds stay one word; bare punctuation is not a word
    assert count_words("the man-of-war -- sails !") == 3
    assert count_words("") == 0


def test_dash_density_formula():
    r = dash_density(f"one two three{EM}four five six seven{EN}eight")
    assert r["words"] == 8
    assert r["em_dashes"] == 1 and r["em_dash_density"] == 125.0
    assert r["all_dashes"] == 2 and r["all_dash_density"] == 250.0


def test_dash_density_no_words():
    assert dash_density(EM)["em_dash_density"] == 0.0


def test_density_cli_json(tmp_path):
    (tmp_path / "a.txt").write_text(f"one{EM}two three four", encoding="utf-8")
    (tmp_path / "b.txt").write_text("five six seven eight", encoding="utf-8")
    res = run_emdash("--density", "--json", str(tmp_path))
    assert res.returncode == 0, res.stderr
    data = json.loads(res.stdout)
    assert len(data["files"]) == 2
    assert data["total"]["words"] == 8
    assert data["total"]["em_dashes"] == 1
    assert data["total"]["em_dash_density"] == 125.0


def test_density_does_not_modify_files(tmp_path):
    p = tmp_path / "a.txt"
    p.write_text(f"x{EM}y", encoding="utf-8")
    res = run_emdash("--density", str(p))
    assert res.returncode == 0
    assert "Em/1k" in res.stdout
    assert p.read_text(encoding="utf-8") == f"x{EM}y"


def test_density_rejects_fix():
    res = run_emdash("--density", "--fix", "x.txt")
    assert res.returncode == 2
