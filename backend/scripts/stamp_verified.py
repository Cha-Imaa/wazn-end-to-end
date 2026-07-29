"""Stamp `verified: true` on KB entries that pass the structural invariants.

The review policy behind the flag (§1.7 decision, 2026-07-30): *verified means
the entry passes the machine-checkable structural invariants*, not that a human
re-reviewed it. The invariants:

    word     arabic + meaning non-empty; root_id resolves; pattern_id (when
             set) resolves; breakdown.root_letters spell the root, hamza
             seats folded (ء أ إ ؤ ئ آ are one letter written six ways)
    root     arabic + meaning non-empty; exactly 8 word_ids; each resolves
             and points back at this root
    pattern  arabic + name + meaning_effect non-empty (the fields the agents'
             evidence packets ground on); used by at least one word

Writing is all-or-nothing: if every entry in a file passes, its
`"verified": false` literals are flipped textually — nothing is re-serialized,
so the hand-tuned compact formatting survives and the diff is exactly the
flag lines. If anything fails, the failures are reported and nothing is
written; fix the data first. `--check` never writes and exits 1 on any fail,
which also makes it the KB integrity check the Deferred section asks for.

Run from `backend/`:

    python -m scripts.stamp_verified            # report + write
    python -m scripts.stamp_verified --check    # report only, exit 1 on any fail
"""

import json
import re
import sys
from pathlib import Path


DATA_DIR = Path(__file__).resolve().parent.parent / "data"

_TASHKEEL_RE = re.compile(r"[ً-ْٰـ]")
_HAMZA_FOLD = str.maketrans({"أ": "ء", "إ": "ء", "ؤ": "ء", "ئ": "ء", "آ": "ء"})


def _root_key(text: str) -> str:
    return _TASHKEEL_RE.sub("", text or "").replace(" ", "").translate(_HAMZA_FOLD)


def check_word(word: dict, roots: dict, patterns: dict) -> list[str]:
    problems = []

    if not word.get("arabic"):
        problems.append("no arabic")
    if not word.get("meaning"):
        problems.append("no meaning")

    root = roots.get(word.get("root_id"))
    if not root:
        problems.append(f"root_id '{word.get('root_id')}' does not resolve")

    pattern_id = word.get("pattern_id")
    if pattern_id and pattern_id not in patterns:
        problems.append(f"pattern_id '{pattern_id}' does not resolve")

    root_letters = (word.get("breakdown") or {}).get("root_letters") or []
    if not root_letters:
        problems.append("breakdown has no root_letters")
    elif root and _root_key("".join(root_letters)) != _root_key(root.get("arabic", "")):
        problems.append(
            f"root letters {root_letters} do not spell root '{root.get('arabic')}'"
        )

    return problems


def check_root(root: dict, words: dict) -> list[str]:
    problems = []

    if not root.get("arabic"):
        problems.append("no arabic")
    if not root.get("meaning"):
        problems.append("no meaning")

    word_ids = root.get("word_ids") or []
    if len(word_ids) != 8:
        problems.append(f"{len(word_ids)} word_ids, expected 8")
    for word_id in word_ids:
        word = words.get(word_id)
        if not word:
            problems.append(f"word_id '{word_id}' does not resolve")
        elif word.get("root_id") != root.get("id"):
            problems.append(f"word '{word_id}' points at root '{word.get('root_id')}'")

    return problems


def check_pattern(pattern: dict, used_pattern_ids: set) -> list[str]:
    problems = []

    for field in ("arabic", "name", "meaning_effect"):
        if not pattern.get(field):
            problems.append(f"no {field}")
    if pattern.get("id") not in used_pattern_ids:
        problems.append("used by no word")

    return problems


def main() -> int:
    check_only = "--check" in sys.argv

    words = json.loads((DATA_DIR / "words.json").read_text(encoding="utf-8"))
    roots = json.loads((DATA_DIR / "roots.json").read_text(encoding="utf-8"))
    patterns = json.loads((DATA_DIR / "patterns.json").read_text(encoding="utf-8"))

    used_pattern_ids = {w.get("pattern_id") for w in words.values() if w.get("pattern_id")}

    failures = 0
    clean_files = []
    for filename, kind, collection, check in (
        ("words.json", "word", words, lambda e: check_word(e, roots, patterns)),
        ("roots.json", "root", roots, lambda e: check_root(e, words)),
        ("patterns.json", "pattern", patterns, lambda e: check_pattern(e, used_pattern_ids)),
    ):
        passed = 0
        for entry_id, entry in collection.items():
            problems = check(entry)
            passed += not problems
            for problem in problems:
                failures += 1
                print(f"FAIL {kind} {entry_id}: {problem}")
        print(f"{kind}s: {passed}/{len(collection)} pass the invariants")
        if passed == len(collection):
            clean_files.append(filename)

    if check_only:
        return 1 if failures else 0

    if failures:
        print("nothing written — fix the failures above first")
        return 1

    for filename in clean_files:
        path = DATA_DIR / filename
        text = path.read_text(encoding="utf-8")
        flipped = text.count('"verified": false')
        path.write_text(
            text.replace('"verified": false', '"verified": true'),
            encoding="utf-8",
        )
        print(f"wrote {filename}: flipped {flipped} flags")

    return 0


if __name__ == "__main__":
    sys.exit(main())
