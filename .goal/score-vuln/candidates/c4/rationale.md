# c4 — defensive / error-handling

The function is already robust: the `isinstance` guard rejects `None`/`str`,
the leverage tiers are an exclusive `elif`, and fragility uses exact string
matches so anything else (lowercase, `None`, typos) falls through cleanly. No
real bug exists here, so I add only guards that make existing-but-implicit
behaviour explicit, keeping every output byte-identical.

- **bool exclusion** (`not isinstance(leverage, bool)`): `True`/`False` are
  `int` subclasses and pass the numeric guard, but `True >= 6.0` is `False`, so
  a bool already scored 0. Made explicit because a boolean flag is never a
  leverage ratio; behaviour unchanged.
- **NaN exclusion** (`leverage == leverage`, false only for NaN): NaN passes
  `isinstance` but `NaN >= 6.0`/`>= 5.0` are both `False`, so NaN already
  scored 0. The self-comparison is the stdlib-free NaN test, so no `math`
  import is needed. Behaviour unchanged.

All six golden cases (numeric tiers, exclusive elif, non-numeric fall-through,
`{leverage:g}` formatting, fragility scoring, banding) are preserved exactly.
