#!/usr/bin/env python3
import argparse
import json
import os
import shutil
import stat
import subprocess
import sys
import threading

# Comprehensive target dash variants to detect and replace
DASH_CATEGORIES = {
    'EM_DASH': ('—', 'U+2014', r'\u2014'),
    'EN_DASH': ('–', 'U+2013', r'\u2013'),
    'FIGURE_DASH': ('‒', 'U+2012', r'\u2012'),
    'HORIZONTAL_BAR': ('―', 'U+2015', r'\u2015'),
    'TWO_EM_DASH': ('⸺', 'U+2E3A', r'\u2E3A'),
    'THREE_EM_DASH': ('⸻', 'U+2E3B', r'\u2E3B'),
    'MINUS_SIGN': ('−', 'U+2212', r'\u2212'),
    'HYPHEN': ('‐', 'U+2010', r'\u2010'),
    'NON_BREAKING_HYPHEN': ('‑', 'U+2011', r'\u2011'),
    'HYPHEN_BULLET': ('⁃', 'U+2043', r'\u2043'),
    'SOFT_HYPHEN': ('\u00ad', 'U+00AD', r'\u00AD'),
    'PRESENTATION_EM_DASH': ('︱', 'U+FE31', r'\uFE31'),
    'PRESENTATION_EN_DASH': ('︲', 'U+FE32', r'\uFE32'),
    'SMALL_EM_DASH': ('﹘', 'U+FE58', r'\uFE58'),
    'SMALL_HYPHEN_MINUS': ('﹣', 'U+FE63', r'\uFE63'),
    'FULLWIDTH_HYPHEN_MINUS': ('－', 'U+FF0D', r'\uFF0D'),
}

CHAR_TO_CATEGORY = {data[0]: (cat, data[1], data[2]) for cat, data in DASH_CATEGORIES.items()}
TARGET_CHARS = set(CHAR_TO_CATEGORY.keys())
DEFAULT_IGNORE_DIRS = {'.git', '.venv', 'venv', '__pycache__', 'node_modules', '.idea', '.vscode'}

# Replacement character: Regular ASCII Hyphen-Minus U+002D
REPLACEMENT_CHAR = '-'
REPLACEMENT_UNICODE = 'U+002D'

# File argument meaning stdin (a file really named '-' can be passed as ./-)
STDIN_TARGET = '-'

# Invisible characters are deleted: a visible '-' would change the rendered text
REMOVE_CHARS = {'\u00ad'}


def is_self_script(filepath: str) -> bool:
    """Check if the given filepath is actually this exact script running on disk."""
    try:
        this_file = os.path.realpath(__file__)
        target_file = os.path.realpath(filepath)
        return os.path.samefile(this_file, target_file)
    except (OSError, ValueError):
        return False


def categorize_dashes(text: str) -> dict:
    """Categorize and count specific dash variants found in text.
    Returns a dict of category -> {count, char, unicode_format, unicode_escape}.
    Does NOT modify the input text.
    """
    intersections = TARGET_CHARS.intersection(text)
    if not intersections:
        return {}

    found_categories = {}
    for dash_char in intersections:
        category, unicode_format, unicode_escape = CHAR_TO_CATEGORY[dash_char]
        found_categories[category] = {
            'count': text.count(dash_char),
            'char': dash_char,
            'unicode_format': unicode_format,
            'unicode_escape': unicode_escape,
        }
    return found_categories


def replace_dashes_in_text(text: str) -> tuple:
    """Replace target dash variants with ASCII hyphen-minus ('-'), deleting REMOVE_CHARS.
    Returns (new_text, replacement_count).
    """
    total_replaced = 0
    new_chars = []
    for ch in text:
        if ch in REMOVE_CHARS:
            total_replaced += 1
        elif ch in TARGET_CHARS:
            new_chars.append(REPLACEMENT_CHAR)
            total_replaced += 1
        else:
            new_chars.append(ch)
    return ''.join(new_chars), total_replaced


def process_file(filepath: str, verbose: bool = True, fix: bool = False, dry_run: bool = False, backup: bool = False) -> tuple:
    """Scan and optionally fix dash characters in a file.
    Returns (dash_found, file_summary, replacements_made, is_excluded, file_error).
    """
    dash_found = False
    file_summary = {}
    replacements_made = 0
    file_error = False

    # 1. Skip symlinks to avoid replacing links with target regular files
    if os.path.islink(filepath):
        if verbose:
            print(f"Skipping symlink: {filepath}", file=sys.stderr)
        return False, {}, 0, False, False

    is_excluded = is_self_script(filepath)

    try:
        # Open with newline='' to preserve original CRLF / LF line endings
        with open(filepath, 'r', encoding='utf-8', newline='') as f:
            content = f.read()

        # Binary check: null bytes usually indicate non-text files
        if '\x00' in content:
            if verbose:
                print(f"Skipping binary file: {filepath}", file=sys.stderr)
            return False, {}, 0, False, False

        # Split preserving newlines to keep exact line numbering aligned
        lines = content.split('\n')
        for line_num, line in enumerate(lines, 1):
            categories = categorize_dashes(line)
            if categories:
                if verbose:
                    prefix = "[SELF-DEFINITION] " if is_excluded else ""
                    display_line = line.rstrip('\r')
                    print(f"{prefix}{filepath}:{line_num}: {display_line}")
                dash_found = True

                for category, data in categories.items():
                    if category not in file_summary:
                        file_summary[category] = {
                            'count': 0,
                            'char': data['char'],
                            'unicode_format': data['unicode_format'],
                            'unicode_escape': data['unicode_escape'],
                        }
                    file_summary[category]['count'] += data['count']

        if fix and dash_found:
            if is_excluded:
                if verbose:
                    print(f"[SKIPPED FIX] Excluded self script from replacement: {filepath}")
            else:
                new_content, count_to_replace = replace_dashes_in_text(content)
                if count_to_replace > 0:
                    if dry_run:
                        replacements_made = count_to_replace
                        if verbose:
                            print(f"[DRY-RUN] Would replace {count_to_replace} dash(es) with '-' ({REPLACEMENT_UNICODE}) in: {filepath}")
                    else:
                        if backup:
                            shutil.copy2(filepath, f"{filepath}.bak")

                        tmp_filepath = f"{filepath}.tmp_dash_fix"
                        try:
                            # Preserve line endings
                            with open(tmp_filepath, 'w', encoding='utf-8', newline='') as f_out:
                                f_out.write(new_content)

                            # Preserve exact POSIX permissions / execute bit
                            shutil.copymode(filepath, tmp_filepath)

                            # Atomic rename
                            os.replace(tmp_filepath, filepath)
                            replacements_made = count_to_replace

                            if verbose:
                                print(f"[FIXED] Replaced {replacements_made} dash(es) with '-' ({REPLACEMENT_UNICODE}) in: {filepath}")
                        except Exception as write_err:
                            if os.path.exists(tmp_filepath):
                                try:
                                    os.remove(tmp_filepath)
                                except OSError:
                                    pass
                            raise write_err

    except UnicodeDecodeError:
        if verbose:
            print(f"Skipping non-UTF-8 / binary file: {filepath}", file=sys.stderr)
    except Exception as e:
        print(f"Error processing {filepath}: {e}", file=sys.stderr)
        file_error = True

    return dash_found, file_summary, replacements_made, is_excluded, file_error


def stdin_has_data() -> bool:
    """Return True if stdin is a pipe or redirected file, not a terminal or /dev/null."""
    try:
        mode = os.fstat(sys.stdin.fileno()).st_mode
    except (OSError, ValueError):
        return False
    return stat.S_ISFIFO(mode) or stat.S_ISREG(mode)


def process_stdin(output, verbose: bool = True, fix: bool = False, dry_run: bool = False) -> tuple:
    """Scan stdin; with fix (and not dry_run) write the cleaned text to output as a filter.
    Returns the same tuple as process_file.
    """
    # surrogateescape round-trips any non-UTF-8 bytes unchanged
    content = sys.stdin.buffer.read().decode('utf-8', 'surrogateescape')
    file_summary = {}
    for line_num, line in enumerate(content.split('\n'), 1):
        categories = categorize_dashes(line)
        if categories and verbose:
            display_line = line.rstrip('\r').encode('utf-8', 'surrogateescape').decode('utf-8', 'replace')
            print(f"<stdin>:{line_num}: {display_line}")
        for category, data in categories.items():
            if category in file_summary:
                file_summary[category]['count'] += data['count']
            else:
                file_summary[category] = dict(data)

    new_content, replacements_made = replace_dashes_in_text(content)
    if not fix:
        replacements_made = 0
    elif not dry_run:
        output.write(new_content.encode('utf-8', 'surrogateescape'))
        output.flush()
    return bool(file_summary), file_summary, replacements_made, False, False


def scan_directory(path: str, recursive: bool = False):
    """Yield file paths from directory, optionally recursively, ignoring VCS/virtualenvs."""
    if recursive:
        for root, dirs, files in os.walk(path):
            dirs[:] = [d for d in dirs if not d.startswith('.') and d not in DEFAULT_IGNORE_DIRS]
            for f in files:
                if not f.startswith('.'):
                    yield os.path.join(root, f)
    else:
        try:
            for f in os.listdir(path):
                if f.startswith('.'):
                    continue
                full = os.path.join(path, f)
                if os.path.isfile(full):
                    yield full
        except OSError as e:
            print(f"Error accessing directory {path}: {e}", file=sys.stderr)


def resolve_targets(paths: list, recursive: bool = False):
    """Resolve file or directory arguments into a stream of target file paths."""
    if not paths:
        yield from scan_directory('.', recursive=recursive)
        return

    for path in paths:
        if path == STDIN_TARGET:
            yield path
        elif os.path.islink(path):
            continue
        elif os.path.isdir(path):
            yield from scan_directory(path, recursive=recursive)
        elif os.path.isfile(path):
            yield path
        else:
            print(f"Target not found: {path}", file=sys.stderr)


def _cat_file_content(stream, spec: bytes):
    """Read one `git cat-file --batch` response for the given request spec.
    Returns the blob content, or None when the object is missing.
    Requests are NUL-terminated (paths may contain newlines), but responses
    stay LF-framed: "<oid> SP <type> SP <size> LF <content> LF". The size in
    the header makes the content unambiguous regardless of embedded newlines.
    """
    first = stream.read(1)
    if not first:
        raise EOFError('cat-file stream ended early')
    if first == b':':
        # Missing object: the spec is echoed verbatim ("<spec> missing\\n")
        # and may itself contain newlines, so consume by known length.
        stream.read(len(spec) + 8)
        return None
    header = first
    while True:
        b = stream.read(1)
        if not b:
            raise EOFError('cat-file stream ended early')
        if b == b'\n':
            break
        header += b
    _oid, _type, size_str = header.split(b' ', 2)
    size = int(size_str)
    content = stream.read(size)
    if len(content) != size:
        raise EOFError('cat-file stream ended early')
    stream.read(1)  # trailing newline after the content
    return content


def scan_staged() -> int:
    """Hook mode: read NUL-delimited staged paths from stdin, scan the staged
    blob of each in a single batched pass, and write the paths whose blob
    contains Unicode dashes (NUL-delimited) to stdout.
    Exit status: 0 = clean, 1 = dashes found, 2 = internal error.
    """
    paths = [p for p in sys.stdin.buffer.read().split(b'\x00') if p]
    files = []
    for p in paths:
        fs_path = os.fsdecode(p)
        if os.path.isfile(fs_path) and not os.path.islink(fs_path):
            files.append(p)
    if not files:
        return 0

    # One git process: exempt paths are filtered by the -emdash attribute
    try:
        attr = subprocess.run(
            ['git', 'check-attr', '-z', '--stdin', 'emdash'],
            input=b'\x00'.join(files) + b'\x00',
            stdout=subprocess.PIPE, stderr=subprocess.PIPE)
    except OSError as e:
        print(f"[emdash pre-commit] cannot run git check-attr: {e}", file=sys.stderr)
        return 2
    if attr.returncode != 0:
        print(f"[emdash pre-commit] git check-attr failed: "
              f"{attr.stderr.decode('utf-8', 'replace').strip()}", file=sys.stderr)
        return 2

    # Records are "<path> NUL <attr> NUL <value> NUL"
    fields = attr.stdout.split(b'\x00')
    if fields and fields[-1] == b'':
        fields.pop()
    if len(fields) % 3:
        print('[emdash pre-commit] unexpected check-attr output layout', file=sys.stderr)
        return 2
    candidates = [fields[i] for i in range(0, len(fields), 3) if fields[i + 2] != b'unset']
    if not candidates:
        return 0

    # One git process: fetch every staged blob at once
    specs = [b':' + p for p in candidates]
    try:
        proc = subprocess.Popen(['git', 'cat-file', '--batch', '-z'],
                                 stdin=subprocess.PIPE, stdout=subprocess.PIPE)
    except OSError as e:
        print(f"[emdash pre-commit] cannot run git cat-file: {e}", file=sys.stderr)
        return 2

    # Feed requests from a thread so a large batch cannot deadlock on pipe
    # buffers while git is writing responses back
    def feed():
        try:
            for s in specs:
                proc.stdin.write(s + b'\x00')
            proc.stdin.close()
        except OSError:
            pass

    writer = threading.Thread(target=feed)
    writer.start()
    dirty = []
    try:
        for spec in specs:
            content = _cat_file_content(proc.stdout, spec)
            if content is None:
                continue
            if b'\x00' in content:
                continue  # binary
            text = content.decode('utf-8', 'surrogateescape')
            if TARGET_CHARS.intersection(text):
                dirty.append(spec[1:])
    except (EOFError, ValueError) as e:
        print(f"[emdash pre-commit] failed to parse cat-file output: {e}", file=sys.stderr)
        return 2
    finally:
        writer.join()
        proc.stdout.close()
        proc.wait()

    if dirty:
        sys.stdout.buffer.write(b'\x00'.join(dirty) + b'\x00')
        sys.stdout.buffer.flush()
        return 1
    return 0


def main():
    parser = argparse.ArgumentParser(description='Detect and replace Unicode dash/emdash characters in files')
    parser.add_argument('files', nargs='*', help="Files or directories to scan, or '-' for stdin (default: piped stdin, else current directory)")
    parser.add_argument('-r', '--recursive', action='store_true', help='Scan directories recursively')
    parser.add_argument('--fix', action='store_true', help=f"Replace detected Unicode dashes with regular '-' ({REPLACEMENT_UNICODE})")
    parser.add_argument('--dry-run', action='store_true', help='Simulate replacements with --fix without altering files')
    parser.add_argument('--backup', action='store_true', help='Create .bak backup files before modifying with --fix')
    parser.add_argument('--json', action='store_true', help='Output summary strictly as JSON to stdout')
    parser.add_argument('-q', '--quiet', action='store_true', help='Suppress per-file progress output')
    parser.add_argument('--exit-code', action='store_true', help='Exit with code 1 if dashes found or read errors (for CI)')
    parser.add_argument('--scan-staged', action='store_true', help='(hook mode) read NUL-delimited staged paths on stdin and print the ones whose staged blob contains dashes')
    args = parser.parse_args()

    if args.scan_staged:
        sys.exit(scan_staged())

    # If --dry-run is supplied without --fix, automatically imply fix inspection mode
    if args.dry_run and not args.fix:
        args.fix = True

    if not args.files and stdin_has_data():
        args.files = [STDIN_TARGET]

    # Filter mode: cleaned text owns stdout, so every report moves to stderr
    filter_output = sys.stdout.buffer
    if STDIN_TARGET in args.files and args.fix and not args.dry_run:
        sys.stdout = sys.stderr

    overall_summary = {}
    any_found = False
    any_errors = False
    total_replacements = 0
    excluded_files = []
    verbose = not args.json and not args.quiet

    if verbose and not args.files:
        print("Scanning current directory for dash characters...")

    for filepath in resolve_targets(args.files, args.recursive):
        if verbose:
            print(f"\nProcessing: {filepath}")

        if filepath == STDIN_TARGET:
            result = process_stdin(filter_output, verbose=verbose and not args.fix, fix=args.fix, dry_run=args.dry_run)
        else:
            result = process_file(
                filepath,
                verbose=verbose,
                fix=args.fix,
                dry_run=args.dry_run,
                backup=args.backup,
            )
        found, file_summary, replaced, is_excluded, file_error = result

        if file_error:
            any_errors = True

        total_replacements += replaced

        if is_excluded and found:
            excluded_files.append(filepath)

        if found:
            if not is_excluded:
                any_found = True

            if verbose and not args.fix and not is_excluded:
                print(f"Dashes found in: {filepath}")
            if is_excluded:
                continue
            for category, data in file_summary.items():
                if category not in overall_summary:
                    overall_summary[category] = {
                        'count': 0,
                        'char': data['char'],
                        'unicode_format': data['unicode_format'],
                        'unicode_escape': data['unicode_escape'],
                    }
                overall_summary[category]['count'] += data['count']
        elif verbose:
            print(f"No dashes found in: {filepath}")

    if args.json:
        payload = {
            'dashes_found': any_found,
            'errors_encountered': any_errors,
            'total_detected': sum(d['count'] for d in overall_summary.values()),
            'fix_enabled': args.fix,
            'dry_run': args.dry_run,
            'replacement_char': REPLACEMENT_CHAR,
            'replacement_unicode': REPLACEMENT_UNICODE,
            'replacements_made': total_replacements,
            'excluded_from_fix': list(set(excluded_files)),
            'summary': overall_summary,
        }
        print(json.dumps(payload, indent=2, ensure_ascii=False))
    elif overall_summary:
        print("\n" + "=" * 100)
        mode_header = "DASH DETECTION & FIX SUMMARY" if args.fix else "DASH DETECTION SUMMARY"
        print(mode_header)
        print("=" * 100)
        print(f"{'Category':<25} {'Count':<8} {'Character':<12} {'Unicode Format':<15} {'Escape Sequence':<18} {'Prints As':<12}")
        print("-" * 100)
        for category, data in sorted(overall_summary.items()):
            print(f"{category:<25} {data['count']:<8} {data['char']:<12} {data['unicode_format']:<15} {data['unicode_escape']:<18} {repr(data['char']):<12}")
        print("=" * 100)
        total = sum(data['count'] for data in overall_summary.values())
        print(f"Total dash variants detected: {total}")
        if excluded_files:
            print(f"Note: Self-utility ({', '.join(set(excluded_files))}) was preserved and excluded from --fix.")
        if args.fix:
            status = "would be replaced (dry-run)" if args.dry_run else "successfully replaced"
            print(f"Total dashes {status} with regular '-' ({REPLACEMENT_UNICODE}): {total_replacements}")
    elif not args.quiet:
        print("\nNo dash characters found in any files.")

    if args.exit_code:
        # Exit with error if un-excluded dashes remain or if file errors occurred
        sys.exit(1 if (any_found or any_errors) else 0)


if __name__ == "__main__":
    main()
