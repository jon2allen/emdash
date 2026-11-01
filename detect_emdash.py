#!/usr/bin/env python3
import argparse
import json
import os
import shutil
import sys

# Target dash variants to detect and replace
DASH_CATEGORIES = {
    'EM_DASH': ('—', 'U+2014', r'\u2014'),
    'EN_DASH': ('–', 'U+2013', r'\u2013'),
    'FIGURE_DASH': ('‒', 'U+2012', r'\u2012'),
    'HORIZONTAL_BAR': ('―', 'U+2015', r'\u2015'),
    'TWO_EM_DASH': ('⸺', 'U+2E3A', r'\u2E3A'),
    'THREE_EM_DASH': ('⸻', 'U+2E3B', r'\u2E3B'),
    'MINUS_SIGN': ('−', 'U+2212', r'\u2212'),
    'SMALL_EM_DASH': ('﹘', 'U+FE58', r'\uFE58'),
    'SMALL_HYPHEN_MINUS': ('﹣', 'U+FE63', r'\uFE63'),
    'FULLWIDTH_HYPHEN_MINUS': ('－', 'U+FF0D', r'\uFF0D'),
}

CHAR_TO_CATEGORY = {data[0]: (cat, data[1], data[2]) for cat, data in DASH_CATEGORIES.items()}
TARGET_CHARS = set(CHAR_TO_CATEGORY.keys())
DEFAULT_IGNORE_DIRS = {'.git', '.venv', 'venv', '__pycache__', 'node_modules', '.idea', '.vscode'}

# Self-exclusion: this script file must never have its lookup definitions replaced
SELF_FILENAME = "detect_emdash.py"

# Replacement character: Regular ASCII Hyphen-Minus U+002D
REPLACEMENT_CHAR = '-'
REPLACEMENT_UNICODE = 'U+002D'


def is_self_script(filepath: str) -> bool:
    """Return True if the filepath points to this script (detect_emdash.py)."""
    return os.path.basename(filepath) == SELF_FILENAME


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


def replace_dashes_in_text(text: str) -> tuple[str, int]:
    """Replace all target dash variants with regular ASCII hyphen-minus ('-').
    Returns (new_text, replacement_count).
    """
    total_replaced = 0
    new_chars = []
    for ch in text:
        if ch in TARGET_CHARS:
            new_chars.append(REPLACEMENT_CHAR)
            total_replaced += 1
        else:
            new_chars.append(ch)
    return ''.join(new_chars), total_replaced


def process_file(filepath: str, verbose: bool = True, fix: bool = False, dry_run: bool = False, backup: bool = False):
    """Scan and optionally fix dash characters in a file.
    Returns (dash_found, file_summary, replacements_made, is_excluded).
    """
    dash_found = False
    file_summary = {}
    replacements_made = 0
    is_excluded = is_self_script(filepath)

    try:
        with open(filepath, 'r', encoding='utf-8') as f:
            content = f.read()

        # Binary check: null bytes usually indicate non-text files
        if '\x00' in content:
            if verbose:
                print(f"Skipping binary file: {filepath}", file=sys.stderr)
            return False, {}, 0, False

        # Line-by-line categorization for reporting
        for line_num, line in enumerate(content.splitlines(), 1):
            categories = categorize_dashes(line)
            if categories:
                if verbose:
                    prefix = "[SELF-DEFINITION] " if is_excluded else ""
                    print(f"{prefix}{filepath}:{line_num}: {line}")
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
                new_content, replacements_made = replace_dashes_in_text(content)
                if replacements_made > 0:
                    if dry_run:
                        if verbose:
                            print(f"[DRY-RUN] Would replace {replacements_made} dash(es) with '-' ({REPLACEMENT_UNICODE}) in: {filepath}")
                    else:
                        if backup:
                            shutil.copy2(filepath, f"{filepath}.bak")

                        # Atomic write using a temporary sibling file
                        tmp_filepath = f"{filepath}.tmp_dash_fix"
                        with open(tmp_filepath, 'w', encoding='utf-8') as f_out:
                            f_out.write(new_content)
                        os.replace(tmp_filepath, filepath)

                        if verbose:
                            print(f"[FIXED] Replaced {replacements_made} dash(es) with '-' ({REPLACEMENT_UNICODE}) in: {filepath}")

    except UnicodeDecodeError:
        if verbose:
            print(f"Skipping binary / non-UTF-8 file: {filepath}", file=sys.stderr)
    except Exception as e:
        print(f"Error processing {filepath}: {e}", file=sys.stderr)

    return dash_found, file_summary, replacements_made, is_excluded


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


def resolve_targets(paths: list[str], recursive: bool = False):
    """Resolve file or directory arguments into a stream of target file paths."""
    if not paths:
        yield from scan_directory('.', recursive=recursive)
        return

    for path in paths:
        if os.path.isdir(path):
            yield from scan_directory(path, recursive=recursive)
        elif os.path.isfile(path):
            yield path
        else:
            print(f"Target not found: {path}", file=sys.stderr)


def main():
    parser = argparse.ArgumentParser(description='Detect and replace Unicode dash/emdash characters in files')
    parser.add_argument('files', nargs='*', help='Files or directories to scan (default: current directory)')
    parser.add_argument('-r', '--recursive', action='store_true', help='Scan directories recursively')
    parser.add_argument('--fix', action='store_true', help=f"Replace detected Unicode dashes with regular '-' ({REPLACEMENT_UNICODE})")
    parser.add_argument('--dry-run', action='store_true', help='Simulate replacements with --fix without altering files')
    parser.add_argument('--backup', action='store_true', help='Create .bak backup files before modifying with --fix')
    parser.add_argument('--json', action='store_true', help='Output summary strictly as JSON to stdout')
    parser.add_argument('-q', '--quiet', action='store_true', help='Suppress per-file progress output')
    parser.add_argument('--exit-code', action='store_true', help='Exit with code 1 if dashes found (for CI)')
    args = parser.parse_args()

    overall_summary = {}
    any_found = False
    total_replacements = 0
    excluded_files = []
    verbose = not args.json and not args.quiet

    if verbose and not args.files:
        print("Scanning current directory for dash characters...")

    for filepath in resolve_targets(args.files, args.recursive):
        if verbose:
            print(f"\nProcessing: {filepath}")

        found, file_summary, replaced, is_excluded = process_file(
            filepath,
            verbose=verbose,
            fix=args.fix,
            dry_run=args.dry_run,
            backup=args.backup,
        )

        total_replacements += replaced

        if is_excluded and found:
            excluded_files.append(filepath)

        if found:
            # If the only file found with dashes was detect_emdash.py itself, don't trigger failure for CI exit-code
            if not is_excluded:
                any_found = True
            elif not any_found:
                # found in self, but we check if other files have dashes
                pass

            if verbose and not args.fix and not is_excluded:
                print(f"Dashes found in: {filepath}")
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
            'total_detected': sum(d['count'] for d in overall_summary.values()),
            'fix_enabled': args.fix,
            'dry_run': args.dry_run,
            'replacement_char': REPLACEMENT_CHAR,
            'replacement_unicode': REPLACEMENT_UNICODE,
            'replacements_made': total_replacements,
            'excluded_from_fix': excluded_files,
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
    else:
        print("\nNo dash characters found in any files.")

    if args.exit_code:
        sys.exit(1 if any_found else 0)


if __name__ == "__main__":
    main()
