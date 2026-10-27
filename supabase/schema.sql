-- Run this in the Supabase SQL editor.
create table if not exists public.trips (
  id          uuid primary key,
  user_id     text not null,
  title       text not null,
  request     jsonb not null,
  itinerary   jsonb not null,
  created_at  timestamptz not null default now(),
  updated_at  timestamptz not null default now()
);

create index if not exists trips_user_updated_idx on public.trips (user_id, updated_at desc);

-- The FastAPI backend filters every query by user_id and should connect with the
-- *service role* key (kept server-side only). Enabling RLS blocks any direct access
-- from browsers using the public anon key.
alter table public.trips enable row level security;
