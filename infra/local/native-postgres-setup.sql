-- ClaimSathi: LOCAL development on a native PostgreSQL (used when Docker is unavailable).
-- Run once as the postgres superuser:
--   psql -U postgres -h localhost -p 5432 -f infra/local/native-postgres-setup.sql
-- Creates only a dedicated role and two databases. The password is for local development only.
CREATE ROLE claimsathi LOGIN PASSWORD 'claimsathi-local-only';
CREATE DATABASE claimsathi OWNER claimsathi;
CREATE DATABASE claimsathi_test OWNER claimsathi;
