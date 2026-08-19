# Verification Gate — results

Target: `altman_z_double_prime` @ `caos/server/engine/distress.py:36-55`
Baseline: contract 18/18 green + 7 existing distress tests green on the
unmodified unit. **The contract was then HARDENED by an adversarial gap-hunt**
(3 independent critics) to 28 cases — see below. Gate per candidate: splice over
lines 36-55 → `py_compile` → 28-case contract + 7 existing distress tests →
restore (byte-exact, asserted).

## Adversarial contract hardening (ultracode)

A workflow ran 3 completeness critics against the original 18 cases. They found
**10 real holes** — inputs where a plausible "cleaner" rewrite mistake would
ship silently. Every value was re-VERIFIED against the live function (not trusted
from the critics' hand-math); the verification caught one wrong hand-computation:

| gap class | isolating input | live result | a rewrite mistake it now catches |
|-----------|-----------------|-------------|-----------------------------------|
| X2↔X3 weight swap | X1=X4=0, X2=.5, X3=.1 | (5.55, safe) | swap 3.26↔6.72 / RE↔EBIT numerators |
| X3↔X4 weight swap | X1=X2=0, X3=.1, X4=.8 | (4.76, safe) | swap 6.72↔1.05 |
| X1↔X3 weight swap | X2=X4=0, X1=.4, X3=.05 | (6.21, safe) | swap 6.56↔6.72 (near-equal, survives rounding elsewhere) |
| X1↔X2 weight swap | X3=X4=0, X1=.5, X2=.1 | (6.86, safe) | swap 6.56↔3.26 (mutant stays in 'safe', no zone flip) |
| **half-even rounding** | raw z=3.775 | **(3.77, safe)** | half-up / Decimal(HALF_UP) → 3.78 |
| intermediate rounding | X4=0.025 near boundary | (2.6, grey) | round(x4,2) first → 2.61 safe (zone flip) |
| **1dp vs 2dp** | raw z=2.645 | **(2.64, safe)** | round(z,1) → 2.6 grey (safe→grey demotion) |
| X4 denom @ boundary | TA=300,TL=100,BE=-100 | (2.2, grey) | X4=BE/TA → 2.9 safe (zone flip) |
| X4 denom value | TA=100,TL=400,BE=200 | (3.77, safe) | X4=BE/TA → 5.35 |
| X4 denom unit | TA=200,TL=100,BE=100 | (4.3, safe) | X4=BE/TA → 3.78 |

> Caught hand-math error: the X4-denom-value critic claimed (3.78); the live
> function returns **3.77** (raw 3.775 stored as 3.77499… → round down). Froze 3.77.

## Gate

| cand | objective          | compiles | 28-case contract | existing distress (7) | verdict |
|------|--------------------|----------|------------------|-----------------------|---------|
| c1   | minimal-diff       | ✅       | ✅ 28/28         | ✅ 7/7                | **ADVANCE** (no-op) |
| c2   | readability-first  | ✅       | ✅ 28/28         | ✅ 7/7                | **ADVANCE** |
| c3   | performance-first  | ✅       | ✅ 28/28         | ✅ 7/7                | **ADVANCE** (no-op) |
| c4   | defensive          | ✅       | ✅ 28/28         | ✅ 7/7                | **ADVANCE** |
| c5   | maximally-testable | ✅       | ✅ 28/28         | ✅ 7/7                | **ADVANCE** |
| c6   | domain-legible     | ✅       | ✅ 28/28         | ✅ 7/7                | **ADVANCE** |

All six provably equivalent on the hardened contract (incl. all 10 mutation
isolators). c1 and c3 returned byte-identical no-ops (honest — the original is
already optimal for those objectives). All advance to judging.
