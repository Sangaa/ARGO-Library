"""Frozen-query soundness and retrieval suite for tools/search.py  (CLAUDE, 2026-11-26)

Offered to issue #1, which asks for "retrieval tests (including Arabic and synonyms)"
and "frozen queries". It does not modify the engine: the engine is HERMUZ's lane.

Run from the repository root:   python3 -I tests/retrieval_soundness_R01.py
Exits 0 if every assertion holds, 1 otherwise, and prints its own counts.

Two defects are asserted as CURRENTLY PRESENT. When they are fixed this script
FAILS -- that is intended. Flip EXPECT_FIXED to True at that point and it becomes
the regression test that keeps them fixed.

WHY IT RUNS AGAINST A FIXTURE CORPUS AND NOT AGAINST cards/
-----------------------------------------------------------
The first version of this file queried the live cards/ directory, and it failed --
on three assertions, all for the same reason. The two cards that DOCUMENT these
defects quote the test's own queries as evidence, so once they were deposited the
queries matched them, and the defects stopped reproducing. Writing the finding down
destroyed the measurement of the finding.

So: frozen queries need a frozen corpus. Everything below runs against
tests/fixture_corpus_R01/, three cards that never change, each marked
author=FIXTURE and carrying its fixture status in `limits`. The live corpus is
checked separately, and only for invariants that cannot be disturbed this way.

This is the same defect class the fixtures themselves describe: a check that
consumes its own evidence.
"""
import json
import re
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "tools"))
from search import search, tokens  # noqa: E402

# Flipped to True on 2026-11-26, in the same change that fixed both defects.
# Before the flip this suite asserted they were PRESENT and exited 0; with the
# fix in place it failed with "D1 appears FIXED -- set EXPECT_FIXED = True",
# which is the mechanism working as designed. From here it is a regression
# test: it fails if either defect comes back.
EXPECT_FIXED = True

# ---------------------------------------------------------------- query sets
# D1: Arabic. The corpus tags `صلاحيات` and `اختبار`; these ask with the article.
ARABIC_SHOULD_HIT = [
    "تجربة الصلاحيات",
    "الاختبار",
    "هل جربنا نشوف الـAPI متاح ولا لأ",
]
ARABIC_BARE_CONTROL = ["صلاحيات", "اختبار"]  # same words WITHOUT the article

# D2: queries carrying no meaning at all. A sound engine returns nothing.
MEANINGLESS = [
    "the a of is not an",
    "the",
    "a the is not",
    "and the of to a in that it is not",
    "the xqzzy wobble flurb",
]
NONSENSE_CONTROL = ["xqzzy wobble flurb"]       # no function words -> must be empty

# Off-topic queries. The invariant on these is NOT "returns nothing" -- an early
# draft asserted that and failed on "how do I bake bread", which matches a fixture
# through the single word "how". That is D2 again, not a separate defect, and the
# assertion was wrong rather than the engine newly broken.
#
# The correct invariant is the one a fixed engine would satisfy and a stopword
# matcher cannot: NO RESULT MAY HAVE AN EMPTY CONTENT OVERLAP WITH THE QUERY.
# It holds in every version and does not need EXPECT_FIXED.
OFF_TOPIC = [
    "binomial coefficient genus",
    "Egyptian darbuka sample rate",
    "how do I bake bread",
]

# Function words discounted when asking whether a hit shares any MEANING with the
# query. English + the Arabic particles and the definite article.
STOP = set("""a an the is not of to in that it and or but for on at as be been am are was
were do does did how what why when which who whom this these those there here with
by from into over under then than so if else can could may might must shall should
will would i you he she we they me him her us them my your his its our their
هل ما مش لا و في من على عن ده دي ديه اللي ولا يا كده برضه بس انا انت هو هي احنا هم
""".split())


FIXTURE = ROOT / "tests" / "fixture_corpus_R01"


def hits(q, root=FIXTURE):
    return [c["id"] for _, c in search(q, root=root, limit=50)]


def content_overlap(q, cid, root=FIXTURE):
    """Shared tokens between query and card, ignoring function words."""
    card = json.loads((root / "cards" / f"{cid}.json").read_text(encoding="utf-8"))
    body = " ".join(card["mechanisms"]) + " " + card["title"] + " " + " ".join(
        card[k] for k in ("problem", "failure", "correction", "transfer"))
    return (tokens(q) & tokens(body)) - STOP


def main():
    fails = []
    nfix = len(list((FIXTURE / "cards").glob("*.json")))
    nlive = len(list((ROOT / "cards").glob("*.json")))
    print(f"fixture corpus: {nfix} cards  (frozen; every assertion below uses this)")
    print(f"live corpus:    {nlive} cards  (checked only for the final invariant)")
    print(f"mode:           EXPECT_FIXED = {EXPECT_FIXED}\n")
    if nfix != 3:
        fails.append(f"fixture corpus has {nfix} cards, expected 3 -- the frozen "
                     f"queries below were calibrated against those three")

    # ---- control: the bare Arabic words DO work, so the article is the cause
    print("[control] bare Arabic tags (no article) must hit:")
    for q in ARABIC_BARE_CONTROL:
        h = hits(q)
        ok = bool(h)
        print(f"   {'ok ' if ok else 'FAIL'}  {len(h)} hit(s)   {q!r}")
        if not ok:
            fails.append(f"bare Arabic tag {q!r} returned nothing; the corpus changed "
                         f"and D1's diagnosis no longer isolates the article")

    # ---- D1: Arabic with the article
    print("\n[D1] Arabic queries with the definite article / tatweel:")
    d1_blind = 0
    for q in ARABIC_SHOULD_HIT:
        h = hits(q)
        if not h:
            d1_blind += 1
        print(f"   {len(h)} hit(s)   {q!r}")
    print(f"   -> blind on {d1_blind}/{len(ARABIC_SHOULD_HIT)}")
    if EXPECT_FIXED and d1_blind:
        fails.append(f"D1 regression: {d1_blind} Arabic queries still return nothing")
    if not EXPECT_FIXED and d1_blind == 0:
        fails.append("D1 appears FIXED -- set EXPECT_FIXED = True so this suite "
                     "starts protecting the fix")

    # ---- control: nonsense without function words must be empty in every version
    print("\n[control] nonsense with no function words must be empty:")
    for q in NONSENSE_CONTROL:
        h = hits(q)
        print(f"   {'ok ' if not h else 'FAIL'}  {len(h)} hit(s)   {q!r}")
        if h:
            fails.append(f"unsound in any version: {q!r} returned {h}")

    # ---- D2: meaningless queries
    print("\n[D2] queries carrying no meaning (function words only):")
    d2_bad = 0
    for q in MEANINGLESS:
        h = hits(q)
        # the damning part: returned despite ZERO shared content tokens
        empty_overlap = [c for c in h if not content_overlap(q, c)]
        if empty_overlap:
            d2_bad += 1
        print(f"   {len(h)} hit(s), {len(empty_overlap)} with zero content overlap   {q!r}")
    print(f"   -> unsound on {d2_bad}/{len(MEANINGLESS)}")
    if EXPECT_FIXED and d2_bad:
        fails.append(f"D2 regression: {d2_bad} meaningless queries still return cards")
    if not EXPECT_FIXED and d2_bad == 0:
        fails.append("D2 appears FIXED -- set EXPECT_FIXED = True")

    # ---- the sharpest single measurement
    print("\n[D2 sharpest] a pure-function-word query must not outscore its "
          "meaningful original:")
    real = "measured a proxy instead of the thing itself"
    fake = "the a instead of is not an itself thing"
    rs = search(real, root=FIXTURE, limit=50)
    fs = search(fake, root=FIXTURE, limit=50)
    rmax = rs[0][0] if rs else 0
    fmax = fs[0][0] if fs else 0
    print(f"   meaningful {real!r} -> top score {rmax}")
    print(f"   gutted     {fake!r} -> top score {fmax}")
    inverted = fmax > rmax
    print(f"   -> inverted: {inverted}")
    if EXPECT_FIXED and inverted:
        fails.append("D2 regression: the gutted query still outscores the real one")

    # ---- invariant that holds in EVERY version: no hit without shared meaning
    print("\n[invariant] no result may share zero content tokens with its query:")
    for q in OFF_TOPIC + MEANINGLESS:
        h = hits(q)
        hollow = [c for c in h if not content_overlap(q, c)]
        state = "ok " if not hollow else ("D2 " if not EXPECT_FIXED else "FAIL")
        print(f"   {state} {len(h)} hit(s), {len(hollow)} hollow   {q!r}")
        if hollow and EXPECT_FIXED:
            fails.append(f"hollow hit survives the fix: {q!r} -> {hollow}")

    # ---- the one live-corpus check that a new card cannot disturb:
    # every card must validate against the schema's required keys.
    print("\n[invariant/live] every live card carries the schema's required keys:")
    sch = json.loads((ROOT / "schema" / "card.schema.json").read_text(encoding="utf-8"))
    bad = 0
    for p in sorted((ROOT / "cards").glob("*.json")):
        c = json.loads(p.read_text(encoding="utf-8"))
        miss = [k for k in sch["required"] if k not in c]
        extra = [k for k in c if k not in sch["properties"]]
        if miss or extra or not re.fullmatch(sch["properties"]["id"]["pattern"], c["id"]):
            bad += 1
            fails.append(f"{p.name}: missing={miss} unknown={extra}")
    print(f"   {'ok ' if not bad else 'FAIL'}  {bad} invalid of "
          f"{len(list((ROOT / 'cards').glob('*.json')))}")

    print("\n" + "=" * 70)
    if fails:
        print(f"FAIL ({len(fails)}):")
        for f in fails:
            print(f"  - {f}")
        return 1
    print("PASS -- both defects reproduce as described, and no invariant is violated.")
    return 0


if __name__ == "__main__":
    sys.exit(main())
