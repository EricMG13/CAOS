ALTER TABLE runs
    ADD COLUMN IF NOT EXISTS canonical_generation jsonb;

INSERT INTO schema_migrations(version)
VALUES ('006_run_canonical_generation')
ON CONFLICT DO NOTHING;
