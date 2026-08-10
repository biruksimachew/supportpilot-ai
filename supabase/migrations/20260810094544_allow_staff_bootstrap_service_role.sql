-- ============================================================
-- SupportPilot AI
-- M2C.2
-- Least-privilege service-role access for local staff bootstrap
-- ============================================================

grant usage on schema public
to service_role;

grant select, insert, update
on table public.users
to service_role;