-- Create stories table
CREATE TABLE IF NOT EXISTS public.stories (
    id TEXT PRIMARY KEY,
    user_id uuid NOT NULL REFERENCES public.profiles(id),
    title TEXT,
    content TEXT,
    created_at TIMESTAMP WITH TIME ZONE NOT NULL DEFAULT NOW(),
    updated_at TIMESTAMP WITH TIME ZONE NOT NULL DEFAULT NOW()
);

-- Create indexes for better performance
CREATE INDEX IF NOT EXISTS idx_stories_user_id ON public.stories(user_id);
CREATE INDEX IF NOT EXISTS idx_stories_created_at ON public.stories(created_at);

-- Enable Row Level Security
ALTER TABLE public.stories ENABLE ROW LEVEL SECURITY;

-- Create RLS policy for story owners
CREATE POLICY "Story owners"
ON public.stories FOR ALL
USING (auth.uid() = user_id);

-- Create a trigger to automatically update updated_at on row updates
CREATE TRIGGER update_stories_updated_at 
    BEFORE UPDATE ON public.stories 
    FOR EACH ROW 
    EXECUTE FUNCTION update_updated_at_column();
