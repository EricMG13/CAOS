DO $$
BEGIN
    IF to_regclass('caos_state') IS NOT NULL THEN
        EXECUTE $sql$
            INSERT INTO sources(
                id, case_id, filename, media_type, sha256, vault_path,
                bytes, blocks, withdrawn, created_by, created_at
            )
            SELECT DISTINCT ON (source.key)
                source.key,
                source.value->>'case_id',
                source.value->>'filename',
                source.value->>'media_type',
                source.value->>'sha256',
                source.value->>'vault_path',
                (source.value->>'bytes')::bigint,
                COALESCE(source.value->'blocks', '[]'::jsonb),
                COALESCE((source.value->>'withdrawn')::boolean, false),
                source.value->>'created_by',
                (source.value->>'created_at')::timestamptz
            FROM caos_state
            CROSS JOIN LATERAL jsonb_each(caos_state.state->'sources') AS source(key, value)
            JOIN rv_loan_universes ON rv_loan_universes.source_id = source.key
            WHERE caos_state.id = true
            ON CONFLICT (id) DO UPDATE SET withdrawn = EXCLUDED.withdrawn
        $sql$;
    END IF;

    IF NOT EXISTS (
        SELECT 1
        FROM pg_constraint
        WHERE conrelid = 'rv_loan_universes'::regclass
          AND conname = 'rv_loan_universes_source_id_fkey'
          AND contype = 'f'
          AND confrelid = 'sources'::regclass
          AND conkey = ARRAY[(
              SELECT attnum::smallint
              FROM pg_attribute
              WHERE attrelid = 'rv_loan_universes'::regclass AND attname = 'source_id'
          )]
          AND confkey = ARRAY[(
              SELECT attnum::smallint
              FROM pg_attribute
              WHERE attrelid = 'sources'::regclass AND attname = 'id'
          )]
          AND confdeltype = 'r'
    ) THEN
        ALTER TABLE rv_loan_universes
            ADD CONSTRAINT rv_loan_universes_source_id_fkey
            FOREIGN KEY (source_id) REFERENCES sources(id) ON DELETE RESTRICT NOT VALID;
    END IF;
END $$;

ALTER TABLE rv_loan_universes VALIDATE CONSTRAINT rv_loan_universes_source_id_fkey;

INSERT INTO schema_migrations(version)
VALUES ('004_rv_loan_universe_source_fk')
ON CONFLICT DO NOTHING;
