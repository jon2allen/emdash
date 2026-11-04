#!/usr/bin/env python3
"""Em dash density: em dashes per 1,000 words.

    density = (em_dash_count / word_count) * 1000

Follows the metric in Freeburg, "The Last Fingerprint: How Markdown Training
Shapes LLM Prose" (arXiv:2603.27006), which counts U+2014 and normalizes to
frequency per 1,000 words.

Normalization (default):
  * Project Gutenberg license header/footer is stripped; only the body counts.
  * One em dash is counted per run of U+2014, per run of two or more ASCII
    hyphens ('--', the typewriter em dash many Gutenberg editions use), and
    per two-em (U+2E3A) or three-em (U+2E3B) dash.
  * Dashes are treated as word breaks, so 'word<em>word' is two words.
    Hyphenated compounds ('man-of-war') and contractions count as one word.

--strict counts only U+2014 runs, exactly as the paper does.

Dash characters are built with chr() so the file stays pure ASCII and the
dash-cleaning hook leaves it alone.
"""
import argparse
import json
import os
import re
import sys

EM_DASH = chr(0x2014)
TWO_EM_DASH = chr(0x2E3A)
THREE_EM_DASH = chr(0x2E3B)
RIGHT_QUOTE = chr(0x2019)

STRICT_DASH_RE = re.compile(EM_DASH + '+')
NORMALIZED_DASH_RE = re.compile('[' + EM_DASH + TWO_EM_DASH + THREE_EM_DASH + ']+|-{2,}')
# A word: letters/digits, optionally joined by single hyphens or apostrophes
WORD_RE = re.compile(r"[^\W_]+(?:[-'" + RIGHT_QUOTE + r"][^\W_]+)*")

GUTENBERG_START_RE = re.compile(r'^\*\*\* ?START OF (THE|THIS) PROJECT GUTENBERG.*$', re.M | re.I)
GUTENBERG_END_RE = re.compile(r'^\*\*\* ?END OF (THE|THIS) PROJECT GUTENBERG.*$', re.M | re.I)


def strip_gutenberg(text: str) -> str:
    """Return the body between the Gutenberg START and END markers, if present."""
    start = GUTENBERG_START_RE.search(text)
    if start:
        text = text[start.end():]
    end = GUTENBERG_END_RE.search(text)
    if end:
        text = text[:end.start()]
    return text


def measure(text: str, strict: bool = False, keep_boilerplate: bool = False) -> dict:
    """Count em dashes and words in text and compute density per 1,000 words."""
    if not keep_boilerplate:
        text = strip_gutenberg(text)
    dash_re = STRICT_DASH_RE if strict else NORMALIZED_DASH_RE
    em_dashes = len(dash_re.findall(text))
    # Every dash form is a word break, in both modes, so word counts match
    words = len(WORD_RE.findall(NORMALIZED_DASH_RE.sub(' ', text)))
    density = (em_dashes / words) * 1000 if words else 0.0
    return {'em_dashes': em_dashes, 'words': words, 'density': density}


def collect_files(paths):
    for path in paths:
        if os.path.isdir(path):
            for name in sorted(os.listdir(path)):
                if name.endswith('.txt'):
                    yield os.path.join(path, name)
        else:
            yield path


def main(argv=None) -> int:
    parser = argparse.ArgumentParser(description='Em dashes per 1,000 words (arXiv:2603.27006 metric)')
    parser.add_argument('paths', nargs='*', default=['melville'],
                        help='Text files or directories of .txt files (default: melville)')
    parser.add_argument('--strict', action='store_true',
                        help="Count only U+2014, as in the paper (no '--' normalization)")
    parser.add_argument('--keep-boilerplate', action='store_true',
                        help='Do not strip the Project Gutenberg header/footer')
    parser.add_argument('--json', action='store_true', help='Output results as JSON')
    args = parser.parse_args(argv)

    results = []
    for path in collect_files(args.paths):
        try:
            with open(path, encoding='utf-8-sig', errors='replace') as f:
                text = f.read()
        except OSError as e:
            print(f'Error reading {path}: {e}', file=sys.stderr)
            return 2
        results.append({'file': path, **measure(text, args.strict, args.keep_boilerplate)})

    if not results:
        print('No .txt files found.', file=sys.stderr)
        return 2

    total_dashes = sum(r['em_dashes'] for r in results)
    total_words = sum(r['words'] for r in results)
    overall = (total_dashes / total_words) * 1000 if total_words else 0.0
    mode = 'strict' if args.strict else 'normalized'

    if args.json:
        print(json.dumps({'mode': mode, 'files': results,
                          'total': {'em_dashes': total_dashes, 'words': total_words,
                                    'density': overall}}, indent=2))
        return 0

    results.sort(key=lambda r: r['density'], reverse=True)
    width = max(len(os.path.basename(r['file'])) for r in results)
    print(f'Em dash density per 1,000 words ({mode})')
    print(f"{'File':<{width}}  {'Em dashes':>9}  {'Words':>9}  {'Density':>8}")
    for r in results:
        print(f"{os.path.basename(r['file']):<{width}}  {r['em_dashes']:>9}  {r['words']:>9}  {r['density']:>8.2f}")
    print(f"{'TOTAL':<{width}}  {total_dashes:>9}  {total_words:>9}  {overall:>8.2f}")
    return 0


if __name__ == '__main__':
    sys.exit(main())
