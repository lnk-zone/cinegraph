-- Migration: Update alerts table - add user_id column and Row Level Security
-- Description: This migration adds a user_id column to the alerts table, 
-- backfills the data from the stories table, and enables Row Level Security (RLS)

-- Step 1: Add user_id column with foreign key to profiles table
ALTER TABLE public.alerts ADD COLUMN IF NOT EXISTS user_id uuid REFERENCES public.profiles(id);

-- Step 2: Backfill user_id from stories table
-- This assumes there's a stories table with user_id column
-- Cast story_id to text to match the stories table id type
UPDATE public.alerts a
SET user_id = s.user_id
FROM public.stories s
WHERE a.story_id = s.id::text;

-- Step 3: Enable Row Level Security on alerts table
ALTER TABLE public.alerts ENABLE ROW LEVEL SECURITY;

-- Step 4: Create RLS policy for alert owners
CREATE POLICY "Alert owners"
ON public.alerts FOR ALL
USING (auth.uid() = user_id);

-- Optional: Create index on user_id for better performance
CREATE INDEX IF NOT EXISTS idx_alerts_user_id ON public.alerts(user_id);
