-- Dropping data_domain in 024 also dropped providers_unique_idx, which left referrals without any index
-- besides the primary key. Abort before restoring the unique constraint when duplicates were stored since then,
-- so they can be reviewed instead of being removed by a migration.
DO $$
DECLARE
    duplicate_groups bigint;
BEGIN
    SELECT count(*) INTO duplicate_groups
    FROM (
        SELECT 1
        FROM referrals
        GROUP BY ura_number, pseudonym, source
        HAVING count(*) > 1
    ) AS duplicates;

    IF duplicate_groups > 0 THEN
        RAISE EXCEPTION 'Found % duplicate (ura_number, pseudonym, source) combinations in referrals', duplicate_groups
            USING HINT = 'Remove the duplicate referrals before running this migration again';
    END IF;
END
$$;

CREATE UNIQUE INDEX referrals_ura_pseudonym_source_key ON referrals (ura_number, pseudonym, source);

-- Localization searches by pseudonym across all URA numbers
CREATE INDEX referrals_pseudonym_idx ON referrals (pseudonym);

-- Paged searches filter on URA number and are ordered by creation time
CREATE INDEX referrals_ura_created_at_id_idx ON referrals (ura_number, created_at, id);
