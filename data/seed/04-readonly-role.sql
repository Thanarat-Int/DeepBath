-- ─────────────────────────────────────────────────────────────────────────────
--  Read-only role for the Text-to-SQL agent
--  --------------------------------------------------------------------------
--  Defense-in-depth: even if the agent's sqlglot validator is bypassed by a
--  prompt-injection or code bug, the database itself will refuse any write.
--  Banking principle of least privilege.
-- ─────────────────────────────────────────────────────────────────────────────

DO $$
BEGIN
    IF NOT EXISTS (SELECT FROM pg_roles WHERE rolname = 'deepbaht_ro') THEN
        CREATE ROLE deepbaht_ro WITH LOGIN PASSWORD 'deepbaht_ro_dev';
    END IF;
END $$;

-- Strip any inherited write privileges first (in case the role pre-existed)
REVOKE ALL ON SCHEMA public FROM deepbaht_ro;
REVOKE ALL ON ALL TABLES    IN SCHEMA public FROM deepbaht_ro;
REVOKE ALL ON ALL SEQUENCES IN SCHEMA public FROM deepbaht_ro;

-- Grant only what is needed
GRANT  CONNECT ON DATABASE deepbaht TO deepbaht_ro;
GRANT  USAGE   ON SCHEMA   public   TO deepbaht_ro;
GRANT  SELECT  ON ALL TABLES IN SCHEMA public TO deepbaht_ro;

-- Apply to future tables too
ALTER DEFAULT PRIVILEGES IN SCHEMA public GRANT SELECT ON TABLES TO deepbaht_ro;

-- Belt-and-braces: explicitly forbid future write privileges by default
ALTER DEFAULT PRIVILEGES IN SCHEMA public
    REVOKE INSERT, UPDATE, DELETE, TRUNCATE ON TABLES FROM deepbaht_ro;
