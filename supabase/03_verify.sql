-- =====================================================================================================
-- Optional health check after 01_schema.sql (and 02_first_owner.sql). Read-only. Every row should say OK.
-- =====================================================================================================

SELECT 'tables' AS check, CASE WHEN count(*) = 22 THEN 'OK' ELSE 'MISSING: ' || (22 - count(*)) END AS result,
       count(*) || ' tables in public (21 + alembic_version)' AS detail
FROM pg_tables WHERE schemaname = 'public'
UNION ALL
SELECT 'row level security', CASE WHEN bool_and(c.relrowsecurity) THEN 'OK' ELSE 'OFF on: ' ||
       string_agg(c.relname, ', ') FILTER (WHERE NOT c.relrowsecurity) END,
       'RLS must be on for every public table'
FROM pg_class c JOIN pg_namespace n ON n.oid = c.relnamespace WHERE n.nspname = 'public' AND c.relkind = 'r'
UNION ALL
SELECT 'no public grants', CASE WHEN count(*) = 0 THEN 'OK' ELSE 'GRANTED: ' ||
       string_agg(DISTINCT table_name || ' to ' || grantee, ', ') END,
       'anon/authenticated must have no table privileges'
FROM information_schema.role_table_grants
WHERE table_schema = 'public' AND grantee IN ('anon', 'authenticated')
UNION ALL
SELECT 'businesses', CASE WHEN count(*) = 2 THEN 'OK' ELSE 'FOUND ' || count(*) END,
       string_agg(slug || ' (whatsapp ' || whatsapp || ')', ', ')
FROM public.businesses
UNION ALL
SELECT 'storage buckets', CASE WHEN count(*) = 8 THEN 'OK' ELSE 'FOUND ' || count(*) END,
       string_agg(id, ', ' ORDER BY id)
FROM storage.buckets WHERE id IN ('logos','banners','menu','rooms','hall','gallery','testimonials','seo')
UNION ALL
SELECT 'owner account', CASE WHEN count(*) >= 1 THEN 'OK' ELSE 'NONE: run 02_first_owner.sql' END,
       coalesce(string_agg(email, ', '), '-')
FROM public.admin_users WHERE role = 'owner' AND active
UNION ALL
SELECT 'migration version', CASE WHEN max(version_num) = '0004_storage_buckets' THEN 'OK' ELSE 'AT ' ||
       coalesce(max(version_num), 'none') END, 'alembic_version'
FROM public.alembic_version;
