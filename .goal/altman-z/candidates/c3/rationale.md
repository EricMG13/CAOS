# c3 — performance-first (honest)

Objective was "minimize work," but there is no work to minimize here. The
function runs once per issuer (called from edgar_cp1.py:295), does 4 divides and
a weighted sum, and returns. That is nanoseconds, not a hot path.

I evaluated the usual micro-optimizations and rejected each as a real-world
no-op that only costs clarity/correctness:

- Precomputing `1/total_assets` to trade 3 divides for 3 multiplies: saves
  nothing measurable once per issuer, and changing the float order of operations
  risks perturbing the `round(.., 2)` half-even result on a golden boundary case
  (e.g. 2.6/1.1). Not worth it.
- Inlining `zone_for` to skip one call: saves a single function call, hurts the
  "show your work" transparency the module is built around, and risks flipping a
  strict-inequality boundary if transcribed wrong.

The early-return guard already short-circuits the only invalid inputs. The
honest performance-optimal change is therefore the identity: the current code is
already minimal for its call frequency. I return it byte-for-byte so all golden
cases and boundary semantics are provably preserved, with zero risk.
