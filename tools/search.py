"""Local deterministic lexical retrieval; no network, no learning claim.

Bilingual since 2026-11-26 (CLAUDE, issue #1, ARGO baseline
evaluation/BILINGUAL_BASELINE_2026-11-26.md, which assigns search solution
exploration to CLAUDE and asks for conservative normalisation, bilingual concept
aliases and semantic ranking to be kept SEPARATE).

So each repair is its own layer with its own flag, and every layer can be turned
off independently, because a change you cannot switch off is a change you cannot
measure. Defaults reproduce the recommended configuration; `--layers` overrides
it, and `--layers none` reproduces the ORIGINAL pre-2026-11-26 engine exactly, so
the before/after comparison is run rather than remembered.

LAYER 1  norm      conservative Unicode normalisation of Arabic (NOT prefix
                   stripping): unify the alef forms, drop tatweel, drop harakat,
                   unify alef maqsura. This is what makes إختبار match اختبار.
LAYER 2  article   the definite article, handled ADDITIVELY: a token beginning
                   ال also indexes its remainder, so الصلاحيات matches صلاحيات
                   WITHOUT destroying الله, اللغة or any word whose ال is part of
                   the stem -- the original token is always kept. ARGO's baseline
                   says do not blindly strip prefixes; adding a variant is not
                   stripping one.
LAYER 3  stop      discount function words in both languages before scoring.
LAYER 4  content   a card must share at least one MEANING-CARRYING token with the
                   query to be returned at all, whatever its score. Function words
                   do not count; an explicit alias concept does. Without this,
                   matching on articles alone returns the whole corpus (card
                   stopword-scoring-20261126).
LAYER 5  alias     explicit bilingual concept aliases, and ONLY where the concepts
                   are the same concept. authentication/مصادقة are aliases;
                   authorization/تخويل are aliases; the two groups are NOT
                   connected, because ARGO's baseline says not to conflate them
                   and fixtures fx-authn / fx-authz exist to catch it.

Also new: --root. The engine previously derived its corpus from its own file
location, so it could only ever read ../cards and could NOT be pointed at a test
corpus -- which is why it had never been evaluated against one. Its own test
harness found this by returning live cards while claiming to query a fixture.
An engine that cannot be aimed at a corpus cannot be measured on one.

No semantic ranking. No embeddings. No network. Nothing is learned or stored.
"""
import argparse
import json
import re
import unicodedata
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]

ALL_LAYERS = ("norm", "article", "stop", "content", "alias")
DEFAULT_LAYERS = frozenset(ALL_LAYERS)

# ---------------------------------------------------------------- layer 1: norm
_HARAKAT = re.compile(r"[ؐ-ًؚ-ٰٟۖ-ۭ]")
_TATWEEL = "ـ"
_ALEF_MAP = str.maketrans({
    "أ": "ا", "إ": "ا", "آ": "ا",  # أ إ آ -> ا
    "ٱ": "ا",                                          # ٱ   -> ا
    "ى": "ي",                                          # ى   -> ي
})
# ة -> ه is deliberately NOT applied: it merges distinct words often enough that
# it belongs with aliases, not with conservative normalisation.


def normalize_ar(s):
    s = unicodedata.normalize("NFKC", s)
    s = s.replace(_TATWEEL, "")
    s = _HARAKAT.sub("", s)
    return s.translate(_ALEF_MAP)


# ------------------------------------------------------------- layer 3: stop
STOP = set("""
a an the is are was were be been being am do does did of to in into on at as by
for from with without that this these those there here it its his her their our
your my not no and or but if else than then so such which who whom whose what
when where why how can could may might must shall should will would have has had
i you he she we they me him us them one two also very more most much many
هل ما مش لا ولا و في من على عن الى إلى ده دي ديه دا اللي الذي التي يا كده كدة
برضه بس انا أنا انت أنت هو هي احنا إحنا هم هما كان كانت يكون تكون ان أن إن
عشان علشان لأن لان بعد قبل مع عند لو كل بعض اي أي ايه إيه فيه فيها له لها
""".split())

# ------------------------------------------------------------ layer 5: alias
# Each group is ONE concept in two languages. Groups are NEVER merged: ARGO's
# baseline says not to conflate authentication with authorization, and fixtures
# fx-authn / fx-authz exist to catch it if a change does.
#
# WHAT IS DELIBERATELY NOT HERE, and why. The first version of this list included
# the generic English words `scope`, `test`, `direct` and `measure`. Measured
# against the live 7-card corpus, those appear in 3, 4, 4 and 4 cards
# respectively -- because every research card has a SCOPE field, describes a
# TEST, contrasts DIRECT with indirect, and reports a MEASUREMENT. The alias layer
# turned each of them into a false-positive generator: a query for صلاحيات
# returned two of TOTO's number-theory cards on the strength of the token `scope`
# alone, with no real shared term.
#
# The 5-card fixture could not have caught it -- none of its cards used those
# words in a research sense -- which is the "a 5-card corpus cannot measure
# ranking quality" limitation in this suite's own PASS message, biting within
# minutes of being written. A live-corpus precision check is now part of
# tests/retrieval_bilingual_R02.py so the next one is caught by measurement.
#
# RULE: an alias term must be unambiguous IN THIS CORPUS. A term that appears in
# half the cards is not a concept marker, it is a stopword with ambitions.
ALIAS_GROUPS = [
    {"authentication", "authenticate", "authn", "مصادقة", "هوية",
     "login", "signin", "تسجيل-دخول"},
    {"authorization", "authorize", "authz", "تخويل", "permission", "permissions",
     "صلاحيات", "privilege"},
    {"capability", "قدرة", "قدرات"},
    {"اختبار", "تجربة", "فحص"},
    {"مباشر", "مباشرة"},
    {"وسيط", "غير-مباشر"},
    {"retrieval", "استرجاع", "بحث"},
    {"قياس", "مقياس"},
    {"reproducibility", "deterministic", "determinism", "تكرار", "استنساخ"},
]
_ALIAS = {}
for _i, _grp in enumerate(ALIAS_GROUPS):
    for _w in _grp:
        _ALIAS.setdefault(_w, set()).add(f"@c{_i}")


def tokens(s, layers=DEFAULT_LAYERS):
    """Token set for a string, under the enabled layers."""
    if "norm" in layers:
        s = normalize_ar(s)
    out = set(re.findall(r"\w+", s.casefold()))
    if "article" in layers:
        # additive: keep the original token AND its article-stripped remainder
        for t in list(out):
            if t.startswith("ال") and len(t) > 4:
                out.add(t[2:])
    if "alias" in layers:
        for t in list(out):
            out |= _ALIAS.get(t, set())
    return out


def content(toks, layers=DEFAULT_LAYERS):
    """Tokens that carry meaning: function words and alias markers removed."""
    if "stop" not in layers:
        return toks
    return {t for t in toks if t not in STOP}


def _fields(c):
    return (" ".join(c["mechanisms"]),
            c["title"],
            " ".join(c[k] for k in ("problem", "failure", "correction", "transfer")))


def search(query, root=ROOT, limit=5, layers=DEFAULT_LAYERS, with_concepts=False):
    """Ranked cards.

    Returns (score, card) pairs, as it always has. `with_concepts=True` returns
    (score, card, matched) triples instead.

    The signature is backward compatible on purpose. An earlier draft of this
    change returned triples unconditionally, which broke
    tests/retrieval_soundness_R01.py on the first run and would silently have
    broken any other seat's consumer the same way. A shared tool does not get to
    change the shape of its return value to add a feature.
    """
    layers = frozenset(layers)
    q = tokens(query, layers)
    qc = content(q, layers)
    results = []
    for p in sorted((root / "cards").glob("*.json")):
        c = json.loads(p.read_text(encoding="utf-8"))
        mech, title, body = (tokens(x, layers) for x in _fields(c))
        if "stop" in layers:
            mech, title, body = (content(x, layers) for x in (mech, title, body))
            qq = qc
        else:
            qq = q
        score = 3 * len(qq & mech) + 2 * len(qq & title) + len(qq & body)
        if not score:
            continue
        shared = qq & (mech | title | body)
        if "content" in layers:
            # A card must share something that CARRIES MEANING. An alias marker
            # counts: it is an explicit concept identity, which is the opposite of
            # a function word.
            #
            # It did not, at first. The content requirement demanded a literal
            # shared token and rejected alias-only matches, which blocked exactly
            # the case the alias layer exists for -- so layer 5 measured zero
            # benefit and was inert. Two layers written in the same change
            # contradicting each other; found by probing whether the alias layer
            # did anything at all rather than by assuming it did.
            if not shared:
                continue
        results.append((score, c, sorted(shared)))
    results.sort(key=lambda x: (-x[0], x[1]["id"]))
    results = results[:limit]
    if with_concepts:
        return results
    return [(s_, c_) for s_, c_, _ in results]


def parse_layers(spec):
    if spec is None:
        return DEFAULT_LAYERS
    spec = spec.strip().lower()
    if spec in ("none", "off", "original"):
        return frozenset()
    if spec == "all":
        return DEFAULT_LAYERS
    chosen = {s.strip() for s in spec.split(",") if s.strip()}
    bad = chosen - set(ALL_LAYERS)
    if bad:
        raise SystemExit(f"unknown layer(s): {sorted(bad)}; "
                         f"choose from {list(ALL_LAYERS)}, 'all', or 'none'")
    return frozenset(chosen)


if __name__ == "__main__":
    a = argparse.ArgumentParser(description=__doc__.split("\n")[0])
    a.add_argument("query")
    a.add_argument("--limit", type=int, default=5)
    a.add_argument("--layers", default=None,
                   help="comma list of %s, or 'all' (default), or 'none' to "
                        "reproduce the original engine" % (list(ALL_LAYERS),))
    a.add_argument("--concepts", action="store_true",
                   help="print the matched tokens/concepts instead of the card")
    a.add_argument("--root", default=None,
                   help="corpus root containing cards/ (default: the repository "
                        "root next to this script)")
    args = a.parse_args()
    layers = parse_layers(args.layers)
    root = Path(args.root).resolve() if args.root else ROOT
    if not (root / "cards").is_dir():
        raise SystemExit(f"no cards/ directory under {root}")
    for score, card, shared in search(args.query, root=root, limit=args.limit,
                                      layers=layers, with_concepts=True):
        if args.concepts:
            print(json.dumps({"score": score, "id": card["id"],
                              "matched": shared}, ensure_ascii=False))
        else:
            print(json.dumps({"score": score, **card}, ensure_ascii=False))
