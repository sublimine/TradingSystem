-- Inspect trades table structure
SELECT column_name, data_type, character_maximum_length, is_nullable
FROM information_schema.columns
WHERE table_name = 'trades'
ORDER BY ordinal_position;

-- Show sample of existing data if any
SELECT * FROM trades LIMIT 5;

-- Inspect signals table structure
SELECT column_name, data_type, character_maximum_length, is_nullable
FROM information_schema.columns
WHERE table_name = 'signals'
ORDER BY ordinal_position;
