"""Profile-scoped routing and exact lineage for Deploy V."""

from __future__ import annotations

from .identity import parse_route_node, require_profile

ACCEPTED = "ACCEPTED"
BLOCKING = frozenset({"REQUIRED", "CONDITIONAL", "QA_GATE"})
SOFT = frozenset({"OPTIONAL", "ADVISORY"})
RUNNABLE = "RUNNABLE"
BLOCKED = "BLOCKED"
COMPLETE = "COMPLETE"
RESTRICTED = "RESTRICTED"


class RouteError(ValueError):
    pass


class Route:
    def __init__(self, catalog: dict, profile_id: str, selection_id: str) -> None:
        require_profile(profile_id)
        try:
            profile = catalog["profiles"][profile_id]
            pathway = profile["pathways"][selection_id]
        except (KeyError, TypeError) as exc:
            raise RouteError(f"unknown profile/selection: {profile_id}/{selection_id}") from exc
        if pathway.get("profile_id") != profile_id or pathway.get("selection_id") != selection_id:
            raise RouteError("pathway identity does not match its catalog keys")
        self.profile_id = profile_id
        self.selection_id = selection_id
        self.nodes = pathway["nodes"]
        self.edges = profile["edges"]
        self.modules = {entry["module_id"]: entry for entry in catalog["modules"]}
        self.by_node = {}
        self.by_module = {}
        for index, node in enumerate(self.nodes, start=1):
            route_id = node["route_node_id"]
            parsed = parse_route_node(route_id)
            if parsed != (profile_id, selection_id, index, node["module_id"]):
                raise RouteError(f"invalid route occurrence: {route_id}")
            if route_id in self.by_node or node["module_id"] in self.by_module:
                raise RouteError("duplicate route node or module occurrence")
            self.by_node[route_id] = node
            self.by_module[node["module_id"]] = node

    def incoming(self, route_node_id: str):
        target = self.by_node[route_node_id]["module_id"]
        for edge in self.edges:
            if edge["target"] == target and edge["source"] in self.by_module:
                yield edge

    def outgoing(self, route_node_id: str):
        source = self.by_node[route_node_id]["module_id"]
        for edge in self.edges:
            if edge["source"] == source and edge["target"] in self.by_module:
                yield edge


def accepted_digest_for(state: dict, route_node_id: str) -> str | None:
    for attempt in state.get("attempts", ()):
        if attempt.get("route_node_id") == route_node_id and attempt.get("status") == ACCEPTED:
            return attempt.get("artifact_sha256")
    return None


def active_incoming(route: Route, route_node_id: str, predicates: dict[str, bool] | None = None):
    predicates = predicates or {}
    for edge in route.incoming(route_node_id):
        if edge["type"] == "CONDITIONAL" and not predicates.get(edge.get("predicate"), False):
            continue
        yield edge


def expected_upstream_digests(
    route: Route,
    route_node_id: str,
    accepted: dict[str, str],
    *,
    predicates: dict[str, bool] | None = None,
) -> dict[str, str]:
    """Return every accepted active direct input and refuse missing blockers."""
    expected: dict[str, str] = {}
    for edge in active_incoming(route, route_node_id, predicates):
        source_node = route.by_module[edge["source"]]["route_node_id"]
        source_digest = accepted.get(source_node)
        if source_digest is None:
            if edge["type"] in BLOCKING:
                raise RouteError(
                    f"{route_node_id} is missing blocking upstream {source_node}"
                )
            continue
        expected[source_node] = source_digest
    return dict(sorted(expected.items()))


def node_states(route: Route, state: dict, *, predicates: dict[str, bool] | None = None) -> dict:
    accepted = {
        node["route_node_id"]: accepted_digest_for(state, node["route_node_id"])
        for node in route.nodes
    }
    result = {}
    for node in route.nodes:
        route_id = node["route_node_id"]
        if accepted[route_id]:
            result[route_id] = {"status": COMPLETE, "reasons": []}
            continue
        blockers, limitations = [], []
        for edge in active_incoming(route, route_id, predicates):
            source_id = route.by_module[edge["source"]]["route_node_id"]
            if accepted[source_id]:
                continue
            label = route.modules.get(edge["source"], {}).get("display", edge["source"])
            (blockers if edge["type"] in BLOCKING else limitations).append(label)
        status = BLOCKED if blockers else RESTRICTED if limitations else RUNNABLE
        result[route_id] = {"status": status, "reasons": blockers or limitations}
    return result


def frontier(route: Route, state: dict, **kwargs) -> list[str]:
    states = node_states(route, state, **kwargs)
    return [
        node["route_node_id"]
        for node in route.nodes
        if states[node["route_node_id"]]["status"] in {RUNNABLE, RESTRICTED}
    ]
