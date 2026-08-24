CREATE TABLE IF NOT EXISTS model_builds (
    id text PRIMARY KEY,
    case_id text NOT NULL REFERENCES cases(id) ON DELETE CASCADE,
    accepted_run_id text NOT NULL REFERENCES runs(id) ON DELETE RESTRICT,
    accepted_snapshot_id text NOT NULL,
    source_set_id text NOT NULL,
    input_fingerprint char(64) NOT NULL,
    status text NOT NULL CHECK (status IN ('QUEUED', 'BUILDING', 'READY', 'FAILED')),
    record jsonb NOT NULL,
    created_by text NOT NULL,
    queued_at timestamptz NOT NULL,
    started_at timestamptz,
    completed_at timestamptz,
    updated_at timestamptz NOT NULL DEFAULT now(),
    UNIQUE (case_id, input_fingerprint)
);

CREATE INDEX IF NOT EXISTS model_builds_case_queued_idx
    ON model_builds (case_id, queued_at DESC);

CREATE TABLE IF NOT EXISTS model_build_jobs (
    build_id text NOT NULL REFERENCES model_builds(id) ON DELETE CASCADE,
    kind text NOT NULL CHECK (kind IN ('calculate', 'export')),
    state text NOT NULL CHECK (state IN ('queued', 'claimed', 'succeeded', 'failed')),
    worker_id text,
    attempt_token text,
    lease_until timestamptz,
    error jsonb,
    created_at timestamptz NOT NULL DEFAULT now(),
    updated_at timestamptz NOT NULL DEFAULT now(),
    PRIMARY KEY (build_id, kind)
);

CREATE INDEX IF NOT EXISTS model_build_jobs_claim_idx
    ON model_build_jobs (state, lease_until, created_at);

INSERT INTO schema_migrations(version) VALUES ('002_cp_model') ON CONFLICT DO NOTHING;
