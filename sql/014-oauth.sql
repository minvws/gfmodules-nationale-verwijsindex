CREATE TABLE IF NOT EXISTS oauth_tokens (
    id           uuid PRIMARY KEY DEFAULT gen_random_uuid(),

    token_sha256 varchar(64) NOT NULL,
    ura_number   varchar(10) NOT NULL,

    expires_at   timestamptz NOT NULL,
    revoked      boolean NOT NULL DEFAULT false,

    scopes       text NOT NULL DEFAULT '',

    created_at   timestamptz NOT NULL DEFAULT now()
);

CREATE UNIQUE INDEX IF NOT EXISTS ux_oauth_tokens_token_sha256
    ON oauth_tokens (token_sha256);

CREATE INDEX IF NOT EXISTS idx_oauth_tokens_ura_number
    ON oauth_tokens (ura_number);

CREATE INDEX IF NOT EXISTS idx_oauth_tokens_expires_at
    ON oauth_tokens (expires_at);

CREATE INDEX IF NOT EXISTS idx_oauth_tokens_revoked
    ON oauth_tokens (revoked);

-- helps queries like: WHERE scopes @> ARRAY['read']
CREATE INDEX IF NOT EXISTS gin_oauth_tokens_scopes
    ON oauth_tokens USING GIN (scopes);
