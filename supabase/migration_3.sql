-- NutriWise AI — Migration 3 (saved analyses history)
-- Run once in the Supabase SQL Editor AFTER supabase_migration_2.sql.

create table if not exists public.analyses (
  id             bigint generated always as identity primary key,
  user_id        uuid not null references auth.users(id) on delete cascade,
  period         text not null default 'week',   -- week | all | custom
  range_from     date,
  range_to       date,
  label          text default '',
  stats          jsonb not null default '{}'::jsonb,
  insights       jsonb not null default '[]'::jsonb,
  next_week_plan jsonb not null default '[]'::jsonb,
  narrative      text,
  created_at     timestamptz not null default now()
);
create index if not exists analyses_user_idx on public.analyses (user_id, created_at desc);

alter table public.analyses enable row level security;
do $$
begin
  if not exists (select 1 from pg_policies where tablename='analyses' and policyname='own analyses') then
    create policy "own analyses" on public.analyses
      for all using (auth.uid() = user_id) with check (auth.uid() = user_id);
  end if;
end $$;
