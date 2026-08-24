CREATE TABLE IF NOT EXISTS rv_loan_universes (
    id text PRIMARY KEY,
    case_id text NOT NULL REFERENCES cases(id) ON DELETE CASCADE,
    source_id text NOT NULL,
    source_sha256 char(64) NOT NULL,
    workbook_date date,
    template_version text NOT NULL,
    importer_version text NOT NULL,
    universe_digest char(64),
    row_count integer NOT NULL CHECK (row_count >= 0),
    version integer CHECK (version IS NULL OR version >= 1),
    status text NOT NULL CHECK (status IN ('ACTIVE', 'SUPERSEDED', 'REJECTED', 'WITHDRAWN')),
    record jsonb NOT NULL,
    created_by text NOT NULL,
    created_at timestamptz NOT NULL,
    activated_at timestamptz,
    superseded_at timestamptz,
    withdrawn_at timestamptz,
    UNIQUE (case_id, source_sha256, template_version, importer_version)
);

CREATE UNIQUE INDEX IF NOT EXISTS rv_loan_universes_active_case_idx
    ON rv_loan_universes (case_id)
    WHERE status = 'ACTIVE';

CREATE INDEX IF NOT EXISTS rv_loan_universes_case_created_idx
    ON rv_loan_universes (case_id, created_at DESC);

CREATE TABLE IF NOT EXISTS rv_loan_rows (
    universe_id text NOT NULL REFERENCES rv_loan_universes(id) ON DELETE CASCADE,
    instrument_key text NOT NULL,
    record jsonb NOT NULL,
    PRIMARY KEY (universe_id, instrument_key)
);

CREATE INDEX IF NOT EXISTS rv_loan_rows_universe_idx
    ON rv_loan_rows (universe_id);

INSERT INTO schema_migrations(version) VALUES ('003_rv_loan_universes') ON CONFLICT DO NOTHING;
