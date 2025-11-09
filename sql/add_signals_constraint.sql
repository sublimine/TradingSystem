-- Add unique constraint to prevent duplicate signals
-- First check if constraint already exists
DO $$ 
BEGIN
    IF NOT EXISTS (
        SELECT 1 FROM pg_constraint 
        WHERE conname = 'signals_unique_signal'
    ) THEN
        ALTER TABLE signals 
        ADD CONSTRAINT signals_unique_signal 
        UNIQUE (timestamp, symbol, strategy, signal_type);
    END IF;
END $$;
