-- Run this once in Supabase: Dashboard -> SQL Editor -> paste -> Run.
-- Creates per-user tables for chats/settings/memory/agents, with row-level
-- security so each user can only ever see/edit their own rows.

create table if not exists chats (
  id uuid primary key default gen_random_uuid(),
  user_id uuid not null default auth.uid() references auth.users(id) on delete cascade,
  title text not null default 'New chat',
  messages jsonb not null default '[]',
  model text not null default 'koda',
  effort text not null default 'medium',
  agent_id uuid,
  created_at timestamptz not null default now(),
  updated_at timestamptz not null default now()
);

create table if not exists agents (
  id uuid primary key default gen_random_uuid(),
  user_id uuid not null default auth.uid() references auth.users(id) on delete cascade,
  name text not null,
  prompt text not null,
  created_at timestamptz not null default now()
);

create table if not exists memory (
  id uuid primary key default gen_random_uuid(),
  user_id uuid not null default auth.uid() references auth.users(id) on delete cascade,
  fact text not null,
  created_at timestamptz not null default now()
);

create table if not exists settings (
  user_id uuid primary key default auth.uid() references auth.users(id) on delete cascade,
  enthusiasm text not null default 'low',
  emojis text not null default 'low',
  sarcasm text not null default 'low'
);

alter table chats enable row level security;
alter table agents enable row level security;
alter table memory enable row level security;
alter table settings enable row level security;

create policy "own chats" on chats for all using (auth.uid() = user_id) with check (auth.uid() = user_id);
create policy "own agents" on agents for all using (auth.uid() = user_id) with check (auth.uid() = user_id);
create policy "own memory" on memory for all using (auth.uid() = user_id) with check (auth.uid() = user_id);
create policy "own settings" on settings for all using (auth.uid() = user_id) with check (auth.uid() = user_id);
