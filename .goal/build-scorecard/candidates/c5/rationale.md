# Candidate c5 — maximally-testable

Factored into three pure, stateless helpers the public function composes:

- `_recommend(composite) -> str` — the band map, isolated. Test the boundaries
  (60->OW, 40->NEUTRAL, 39->UW) without constructing any dict.
- `_composite(scored) -> int` — mean + `round`-to-int (half-even). Test
  58.5->58 / 59.5->60 directly; bool {True,False}->0 falls out for free.
- `_scored(cp1c_rt) -> list[dict]` — the numeric-percentile filter and ordering,
  testable in isolation (empty / none-numeric -> []).

`build_scorecard` only wires them together: extract -> guard empty (None) ->
composite -> recommend -> assemble. No hidden state, deterministic, public
signature unchanged. Scorecard still preserves percentile value+type via `c[...]`
and degrades optional fields with `.get` -> None; `peer_scope` defaults "peers".
Helpers reference module-level `_OVERWEIGHT/_UNDERWEIGHT` and `Optional`, both
already in scope at the splice site.
