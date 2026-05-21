-- Run this once inside the satzone Postgres cluster (NOT the mini-app DB).
-- It creates a read-only role the mini-app's BFF uses to look up users
-- and enrollments by phone.
--
-- The role can SELECT from three tables. Any write attempt raises at the
-- Postgres layer, so even a buggy mini-app cannot mutate satzone state.

-- 1) Create the role with a strong password (replace !!CHANGE_ME!!).
DO $$
BEGIN
   IF NOT EXISTS (SELECT FROM pg_roles WHERE rolname = 'miniapp_ro') THEN
      CREATE ROLE miniapp_ro LOGIN PASSWORD '!!CHANGE_ME!!';
   END IF;
END
$$;

-- 2) Allow the role to use the schema where these tables live (default 'public').
GRANT USAGE ON SCHEMA public TO miniapp_ro;

-- 3) Grant SELECT on the three tables the mini-app reads.
GRANT SELECT ON TABLE public.users TO miniapp_ro;
GRANT SELECT ON TABLE public.courses TO miniapp_ro;
GRANT SELECT ON TABLE public.instructors TO miniapp_ro;
GRANT SELECT ON TABLE public.enrollments TO miniapp_ro;

-- 4) Optional sanity probe.
-- SET ROLE miniapp_ro;
-- SELECT count(*) FROM public.users;     -- works
-- INSERT INTO public.users (id) VALUES (gen_random_uuid());  -- raises permission denied
-- RESET ROLE;
