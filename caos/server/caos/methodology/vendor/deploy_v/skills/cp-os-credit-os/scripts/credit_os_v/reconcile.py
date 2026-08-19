"""Reconstruct a profile-bound Deploy V run from observed artifacts."""

from __future__ import annotations

from dataclasses import dataclass, field
from weakref import ReferenceType, ref

from credit_os.source import ReadOnlySource, SourceError

from . import envelope as env
from .identity import IdentityError, parse_route_node
from .routing import ACCEPTED, Route, RouteError, expected_upstream_digests

STALE = "STALE"
INVALID = "INVALID"
FOREIGN = "FOREIGN"
DUPLICATE = "DUPLICATE"
UNSTABLE = "UNSTABLE"
UNREADABLE = "UNREADABLE"


class ReconcileError(Exception):
    pass


class AuthorityDrifted(ReconcileError):
    """The artifacts were issued under an authority bundle that is no longer current."""


CANONICAL_HANDOFF_HEADINGS = (
    "Audit Summary",
    "Analysis",
    "Evidence Trace",
    "Source Registry",
    "Gaps & Conflicts",
    "QA Validation",
)


def canonical_handoff_content(
    text: str,
    expected_module: str | None = None,
) -> dict | None:
    """Return validated frontmatter, or ``None`` for a rejected handoff.

    ``validate_text`` already parses the restricted frontmatter and returns it
    on the validation result.  Returning those fields lets reconciliation reuse
    that parse instead of scanning every artifact a second time solely to
    recover ``module_id`` and the envelope fields.
    """
    if not isinstance(text, str) or not text or text.isspace():
        return None
    if "### Analytical appendix — complete canonical registers" not in text:
        return None
    try:
        import importlib

        validator = importlib.import_module("validate_handoff").validate_text
        result = validator(text, expected_module=expected_module)
        exit_code = result.exit_code
        fields = result.fields
        if exit_code != 0 or not isinstance(fields, dict):
            return None
        module_id = str(fields.get("module_id") or "") or None
    except (ImportError, AttributeError, TypeError, ValueError):
        return None
    if module_id and module_id.startswith("CP-L"):
        suffix = module_id[4:]
        if (
            f"TL{suffix}.1" not in text
            or f"TL{suffix}.2" not in text
            or f"TL{suffix}.3" not in text
            or f"TL{suffix}.4" not in text
        ):
            return None
    return fields


def canonical_handoff_content_valid(text: str, _module_id: str | None = None) -> bool:
    """Compatibility predicate for callers that only need accept/reject."""
    return canonical_handoff_content(text, expected_module=_module_id) is not None


@dataclass(frozen=True)
class ParsedArtifact:
    name: str
    declared: dict
    sha256: str


@dataclass
class Observation:
    name: str
    outcome: str
    detail: str = ""
    route_node_id: str | None = None
    module_id: str | None = None
    sha256: str | None = None


@dataclass(frozen=True)
class AcceptedArtifactProvenance:
    name: str
    route_node_id: str
    module_id: str
    sha256: str


@dataclass(frozen=True)
class ReconciledRunProvenance:
    run_id: str
    profile_id: str
    selection_id: str
    authority_bundle_sha256: str
    parent_run_id: str | None
    upgrade_source_sha256: str | None
    accepted_by_observation_id: tuple[tuple[int, AcceptedArtifactProvenance], ...]


@dataclass
class RunView:
    run_id: str
    profile_id: str
    selection_id: str
    authority_bundle_sha256: str
    parent_run_id: str | None = None
    upgrade_source_sha256: str | None = None
    observations: list[Observation] = field(default_factory=list)
    ambiguous_nodes: list[str] = field(default_factory=list)
    authority_drifted: bool = False

    def accepted(self) -> list[Observation]:
        return [item for item in self.observations if item.outcome == ACCEPTED]

    def problems(self) -> list[Observation]:
        return [item for item in self.observations if item.outcome != ACCEPTED]

    def as_routing_state(self) -> dict:
        return {
            "run_id": self.run_id,
            "profile_id": self.profile_id,
            "selection_id": self.selection_id,
            "authority_bundle_sha256": self.authority_bundle_sha256,
            "attempts": [
                {
                    "route_node_id": item.route_node_id,
                    "module_id": item.module_id,
                    "status": ACCEPTED,
                    "artifact_sha256": item.sha256,
                }
                for item in self.accepted()
            ],
        }


_RECONCILED_PROVENANCE: dict[
    int, tuple[ReferenceType[RunView], ReconciledRunProvenance]
] = {}


def _remember_reconciled_view(view: RunView) -> None:
    accepted = tuple(
        (
            id(item),
            AcceptedArtifactProvenance(
                name=item.name,
                route_node_id=item.route_node_id or "",
                module_id=item.module_id or "",
                sha256=item.sha256 or "",
            ),
        )
        for item in view.accepted()
        if item.route_node_id and item.module_id and item.sha256
    )
    provenance = ReconciledRunProvenance(
        run_id=view.run_id,
        profile_id=view.profile_id,
        selection_id=view.selection_id,
        authority_bundle_sha256=view.authority_bundle_sha256,
        parent_run_id=view.parent_run_id,
        upgrade_source_sha256=view.upgrade_source_sha256,
        accepted_by_observation_id=accepted,
    )
    view_id = id(view)

    def forget(_reference: ReferenceType[RunView]) -> None:
        _RECONCILED_PROVENANCE.pop(view_id, None)

    _RECONCILED_PROVENANCE[view_id] = (ref(view, forget), provenance)


def accepted_artifact_provenance(
    view: object, observation: object
) -> tuple[ReconciledRunProvenance, AcceptedArtifactProvenance]:
    """Return immutable provenance for an observation accepted by `reconcile()`.

    A hand-constructed RunView or a later mutation of its observations is never
    a substitute for the acceptance decision made during reconciliation.
    """
    if not isinstance(view, RunView) or not isinstance(observation, Observation):
        raise ReconcileError("upgrade source is not a reconciled accepted artifact")
    record = _RECONCILED_PROVENANCE.get(id(view))
    if record is None or record[0]() is not view:
        raise ReconcileError("run view was not minted by reconciliation")
    for observation_id, provenance in record[1].accepted_by_observation_id:
        if observation_id == id(observation):
            return record[1], provenance
    raise ReconcileError("observation was not accepted by reconciliation")


def _front_matter(text: str) -> dict:
    import importlib

    for name in ("validate_handoff", "tools.validate_handoff"):
        try:
            parser = importlib.import_module(name).parse_restricted_frontmatter
        except ImportError:
            continue
        return parser(text)[0]
    raise ReconcileError("validate_handoff is unavailable; the V package is incomplete")


def _parsed(
    source: ReadOnlySource,
    entries,
    content_validator=None,
    content_parser=None,
) -> tuple[list[ParsedArtifact], list[Observation]]:
    parsed, problems = [], []
    for entry in entries:
        try:
            read = source.read(entry)
            text = read.data.decode("utf-8")
            if content_parser is not None:
                declared = content_parser(text)
                if not isinstance(declared, dict):
                    problems.append(
                        Observation(entry.name, INVALID, "handoff content failed canonical validation")
                    )
                    continue
            else:
                declared = _front_matter(text)
                if content_validator is not None and not content_validator(
                    text, str(declared.get("module_id") or "") or None
                ):
                    problems.append(
                        Observation(entry.name, INVALID, "handoff content failed canonical validation")
                    )
                    continue
            parsed.append(ParsedArtifact(entry.name, declared, read.sha256))
        except (SourceError, UnicodeError, ValueError, TypeError) as exc:
            problems.append(Observation(entry.name, UNREADABLE, str(exc)))
    return parsed, problems


def _anchor(parsed: list[ParsedArtifact]) -> tuple[ParsedArtifact, dict]:
    """Anchor the post-consolidation run on its first live owner, CP-0."""
    candidates = [
        artifact
        for artifact in parsed
        if str(artifact.declared.get("module_id", "")).strip().upper() == "CP-0"
    ]
    if not candidates:
        raise ReconcileError("no CP-0 — SourceReadiness artifact; the run cannot be identified")
    if len(candidates) != 1:
        raise ReconcileError("a run folder must contain exactly one CP-0 — SourceReadiness anchor")
    try:
        anchor = env.read_anchor(candidates[0].declared)
    except (env.EnvelopeError, IdentityError) as exc:
        raise ReconcileError(f"CP-0 — SourceReadiness anchor is invalid: {exc}") from exc
    return candidates[0], anchor


def _observe_duplicate(view: RunView, records: list[ParsedArtifact], route_id: str) -> None:
    for record in records:
        view.observations.append(
            Observation(
                record.name,
                DUPLICATE,
                f"multiple artifacts claim {route_id}; none is accepted",
                route_id,
                str(record.declared.get("module_id") or "") or None,
                record.sha256,
            )
        )


def reconcile(
    source: ReadOnlySource,
    *,
    catalog: dict,
    current_authority_sha256: str,
    require_stability: bool = True,
    predicates: dict[str, bool] | None = None,
    content_validator=None,
    content_parser=None,
) -> RunView:
    """Reconcile in route order using declared occurrence IDs and exact lineage."""
    listing = source.list()
    if require_stability:
        stable, unstable = source.stable_set(listing.entries)
    else:
        stable, unstable = listing.entries, []
    parsed, parse_problems = _parsed(
        source, stable, content_validator, content_parser
    )
    preparation, anchor = _anchor(parsed)
    try:
        route = Route(catalog, anchor["profile_id"], anchor["selection_id"])
    except RouteError as exc:
        raise ReconcileError(f"CP-0 — SourceReadiness anchor selects no valid route: {exc}") from exc
    expected_preparation_route = route.nodes[0]["route_node_id"]
    if route.nodes[0].get("module_id") != "CP-0":
        raise ReconcileError("selected live route does not begin with CP-0 — SourceReadiness")
    if preparation.declared.get("credit_os_route_node_id") != expected_preparation_route:
        raise ReconcileError(
            "CP-0 — SourceReadiness occurrence does not match its anchored profile and selection"
        )
    if anchor["authority_bundle_sha256"] != current_authority_sha256:
        raise AuthorityDrifted(
            "artifact authority bundle changed; restart reconciliation under the current authority"
        )
    view = RunView(**anchor)
    view.observations.extend(parse_problems)
    view.observations.extend(
        Observation(name, INVALID, reason) for name, reason in listing.rejected
    )
    view.observations.extend(
        Observation(entry.name, UNSTABLE, "changed across the stability window")
        for entry in unstable
    )

    claims: dict[str, list[ParsedArtifact]] = {}
    unclaimed: list[ParsedArtifact] = []
    for record in parsed:
        route_id = record.declared.get("credit_os_route_node_id")
        try:
            node_profile, node_selection, _stage, _module = parse_route_node(route_id)
        except IdentityError:
            unclaimed.append(record)
            continue
        if (node_profile, node_selection) != (view.profile_id, view.selection_id):
            view.observations.append(
                Observation(
                    record.name,
                    FOREIGN,
                    "artifact route occurrence belongs to another profile or selection",
                    str(route_id),
                    str(record.declared.get("module_id") or "") or None,
                    record.sha256,
                )
            )
            continue
        claims.setdefault(str(route_id), []).append(record)

    accepted: dict[str, str] = {}
    cp0_route_node_id = route.by_module["CP-0"]["route_node_id"]
    for node in route.nodes:
        route_id = node["route_node_id"]
        records = claims.get(route_id, [])
        if len(records) > 1:
            _observe_duplicate(view, records, route_id)
            continue
        if not records:
            continue
        record = records[0]
        declared_module = str(record.declared.get("module_id", "")).strip().upper()
        if declared_module != node["module_id"]:
            view.observations.append(
                Observation(
                    record.name,
                    INVALID,
                    f"route occurrence requires {node['module_id']}, not {declared_module}",
                    route_id,
                    declared_module or None,
                    record.sha256,
                )
            )
            continue
        try:
            upstream = expected_upstream_digests(
                route, route_id, accepted, predicates=predicates
            )
            accepted_cp0_sha256 = (
                env.ZERO_SHA256
                if declared_module in {"CP-PARSE", "CP-0"}
                else accepted.get(cp0_route_node_id)
            )
            if accepted_cp0_sha256 is None:
                raise RouteError(
                    "downstream artifact is missing the accepted CP-0 upstream"
                )
            env.reproduce_and_match(
                record.declared,
                run_id=view.run_id,
                profile_id=view.profile_id,
                selection_id=view.selection_id,
                route_node_id=route_id,
                module_id=declared_module,
                module_name=node["module_name"],
                expected_output_filename=record.name,
                authority_bundle_sha256=view.authority_bundle_sha256,
                accepted_cp0_sha256=accepted_cp0_sha256,
                required_upstream_digests=upstream,
                parent_run_id=view.parent_run_id,
                upgrade_source_sha256=view.upgrade_source_sha256,
            )
        except (env.EnvelopeError, IdentityError, RouteError) as exc:
            outcome = STALE if "reproduce" in str(exc) or "upstream" in str(exc) else INVALID
            view.observations.append(
                Observation(
                    record.name,
                    outcome,
                    str(exc),
                    route_id,
                    declared_module,
                    record.sha256,
                )
            )
            continue
        accepted[route_id] = record.sha256
        view.observations.append(
            Observation(record.name, ACCEPTED, route_node_id=route_id,
                        module_id=declared_module, sha256=record.sha256)
        )

    processed_names = {item.name for item in view.observations}
    for record in unclaimed:
        if record.name not in processed_names:
            view.observations.append(
                Observation(
                    record.name,
                    INVALID,
                    "artifact has no valid profile-qualified route occurrence",
                    module_id=str(record.declared.get("module_id") or "") or None,
                    sha256=record.sha256,
                )
            )
    known_claims = set(route.by_node)
    for route_id, records in claims.items():
        if route_id in known_claims:
            continue
        for record in records:
            if record.name not in processed_names:
                view.observations.append(
                    Observation(record.name, FOREIGN, "route occurrence is not in this pathway",
                                route_id, str(record.declared.get("module_id") or "") or None,
                                record.sha256)
                )

    view.ambiguous_nodes = [
        node["route_node_id"] for node in route.nodes if node["route_node_id"] not in accepted
    ]
    _remember_reconciled_view(view)
    return view
