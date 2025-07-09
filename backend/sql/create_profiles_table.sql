-- Create profiles table with RLS
create table if not exists public.profiles (
  id uuid primary key,
  email text not null unique,
  full_name text,
  avatar_url text,
  created_at timestamptz default now()
);

-- Enable row level security
alter table public.profiles enable row level security;

-- Create policy for profiles
create policy "Profiles are editable by owner"
on public.profiles for all
using (auth.uid() = id);

-- Seed existing users
insert into public.profiles (id, email)
select id, email from auth.users
on conflict do nothing;
