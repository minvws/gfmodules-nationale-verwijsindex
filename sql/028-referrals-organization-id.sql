-- Link referrals to the owning organization by its id instead of the URA number (external_id).
--
-- The organizations are filled by tools/migrate_beheer_data.py, which runs after the migrations. Without that copy
-- every referral would look orphaned, so abort when referrals exist but the copy has not run.
-- Deploy the release that performs the copy first.
DO $$
BEGIN
    IF EXISTS (SELECT 1 FROM referrals)
        AND NOT EXISTS (SELECT 1 FROM migrations WHERE name = 'beheer-data-copy') THEN
        RAISE EXCEPTION 'Referrals exist but the beheer data has not been copied into admin.organizations'
            USING HINT = 'Run tools/migrate_beheer_data.py before this migration';
    END IF;
END
$$;

ALTER TABLE referrals ADD COLUMN organization_id UUID;

-- Prefer the active organization. When only deleted organizations carry the URA number, link the most recently
-- deleted one so the referrals stay hidden: referrals are not transferred to an organization that is recreated later.
UPDATE referrals r
SET organization_id = (
    SELECT o.id
    FROM admin.organizations o
    WHERE o.external_id = r.ura_number
    ORDER BY o.deleted_at IS NOT NULL, o.deleted_at DESC
    LIMIT 1
);

-- Referrals without any organization cannot be linked. Abort instead of removing them, so they are dealt with on
-- purpose.
DO $$
DECLARE
    unlinked bigint;
BEGIN
    SELECT count(*) INTO unlinked FROM referrals WHERE organization_id IS NULL;
    IF unlinked > 0 THEN
        RAISE EXCEPTION '% referral(s) have a URA number without any organization in admin.organizations', unlinked
            USING HINT = 'Register the organizations or remove these referrals before this migration';
    END IF;
END
$$;

ALTER TABLE referrals
    ALTER COLUMN organization_id SET NOT NULL,
    ADD CONSTRAINT fk_referrals_organizations FOREIGN KEY (organization_id) REFERENCES admin.organizations (id);

DROP INDEX referrals_ura_pseudonym_source_key;
DROP INDEX referrals_ura_created_at_id_idx;

ALTER TABLE referrals DROP COLUMN ura_number;

CREATE UNIQUE INDEX referrals_organization_pseudonym_source_key ON referrals (organization_id, pseudonym, source);

-- Paged searches filter on the organization and are ordered by creation time
CREATE INDEX referrals_organization_created_at_id_idx ON referrals (organization_id, created_at, id);
