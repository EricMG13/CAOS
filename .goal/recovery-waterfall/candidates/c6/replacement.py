def recovery_waterfall(tranches: List[dict], distressed_ev: float) -> List[dict]:
    """Run the absolute-priority recovery waterfall over a distressed enterprise value.

    Credit reading (what an analyst is verifying line by line):

    - ``distressed_ev`` is the *recovery enterprise value*: the whole pie a creditor
      committee has to split in a distress/restructuring scenario (upstream this is
      roughly 5x LTM EBITDA). It is the only value that ever gets distributed.
    - The ``tranches`` list arrives already ordered senior -> junior (the caller sorts
      on ``seniority_rank``). The *absolute priority rule* then applies in that order:
      a senior claim must be paid in full before any junior claim recovers a cent.
      This function trusts the incoming order and does NOT re-sort.
    - Each tranche's *claim* is its principal outstanding, ``amount_musd`` ($M). Walking
      senior -> junior we hand each tranche ``min(claim, value still on the table)`` and
      shrink the remaining value by the full claim. ``recovery_pct`` is that tranche's
      own recovery divided by its own claim -- cents on the dollar for THAT tranche, not
      for the structure.
    - An *unsized* senior tranche (claim unknown) makes everything below it
      indeterminate: if we don't know how much a senior layer absorbs, we cannot know
      how much value reaches the juniors behind it. So that tranche and ALL juniors are
      reported as null (None) rather than guessed. Crediting juniors against the full
      remaining EV -- as if the unsized senior claimed nothing -- would systematically
      over-state their recovery; refusing to guess is the conservative, defensible read.

    Worked check (RCF 200, 1L 800, 2L 200 against EV 1000): RCF takes 200 (100%),
    1L takes 800 (100%), 0 is left, 2L recovers 0 (0%) -- the 2L is wiped, as expected
    when senior claims (1000) exactly consume the pie (1000).
    """
    # Total value available to distribute, narrowed as senior claims are satisfied.
    # float() coerces ints/strings; a non-positive EV simply leaves nothing to hand out.
    remaining_ev = float(distressed_ev)

    waterfall: List[dict] = []

    # Once an unsized senior claim appears, every junior recovery is indeterminate.
    # This latch never resets: it is sticky senior -> junior, by design.
    indeterminate = False

    for tranche in tranches:
        claim = tranche["amount_musd"]  # principal outstanding ($M); KeyError if absent, by contract

        # A claim is "sized" only if it is a real positive number. None, 0, a negative,
        # or a non-numeric all count as unsized and trip the indeterminate cascade.
        claim_is_sized = isinstance(claim, (int, float)) and claim > 0
        if not claim_is_sized:
            indeterminate = True

        if indeterminate:
            # Unknown senior claim above (or at) this tranche -> recovery cannot be stated.
            waterfall.append({**tranche, "recovery_musd": None, "recovery_pct": None})
            continue

        # Absolute priority: this tranche takes the lesser of its claim and what is left.
        recovery = min(claim, remaining_ev) if remaining_ev > 0 else 0.0

        # The full claim is removed from the pie even if it was only partly satisfied;
        # remaining value is floored at 0 so it can never go negative.
        remaining_ev = max(0.0, remaining_ev - claim)

        waterfall.append({
            **tranche,  # fresh dict: preserve every original key, never mutate the input
            "recovery_musd": round(recovery, 1),
            # Recovery rate on THIS tranche's own claim. round(x, 1) is banker's
            # (half-even) rounding over the float repr -- e.g. 250/800 = 31.25 -> 31.2.
            "recovery_pct": round(100 * recovery / claim, 1),
        })

    return waterfall
