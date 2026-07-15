CREATE TABLE keys_info (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    label VARCHAR(50) NOT NULL UNIQUE,
    mechanism VARCHAR(50) NOT NULL,
    active BOOLEAN NOT NULL,
    created_at TIMESTAMP NOT NULL DEFAULT NOW(),
    deleted_at TIMESTAMP
);

ALTER TABLE referrals
  ADD COLUMN key_id UUID NOT NULL,
  ADD CONSTRAINT fky_referrals_key_info FOREIGN KEY (key_id) REFERENCES keys_info(id);
