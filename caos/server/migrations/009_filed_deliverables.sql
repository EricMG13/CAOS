ALTER TABLE frozen_deliverables
    ADD COLUMN IF NOT EXISTS draft_id text,
    ADD COLUMN IF NOT EXISTS preview_digest char(64),
    ADD COLUMN IF NOT EXISTS input_fingerprint char(64),
    ADD COLUMN IF NOT EXISTS superseded_by_id text,
    ADD COLUMN IF NOT EXISTS change_request jsonb;

DO $$
BEGIN
    IF NOT EXISTS (
        SELECT 1 FROM pg_constraint
        WHERE conname = 'frozen_deliverables_status_check'
          AND conrelid = 'frozen_deliverables'::regclass
    ) THEN
        ALTER TABLE frozen_deliverables
            ADD CONSTRAINT frozen_deliverables_status_check
            CHECK (status IN ('FROZEN', 'FILED', 'SUPERSEDED', 'CHANGES_REQUESTED'));
    END IF;
    IF NOT EXISTS (
        SELECT 1 FROM pg_constraint
        WHERE conname = 'frozen_deliverables_superseded_by_fk'
          AND conrelid = 'frozen_deliverables'::regclass
    ) THEN
        ALTER TABLE frozen_deliverables
            ADD CONSTRAINT frozen_deliverables_superseded_by_fk
            FOREIGN KEY (superseded_by_id) REFERENCES frozen_deliverables(id);
    END IF;
END
$$;

CREATE INDEX IF NOT EXISTS frozen_deliverables_filed_idx
    ON frozen_deliverables (case_id, pathway, approved_at DESC, id)
    WHERE status IN ('FILED', 'SUPERSEDED');

-- Legacy compatibility rows are normalized only when the immutable legacy
-- record already carries the exact report identity needed for a read-only
-- Frozen/Filed record. Export bytes are intentionally not reconstructed here.
INSERT INTO frozen_deliverables(
    id, case_id, pathway, draft_version, status, authority_identity,
    model_identity, template_identity, render_identity, digest, value,
    frozen_by, frozen_at, approved_by, approved_at, approval_comment,
    draft_id, preview_digest, input_fingerprint
)
SELECT
    report.id,
    report.case_id,
    'LEGACY_REPORT',
    1,
    CASE WHEN report.status = 'APPROVED' THEN 'FILED' ELSE 'FROZEN' END,
    jsonb_build_object(
        'accepted_snapshot_id', report.record #>> '{content,snapshot_id}',
        'accepted_snapshot_digest', report.snapshot_digest,
        'legacy', true
    ),
    report.record #> '{content,model}',
    jsonb_build_object('template_id', 'caos.legacy-report.v1', 'template_version', 'legacy'),
    jsonb_build_object('version', 'legacy', 'contract_digest', repeat('0', 64)),
    report.digest,
    jsonb_build_object('legacy_report', report.record),
    report.created_by,
    report.created_at,
    report.approved_by,
    report.approved_at,
    report.approval_comment,
    NULL,
    report.preview_digest,
    report.input_fingerprint
FROM reports AS report
WHERE report.status IN ('PENDING_APPROVAL', 'APPROVED')
  AND report.record IS NOT NULL
  AND report.digest ~ '^[0-9a-f]{64}$'
  AND report.snapshot_digest ~ '^[0-9a-f]{64}$'
ON CONFLICT (id) DO NOTHING;
