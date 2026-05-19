ALTER TABLE referrals DROP CONSTRAINT providers_unique_idx;
ALTER TABLE referrals ADD CONSTRAINT providers_unique_idx UNIQUE (ura_number, pseudonym, source);
ALTER TABLE referrals ALTER COLUMN data_domain DROP NOT NULL;
