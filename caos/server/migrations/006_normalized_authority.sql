ALTER TABLE cases
    ADD COLUMN IF NOT EXISTS current_source_set_id text,
    ADD COLUMN IF NOT EXISTS current_execution_id text,
    ADD COLUMN IF NOT EXISTS accepted_snapshot_id text,
    ADD COLUMN IF NOT EXISTS visible_snapshot_id text,
    ADD COLUMN IF NOT EXISTS record jsonb NOT NULL DEFAULT '{}'::jsonb;

ALTER TABLE sources
    ALTER COLUMN vault_path DROP NOT NULL,
    ADD COLUMN IF NOT EXISTS source_kind text,
    ADD COLUMN IF NOT EXISTS withdrawn_at timestamptz,
    ADD COLUMN IF NOT EXISTS record jsonb NOT NULL DEFAULT '{}'::jsonb;

ALTER TABLE sources DROP CONSTRAINT IF EXISTS sources_case_id_sha256_key;

CREATE UNIQUE INDEX IF NOT EXISTS sources_active_case_sha256_idx
    ON sources (case_id, sha256)
    WHERE withdrawn = false;

ALTER TABLE source_sets
    ADD COLUMN IF NOT EXISTS record jsonb NOT NULL DEFAULT '{}'::jsonb;

DO $$
BEGIN
    IF NOT EXISTS (
        SELECT 1 FROM pg_constraint
        WHERE conrelid = 'cases'::regclass
          AND conname = 'cases_current_source_set_id_fkey'
    ) THEN
        ALTER TABLE cases ADD CONSTRAINT cases_current_source_set_id_fkey
            FOREIGN KEY (current_source_set_id) REFERENCES source_sets(id) ON DELETE SET NULL;
    END IF;
END $$;

ALTER TABLE runs
    ADD COLUMN IF NOT EXISTS current_node_id text,
    ADD COLUMN IF NOT EXISTS upgraded_from_run_id text,
    ADD COLUMN IF NOT EXISTS research jsonb,
    ADD COLUMN IF NOT EXISTS record jsonb NOT NULL DEFAULT '{}'::jsonb;

ALTER TABLE workflow_nodes
    ADD COLUMN IF NOT EXISTS stage integer NOT NULL DEFAULT 0,
    ADD COLUMN IF NOT EXISTS record jsonb NOT NULL DEFAULT '{}'::jsonb;

ALTER TABLE jobs
    ADD COLUMN IF NOT EXISTS actor text;

DROP INDEX IF EXISTS jobs_run_coordinator_idx;
CREATE UNIQUE INDEX jobs_run_coordinator_idx
    ON jobs (run_id)
    WHERE node_id IS NULL AND state IN ('queued', 'claimed');

ALTER TABLE artifacts
    ADD COLUMN IF NOT EXISTS record jsonb NOT NULL DEFAULT '{}'::jsonb;

ALTER TABLE accepted_snapshots
    ADD COLUMN IF NOT EXISTS record jsonb NOT NULL DEFAULT '{}'::jsonb;

CREATE TABLE IF NOT EXISTS workflow_events (
    run_id text NOT NULL REFERENCES runs(id) ON DELETE CASCADE,
    sequence integer NOT NULL CHECK (sequence > 0),
    event text NOT NULL,
    record jsonb NOT NULL,
    created_at timestamptz NOT NULL DEFAULT now(),
    PRIMARY KEY (run_id, sequence)
);

CREATE TABLE IF NOT EXISTS notes (
    id text PRIMARY KEY,
    case_id text NOT NULL REFERENCES cases(id) ON DELETE CASCADE,
    author text NOT NULL,
    promoted_source_id text REFERENCES sources(id) ON DELETE SET NULL,
    record jsonb NOT NULL,
    created_at timestamptz NOT NULL
);

CREATE INDEX IF NOT EXISTS notes_case_created_idx ON notes (case_id, created_at, id);

CREATE TABLE IF NOT EXISTS assumptions (
    id text PRIMARY KEY,
    case_id text NOT NULL REFERENCES cases(id) ON DELETE CASCADE,
    status text NOT NULL,
    evidence_ids jsonb NOT NULL,
    record jsonb NOT NULL,
    created_at timestamptz NOT NULL
);

CREATE INDEX IF NOT EXISTS assumptions_case_created_idx
    ON assumptions (case_id, created_at, id);

ALTER TABLE reports
    ADD COLUMN IF NOT EXISTS preview_digest text,
    ADD COLUMN IF NOT EXISTS input_fingerprint text,
    ADD COLUMN IF NOT EXISTS approved_by text,
    ADD COLUMN IF NOT EXISTS approved_at timestamptz,
    ADD COLUMN IF NOT EXISTS approval_comment text,
    ADD COLUMN IF NOT EXISTS record jsonb NOT NULL DEFAULT '{}'::jsonb;

CREATE UNIQUE INDEX IF NOT EXISTS reports_current_case_idx ON reports (case_id);

CREATE TABLE IF NOT EXISTS methodology_drafts (
    id text PRIMARY KEY,
    status text NOT NULL,
    record jsonb NOT NULL,
    created_by text NOT NULL,
    created_at timestamptz NOT NULL
);

CREATE TABLE IF NOT EXISTS rv_universes (
    id text PRIMARY KEY,
    case_id text NOT NULL REFERENCES cases(id) ON DELETE CASCADE,
    version integer NOT NULL CHECK (version > 0),
    record jsonb NOT NULL,
    created_by text NOT NULL,
    created_at timestamptz NOT NULL,
    UNIQUE (case_id, version)
);

CREATE INDEX IF NOT EXISTS rv_universes_case_version_idx
    ON rv_universes (case_id, version DESC);

DO $$
BEGIN
    IF NOT EXISTS (
        SELECT 1 FROM pg_constraint
        WHERE conrelid = 'accepted_snapshots'::regclass
          AND conname = 'accepted_snapshots_source_set_id_fkey'
    ) THEN
        ALTER TABLE accepted_snapshots
            ADD CONSTRAINT accepted_snapshots_source_set_id_fkey
            FOREIGN KEY (source_set_id) REFERENCES source_sets(id) ON DELETE RESTRICT;
    END IF;
    IF NOT EXISTS (
        SELECT 1 FROM pg_constraint
        WHERE conrelid = 'accepted_snapshots'::regclass
          AND conname = 'accepted_snapshots_previous_snapshot_id_fkey'
    ) THEN
        ALTER TABLE accepted_snapshots
            ADD CONSTRAINT accepted_snapshots_previous_snapshot_id_fkey
            FOREIGN KEY (previous_snapshot_id) REFERENCES accepted_snapshots(id) ON DELETE RESTRICT;
    END IF;
    IF NOT EXISTS (
        SELECT 1 FROM pg_constraint
        WHERE conrelid = 'cases'::regclass
          AND conname = 'cases_accepted_snapshot_id_fkey'
    ) THEN
        ALTER TABLE cases
            ADD CONSTRAINT cases_accepted_snapshot_id_fkey
            FOREIGN KEY (accepted_snapshot_id) REFERENCES accepted_snapshots(id) ON DELETE SET NULL;
    END IF;
    IF NOT EXISTS (
        SELECT 1 FROM pg_constraint
        WHERE conrelid = 'cases'::regclass
          AND conname = 'cases_visible_snapshot_id_fkey'
    ) THEN
        ALTER TABLE cases
            ADD CONSTRAINT cases_visible_snapshot_id_fkey
            FOREIGN KEY (visible_snapshot_id) REFERENCES accepted_snapshots(id) ON DELETE SET NULL;
    END IF;
    IF NOT EXISTS (
        SELECT 1 FROM pg_constraint
        WHERE conrelid = 'runs'::regclass
          AND conname = 'runs_current_node_id_fkey'
    ) THEN
        ALTER TABLE runs
            ADD CONSTRAINT runs_current_node_id_fkey
            FOREIGN KEY (current_node_id) REFERENCES workflow_nodes(id) ON DELETE SET NULL;
    END IF;
    IF NOT EXISTS (
        SELECT 1 FROM pg_constraint
        WHERE conrelid = 'runs'::regclass
          AND conname = 'runs_upgraded_from_run_id_fkey'
    ) THEN
        ALTER TABLE runs
            ADD CONSTRAINT runs_upgraded_from_run_id_fkey
            FOREIGN KEY (upgraded_from_run_id) REFERENCES runs(id) ON DELETE SET NULL;
    END IF;
END $$;

INSERT INTO schema_migrations(version)
VALUES ('006_normalized_authority')
ON CONFLICT DO NOTHING;
