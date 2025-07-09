-- Create the alerts table for storing enriched contradiction alerts
CREATE TABLE IF NOT EXISTS alerts (
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

-- Create indexes for better performance
CREATE INDEX IF NOT EXISTS idx_alerts_story_id ON alerts(story_id);
CREATE INDEX IF NOT EXISTS idx_alerts_severity ON alerts(severity);
CREATE INDEX IF NOT EXISTS idx_alerts_status ON alerts(status);
CREATE INDEX IF NOT EXISTS idx_alerts_detected_at ON alerts(detected_at);
CREATE INDEX IF NOT EXISTS idx_alerts_enriched_at ON alerts(enriched_at);

-- Enable real-time subscriptions for the alerts table
ALTER TABLE alerts REPLICA IDENTITY FULL;

-- Create a function to automatically update the updated_at timestamp
CREATE OR REPLACE FUNCTION update_updated_at_column()
RETURNS TRIGGER AS $$
BEGIN
    NEW.updated_at = NOW();
    RETURN NEW;
END;
$$ language 'plpgsql';

-- Create a trigger to automatically update updated_at on row updates
CREATE TRIGGER update_alerts_updated_at 
    BEFORE UPDATE ON alerts 
    FOR EACH ROW 
    EXECUTE FUNCTION update_updated_at_column();

-- Enable Row Level Security (RLS) if needed
-- ALTER TABLE alerts ENABLE ROW LEVEL SECURITY;

-- Create a policy for read access (adjust as needed for your security requirements)
-- CREATE POLICY "Enable read access for all users" ON alerts
--     FOR SELECT USING (true);

-- Create a policy for insert access (adjust as needed for your security requirements)
-- CREATE POLICY "Enable insert access for all users" ON alerts
--     FOR INSERT WITH CHECK (true);

-- Create a policy for update access (adjust as needed for your security requirements)
-- CREATE POLICY "Enable update access for all users" ON alerts
--     FOR UPDATE USING (true);

-- Grant permissions (adjust as needed)
-- GRANT ALL ON TABLE alerts TO anon;
-- GRANT ALL ON TABLE alerts TO authenticated;
