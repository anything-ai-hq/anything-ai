-- Per-user permissions: model access, subscription placeholder, dev flag,
-- and a server-side-enforced daily image quota (Postgres function, not
-- just client-side counting - a real gate, not just UI decoration).

create table if not exists profiles (
  id uuid primary key references auth.users(id) on delete cascade,
  email text not null,
  created_at timestamptz not null default now()
);

create table if not exists permissions (
  user_id uuid primary key references profiles(id) on delete cascade,
  models jsonb not null default '["koda","soi"]'::jsonb,
  subscribed boolean not null default false,
  is_dev boolean not null default false,
  images_used_today int not null default 0,
  usage_day date not null default current_date
);

-- Auto-create profile + permissions row for every new signup. The two admin
-- emails get is_dev + subscribed set immediately so they never have to be
-- manually granted after signing in for the first time.
create or replace function handle_new_user()
returns trigger as $$
declare
  admin_emails text[] := array['jackcahill1403@outlook.com', 'anythiny-ai-hq@outlook.com'];
begin
  insert into public.profiles (id, email) values (new.id, new.email);
  insert into public.permissions (user_id, is_dev, subscribed)
    values (new.id, new.email = any(admin_emails), new.email = any(admin_emails));
  return new;
end;
$$ language plpgsql security definer;

drop trigger if exists on_auth_user_created on auth.users;
create trigger on_auth_user_created
  after insert on auth.users
  for each row execute function handle_new_user();

alter table profiles enable row level security;
alter table permissions enable row level security;

create policy "own profile or admin" on profiles for select
  using (auth.uid() = id or (auth.jwt() ->> 'email') in ('jackcahill1403@outlook.com', 'anythiny-ai-hq@outlook.com'));

create policy "own permissions or admin select" on permissions for select
  using (auth.uid() = user_id or (auth.jwt() ->> 'email') in ('jackcahill1403@outlook.com', 'anythiny-ai-hq@outlook.com'));

create policy "admin update permissions" on permissions for update
  using ((auth.jwt() ->> 'email') in ('jackcahill1403@outlook.com', 'anythiny-ai-hq@outlook.com'))
  with check ((auth.jwt() ->> 'email') in ('jackcahill1403@outlook.com', 'anythiny-ai-hq@outlook.com'));

-- Real server-side quota check + increment. Callable by the user themselves
-- (security definer bypasses the update-is-admin-only policy above safely,
-- because the function's own logic only ever touches auth.uid()'s own row).
create or replace function use_image_generation()
returns jsonb as $$
declare
  perm record;
  today date := current_date;
  daily_limit int := 20;
begin
  select * into perm from permissions where user_id = auth.uid();
  if perm is null then
    return jsonb_build_object('allowed', false, 'reason', 'no permissions row');
  end if;
  if perm.is_dev then
    return jsonb_build_object('allowed', true, 'remaining', null);
  end if;
  if not (perm.subscribed or perm.models ? 'vela') then
    return jsonb_build_object('allowed', false, 'reason', 'no_access');
  end if;
  if perm.usage_day <> today then
    update permissions set images_used_today = 0, usage_day = today where user_id = auth.uid();
    perm.images_used_today := 0;
  end if;
  if perm.images_used_today >= daily_limit then
    return jsonb_build_object('allowed', false, 'reason', 'limit_reached', 'remaining', 0);
  end if;
  update permissions set images_used_today = images_used_today + 1 where user_id = auth.uid();
  return jsonb_build_object('allowed', true, 'remaining', daily_limit - perm.images_used_today - 1);
end;
$$ language plpgsql security definer;

-- Admin-only: reset one user's usage (target_user_id) or everyone's (null).
create or replace function admin_reset_usage(target_user_id uuid default null)
returns void as $$
begin
  if not ((auth.jwt() ->> 'email') in ('jackcahill1403@outlook.com', 'anythiny-ai-hq@outlook.com')) then
    raise exception 'not authorized';
  end if;
  if target_user_id is null then
    update permissions set images_used_today = 0, usage_day = current_date;
  else
    update permissions set images_used_today = 0, usage_day = current_date where user_id = target_user_id;
  end if;
end;
$$ language plpgsql security definer;

-- Backfill: if either admin email already has an account from earlier
-- testing, flag it now instead of waiting for a fresh signup trigger.
update permissions set is_dev = true, subscribed = true
where user_id in (select id from profiles where email in ('jackcahill1403@outlook.com', 'anythiny-ai-hq@outlook.com'));

-- Backfill: any account that signed up before this migration existed has no
-- profiles/permissions row yet (the trigger only fires on new signups).
insert into profiles (id, email)
select id, email from auth.users
where id not in (select id from profiles);

insert into permissions (user_id, is_dev, subscribed)
select id, email in ('jackcahill1403@outlook.com', 'anythiny-ai-hq@outlook.com'), email in ('jackcahill1403@outlook.com', 'anythiny-ai-hq@outlook.com')
from auth.users
where id not in (select user_id from permissions);
