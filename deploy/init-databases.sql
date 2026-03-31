-- Create all 8 databases in a single PostgreSQL instance
-- This runs automatically on first startup via docker-entrypoint-initdb.d

CREATE DATABASE userdb;
CREATE DATABASE subdb;
CREATE DATABASE inventorydb;
CREATE DATABASE integrationdb;
CREATE DATABASE compliancedb;
CREATE DATABASE aidb;
CREATE DATABASE mediadb;
-- tracedb is created by POSTGRES_DB env var (default database)
