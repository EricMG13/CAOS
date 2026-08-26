DO $$
DECLARE
    authority_is_identity text;
    authority_sequence text;
    max_authority_order bigint;
BEGIN
    LOCK TABLE model_builds IN ACCESS EXCLUSIVE MODE;
    SELECT is_identity
    INTO authority_is_identity
    FROM information_schema.columns
    WHERE table_schema = current_schema()
      AND table_name = 'model_builds'
      AND column_name = 'authority_order';

    IF authority_is_identity IS DISTINCT FROM 'YES' THEN
        IF authority_is_identity IS NULL THEN
            ALTER TABLE model_builds ADD COLUMN authority_order bigint;
        END IF;
        WITH canonical_legacy_order AS (
            SELECT id, row_number() OVER (ORDER BY queued_at, id)::bigint AS rank
            FROM model_builds
        )
        UPDATE model_builds AS build
        SET authority_order = canonical.rank
        FROM canonical_legacy_order AS canonical
        WHERE build.id = canonical.id;
        ALTER TABLE model_builds ALTER COLUMN authority_order SET NOT NULL;
        ALTER TABLE model_builds
            ALTER COLUMN authority_order ADD GENERATED ALWAYS AS IDENTITY;
    END IF;

    SELECT COALESCE(max(authority_order), 0)
    INTO max_authority_order
    FROM model_builds;
    authority_sequence := pg_get_serial_sequence(
        'model_builds', 'authority_order'
    );
    PERFORM setval(
        authority_sequence::regclass,
        max_authority_order + 1,
        false
    );
END;
$$;

CREATE UNIQUE INDEX IF NOT EXISTS model_builds_authority_order_idx
    ON model_builds (authority_order);

CREATE TABLE IF NOT EXISTS model_revisions (
    id text PRIMARY KEY,
    case_id text NOT NULL REFERENCES cases(id) ON DELETE CASCADE,
    build_id text NOT NULL REFERENCES model_builds(id) ON DELETE RESTRICT,
    parent_revision_id text REFERENCES model_revisions(id) ON DELETE RESTRICT,
    revision_number integer NOT NULL CHECK (revision_number > 0),
    preview_digest char(64) NOT NULL,
    record jsonb NOT NULL,
    signed_by text NOT NULL,
    signed_at timestamptz NOT NULL,
    UNIQUE (case_id, revision_number)
);

CREATE INDEX IF NOT EXISTS model_revisions_case_signed_idx
    ON model_revisions (case_id, revision_number);

CREATE TABLE IF NOT EXISTS model_revision_heads (
    case_id text PRIMARY KEY REFERENCES cases(id) ON DELETE CASCADE,
    build_id text NOT NULL REFERENCES model_builds(id) ON DELETE RESTRICT,
    revision_id text NOT NULL REFERENCES model_revisions(id) ON DELETE RESTRICT,
    updated_at timestamptz NOT NULL DEFAULT now()
);

CREATE TABLE IF NOT EXISTS model_revision_exports (
    revision_id text PRIMARY KEY REFERENCES model_revisions(id) ON DELETE CASCADE,
    actor text NOT NULL,
    state text NOT NULL CHECK (state IN ('queued', 'claimed', 'succeeded', 'failed')),
    worker_id text,
    attempt_token text,
    lease_until timestamptz,
    error jsonb,
    record jsonb NOT NULL,
    created_at timestamptz NOT NULL DEFAULT now(),
    updated_at timestamptz NOT NULL DEFAULT now()
);

CREATE INDEX IF NOT EXISTS model_revision_exports_claim_idx
    ON model_revision_exports (state, lease_until, created_at);

INSERT INTO schema_migrations(version)
VALUES ('007_model_revisions')
ON CONFLICT DO NOTHING;
