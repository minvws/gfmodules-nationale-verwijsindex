ALTER TABLE referrals DROP CONSTRAINT providers_unique_idx;
ALTER TABLE referrals DROP COLUMN data_domain;
ALTER TABLE referrals ADD CONSTRAINT providers_unique_idx UNIQUE (ura_number, pseudonym, source);