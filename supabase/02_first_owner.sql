-- =====================================================================================================
-- Make an existing Supabase Auth user the first OWNER of the admin panel.
--
-- 1. Supabase dashboard > Authentication > Users > Add user > Create new user
--    Enter the owner's email and a strong password, and tick "Auto Confirm User".
-- 2. Change the email and name below, then run this in SQL Editor.
--
-- (Alternative without the dashboard: `uv run python -m app.cli create-owner --email ... --name ...
--  --password ...`, which needs SUPABASE_SECRET_KEY in .env.)
-- =====================================================================================================

INSERT INTO public.admin_users (id, name, email, role, active)
SELECT u.id, 'Owner', lower(u.email), 'owner', true          -- <- change 'Owner' to the owner's name
FROM auth.users AS u
WHERE lower(u.email) = lower('owner@example.com')            -- <- change to the owner's email
ON CONFLICT (id) DO UPDATE SET role = 'owner', active = true, name = EXCLUDED.name;

-- Should return one row. If it returns nothing, the email above does not match a user in step 1.
SELECT id, name, email, role, active FROM public.admin_users WHERE role = 'owner';
