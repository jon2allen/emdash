import os
import subprocess
import tempfile
import pytest

SCRIPT_PATH = os.path.abspath(os.path.join(os.path.dirname(__file__), "detect_emdash.py"))


def run_emdash(*args):
    return subprocess.run([sys.executable, SCRIPT_PATH, *args], capture_output=True, text=True)


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

