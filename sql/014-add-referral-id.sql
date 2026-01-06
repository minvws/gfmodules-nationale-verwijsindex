CREATE EXTENSION IF NOT EXISTS "uuid-ossp";
ALTER TABLE referrals DROP CONSTRAINT providers_pkey;
ALTER TABLE referrals ADD CONSTRAINT providers_unique_idx UNIQUE (pseudonym, ura_number, data_domain);
ALTER TABLE referrals ADD COLUMN id UUID PRIMARY KEY DEFAULT uuid_generate_v4();

