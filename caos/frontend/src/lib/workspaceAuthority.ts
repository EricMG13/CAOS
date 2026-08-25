export type AuthorityStatus = "idle" | "loading" | "ready" | "error";

export type RequestContext = {
  generation: number;
  caseId: string | null;
  runId: string | null;
};

export type AuthorityState = {
  caseId: string | null;
  runId: string | null;
  hydrated: boolean;
  status: AuthorityStatus;
  generation: number;
  pending: { scope: string; context: RequestContext } | null;
  acceptedSnapshotId: string | null;
};

export type AuthorityEvent =
  | { type: "hydrate"; caseId: string | null; runId: string | null }
  | { type: "selectCase"; caseId: string | null }
  | { type: "selectRun"; caseId: string; runId: string }
  | { type: "requestStarted"; scope: string }
  | { type: "requestSucceeded"; context: RequestContext; scope: string }
  | { type: "requestFailed"; context: RequestContext; scope: string }
  | { type: "invalidateCase"; caseId: string }
  | { type: "invalidateRun"; caseId: string; runId: string }
  | { type: "snapshotAccepted"; context: RequestContext; snapshotId: string };

export const initialAuthorityState: AuthorityState = {
  caseId: null,
  runId: null,
  hydrated: false,
  status: "idle",
  generation: 0,
  pending: null,
  acceptedSnapshotId: null,
};

export function requestContext(state: AuthorityState): RequestContext {
  return { generation: state.generation, caseId: state.caseId, runId: state.runId };
}

export function matchesAuthority(state: AuthorityState, context: RequestContext) {
  return context.generation === state.generation && context.caseId === state.caseId && context.runId === state.runId;
}

export function workspaceAuthorityReducer(state: AuthorityState, event: AuthorityEvent): AuthorityState {
  switch (event.type) {
    case "hydrate": {
      const runId = event.caseId ? event.runId : null;
      const generation = state.generation + 1;
      return {
        ...state,
        caseId: event.caseId,
        runId,
        hydrated: true,
        status: event.caseId ? "loading" : "idle",
        generation,
        pending: event.caseId ? { scope: "case", context: { generation, caseId: event.caseId, runId } } : null,
        acceptedSnapshotId: null,
      };
    }
    case "selectCase": {
      if (state.caseId === event.caseId) return state;
      const generation = state.generation + 1;
      return {
        ...state,
        caseId: event.caseId,
        runId: null,
        status: event.caseId ? "loading" : "idle",
        generation,
        pending: event.caseId ? { scope: "case", context: { generation, caseId: event.caseId, runId: null } } : null,
        acceptedSnapshotId: null,
      };
    }
    case "selectRun": {
      if (state.caseId !== event.caseId || state.runId === event.runId) return state;
      const generation = state.generation + 1;
      return {
        ...state,
        runId: event.runId,
        status: "loading",
        generation,
        pending: { scope: "case", context: { generation, caseId: event.caseId, runId: event.runId } },
        acceptedSnapshotId: null,
      };
    }
    case "requestStarted": {
      const generation = state.generation + 1;
      const context = { generation, caseId: state.caseId, runId: state.runId };
      return { ...state, status: "loading", generation, pending: { scope: event.scope, context } };
    }
    case "requestSucceeded":
      if (!matchesAuthority(state, event.context) || state.pending?.scope !== event.scope) return state;
      return { ...state, status: "ready", pending: null };
    case "requestFailed": {
      const pendingScope = state.pending?.scope;
      const parentFailure =
        (event.scope === "cases" && (pendingScope === "case" || pendingScope === "run"))
        || (event.scope === "case" && pendingScope === "run");
      if (!matchesAuthority(state, event.context) || (pendingScope !== event.scope && !parentFailure)) return state;
      return { ...state, status: "error", pending: null };
    }
    case "snapshotAccepted":
      if (!matchesAuthority(state, event.context)) return state;
      return { ...state, status: "ready", pending: null, acceptedSnapshotId: event.snapshotId };
    case "invalidateCase":
      if (state.caseId !== event.caseId) return state;
      return {
        ...state,
        caseId: null,
        runId: null,
        status: "idle",
        generation: state.generation + 1,
        pending: null,
        acceptedSnapshotId: null,
      };
    case "invalidateRun": {
      if (state.caseId !== event.caseId || state.runId !== event.runId) return state;
      const generation = state.generation + 1;
      return {
        ...state,
        runId: null,
        status: "loading",
        generation,
        pending: { scope: "case", context: { generation, caseId: event.caseId, runId: null } },
        acceptedSnapshotId: null,
      };
    }
  }
}
