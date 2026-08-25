ALTER TABLE cases
    ADD COLUMN IF NOT EXISTS accepted_snapshot_id text,
    ADD COLUMN IF NOT EXISTS visible_snapshot_id text,
    ADD COLUMN IF NOT EXISTS current_execution_id text,
    ADD COLUMN IF NOT EXISTS current_source_set_id text;

ALTER TABLE sources DROP CONSTRAINT IF EXISTS sources_case_id_sha256_key;
ALTER TABLE sources ALTER COLUMN vault_path DROP NOT NULL;
ALTER TABLE sources
    ADD COLUMN IF NOT EXISTS withdrawn_at timestamptz,
    ADD COLUMN IF NOT EXISTS source_kind text,
    ADD COLUMN IF NOT EXISTS origin_family text,
    ADD COLUMN IF NOT EXISTS authority_class text,
    ADD COLUMN IF NOT EXISTS record jsonb NOT NULL DEFAULT '{}'::jsonb;

CREATE UNIQUE INDEX IF NOT EXISTS sources_active_digest_idx
    ON sources (case_id, sha256)
    WHERE withdrawn = false;
CREATE INDEX IF NOT EXISTS sources_case_active_idx
    ON sources (case_id, created_at, id)
    WHERE withdrawn = false;

ALTER TABLE runs
    ADD COLUMN IF NOT EXISTS current_node_id text,
    ADD COLUMN IF NOT EXISTS upgraded_from_run_id text,
    ADD COLUMN IF NOT EXISTS research jsonb,
    ADD COLUMN IF NOT EXISTS final_attempt_token text;

ALTER TABLE workflow_nodes
    ADD COLUMN IF NOT EXISTS case_id text REFERENCES cases(id) ON DELETE CASCADE,
    ADD COLUMN IF NOT EXISTS stage integer,
    ADD COLUMN IF NOT EXISTS position integer,
    ADD COLUMN IF NOT EXISTS last_attempt_token text;
UPDATE workflow_nodes AS node
SET case_id = run.case_id
FROM runs AS run
WHERE node.run_id = run.id AND node.case_id IS NULL;
ALTER TABLE workflow_nodes ALTER COLUMN case_id SET NOT NULL;
UPDATE workflow_nodes SET stage = 0 WHERE stage IS NULL;
ALTER TABLE workflow_nodes ALTER COLUMN stage SET NOT NULL;
UPDATE workflow_nodes SET position = 0 WHERE position IS NULL;
ALTER TABLE workflow_nodes ALTER COLUMN position SET NOT NULL;

CREATE UNIQUE INDEX IF NOT EXISTS jobs_run_idx ON jobs (run_id);
CREATE INDEX IF NOT EXISTS runs_pending_idx
    ON runs (created_at, id)
    WHERE status IN ('queued', 'running');

CREATE TABLE IF NOT EXISTS workflow_events (
    run_id text NOT NULL REFERENCES runs(id) ON DELETE CASCADE,
    sequence integer NOT NULL CHECK (sequence > 0),
    event text NOT NULL,
    data jsonb NOT NULL,
    attempt_token text,
    created_at timestamptz NOT NULL,
    PRIMARY KEY (run_id, sequence)
);

ALTER TABLE artifacts ALTER COLUMN markdown SET DEFAULT '';
ALTER TABLE artifacts ALTER COLUMN input_fingerprint TYPE text;
ALTER TABLE artifacts
    ADD COLUMN IF NOT EXISTS case_id text REFERENCES cases(id) ON DELETE CASCADE,
    ADD COLUMN IF NOT EXISTS created_by text,
    ADD COLUMN IF NOT EXISTS attempt_token text,
    ADD COLUMN IF NOT EXISTS record jsonb NOT NULL DEFAULT '{}'::jsonb;

ALTER TABLE accepted_snapshots
    ADD COLUMN IF NOT EXISTS accepted_by text,
    ADD COLUMN IF NOT EXISTS attempt_token text,
    ADD COLUMN IF NOT EXISTS record jsonb NOT NULL DEFAULT '{}'::jsonb;

ALTER TABLE model_builds ADD COLUMN IF NOT EXISTS last_attempt_token text;

CREATE TABLE IF NOT EXISTS notes (
    id text PRIMARY KEY,
    case_id text NOT NULL REFERENCES cases(id) ON DELETE CASCADE,
    author text NOT NULL,
    body text NOT NULL,
    promoted boolean NOT NULL DEFAULT false,
    promoted_source_id text REFERENCES sources(id) ON DELETE SET NULL,
    created_at timestamptz NOT NULL
);

CREATE TABLE IF NOT EXISTS assumptions (
    id text PRIMARY KEY,
    case_id text NOT NULL REFERENCES cases(id) ON DELETE CASCADE,
    author text NOT NULL,
    statement text NOT NULL,
    supporting_claim text NOT NULL DEFAULT '',
    conflicting_claim text NOT NULL DEFAULT '',
    evidence_ids jsonb NOT NULL,
    affected_module_ids jsonb NOT NULL,
    status text NOT NULL,
    stale boolean NOT NULL DEFAULT false,
    created_at timestamptz NOT NULL
);
CREATE INDEX IF NOT EXISTS assumptions_case_idx ON assumptions (case_id, created_at, id);

CREATE TABLE IF NOT EXISTS report_inputs (
    id text PRIMARY KEY,
    case_id text NOT NULL REFERENCES cases(id) ON DELETE CASCADE,
    thesis_version integer NOT NULL,
    recommendation_version integer NOT NULL,
    accepted_snapshot_id text REFERENCES accepted_snapshots(id) ON DELETE RESTRICT,
    created_by text NOT NULL,
    created_at timestamptz NOT NULL,
    UNIQUE (case_id, thesis_version, recommendation_version)
);
ALTER TABLE report_inputs
    ADD CONSTRAINT report_inputs_thesis_fk
    FOREIGN KEY (case_id, thesis_version)
    REFERENCES thesis_versions(case_id, version) ON DELETE RESTRICT;
ALTER TABLE report_inputs
    ADD CONSTRAINT report_inputs_recommendation_fk
    FOREIGN KEY (case_id, recommendation_version)
    REFERENCES recommendation_versions(case_id, version) ON DELETE RESTRICT;

ALTER TABLE reports
    ADD COLUMN IF NOT EXISTS preview_digest text,
    ADD COLUMN IF NOT EXISTS input_fingerprint text,
    ADD COLUMN IF NOT EXISTS approved_by text,
    ADD COLUMN IF NOT EXISTS approved_at timestamptz,
    ADD COLUMN IF NOT EXISTS approval_comment text;
CREATE UNIQUE INDEX IF NOT EXISTS reports_current_case_idx ON reports (case_id);

CREATE TABLE IF NOT EXISTS report_approvals (
    report_id text PRIMARY KEY REFERENCES reports(id) ON DELETE CASCADE,
    actor text NOT NULL,
    preview_digest text NOT NULL,
    input_fingerprint text NOT NULL,
    comment text,
    approved_at timestamptz NOT NULL
);

CREATE TABLE IF NOT EXISTS methodology_drafts (
    id text PRIMARY KEY,
    status text NOT NULL,
    module_id text,
    value jsonb NOT NULL,
    digest char(64) NOT NULL,
    created_by text NOT NULL,
    created_at timestamptz NOT NULL,
    validated_by text,
    validated_at timestamptz,
    confirmed_by text,
    confirmed_at timestamptz,
    signature text
);

CREATE TABLE IF NOT EXISTS rv_universes (
    case_id text NOT NULL REFERENCES cases(id) ON DELETE CASCADE,
    version integer NOT NULL CHECK (version > 0),
    id text NOT NULL UNIQUE,
    value jsonb NOT NULL,
    author text NOT NULL,
    created_at timestamptz NOT NULL,
    PRIMARY KEY (case_id, version)
);

ALTER TABLE audit_events ADD COLUMN IF NOT EXISTS event_id text;
ALTER TABLE audit_events ALTER COLUMN event_id SET NOT NULL;
CREATE UNIQUE INDEX IF NOT EXISTS audit_events_event_id_idx ON audit_events (event_id);

ALTER TABLE rv_loan_rows ADD COLUMN IF NOT EXISTS position integer;
UPDATE rv_loan_rows SET position = 0 WHERE position IS NULL;
ALTER TABLE rv_loan_rows ALTER COLUMN position SET NOT NULL;

ALTER TABLE rv_loan_universes
    ADD CONSTRAINT rv_loan_universes_source_fk
    FOREIGN KEY (source_id) REFERENCES sources(id) ON DELETE RESTRICT;

ALTER TABLE model_builds
    ADD CONSTRAINT model_builds_snapshot_fk
    FOREIGN KEY (accepted_snapshot_id) REFERENCES accepted_snapshots(id) ON DELETE RESTRICT;
ALTER TABLE model_builds
    ADD CONSTRAINT model_builds_source_set_fk
    FOREIGN KEY (source_set_id) REFERENCES source_sets(id) ON DELETE RESTRICT;
ALTER TABLE accepted_snapshots
    ADD CONSTRAINT accepted_snapshots_source_set_fk
    FOREIGN KEY (source_set_id) REFERENCES source_sets(id) ON DELETE RESTRICT;
ALTER TABLE accepted_snapshots
    ADD CONSTRAINT accepted_snapshots_previous_fk
    FOREIGN KEY (previous_snapshot_id) REFERENCES accepted_snapshots(id) ON DELETE RESTRICT;

ALTER TABLE cases
    ADD CONSTRAINT cases_accepted_snapshot_fk
    FOREIGN KEY (accepted_snapshot_id) REFERENCES accepted_snapshots(id) ON DELETE RESTRICT;
ALTER TABLE cases
    ADD CONSTRAINT cases_visible_snapshot_fk
    FOREIGN KEY (visible_snapshot_id) REFERENCES accepted_snapshots(id) ON DELETE RESTRICT;
ALTER TABLE cases
    ADD CONSTRAINT cases_current_execution_fk
    FOREIGN KEY (current_execution_id) REFERENCES runs(id) ON DELETE SET NULL;
ALTER TABLE cases
    ADD CONSTRAINT cases_current_source_set_fk
    FOREIGN KEY (current_source_set_id) REFERENCES source_sets(id) ON DELETE SET NULL;
ALTER TABLE runs
    ADD CONSTRAINT runs_accepted_snapshot_fk
    FOREIGN KEY (accepted_snapshot_id) REFERENCES accepted_snapshots(id) ON DELETE RESTRICT;
ALTER TABLE runs
    ADD CONSTRAINT runs_current_node_fk
    FOREIGN KEY (current_node_id) REFERENCES workflow_nodes(id) ON DELETE SET NULL;
ALTER TABLE runs
    ADD CONSTRAINT runs_upgraded_from_fk
    FOREIGN KEY (upgraded_from_run_id) REFERENCES runs(id) ON DELETE SET NULL;

INSERT INTO schema_migrations(version)
VALUES ('005_normalized_authority')
ON CONFLICT DO NOTHING;
