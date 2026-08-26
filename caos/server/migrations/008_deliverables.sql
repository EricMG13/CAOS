CREATE TABLE IF NOT EXISTS deliverable_draft_revisions (
    id text PRIMARY KEY,
    case_id text NOT NULL REFERENCES cases(id) ON DELETE CASCADE,
    pathway text NOT NULL,
    version integer NOT NULL CHECK (version > 0),
    template_id text NOT NULL,
    template_version text NOT NULL,
    digest char(64) NOT NULL,
    value jsonb NOT NULL,
    author text NOT NULL,
    created_at timestamptz NOT NULL DEFAULT now(),
    UNIQUE (case_id, pathway, version)
);

CREATE INDEX IF NOT EXISTS deliverable_draft_revisions_current_idx
    ON deliverable_draft_revisions (case_id, pathway, version DESC);

-- Phase 6 writes these records. Phase 5 creates the authority schema only so
-- an upgrade cannot split the structured draft/frozen publication boundary.
CREATE TABLE IF NOT EXISTS frozen_deliverables (
    id text PRIMARY KEY,
    case_id text NOT NULL REFERENCES cases(id) ON DELETE CASCADE,
    pathway text NOT NULL,
    draft_version integer NOT NULL CHECK (draft_version > 0),
    status text NOT NULL,
    authority_identity jsonb NOT NULL,
    model_identity jsonb,
    template_identity jsonb NOT NULL,
    render_identity jsonb,
    digest char(64) NOT NULL,
    value jsonb NOT NULL,
    frozen_by text NOT NULL,
    frozen_at timestamptz NOT NULL DEFAULT now(),
    approved_by text,
    approved_at timestamptz,
    approval_comment text
);

CREATE INDEX IF NOT EXISTS frozen_deliverables_case_pathway_idx
    ON frozen_deliverables (case_id, pathway, frozen_at DESC, id);

CREATE TABLE IF NOT EXISTS deliverable_exports (
    deliverable_id text NOT NULL REFERENCES frozen_deliverables(id) ON DELETE CASCADE,
    format text NOT NULL,
    vault_key text NOT NULL,
    sha256 char(64) NOT NULL,
    size bigint NOT NULL CHECK (size >= 0),
    renderer_identity jsonb NOT NULL,
    created_at timestamptz NOT NULL DEFAULT now(),
    PRIMARY KEY (deliverable_id, format)
);
