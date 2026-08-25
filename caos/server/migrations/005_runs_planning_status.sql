DO $$
BEGIN
    IF EXISTS (
        SELECT 1
        FROM pg_constraint
        WHERE conrelid = 'runs'::regclass
          AND conname = 'runs_status_check'
          AND pg_get_constraintdef(oid) NOT LIKE '%planning%'
    ) THEN
        ALTER TABLE runs
            DROP CONSTRAINT runs_status_check,
            ADD CONSTRAINT runs_status_check
                CHECK (status IN ('planning', 'queued', 'running', 'paused', 'succeeded', 'failed'));
    END IF;
END $$;

INSERT INTO schema_migrations(version)
VALUES ('005_runs_planning_status')
ON CONFLICT DO NOTHING;
