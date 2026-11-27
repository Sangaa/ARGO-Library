"""Bilingual retrieval evaluation, layer by layer, through the ACTUAL CLI.

Assignment: issue #1 and evaluation/BILINGUAL_BASELINE_2026-11-26.md, which says
"Claude owns search solution exploration", asks for paired queries, distractors,
negative controls and concept-level relevance, says not to conflate
authentication with authorization, not to blindly strip prefixes, and says
"Evaluate actual CLI and report costs/limitations before merge".

So this harness runs `python3 -I tools/search.py ...` as a SUBPROCESS, not an
import. ARGO's own baseline notes its measurement was "not a full checkout/CLI
test"; mine was an import too (tests/retrieval_soundness_R01.py). An engine is
what its entry point does.

The engine had no way to be aimed at a corpus: it derived one from its own file
location. The first run of this harness passed cwd and got the LIVE cards back
while reporting them as fixture results -- 0/14 recall against a corpus it was
never reading. --root was added to tools/search.py for that reason. An engine that
cannot be aimed at a corpus cannot be measured on one.

It runs against tests/fixture_corpus_R02/ -- a frozen corpus with two DELIBERATE
near-neighbour pairs (fx-authn / fx-authz, fx-direct-probe / fx-indirect-signal)
and one unrelated card. The pairs exist so that a change which improves recall by
collapsing distinct concepts is scored as the regression it is, not as a win.

Why a frozen corpus: R01's first version queried the live cards/ and the cards
documenting the defect quoted the test's own queries, so depositing them made the
defect stop reproducing. Frozen queries need a frozen corpus.

Exit 0 only if every assertion holds.
"""
import json
import subprocess
import sys
import time
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
FIXTURE = ROOT / "tests" / "fixture_corpus_R02"
CLI = ROOT / "tools" / "search.py"

# ------------------------------------------------------------------ query sets
# Paired: same concept, Arabic and English. Each names the cards that are RIGHT.
PAIRS = [
    ("authentication",            {"fx-authn"}),
    ("المصادقة",                  {"fx-authn"}),
    ("authorization",             {"fx-authz"}),
    ("التخويل",                   {"fx-authz"}),
    ("permissions",               {"fx-authz"}),
    ("الصلاحيات",                 {"fx-authz"}),
    ("صلاحيات",                   {"fx-authz"}),
    ("direct capability test",    {"fx-direct-probe"}),
    ("اختبار القدرة مباشرة",       {"fx-direct-probe"}),
    ("إختبار",                    {"fx-direct-probe"}),     # hamza variant
    # 'الـAPI مش متاح' was here, expecting fx-direct-probe. It MISSED, and the
    # expectation was the error, not the engine: tokenisation produces 'api'
    # correctly from tatweel + article, and no fixture card contains the word.
    # Reshaping the fixture to make the query pass would be fitting the data to
    # the test, so the tokenisation it was really probing is asserted directly in
    # part D instead.
    ("indirect proxy measure",    {"fx-indirect-signal"}),
    ("مؤشر غير مباشر",            {"fx-indirect-signal"}),
    ("reproducible render",       {"fx-unrelated-music"}),
]

# Meaningless: function words only. A sound engine returns nothing.
MEANINGLESS = ["the a of is not an", "the", "a the is not",
               "and the of to a in that it is not", "the xqzzy wobble flurb",
               "هل ده ولا لا", "في من على عن"]

# Unrelated but meaningful. Must not return retrieval/identity cards.
UNRELATED = ["how do I bake bread", "Egyptian darbuka sample rate",
             "binomial coefficient genus", "خبز بالفرن"]

# The conflation traps. An authentication query must NOT surface the
# authorization card ABOVE the authentication one, and vice versa.
NO_CONFLATE = [("authentication", "fx-authn", "fx-authz"),
               ("المصادقة",       "fx-authn", "fx-authz"),
               ("authorization",  "fx-authz", "fx-authn"),
               ("التخويل",        "fx-authz", "fx-authn"),
               ("direct capability test", "fx-direct-probe", "fx-indirect-signal"),
               ("indirect proxy measure", "fx-indirect-signal", "fx-direct-probe")]

# Words whose ال is part of the stem. A blind prefix strip corrupts these.
PREFIX_TRAPS = ["اللغة", "الله", "التزام"]


def run(query, layers, concepts=False):
    """Invoke the real CLI. Returns (rows, seconds)."""
    cmd = [sys.executable, "-I", str(CLI), query, "--limit", "50",
           "--layers", layers, "--root", str(FIXTURE)]
    if concepts:
        cmd.append("--concepts")
    t0 = time.perf_counter()
    p = subprocess.run(cmd, capture_output=True, text=True)
    dt = time.perf_counter() - t0
    if p.returncode != 0:
        raise SystemExit(f"CLI failed on {query!r} layers={layers}:\n{p.stderr}")
    rows = [json.loads(l) for l in p.stdout.splitlines() if l.strip()]
    return rows, dt


def ids(rows):
    return [r["id"] for r in rows]


def measure(layers):
    """Recall@1, false positives, unsound hits and conflations for one config.

    Recall is measured at RANK 1, not anywhere in the list. A change that surfaces
    the right card fourth is not a change that answers the question, and on a
    5-card corpus "appears somewhere" is nearly free.
    """
    hit = miss = 0
    for q, want in PAIRS:
        got = ids(run(q, layers)[0])
        if got and got[0] in want:
            hit += 1
        else:
            miss += 1
    unsound = sum(1 for q in MEANINGLESS if run(q, layers)[0])
    fp = sum(1 for q in UNRELATED if run(q, layers)[0])
    conf = 0
    for q, right, wrong in NO_CONFLATE:
        got = ids(run(q, layers)[0])
        if wrong in got and (right not in got or got.index(wrong) < got.index(right)):
            conf += 1
    return hit, miss, unsound, fp, conf


def main():
    fails = []
    ncards = len(list((FIXTURE / "cards").glob("*.json")))
    print(f"corpus: {ncards} frozen fixture cards, 2 deliberate near-neighbour pairs")
    print(f"cli:    {sys.executable} -I {CLI.relative_to(ROOT)} (subprocess, not import)")
    print(f"queries: {len(PAIRS)} paired, {len(MEANINGLESS)} meaningless, "
          f"{len(UNRELATED)} unrelated, {len(NO_CONFLATE)} conflation traps\n")

    # --- the before/after comparison, run rather than remembered
    configs = [
        ("none",                      "ORIGINAL engine"),
        ("norm",                      "+ L1 Unicode normalisation"),
        ("norm,article",              "+ L2 article (additive)"),
        ("norm,article,stop",         "+ L3 stopwords"),
        ("norm,article,stop,content", "+ L4 content-token requirement"),
        ("all",                       "+ L5 bilingual aliases (default)"),
    ]
    print("A. layer by layer, each measured on its own")
    print(f"   {'config':<28} {'recall@1':>9} {'miss':>5} {'unsound':>8} "
          f"{'false+':>7} {'conflate':>9}")
    rows = {}
    for spec, label in configs:
        hit, miss, unsound, fp, conf = measure(spec)
        rows[spec] = (hit, miss, unsound, fp, conf)
        print(f"   {label:<28} {hit:>4}/{len(PAIRS):<3} {miss:>5} {unsound:>4}/"
              f"{len(MEANINGLESS):<3} {fp:>3}/{len(UNRELATED):<3} "
              f"{conf:>4}/{len(NO_CONFLATE)}")

    o_hit, o_miss, o_un, o_fp, o_cf = rows["none"]
    f_hit, f_miss, f_un, f_fp, f_cf = rows["all"]
    print(f"\n   original -> final:  recall {o_hit}/{len(PAIRS)} -> {f_hit}/{len(PAIRS)}"
          f"   unsound {o_un} -> {f_un}   false+ {o_fp} -> {f_fp}"
          f"   conflations {o_cf} -> {f_cf}")

    if f_hit <= o_hit:
        fails.append(f"recall did not improve: {o_hit} -> {f_hit}")
    if f_un:
        fails.append(f"still unsound on {f_un} meaningless queries")
    if f_fp:
        fails.append(f"{f_fp} false positives on unrelated meaningful queries")
    if f_cf:
        fails.append(f"{f_cf} conflations of deliberately distinct concepts")

    # --- which queries still miss, named rather than hidden in a count
    print("\nB. paired queries, final config -- the wanted card must be RANK 1")
    for q, want in PAIRS:
        rows_, _ = run(q, "all")
        got = ids(rows_)
        ok = bool(got) and got[0] in want
        print(f"   {'ok ' if ok else 'MISS'} {q!r} -> {got if got else 'nothing'}"
              f"   (wanted {sorted(want)} first)")

    # --- ARGO asked for matched concepts to be reported
    print("\nC. matched concepts reported by the CLI (--concepts)")
    for q in ("المصادقة", "الصلاحيات", "إختبار"):
        rows_, _ = run(q, "all", concepts=True)
        for r in rows_[:1]:
            print(f"   {q!r} -> {r['id']}  matched={r['matched']}")

    # --- the prefix trap ARGO warned about
    print("\nD1. tokenisation, asserted directly")
    sys.path.insert(0, str(ROOT / "tools"))
    import search as S
    TOK = [("الـAPI مش متاح", "api",      "tatweel + definite article"),
           ("إختبار",         "اختبار",   "hamza-on-alef normalised"),
           ("الصلاحيات",      "صلاحيات",  "article variant added"),
           ("الْمُصَادَقَة",      "مصادقة",   "harakat removed")]
    for src, want, why in TOK:
        t = S.tokens(src, S.DEFAULT_LAYERS)
        ok = want in t
        print(f"   {'ok ' if ok else 'FAIL'} {src!r} produces {want!r}  ({why})")
        if not ok:
            fails.append(f"tokenisation: {src!r} did not produce {want!r}; got {sorted(t)}")

    print("\nD2. ال is part of the stem in these; a blind strip would corrupt them")
    for w in PREFIX_TRAPS:
        t = S.tokens(w, S.DEFAULT_LAYERS)
        kept = w in t
        print(f"   {'ok ' if kept else 'FAIL'} {w!r} -> {sorted(t)}"
              f"   original token kept: {kept}")
        if not kept:
            fails.append(f"blind-strip regression: {w!r} lost its original token")

    # --- the check the 5-card fixture structurally cannot do
    print("\nF. live-corpus alias polysemy: an alias term must be unambiguous HERE")
    print("   An alias term that occurs in a large share of the corpus is not a")
    print("   concept marker, it is a stopword with ambitions. The first version of")
    print("   the alias list contained scope/test/direct/measure, which occur in")
    print("   3,4,4,4 of 7 live cards -- every research card has a SCOPE field,")
    print("   describes a TEST, contrasts DIRECT with indirect and reports a")
    print("   MEASUREMENT. The 5-card fixture has no card using them in that sense,")
    print("   so only the live corpus can catch it.")
    sys.path.insert(0, str(ROOT / "tools"))
    import search as S0
    live = sorted((ROOT / "cards").glob("*.json"))
    # Ambiguity is judged on the fields that state what a card is ABOUT --
    # mechanisms and title -- not on the whole body.
    #
    # Measuring on the body was the first version, and it flagged `capability` at
    # 4/8 cards. Inspecting those four, most carry the word only because they CITE
    # the card `proxy-capability` by its id. So the body measure was itself
    # polluted by the limitation recorded in cards/card-id-citation-20261126.json,
    # and the flag was an artifact of cross-references rather than of ambiguity.
    #
    # Raising the threshold until the flag disappeared was the other option and is
    # refused: that is choosing a threshold to clear it, the same defect as the
    # 1e-9 guard in ARGO-Research's LIT_02. Narrowing the FIELD is a principled
    # change -- a card's aboutness is what its mechanisms and title declare -- and
    # the body count is still printed so the difference is visible.
    about, bodies = [], []
    for p_ in live:
        c = json.loads(p_.read_text(encoding="utf-8"))
        about.append((" ".join(c["mechanisms"]) + " " + c["title"]).lower())
        bodies.append(" ".join(c[k] for k in ("problem", "failure", "correction",
                                              "transfer")).lower())
    blobs = about
    LIMIT = 0.5
    worst = []
    for i, grp in enumerate(S0.ALIAS_GROUPS):
        for w in sorted(grp):
            n = sum(1 for b in about if w in b)
            nb = sum(1 for a, bd in zip(about, bodies) if w in a + " " + bd)
            if n / len(about) >= LIMIT:
                worst.append((n, w, i))
            elif nb / len(about) >= LIMIT:
                print(f"     note  {w!r}: {n}/{len(about)} by aboutness but "
                      f"{nb}/{len(about)} counting body text -- the extra hits are "
                      f"citations, see cards/card-id-citation-20261126.json")
    print(f"\n   alias terms in >= {LIMIT:.0%} of {len(about)} live cards, "
          f"by mechanisms+title:")
    if worst:
        for n, w, i in sorted(worst, reverse=True):
            print(f"     FAIL  {w!r} in {n}/{len(blobs)} cards  (group @c{i})")
        fails.append(f"{len(worst)} alias term(s) occur in >= {LIMIT:.0%} of the "
                     f"live corpus and generate false positives: "
                     f"{sorted(w for _, w, _ in worst)}")
    else:
        print("     none -- every alias term is specific in this corpus")

    print("\n   alias-only hits, reported rather than failed:")
    print("   A hit matching ONLY an alias marker is the cross-language bridge")
    print("   working, not a defect -- an Arabic query reaching an English-only")
    print("   card is the whole point of layer 5. An earlier draft of this check")
    print("   asserted the opposite and failed on المصادقة -> proxy-capability,")
    print("   where the card does carry `authentication`. The criterion was wrong,")
    print("   not the engine.")
    for q in ("المصادقة", "استرجاع", "قدرة", "تخويل"):
        out = subprocess.run([sys.executable, "-I", str(CLI), q, "--limit", "50",
                              "--layers", "all", "--concepts"],
                             capture_output=True, text=True)
        rs = [json.loads(l) for l in out.stdout.splitlines() if l.strip()]
        bridged = [r["id"] for r in rs
                   if all(m.startswith("@c") for m in r["matched"])]
        print(f"     {q!r}: {len(rs)} hit(s) of {len(blobs)}, "
              f"{len(bridged)} via the alias bridge {bridged if bridged else ''}")
    print("\n   KNOWN LIMITATION, not asserted: card text that CITES another card")
    print("   by id makes that id's words searchable. 'قدرة' reaches TOTO's R04")
    print("   card because its transfer field says \"the earlier Library")
    print("   proxy-capability card\". The match is real text, but the card is not")
    print("   about capability. Recorded in cards/card-id-citation-20261126.json.")

    # --- what this suite's own PASS message said it could not do
    print("\nG. live-corpus selectivity: do the five layers add noise at scale?")
    print("   The fixture is 5 cards; the live corpus is now "
          f"{len(blobs)}. The worry this")
    print("   check exists for is mine: that the alias layer, written when the")
    print("   corpus held 7 cards, would pull unrelated cards in once the corpus")
    print("   grew. That is measurable WITHOUT authoring any query, by comparing")
    print("   the returned-set size and the top-1 margin with the layers off and")
    print("   on, over one query per card built from that card's own mechanisms.")
    print("")
    print("   NOT a recall measurement, and the reason is the point: a query taken")
    print("   from a card's own text is matched verbatim by that card, so recall@1")
    print("   comes out 26/26 with the layers off AND on. Measured, and it says")
    print("   nothing. Live-corpus recall needs a held-out query set written by a")
    print("   seat who has not read the cards; it cannot be derived from here.")
    import statistics as _st
    sel = {}
    for lab, lay in (("off", set()), ("on", S0.DEFAULT_LAYERS)):
        sizes, margins = [], []
        for c in (json.loads(p_.read_text(encoding="utf-8")) for p_ in live):
            got = S0.search(" ".join(c["mechanisms"]), limit=1000, layers=lay)
            sizes.append(len(got))
            if len(got) >= 2:
                margins.append(got[0][0] - got[1][0])
        sel[lab] = (sum(sizes) / len(sizes), max(sizes), _st.median(margins))
        print(f"     layers {lab:3}: returned set mean {sel[lab][0]:4.1f} of "
              f"{len(live)}, max {sel[lab][1]}, top1-top2 margin median "
              f"{sel[lab][2]:.0f}")
    if sel["on"][0] > sel["off"][0]:
        fails.append("the layers enlarge the mean returned set on the live corpus "
                     f"({sel['off'][0]:.1f} -> {sel['on'][0]:.1f}): an alias term "
                     "has become generic, re-check section F's threshold")
    else:
        print("     ok   the layers do not enlarge the returned set -- the stopword")
        print("          layer removes more than the alias layer adds. My worry is")
        print("          refuted by measurement, which is the useful outcome.")
    print(f"   REMAINING FINDING, not a failure: a typical query returns a mean")
    print(f"   of about half the corpus. The ranking separates well (margin above),")
    print(f"   so the defect is a long tail, not a wrong order. The remedy is a")
    print(f"   relative-score cutoff at display time, which is the engine owner's")
    print(f"   lane (HERMUZ, issue #1), not a scoring change made from here.")

    # --- cost, which ARGO asked for explicitly
    print("\nE. cost")
    t_none = sum(run(q, "none")[1] for q, _ in PAIRS) / len(PAIRS)
    t_all = sum(run(q, "all")[1] for q, _ in PAIRS) / len(PAIRS)
    print(f"   mean CLI wall time per query, {ncards} cards:")
    print(f"     original : {t_none*1000:7.1f} ms")
    print(f"     final    : {t_all*1000:7.1f} ms   "
          f"({t_all/t_none:.2f}x)")
    print("   Dominated by interpreter start-up, not by retrieval. No network, no")
    print("   model, no index: offline cost is the corpus read, linear in cards.")

    print("\n" + "=" * 72)
    if fails:
        print(f"FAIL ({len(fails)}):")
        for f in fails:
            print("  -", f)
        return 1
    print("PASS")
    print(f"  recall {o_hit}/{len(PAIRS)} -> {f_hit}/{len(PAIRS)};  "
          f"unsound {o_un}/{len(MEANINGLESS)} -> 0;  "
          f"false positives {o_fp}/{len(UNRELATED)} -> 0;  conflations 0/{len(NO_CONFLATE)}")
    print("  EVIDENCE CLASS: MEASURED, on a 5-card frozen fixture through the real")
    print("  CLI, plus section G's selectivity measurement on the live corpus.")
    print("  What is established on the live library is SELECTIVITY -- that the")
    print("  layers add no noise at this size. Live-corpus RECALL is still not")
    print("  established and cannot be, from queries derived from the cards.")
    return 0


if __name__ == "__main__":
    sys.exit(main())
