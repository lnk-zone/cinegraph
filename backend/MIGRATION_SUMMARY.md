# Alerts Table Migration Summary

## Task Completed
**Step 4: Update `alerts` table: add `user_id` & RLS**

## Migration Details

### What was accomplished:
1. **Added `user_id` column** to the `alerts` table with proper foreign key constraint to `profiles(id)`
2. **Backfilled existing data** from the `stories` table to populate the `user_id` column
3. **Enabled Row Level Security (RLS)** on the `alerts` table
4. **Created RLS policy** "Alert owners" that restricts access to alerts based on `auth.uid() = user_id`
5. **Added performance index** on the `user_id` column

### SQL Migration Applied:
```sql
-- Step 1: Add user_id column with foreign key to profiles table
ALTER TABLE public.alerts ADD COLUMN IF NOT EXISTS user_id uuid REFERENCES public.profiles(id);

-- Step 2: Backfill user_id from stories table
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

-- Step 5: Create index on user_id for better performance
CREATE INDEX IF NOT EXISTS idx_alerts_user_id ON public.alerts(user_id);
```

### Files Created:
- `sql/004_update_alerts_table_add_user_id_and_rls.sql` - The migration SQL file
- `apply_alerts_migration.py` - Python script to apply the migration
- `verify_alerts_migration.py` - Python script to verify the migration was successful
- `sql/create_stories_table.sql` - Stories table creation (prerequisite)

### Prerequisites Created:
- `profiles` table (using existing `sql/create_profiles_table.sql`)
- `stories` table (created `sql/create_stories_table.sql`)
- `alerts` table (using existing `sql/create_alerts_table.sql`)

### Verification Results:
✅ `user_id` column exists with `uuid` data type and foreign key constraint to `profiles(id)`
✅ Row Level Security is enabled on the `alerts` table
✅ RLS policy "Alert owners" exists with condition `auth.uid() = user_id`
✅ Performance index `idx_alerts_user_id` exists on the `user_id` column

## Status: ✅ COMPLETED
The migration has been successfully applied and verified in the Supabase database.
