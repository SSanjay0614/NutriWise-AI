-- NutriWise AI — Migration 2 (time, one-meal-per-type, audit, activity)
-- Run this once in the Supabase SQL Editor AFTER supabase_schema.sql.

-- 1) meals: add time + updated_at, enforce one row per (user, day, meal_type)
alter table public.meals add column if not exists eaten_at   timestamptz;
alter table public.meals add column if not exists updated_at timestamptz not null default now();

-- De-duplicate any existing rows (keep the most recent per user/day/type)
-- so the unique constraint below can be added safely.
delete from public.meals m
using public.meals m2
where m.user_id = m2.user_id
  and m.meal_date = m2.meal_date
  and m.meal_type = m2.meal_type
  and m.created_at < m2.created_at;

do $$
begin
  if not exists (
    select 1 from pg_constraint where conname = 'meals_user_day_type_uniq'
  ) then
    alter table public.meals
      add constraint meals_user_day_type_uniq unique (user_id, meal_date, meal_type);
  end if;
end $$;

-- 2) meal_audit: immutable trail of every create/replace/merge/edit/delete
create table if not exists public.meal_audit (
  id         bigint generated always as identity primary key,
  user_id    uuid not null references auth.users(id) on delete cascade,
  meal_date  date not null,
  meal_type  text not null,
  action     text not null,            -- create | replace | merge | edit | delete
  snapshot   jsonb not null default '{}'::jsonb,
  created_at timestamptz not null default now()
);
create index if not exists meal_audit_user_idx on public.meal_audit (user_id, created_at);

-- 3) activities: logged exercise per day
create table if not exists public.activities (
  id              bigint generated always as identity primary key,
  user_id         uuid not null references auth.users(id) on delete cascade,
  activity_date   date not null,
  activity_type   text not null,
  duration_min    numeric not null default 0,
  calories_burned numeric not null default 0,
  performed_at    timestamptz,
  note            text default '',
  created_at      timestamptz not null default now()
);
create index if not exists activities_user_date_idx on public.activities (user_id, activity_date);

-- 4) RLS for the new tables
alter table public.meal_audit enable row level security;
alter table public.activities enable row level security;

do $$
begin
  if not exists (select 1 from pg_policies where tablename='meal_audit' and policyname='own audit') then
    create policy "own audit" on public.meal_audit
      for all using (auth.uid() = user_id) with check (auth.uid() = user_id);
  end if;
  if not exists (select 1 from pg_policies where tablename='activities' and policyname='own activities') then
    create policy "own activities" on public.activities
      for all using (auth.uid() = user_id) with check (auth.uid() = user_id);
  end if;
end $$;
