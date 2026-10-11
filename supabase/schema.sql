-- NutriWise AI — Supabase schema
-- Run this once in your Supabase project: SQL Editor -> New query -> paste -> Run.
-- Creates per-user tables with Row Level Security. The FastAPI backend uses the
-- service_role key (which bypasses RLS); the policies additionally protect the
-- data if it is ever accessed with the anon key.

-- ------------------------------------------------------------------ profiles
create table if not exists public.profiles (
  user_id        uuid primary key references auth.users(id) on delete cascade,
  name           text    not null default 'User',
  age            int     not null,
  gender         text    not null default 'male',
  weight_kg      numeric not null,
  height_cm      numeric not null,
  activity_level text    not null default 'sedentary',
  diabetes_type  text    not null default 'type2',
  on_insulin     boolean not null default false,
  hba1c          numeric,
  conditions     jsonb   not null default '[]'::jsonb,
  updated_at     timestamptz not null default now()
);

-- ------------------------------------------------------ glucose_readings (1/day)
create table if not exists public.glucose_readings (
  id           bigint generated always as identity primary key,
  user_id      uuid not null references auth.users(id) on delete cascade,
  value_mg_dl  numeric not null,
  reading_type text not null default 'fasting',
  reading_date date not null,
  category     text not null default 'unknown',
  created_at   timestamptz not null default now(),
  unique (user_id, reading_date)
);

-- ------------------------------------------------------------------- meals
create table if not exists public.meals (
  id         bigint generated always as identity primary key,
  user_id    uuid not null references auth.users(id) on delete cascade,
  meal_date  date not null,
  meal_type  text not null default 'meal',
  nutrition  jsonb not null default '{}'::jsonb,
  foods      jsonb not null default '[]'::jsonb,
  created_at timestamptz not null default now()
);

create index if not exists meals_user_date_idx on public.meals (user_id, meal_date);
create index if not exists glucose_user_date_idx on public.glucose_readings (user_id, reading_date);

-- --------------------------------------------------------------- row level security
alter table public.profiles         enable row level security;
alter table public.glucose_readings enable row level security;
alter table public.meals            enable row level security;

-- Each signed-in user may only touch their own rows (anon-key access path).
do $$
begin
  -- profiles
  if not exists (select 1 from pg_policies where tablename='profiles' and policyname='own profile') then
    create policy "own profile" on public.profiles
      for all using (auth.uid() = user_id) with check (auth.uid() = user_id);
  end if;
  -- glucose
  if not exists (select 1 from pg_policies where tablename='glucose_readings' and policyname='own glucose') then
    create policy "own glucose" on public.glucose_readings
      for all using (auth.uid() = user_id) with check (auth.uid() = user_id);
  end if;
  -- meals
  if not exists (select 1 from pg_policies where tablename='meals' and policyname='own meals') then
    create policy "own meals" on public.meals
      for all using (auth.uid() = user_id) with check (auth.uid() = user_id);
  end if;
end $$;
