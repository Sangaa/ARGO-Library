# Bilingual retrieval baseline — 2026-11-26
Owner reported Claude discovered bilingual retrieval trouble. ARGO independently inspected tools/search.py blob 303df7c0c29ef9a604a1148f6903fbdf22ab16ab and card blob d9e42380d9bd68548b95040cbbe1282a07b7188d, main 94329578885a35eef9d4bdb541bd35c404764c0d. No Claude implementation was inspected; do not attribute a solution to ARGO.
## Measured bounded proxy
Locally reproduced exact tokenizer and weighted overlap on the card's indexed fields (not a full checkout/CLI test).
| Query | Score |
|---|---:|
| authentication | 3 |
| المصادقة | 0 |
| صلاحيات | 3 |
| الصلاحيات | 0 |
| اختبار مباشر | 3 |
| direct capability test | 11 |
| اختبار القدرة مباشرة | 3 |
| اختبار وسيط | 3 |
| إختبار | 0 |
| اختبار الصلاحيات | 3 |
| music composition | 0 |

Zero = omitted by current implementation. One-card fixture cannot measure ranking quality. Generic Arabic overlap does not establish semantic relevance; negative control passed only on this card.
## Recommended acceptance
Freeze bilingual paired queries, Arabic spelling/diacritics and definite article variants, mixed-language queries and unrelated negatives. Add distractor cards on authentication vs authorization and direct vs proxy testing. Separate conservative Unicode normalization, explicit bilingual concept aliases, and semantic ranking if warranted. Do not conflate authentication with authorization or blindly strip prefixes. Compare top-k relevance/recall, false positives, runtime and offline cost. Preserve original texts, report matched concepts, avoid translating away provenance. Claude owns solution exploration; ARGO contributes baseline, not competing search implementation. No paid CI.
