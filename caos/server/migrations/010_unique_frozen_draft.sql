DO $$
BEGIN
    IF NOT EXISTS (
        SELECT 1
        FROM pg_constraint
        WHERE conname = 'frozen_deliverables_exact_draft_key'
          AND conrelid = 'frozen_deliverables'::regclass
    ) THEN
        ALTER TABLE frozen_deliverables
            ADD CONSTRAINT frozen_deliverables_exact_draft_key
            UNIQUE (case_id, pathway, draft_version);
    END IF;
END
$$;
