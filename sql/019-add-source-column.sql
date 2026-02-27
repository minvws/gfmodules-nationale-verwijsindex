ALTER TABLE referrals ADD COLUMN source VARCHAR(255) NOT NULL;
ALTER TABLE referrals DROP CONSTRAINT providers_unique_idx;
ALTER TABLE referrals ADD CONSTRAINT providers_unique_idx UNIQUE (ura_number, pseudonym, data_domain, source);
