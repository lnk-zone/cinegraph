-- Migration: Authentication and Row Level Security setup
-- Description: This migration creates the necessary tables and policies for authentication and RLS

-- Create a function to automatically update the updated_at timestamp
CREATE OR REPLACE FUNCTION update_updated_at_column()
RETURNS TRIGGER AS $$
BEGIN
    NEW.updated_at = NOW();
    RETURN NEW;
END;
$$ language 'plpgsql';

-- Create profiles table with RLS
CREATE TABLE IF NOT EXISTS public.profiles (
  id uuid PRIMARY KEY,
  email text NOT NULL UNIQUE,
  full_name text,
  avatar_url text,
  created_at timestamptz DEFAULT now()
);

-- Enable row level security on profiles
ALTER TABLE public.profiles ENABLE ROW LEVEL SECURITY;

-- Create policy for profiles
CREATE POLICY "Profiles are editable by owner"
ON public.profiles FOR ALL
USING (auth.uid() = id);

-- Seed existing users
INSERT INTO public.profiles (id, email)
SELECT id, email FROM auth.users
ON CONFLICT DO NOTHING;

-- Create stories table
CREATE TABLE IF NOT EXISTS public.stories (
    story_type TEXT DEFAULT 'regular' CHECK (story_type IN ('Arc', 'Chapter', 'Thread')),
    id TEXT PRIMARY KEY,
    user_id uuid NOT NULL REFERENCES public.profiles(id),
    title TEXT,
    content TEXT,
    created_at TIMESTAMP WITH TIME ZONE NOT NULL DEFAULT NOW(),
    updated_at TIMESTAMP WITH TIME ZONE NOT NULL DEFAULT NOW()
);

-- Create indexes for better performance on stories
CREATE INDEX IF NOT EXISTS idx_stories_user_id ON public.stories(user_id);
CREATE INDEX IF NOT EXISTS idx_stories_created_at ON public.stories(created_at);

-- Enable Row Level Security on stories
ALTER TABLE public.stories ENABLE ROW LEVEL SECURITY;

-- Create RLS policy for story owners
CREATE POLICY "Story owners"
ON public.stories FOR ALL
USING (auth.uid() = user_id);

-- Create a trigger to automatically update updated_at on stories
CREATE TRIGGER update_stories_updated_at 
    BEFORE UPDATE ON public.stories 
    FOR EACH ROW 
    EXECUTE FUNCTION update_updated_at_column();

-- Create the alerts table for storing enriched contradiction alerts
CREATE TABLE IF NOT EXISTS public.alerts (
    id TEXT PRIMARY KEY,
    story_id TEXT NOT NULL,
    alert_type TEXT NOT NULL DEFAULT 'contradiction_detected',
    severity TEXT NOT NULL CHECK (severity IN ('low', 'medium', 'high', 'critical')),
    explanation TEXT,
    original_alert JSONB,
    detected_at TIMESTAMP WITH TIME ZONE NOT NULL,
    enriched_at TIMESTAMP WITH TIME ZONE NOT NULL DEFAULT NOW(),
    status TEXT NOT NULL DEFAULT 'active' CHECK (status IN ('active', 'resolved', 'dismissed')),
    created_at TIMESTAMP WITH TIME ZONE NOT NULL DEFAULT NOW(),
    updated_at TIMESTAMP WITH TIME ZONE NOT NULL DEFAULT NOW()
);

-- Create indexes for better performance on alerts
CREATE INDEX IF NOT EXISTS idx_alerts_story_id ON public.alerts(story_id);
CREATE INDEX IF NOT EXISTS idx_alerts_severity ON public.alerts(severity);
CREATE INDEX IF NOT EXISTS idx_alerts_status ON public.alerts(status);
CREATE INDEX IF NOT EXISTS idx_alerts_detected_at ON public.alerts(detected_at);
CREATE INDEX IF NOT EXISTS idx_alerts_enriched_at ON public.alerts(enriched_at);

-- Enable real-time subscriptions for the alerts table
ALTER TABLE public.alerts REPLICA IDENTITY FULL;

-- Create a trigger to automatically update updated_at on alerts
CREATE TRIGGER update_alerts_updated_at 
    BEFORE UPDATE ON public.alerts 
    FOR EACH ROW 
    EXECUTE FUNCTION update_updated_at_column();

-- Add user_id column to alerts table with foreign key to profiles table
ALTER TABLE public.alerts ADD COLUMN IF NOT EXISTS user_id uuid REFERENCES public.profiles(id);

-- Backfill user_id from stories table
-- This assumes there's a stories table with user_id column
-- Cast story_id to text to match the stories table id type
UPDATE public.alerts a
SET user_id = s.user_id
FROM public.stories s
WHERE a.story_id = s.id::text;

-- Enable Row Level Security on alerts table
ALTER TABLE public.alerts ENABLE ROW LEVEL SECURITY;

-- Create RLS policy for alert owners
CREATE POLICY "Alert owners"
ON public.alerts FOR ALL
USING (auth.uid() = user_id);

-- Create index on user_id for better performance
CREATE INDEX IF NOT EXISTS idx_alerts_user_id ON public.alerts(user_id);
