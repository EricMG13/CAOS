CREATE TABLE IF NOT EXISTS schema_migrations (
    version text PRIMARY KEY,
    applied_at timestamptz NOT NULL DEFAULT now()
);

CREATE TABLE IF NOT EXISTS cases (
    id text PRIMARY KEY,
    name text NOT NULL,
    issuer text NOT NULL,
    sector text NOT NULL,
    created_by text NOT NULL,
    created_at timestamptz NOT NULL DEFAULT now()
);

CREATE TABLE IF NOT EXISTS case_members (
    case_id text NOT NULL REFERENCES cases(id) ON DELETE CASCADE,
    subject text NOT NULL,
    role text NOT NULL CHECK (role IN ('ANALYST', 'APPROVER', 'ADMIN', 'READER')),
    PRIMARY KEY (case_id, subject)
);

CREATE TABLE IF NOT EXISTS sources (
    id text PRIMARY KEY,
    case_id text NOT NULL REFERENCES cases(id) ON DELETE CASCADE,
    filename text NOT NULL,
    media_type text NOT NULL,
    sha256 char(64) NOT NULL,
    vault_path text NOT NULL,
    bytes bigint NOT NULL CHECK (bytes >= 0),
    blocks jsonb NOT NULL,
    withdrawn boolean NOT NULL DEFAULT false,
    created_by text NOT NULL,
    created_at timestamptz NOT NULL DEFAULT now(),
    UNIQUE (case_id, sha256)
);

CREATE TABLE IF NOT EXISTS source_sets (
    id text PRIMARY KEY,
    case_id text NOT NULL REFERENCES cases(id) ON DELETE CASCADE,
    version integer NOT NULL CHECK (version > 0),
    source_ids jsonb NOT NULL,
    created_by text NOT NULL,
    created_at timestamptz NOT NULL DEFAULT now(),
    UNIQUE (case_id, version)
);

CREATE TABLE IF NOT EXISTS runs (
    id text PRIMARY KEY,
    case_id text NOT NULL REFERENCES cases(id) ON DELETE CASCADE,
    status text NOT NULL CHECK (status IN ('planning', 'queued', 'running', 'paused', 'succeeded', 'failed')),
    plan jsonb NOT NULL,
    accepted_snapshot_id text,
    created_by text NOT NULL,
    created_at timestamptz NOT NULL DEFAULT now(),
    error jsonb
);

DO $$
BEGIN
    IF EXISTS (
        SELECT 1
        FROM pg_constraint
        WHERE conrelid = 'runs'::regclass
          AND conname = 'runs_status_check'
          AND pg_get_constraintdef(oid) NOT LIKE '%planning%'
    ) THEN
        ALTER TABLE runs DROP CONSTRAINT runs_status_check;
        ALTER TABLE runs ADD CONSTRAINT runs_status_check
            CHECK (status IN ('planning', 'queued', 'running', 'paused', 'succeeded', 'failed'));
    END IF;
END $$;

CREATE TABLE IF NOT EXISTS workflow_nodes (
    id text PRIMARY KEY,
    run_id text NOT NULL REFERENCES runs(id) ON DELETE CASCADE,
    module_id text NOT NULL,
    dependencies jsonb NOT NULL,
    status text NOT NULL CHECK (status IN ('pending', 'ready', 'running', 'succeeded', 'failed', 'blocked')),
    attempt integer NOT NULL DEFAULT 0,
    attempt_token text,
    lease_until timestamptz,
    artifact_id text,
    error jsonb,
    UNIQUE (run_id, module_id)
);

CREATE TABLE IF NOT EXISTS jobs (
    id bigserial PRIMARY KEY,
    run_id text NOT NULL REFERENCES runs(id) ON DELETE CASCADE,
    node_id text REFERENCES workflow_nodes(id) ON DELETE CASCADE,
    state text NOT NULL CHECK (state IN ('queued', 'claimed', 'succeeded', 'failed')),
    worker_id text,
    attempt_token text,
    lease_until timestamptz,
    budget_reserved integer NOT NULL DEFAULT 0,
    created_at timestamptz NOT NULL DEFAULT now()
);

CREATE INDEX IF NOT EXISTS jobs_claim_idx ON jobs (state, lease_until, id);

CREATE TABLE IF NOT EXISTS artifacts (
    id text PRIMARY KEY,
    run_id text NOT NULL REFERENCES runs(id) ON DELETE CASCADE,
    module_id text NOT NULL,
    digest char(64) NOT NULL,
    payload jsonb NOT NULL,
    markdown text NOT NULL,
    input_fingerprint char(64) NOT NULL,
    created_at timestamptz NOT NULL DEFAULT now(),
    UNIQUE (run_id, module_id, input_fingerprint)
);

CREATE TABLE IF NOT EXISTS accepted_snapshots (
    id text PRIMARY KEY,
    case_id text NOT NULL REFERENCES cases(id) ON DELETE CASCADE,
    run_id text NOT NULL REFERENCES runs(id) ON DELETE RESTRICT,
    digest char(64) NOT NULL,
    source_set_id text,
    source_set_version integer,
    artifact_refs jsonb NOT NULL,
    previous_snapshot_id text,
    accepted_at timestamptz NOT NULL DEFAULT now(),
    UNIQUE (case_id, run_id)
);

CREATE TABLE IF NOT EXISTS thesis_versions (
    case_id text NOT NULL REFERENCES cases(id) ON DELETE CASCADE,
    version integer NOT NULL,
    value jsonb NOT NULL,
    author text NOT NULL,
    created_at timestamptz NOT NULL DEFAULT now(),
    PRIMARY KEY (case_id, version)
);

CREATE TABLE IF NOT EXISTS recommendation_versions (
    case_id text NOT NULL REFERENCES cases(id) ON DELETE CASCADE,
    version integer NOT NULL,
    value jsonb NOT NULL,
    author text NOT NULL,
    created_at timestamptz NOT NULL DEFAULT now(),
    PRIMARY KEY (case_id, version)
);

CREATE TABLE IF NOT EXISTS reports (
    id text PRIMARY KEY,
    case_id text NOT NULL REFERENCES cases(id) ON DELETE CASCADE,
    status text NOT NULL CHECK (status IN ('PENDING_APPROVAL', 'APPROVED')),
    digest char(64) NOT NULL,
    snapshot_digest char(64) NOT NULL,
    value jsonb NOT NULL,
    created_by text NOT NULL,
    created_at timestamptz NOT NULL DEFAULT now()
);

CREATE TABLE IF NOT EXISTS audit_events (
    id bigserial PRIMARY KEY,
    actor text NOT NULL,
    action text NOT NULL,
    case_id text,
    payload jsonb NOT NULL,
    created_at timestamptz NOT NULL DEFAULT now()
);

INSERT INTO schema_migrations(version) VALUES ('001_baseline') ON CONFLICT DO NOTHING;
