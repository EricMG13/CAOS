ALTER TABLE model_build_jobs ADD COLUMN actor text;

UPDATE model_build_jobs AS job
SET actor = build.created_by
FROM model_builds AS build
WHERE job.build_id = build.id;

ALTER TABLE model_build_jobs ALTER COLUMN actor SET NOT NULL;

INSERT INTO schema_migrations(version) VALUES ('004_model_build_job_actor') ON CONFLICT DO NOTHING;
