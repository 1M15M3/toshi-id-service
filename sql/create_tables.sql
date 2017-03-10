CREATE TABLE IF NOT EXISTS users (
    token_id VARCHAR PRIMARY KEY,
    payment_address VARCHAR,
    created TIMESTAMP WITHOUT TIME ZONE DEFAULT (now() AT TIME ZONE 'utc'),
    updated TIMESTAMP WITHOUT TIME ZONE DEFAULT (now() AT TIME ZONE 'utc'),
    username VARCHAR UNIQUE,
    is_app BOOLEAN DEFAULT FALSE,
    reputation_score DECIMAL,
    review_count INTEGER DEFAULT 0,
    tsv TSVECTOR,
    custom JSON
);

CREATE UNIQUE INDEX IF NOT EXISTS idx_users_lower_username ON users (lower(username));
CREATE INDEX IF NOT EXISTS idx_users_apps ON users (is_app);
CREATE INDEX IF NOT EXISTS  idx_users_tsv ON users USING gin(tsv);

CREATE TABLE IF NOT EXISTS auth_tokens (
    token VARCHAR PRIMARY KEY,
    address VARCHAR,
    created TIMESTAMP WITHOUT TIME ZONE DEFAULT (now() AT TIME ZONE 'utc')
);

CREATE FUNCTION users_search_trigger() RETURNS TRIGGER AS $$
BEGIN
    NEW.tsv :=
        SETWEIGHT(TO_TSVECTOR(COALESCE(NEW.custom->>'name', '')), 'A') ||
        SETWEIGHT(TO_TSVECTOR(COALESCE(NEW.username, '')), 'C');
    RETURN NEW;
END
$$ LANGUAGE plpgsql;

CREATE TRIGGER tsvectorupdate BEFORE INSERT OR UPDATE
ON users FOR EACH ROW EXECUTE PROCEDURE users_search_trigger();

UPDATE database_version SET version_number = 7;
