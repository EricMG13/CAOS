"""Pure, read-only CP-OS navigation runtime copied into generated packages."""
from __future__ import annotations

import copy
import hashlib
import json
import re
from dataclasses import dataclass
from types import MappingProxyType
from typing import Any, Callable, Mapping, Sequence

from credit_os.identity import sanitize_display
from validate_handoff import validate_text


READINESS = frozenset({
    "READY", "READY_WITH_LIMITATIONS", "CONDITIONAL", "BLOCKED"
})
RUNNABLE = frozenset({"READY", "READY_WITH_LIMITATIONS"})
SUPPRESSED_MODULES = frozenset({"CP-0", "CP-X", "CP-PARSE"})
COMMAND_RE = re.compile(r"^Run (CP-(?:\d+[A-Z]?|[A-Z][A-Z0-9-]*))(?:[ \t]+.+)?$")
SEPARATOR_RE = re.compile(r"^:?-{3,}:?$")
NEW_HEADERS = (
    "Sequence", "Module", "Candidate command", "Exact command",
    "Source files to attach", "Upstream handoff", "Readiness",
    "Why now / blocker",
)
NEW_HEADERS_ALT = (*NEW_HEADERS[:-1], "Why now or blocker")
LEGACY_HEADERS = (
    "Sequence", "Module", "Exact command", "Source files to attach",
    "Upstream handoff", "Readiness", "Why now / blocker",
)
LEGACY_HEADERS_ALT = (*LEGACY_HEADERS[:-1], "Why now or blocker")
LEGACY_HEADERS_SNAKE = (
    "sequence", "module_id", "exact_command", "source_files_to_attach",
    "upstream_handoff", "readiness", "why_now_or_blocker",
)


class NavigationError(ValueError):
    """Raised when an authority or canonical CP-0 context fails closed."""


@dataclass(frozen=True)
class Layer:
    layer_id: str
    label: str


@dataclass(frozen=True)
class Module:
    module_id: str
    display: str
    description: str
    layer_id: str | None
    skip_implication: str | None
    navigable: bool


@dataclass(frozen=True)
class Catalog:
    layers: tuple[Layer, ...]
    modules: Mapping[str, Module]
    dependencies: frozenset[tuple[str, str]]
    superseded_modules: frozenset[str]


@dataclass(frozen=True)
class Artifact:
    name: str
    text: str
    sha256: str
    fields: Mapping[str, Any] | None
    accepted: bool
    exit_code: int


@dataclass(frozen=True)
class Recommendation:
    sequence: int
    module_id: str
    readiness: str
    candidate_command: str
    exact_command: str
    why_now_or_blocker: str

    @property
    def runnable(self) -> bool:
        return self.readiness in RUNNABLE


@dataclass(frozen=True)
class Context:
    key: str
    identity_field: str
    identity: str
    period: str
    run_id: str
    artifact_name: str
    digest: str
    recommendations: tuple[Recommendation, ...]
    layers: tuple[str, ...]
    completed: frozenset[str]


@dataclass(frozen=True)
class Discovery:
    contexts: tuple[Context, ...]
    invalid_artifacts: tuple[str, ...]
    conflicting_contexts: tuple[tuple[str, str, str, str], ...]


@dataclass(frozen=True)
class NavigationState:
    status: str
    context_key: str | None = None
    layer_index: int = 0
    message: str | None = None
    selection_fingerprint: str | None = None
    selection_count: int | None = None

    def as_dict(self) -> dict[str, object]:
        return {
            "status": self.status,
            "context_key": self.context_key,
            "layer_index": self.layer_index,
            "selection_fingerprint": self.selection_fingerprint,
            "selection_count": self.selection_count,
        }


@dataclass(frozen=True)
class NavigationResult:
    status: str
    card: str
    state: NavigationState
    discovery: Discovery


def _nonempty(value: object, label: str) -> str:
    if not isinstance(value, str) or not value.strip():
        raise NavigationError(f"{label} must be a non-empty string")
    return value.strip()


def _safe(value: str, *, limit: int = 200) -> str:
    """Sanitize one rendered line without joining words across controls."""
    return sanitize_display(re.sub(r"[\r\n\t]+", " ", value), limit=limit)


def validate_catalog(raw: Mapping[str, Any]) -> Catalog:
    """Validate schema 1.0 and return immutable navigation lookups."""
    if not isinstance(raw, Mapping):
        raise NavigationError("catalog must be an object")
    navigation = raw.get("navigation")
    modules_raw = raw.get("modules")
    if not isinstance(navigation, Mapping) or navigation.get("schema_version") != "1.0":
        raise NavigationError("catalog navigation schema_version must be 1.0")
    if not isinstance(modules_raw, list):
        raise NavigationError("catalog modules must be a list")

    layers_raw = navigation.get("layers")
    if not isinstance(layers_raw, list) or not layers_raw:
        raise NavigationError("catalog navigation layers must be a non-empty list")
    layers: list[Layer] = []
    layer_ids: set[str] = set()
    for index, item in enumerate(layers_raw):
        if not isinstance(item, Mapping) or set(item) != {"layer_id", "label"}:
            raise NavigationError(f"navigation layer {index} has an invalid shape")
        layer_id = _nonempty(item["layer_id"], f"navigation layer {index} ID")
        label = _nonempty(item["label"], f"navigation layer {index} label")
        if layer_id in layer_ids:
            raise NavigationError(f"duplicate navigation layer: {layer_id}")
        layer_ids.add(layer_id)
        layers.append(Layer(layer_id, label))

    modules: dict[str, Module] = {}
    for index, item in enumerate(modules_raw):
        if not isinstance(item, Mapping):
            raise NavigationError(f"catalog module {index} must be an object")
        module_id = _nonempty(item.get("module_id"), f"catalog module {index} ID")
        if module_id in modules:
            raise NavigationError(f"duplicate catalog module: {module_id}")
        navigable = item.get("navigable")
        if not isinstance(navigable, bool):
            raise NavigationError(f"{module_id}: navigable must be boolean")
        display = _nonempty(item.get("display"), f"{module_id}: display")
        description = _nonempty(item.get("description"), f"{module_id}: description")
        layer_id = item.get("layer_id")
        implication = item.get("skip_implication")
        if navigable:
            if not isinstance(layer_id, str) or layer_id not in layer_ids:
                raise NavigationError(f"{module_id}: navigable module has no known layer")
            implication = _nonempty(implication, f"{module_id}: skip implication")
        elif layer_id is not None or implication is not None:
            raise NavigationError(f"{module_id}: non-navigable metadata must be null")
        modules[module_id] = Module(
            module_id, display, description, layer_id, implication, navigable
        )

    dependencies_raw = navigation.get("dependencies")
    if not isinstance(dependencies_raw, list):
        raise NavigationError("catalog navigation dependencies must be a list")
    dependencies: set[tuple[str, str]] = set()
    layer_order = {layer.layer_id: index for index, layer in enumerate(layers)}
    for index, item in enumerate(dependencies_raw):
        if not isinstance(item, Mapping) or set(item) != {"source", "target"}:
            raise NavigationError(f"navigation dependency {index} has an invalid shape")
        edge = (
            _nonempty(item["source"], f"dependency {index} source"),
            _nonempty(item["target"], f"dependency {index} target"),
        )
        if edge in dependencies or edge[0] == edge[1]:
            raise NavigationError(f"invalid or duplicate navigation dependency: {edge}")
        endpoints = [modules.get(endpoint) for endpoint in edge]
        if any(module is None or not module.navigable for module in endpoints):
            raise NavigationError(f"dependency endpoint is not navigable: {edge}")
        source_module, target_module = endpoints
        assert source_module is not None and target_module is not None
        assert source_module.layer_id is not None and target_module.layer_id is not None
        if layer_order[target_module.layer_id] < layer_order[source_module.layer_id]:
            raise NavigationError(f"dependency moves backward through layers: {edge}")
        dependencies.add(edge)
    superseded_raw = raw.get("superseded_module_ids", {})
    if not isinstance(superseded_raw, Mapping):
        raise NavigationError("catalog superseded_module_ids must be an object")
    superseded_modules = frozenset(
        _nonempty(module_id, "superseded module ID")
        for module_id in superseded_raw
    )
    if superseded_modules & modules.keys():
        raise NavigationError("catalog module cannot be both live and superseded")
    return Catalog(
        tuple(layers), MappingProxyType(modules), frozenset(dependencies),
        superseded_modules,
    )


def validate_artifacts(
    artifacts: Mapping[str, str],
    *,
    validator: Callable[..., Any] = validate_text,
) -> tuple[Artifact, ...]:
    """Validate each supplied snapshot body exactly once, in name order."""
    if not isinstance(artifacts, Mapping):
        raise NavigationError("artifacts must be an object")
    if not all(isinstance(name, str) and isinstance(text, str) for name, text in artifacts.items()):
        raise NavigationError("artifact names and bodies must be strings")
    validated: list[Artifact] = []
    for name in sorted(artifacts):
        text = artifacts[name]
        result = validator(text, filename=name)
        fields = result.fields if isinstance(result.fields, dict) else None
        exit_code = result.exit_code
        validated.append(Artifact(
            name=name,
            text=text,
            sha256=hashlib.sha256(text.encode("utf-8")).hexdigest(),
            fields=_deep_freeze(fields) if fields is not None else None,
            accepted=exit_code == 0,
            exit_code=exit_code,
        ))
    return tuple(validated)


def _deep_freeze(value: Any) -> Any:
    """Detach validator-owned values and make nested decision inputs immutable."""
    if isinstance(value, Mapping):
        return MappingProxyType({key: _deep_freeze(item) for key, item in value.items()})
    if isinstance(value, (list, tuple)):
        return tuple(_deep_freeze(item) for item in value)
    if isinstance(value, (set, frozenset)):
        return frozenset(_deep_freeze(item) for item in value)
    return copy.deepcopy(value)


def _unfenced_lines(text: str) -> tuple[str, ...]:
    lines: list[str] = []
    fence_char: str | None = None
    fence_length = 0
    for line in text.splitlines():
        stripped = line.lstrip(" ")
        indentation = len(line) - len(stripped)
        marker = re.match(r"(`{3,}|~{3,})", stripped) if indentation <= 3 else None
        if fence_char is not None:
            if indentation <= 3 and re.fullmatch(
                re.escape(fence_char) + "{" + str(fence_length) + ",}[ \t]*",
                stripped,
            ):
                fence_char = None
            continue
        if marker:
            fence_char = marker.group(1)[0]
            fence_length = len(marker.group(1))
            continue
        lines.append(line)
    return tuple(lines)


def _table_cells(line: str) -> tuple[str, ...]:
    """Split a Markdown row while treating backslash-escaped pipes as data."""
    stripped = line.strip()
    if not stripped.startswith("|"):
        return ()
    cells: list[str] = []
    cell: list[str] = []
    for char in stripped[1:]:
        if char != "|":
            cell.append(char)
            continue
        backslashes = 0
        for preceding in reversed(cell):
            if preceding != "\\":
                break
            backslashes += 1
        if backslashes % 2:
            cell.pop()
            cell.append("|")
            continue
        cells.append("".join(cell).strip())
        cell = []
    if cell or not stripped.endswith("|"):
        cells.append("".join(cell).strip())
    return tuple(cells)


def _matching_header(cells: tuple[str, ...]) -> tuple[str, ...] | None:
    for headers in (
        NEW_HEADERS, NEW_HEADERS_ALT, LEGACY_HEADERS, LEGACY_HEADERS_ALT,
        LEGACY_HEADERS_SNAKE,
    ):
        if cells == headers:
            return headers
    return None


def _unwrap_command(value: str, module_id: str) -> str:
    """Accept plain commands or one complete single-backtick code wrapper."""
    tick_count = value.count("`")
    if tick_count == 0:
        return value
    if (
        tick_count == 2
        and len(value) > 2
        and value.startswith("`")
        and value.endswith("`")
    ):
        return value[1:-1]
    raise NavigationError(f"{module_id}: command has malformed inline-code wrapper")


def parse_t8(text: str, catalog: Catalog) -> tuple[Recommendation, ...]:
    """Extract exactly one visible canonical T8 table and validate every row."""
    lines = _unfenced_lines(text)
    match_count = 0
    match_index = -1
    headers: tuple[str, ...] | None = None
    for index, line in enumerate(lines[:-1]):
        matched_headers = _matching_header(_table_cells(line))
        if matched_headers is not None:
            match_count += 1
            if match_count == 1:
                match_index = index
                headers = matched_headers
    if match_count != 1:
        raise NavigationError(
            "CP-0 must contain exactly one unfenced canonical T8 table; "
            f"found {match_count}"
        )
    assert headers is not None
    separators = _table_cells(lines[match_index + 1])
    if len(separators) != len(headers) or not all(SEPARATOR_RE.fullmatch(cell) for cell in separators):
        raise NavigationError("CP-0 T8 separator row is invalid")

    is_legacy = len(headers) == len(LEGACY_HEADERS)
    rows: list[Recommendation] = []
    seen_sequences: set[int] = set()
    seen_modules: set[str] = set()
    duplicate_sequence = False
    duplicate_module = False
    ordered = True
    previous_sequence: int | None = None
    row_index = match_index + 2
    while row_index < len(lines):
        cells = _table_cells(lines[row_index])
        if not cells:
            break
        if len(cells) != len(headers):
            raise NavigationError("CP-0 T8 row width does not match its header")
        try:
            sequence = int(cells[0])
        except ValueError:
            raise NavigationError("CP-0 T8 sequence must be a positive integer") from None
        if sequence < 1:
            raise NavigationError("CP-0 T8 sequence must be a positive integer")
        module_id = cells[1]
        if module_id in SUPPRESSED_MODULES or module_id in catalog.superseded_modules:
            row_index += 1
            continue
        if is_legacy:
            exact_command, readiness, reason = cells[2], cells[5], cells[6]
            exact_command = _unwrap_command(exact_command, module_id)
            if readiness in RUNNABLE:
                candidate_command = exact_command
            elif COMMAND_RE.fullmatch(exact_command):
                candidate_command = exact_command
                exact_command = "DO NOT RUN"
            elif readiness in READINESS and exact_command == "DO NOT RUN":
                raise NavigationError(
                    f"{module_id}: legacy non-runnable row has no candidate "
                    "command; rerun CP-0 with the current T8 contract"
                )
            else:
                candidate_command = exact_command
        else:
            candidate_command, exact_command = cells[2], cells[3]
            candidate_command = _unwrap_command(candidate_command, module_id)
            exact_command = _unwrap_command(exact_command, module_id)
            readiness, reason = cells[6], cells[7]
        module = catalog.modules.get(module_id)
        if module is None or not module.navigable or module.layer_id is None:
            raise NavigationError(f"CP-0 recommends unknown or non-navigable module: {module_id}")
        if readiness not in READINESS:
            raise NavigationError(f"{module_id}: unsupported readiness {readiness!r}")
        command_match = COMMAND_RE.fullmatch(candidate_command)
        if command_match is None or command_match.group(1) != module_id:
            raise NavigationError(f"{module_id}: candidate command does not match module")
        if readiness in RUNNABLE and exact_command != candidate_command:
            raise NavigationError(f"{module_id}: runnable exact command must equal candidate command")
        if readiness not in RUNNABLE and exact_command != "DO NOT RUN":
            raise NavigationError(f"{module_id}: non-runnable exact command must be DO NOT RUN")
        if not reason.strip():
            raise NavigationError(f"{module_id}: why-now or blocker is empty")
        duplicate_sequence |= sequence in seen_sequences
        duplicate_module |= module_id in seen_modules
        seen_sequences.add(sequence)
        seen_modules.add(module_id)
        if previous_sequence is not None and sequence < previous_sequence:
            ordered = False
        previous_sequence = sequence
        rows.append(Recommendation(
            sequence, module_id, readiness, candidate_command,
            exact_command, reason.strip(),
        ))
        row_index += 1
    if not rows:
        raise NavigationError("CP-0 T8 has no navigable recommendation rows")
    if duplicate_sequence:
        raise NavigationError("CP-0 T8 contains duplicate sequences")
    if duplicate_module:
        raise NavigationError("CP-0 T8 contains duplicate modules")
    if ordered:
        return tuple(rows)
    return tuple(sorted(rows, key=lambda row: row.sequence))


def _identity(fields: Mapping[str, Any]) -> tuple[str, str]:
    for field in ("scope_key", "issuer_id"):
        value = fields.get(field)
        if isinstance(value, (str, int, float)) and not isinstance(value, bool) and str(value).strip():
            return field, str(value).strip()
    raise NavigationError("CP-0 has no issuer_id or scope_key")


def _completion_matches(
    artifact: Artifact,
    *,
    recommendation: Recommendation,
    identity_field: str,
    identity: str,
    period: str,
    cp0_run_id: str,
    conflicting_artifacts: frozenset[tuple[str, str, str, str, str]],
) -> bool:
    if not artifact.accepted or artifact.fields is None or not recommendation.runnable:
        return False
    fields = artifact.fields
    artifact_run_id = str(fields.get("run_id", ""))
    if (
        fields.get("module_id") != recommendation.module_id
        or str(fields.get(identity_field, "")) != identity
        or fields.get("reporting_period") != period
        or (
            recommendation.module_id,
            identity_field,
            identity,
            period,
            artifact_run_id,
        ) in conflicting_artifacts
    ):
        return False
    upstream = fields.get("upstream_artifacts_used")
    if not isinstance(upstream, Sequence) or isinstance(upstream, (str, bytes)):
        return False
    return any(
        isinstance(item, Mapping)
        and item.get("module_id") == "CP-0"
        and item.get("run_id") == cp0_run_id
        and item.get("period") == period
        for item in upstream
    )


def _context_from_cp0(
    cp0: Artifact,
    artifacts: Sequence[Artifact],
    catalog: Catalog,
    conflicting_artifacts: frozenset[tuple[str, str, str, str, str]],
) -> Context:
    assert cp0.fields is not None
    fields = cp0.fields
    identity_field, identity = _identity(fields)
    period = _nonempty(fields.get("reporting_period"), "CP-0 reporting_period")
    run_id = _nonempty(fields.get("run_id"), "CP-0 run_id")
    recommendations = parse_t8(cp0.text, catalog)
    layer_order = {layer.layer_id: index for index, layer in enumerate(catalog.layers)}
    layers = tuple(dict.fromkeys(
        module.layer_id
        for recommendation in recommendations
        for module in (catalog.modules[recommendation.module_id],)
        if module.layer_id is not None
    ))
    layers = tuple(sorted(layers, key=layer_order.__getitem__))
    completed = frozenset(
        recommendation.module_id
        for recommendation in recommendations
        if any(
            _completion_matches(
                artifact,
                recommendation=recommendation,
                identity_field=identity_field,
                identity=identity,
                period=period,
                cp0_run_id=run_id,
                conflicting_artifacts=conflicting_artifacts,
            )
            for artifact in artifacts
        )
    )
    key_material = "\x1f".join(
        (identity_field, identity, period, run_id, cp0.sha256)
    )
    return Context(
        key=hashlib.sha256(key_material.encode("utf-8")).hexdigest(),
        identity_field=identity_field,
        identity=identity,
        period=period,
        run_id=run_id,
        artifact_name=cp0.name,
        digest=cp0.sha256,
        recommendations=recommendations,
        layers=layers,
        completed=completed,
    )


def _downstream_conflicts(
    artifacts: Sequence[Artifact],
) -> frozenset[tuple[str, str, str, str, str]]:
    """Index accepted downstream identities whose run ID has divergent content."""
    indexed: dict[tuple[str, str, str, str, str], set[str]] = {}
    for artifact in artifacts:
        if not artifact.accepted or artifact.fields is None:
            continue
        fields = artifact.fields
        module_id = fields.get("module_id")
        period = fields.get("reporting_period")
        run_id = fields.get("run_id")
        if (
            not isinstance(module_id, str)
            or module_id == "CP-0"
            or not isinstance(period, str)
            or not isinstance(run_id, str)
        ):
            continue
        for identity_field in ("scope_key", "issuer_id"):
            identity = fields.get(identity_field)
            if isinstance(identity, (str, int, float)) and not isinstance(identity, bool):
                identity_text = str(identity).strip()
                if identity_text:
                    key = (
                        module_id, identity_field, identity_text, period, run_id,
                    )
                    indexed.setdefault(key, set()).add(artifact.sha256)
    return frozenset(key for key, digests in indexed.items() if len(digests) > 1)


def discover(artifacts: Sequence[Artifact], catalog: Catalog) -> Discovery:
    """Build deterministic selectable CP-0 contexts from one fresh snapshot."""
    candidates: list[Context] = []
    invalid: list[str] = []
    conflicting_artifacts = _downstream_conflicts(artifacts)
    for artifact in artifacts:
        if artifact.fields is None or artifact.fields.get("module_id") != "CP-0":
            continue
        if not artifact.accepted:
            invalid.append(artifact.name)
            continue
        try:
            candidates.append(_context_from_cp0(
                artifact, artifacts, catalog, conflicting_artifacts
            ))
        except NavigationError:
            invalid.append(artifact.name)
    by_identity: dict[tuple[str, str, str, str], dict[str, Context]] = {}
    for context in candidates:
        collision_key = (
            context.identity_field, context.identity, context.period, context.run_id
        )
        by_identity.setdefault(collision_key, {})[context.digest] = context
    conflicts = tuple(sorted(
        key for key, digests in by_identity.items() if len(digests) > 1
    ))
    contexts = tuple(sorted(
        (
            next(iter(digests.values()))
            for key, digests in by_identity.items()
            if key not in conflicts
        ),
        key=lambda item: (item.identity, item.period, item.run_id, item.digest),
    ))
    return Discovery(contexts, tuple(sorted(invalid)), conflicts)


def recommendations_for_layer(
    context: Context, catalog: Catalog, layer_id: str
) -> tuple[Recommendation, ...]:
    return tuple(
        row for row in context.recommendations
        if catalog.modules[row.module_id].layer_id == layer_id
    )


def skip_warnings(
    context: Context, catalog: Catalog, layer_index: int
) -> tuple[str, ...]:
    """Return one pre-authored warning per skipped active source module."""
    if layer_index < 0 or layer_index >= len(context.layers) - 1:
        return ()
    current = context.layers[layer_index]
    later = set(context.layers[layer_index + 1:])
    recommended = {row.module_id for row in context.recommendations}
    warnings: list[str] = []
    for row in recommendations_for_layer(context, catalog, current):
        if not row.runnable or row.module_id in context.completed:
            continue
        active = any(
            source == row.module_id
            and target in recommended
            and catalog.modules[target].layer_id in later
            for source, target in catalog.dependencies
        )
        if active:
            implication = catalog.modules[row.module_id].skip_implication
            assert implication is not None
            warnings.append(f"Skipping {row.module_id}: {_safe(implication)}")
    return tuple(warnings)


def _context_by_key(discovery: Discovery, key: str | None) -> Context | None:
    return next((context for context in discovery.contexts if context.key == key), None)


def _selection_fingerprint(discovery: Discovery) -> str:
    ordered_keys = [context.key for context in discovery.contexts]
    encoded = json.dumps(ordered_keys, ensure_ascii=True, separators=(",", ":"))
    return hashlib.sha256(encoded.encode("utf-8")).hexdigest()


def _selector_state(
    discovery: Discovery, message: str | None = None
) -> NavigationState:
    return NavigationState(
        "SELECT_RUN",
        message=message,
        selection_fingerprint=_selection_fingerprint(discovery),
        selection_count=len(discovery.contexts),
    )


def _state_with_message(state: NavigationState, message: str) -> NavigationState:
    return NavigationState(
        state.status,
        state.context_key,
        state.layer_index,
        message,
        state.selection_fingerprint,
        state.selection_count,
    )


def _bootstrap(discovery: Discovery) -> NavigationState:
    if not discovery.contexts:
        return NavigationState("NO_CP0")
    if len(discovery.contexts) > 1:
        return _selector_state(discovery)
    return NavigationState("SHOW_LAYER", discovery.contexts[0].key, 0)


def transition(
    discovery: Discovery,
    catalog: Catalog,
    state: NavigationState | None,
    response: int | None,
    *,
    folder_error: str | None = None,
) -> NavigationState:
    """Apply one numbered reply without retaining any folder-derived cache."""
    if state is not None:
        status = state.status
        if status == "STOPPED":
            return state
        if (
            (status == "NO_CP0" and response == 3)
            or (status == "FOLDER_ERROR" and response == 2)
            or (status == "SHOW_LAYER" and response == 5)
            or (
                status == "SELECT_RUN"
                and state.selection_count is not None
                and response == state.selection_count + 2
            )
        ):
            # Resolve the numbered choice from the card the user actually saw.
            # A failed or changed fresh scan must never reinterpret its Stop value.
            return NavigationState("STOPPED")
        if status == "FOLDER_ERROR":
            if response is not None and response != 1:
                return NavigationState("FOLDER_ERROR", message="Invalid reply.")
            if response is None and folder_error is None:
                return state
            if folder_error is not None:
                return NavigationState("FOLDER_ERROR", message=_safe(folder_error))
            return _bootstrap(discovery)
    if folder_error is not None:
        return NavigationState("FOLDER_ERROR", message=_safe(folder_error))
    current = state if state is not None else _bootstrap(discovery)
    status = current.status
    if status == "NO_CP0":
        if response == 3:
            return NavigationState("STOPPED")
        refreshed = _bootstrap(discovery)
        if response is None or response == 1 or response == 2:
            return refreshed
        return _state_with_message(refreshed, "Invalid reply.")
    if status == "SELECT_RUN":
        contexts = discovery.contexts
        context_count = len(contexts)
        fingerprint = _selection_fingerprint(discovery)
        if current.selection_fingerprint != fingerprint:
            message = "Available runs changed. Choose again."
            if context_count == 0:
                return NavigationState("NO_CP0", message=message)
            if context_count == 1:
                return NavigationState("SHOW_LAYER", contexts[0].key, 0, message)
            return NavigationState(
                "SELECT_RUN",
                message=message,
                selection_fingerprint=fingerprint,
                selection_count=context_count,
            )
        if context_count == 0:
            return NavigationState("NO_CP0")
        if response is None:
            return current
        if 1 <= response <= context_count:
            return NavigationState("SHOW_LAYER", contexts[response - 1].key, 0)
        if response == context_count + 1:
            if context_count == 1:
                return NavigationState("SHOW_LAYER", contexts[0].key, 0)
            return NavigationState(
                "SELECT_RUN",
                selection_fingerprint=fingerprint,
                selection_count=context_count,
            )
        if response == context_count + 2:
            return NavigationState("STOPPED")
        return NavigationState(
            "SELECT_RUN",
            message="Invalid reply.",
            selection_fingerprint=fingerprint,
            selection_count=context_count,
        )
    if status != "SHOW_LAYER":
        return _bootstrap(discovery)
    context = _context_by_key(discovery, current.context_key)
    if context is None:
        refreshed = _bootstrap(discovery)
        return _state_with_message(
            refreshed, "Selected run is no longer available."
        )
    last_index = len(context.layers) - 1
    index = min(max(current.layer_index, 0), last_index)
    if response is None:
        return NavigationState("SHOW_LAYER", context.key, index, current.message)
    if response == 1:
        if index == last_index:
            return NavigationState("SHOW_LAYER", context.key, index, "Already at the last layer.")
        warnings = skip_warnings(context, catalog, index)
        return NavigationState("SHOW_LAYER", context.key, index + 1, "\n".join(warnings) or None)
    if response == 2:
        if index == 0:
            return NavigationState("SHOW_LAYER", context.key, index, "Already at the first layer.")
        return NavigationState("SHOW_LAYER", context.key, index - 1)
    if response == 3:
        # Discovery already represents the fresh snapshot, and the lookup
        # above proved this exact context remains present.
        return NavigationState("SHOW_LAYER", context.key, index)
    if response == 4:
        return _selector_state(discovery)
    if response == 5:
        return NavigationState("STOPPED")
    return NavigationState("SHOW_LAYER", context.key, index, "Invalid reply.")


def _render_no_cp0(message: str | None = None) -> str:
    prefix = f"{message}\n\n" if message else ""
    return prefix + "\n".join((
        "🔴 CP-0 REQUIRED", "", "Run CP-0", "",
        "1. CP-0 has been run — refresh _RUNS",
        "2. Refresh _RUNS now", "3. Stop", "",
        "Reply with 1, 2, or 3.",
    ))


def _render_selector(discovery: Discovery, message: str | None = None) -> str:
    lines = ["SELECT CP-0 RUN", ""]
    for index, context in enumerate(discovery.contexts, 1):
        lines.append(f"{index}. {_safe(context.identity)} — {_safe(context.period)} — {_safe(context.run_id)}")
    lines.extend((
        f"{len(discovery.contexts) + 1}. Refresh _RUNS",
        f"{len(discovery.contexts) + 2}. Stop", "",
        "Reply with " + ", ".join(str(index) for index in range(1, len(discovery.contexts) + 3)) + ".",
    ))
    if message:
        lines[0:0] = [message, ""]
    return "\n".join(lines)


def render_layer(
    context: Context, catalog: Catalog, layer_index: int, message: str | None = None
) -> str:
    layer_id = context.layers[layer_index]
    layer = next(item for item in catalog.layers if item.layer_id == layer_id)
    lines: list[str] = []
    if message:
        lines.extend(_safe(line, limit=600) for line in message.splitlines())
        lines.append("")
    lines.append(f"Layer {layer.layer_id} — {_safe(layer.label)}")
    for row in recommendations_for_layer(context, catalog, layer_id):
        module = catalog.modules[row.module_id]
        emoji = "✅" if row.module_id in context.completed else {
            "READY": "🟢",
            "READY_WITH_LIMITATIONS": "🟡",
            "CONDITIONAL": "🟠",
            "BLOCKED": "🔴",
        }[row.readiness]
        lines.extend((
            "",
            f"{emoji} {module.module_id} — {_safe(module.description)}",
            _safe(row.candidate_command, limit=300),
        ))
        if not row.runnable:
            lines.append("Cannot run: " + _safe(row.why_now_or_blocker))
    lines.extend((
        "",
        "1. Next layer" + (" — unavailable" if layer_index == len(context.layers) - 1 else ""),
        "2. Previous layer" + (" — unavailable" if layer_index == 0 else ""),
        "3. Refresh _RUNS", "4. Change run", "5. Stop", "",
        "Reply with 1, 2, 3, 4, or 5.",
    ))
    return "\n".join(lines)


def render(
    state: NavigationState, discovery: Discovery, catalog: Catalog
) -> str:
    if state.status == "NO_CP0":
        return _render_no_cp0(state.message)
    if state.status == "SELECT_RUN":
        return _render_selector(discovery, state.message)
    if state.status == "FOLDER_ERROR":
        return "\n".join((
            "🔴 _RUNS UNAVAILABLE", "", state.message or "The configured folder could not be read.", "",
            "1. Refresh _RUNS", "2. Stop", "", "Reply with 1 or 2.",
        ))
    if state.status == "STOPPED":
        return "CP-OS navigation stopped."
    context = _context_by_key(discovery, state.context_key)
    if context is None:
        return _render_no_cp0("Selected run is no longer available.")
    return render_layer(context, catalog, state.layer_index, state.message)


def navigate(
    raw_catalog: Mapping[str, Any],
    artifacts: Mapping[str, str],
    *,
    state: NavigationState | None = None,
    response: int | None = None,
    folder_error: str | None = None,
    validator: Callable[..., Any] = validate_text,
) -> NavigationResult:
    """Validate one fresh snapshot, transition once, and render a compact card."""
    catalog = validate_catalog(raw_catalog)
    validated = validate_artifacts(artifacts, validator=validator)
    discovery = discover(validated, catalog)
    next_state = transition(
        discovery, catalog, state, response, folder_error=folder_error
    )
    return NavigationResult(
        next_state.status, render(next_state, discovery, catalog), next_state, discovery
    )


__all__ = [
    "Artifact", "Catalog", "Context", "Discovery", "NavigationError",
    "NavigationResult", "NavigationState", "Recommendation", "discover",
    "navigate", "parse_t8", "recommendations_for_layer", "render",
    "render_layer", "skip_warnings", "transition", "validate_artifacts",
    "validate_catalog",
]
