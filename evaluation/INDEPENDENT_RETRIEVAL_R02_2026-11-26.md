# Independent retrieval reproduction R02 — 2026-11-26
ARGO, bounded independent implementation of the lexical scoring formula in JavaScript (not execution of Python CLI or Claude's suite). Source: [Claude PR head](https://github.com/Sangaa/ARGO-Library/tree/be20107ca4f17db2a76d6597551001847da2ca18), engine blob 303df7c0c29ef9a604a1148f6903fbdf22ab16ab. Fixture blobs a542e731a5c30d6469817bbf735c2b7fe3a37cfd (proxy), 712b13fe2b5435c41a767571c362a3419594f1f3 (regenerated), 3a4c3c7c6af586e9f0ea58870c66258195d75445 (typed). JS lowercase and Unicode letters/numbers/underscore tokenizer; equivalent for observed fixture tokens, not claimed general Python casefold equivalence. Score 3*mechanism overlap +2*title overlap +body overlap. Scores below sorted descending (ties by ID).
| Query | Scores |
|---|---|
| تجربة الصلاحيات | none |
| الاختبار | none |
| هل جربنا نشوف الـAPI متاح ولا لأ | none |
| صلاحيات | 3 |
| اختبار | 3 |
| the a of is not an | 13,12,7 |
| the | 3,3,1 |
| a the is not | 10,9,6 |
| and the of to a in that it is not | 18,12,12 |
| the xqzzy wobble flurb | 3,3,1 |
| xqzzy wobble flurb | none |
| music composition | none |
| the music composition | 3,3,1 |
| measured a proxy instead of the thing itself | 11,10,8 |
| the a instead of is not an itself thing | 15,13,9 |
| المصادقة | none |
| the المصادقة | 3,3,1 |

D1 3/3 misses; D2 5/5 meaningless queries return all 3. Inversion 11→15. Claude's mechanism finding independently reproduced by ARGO's bounded proxy. Some exact scores quoted in defect cards differ from this pinned corpus (e.g. 13/11/9 vs 13/12/7; 17/13/10 vs 18/12/12). Preserve prior measurements as historical, bind each to its actual fixture revision, rerun exact Python and reconcile before calling numeric values verified. No repair or semantic accuracy established.
## Experience reuse
Source author CLAUDE: PR #3 at pinned head above. Consumer ARGO; exact first-read time/session ID unavailable. Borrowed mechanism: freeze corpus separately from documentation of failures; reused its three fixtures in independent scoring. Outcome: both failure classes reproduced and numeric discrepancy exposed. Evidence: table and blob IDs above. Status OUTCOME_EVIDENCED for this bounded reproduction only, causal improvement untested. New lesson: freeze the fixture revision as well as query text when comparing scores.