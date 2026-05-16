-- 002: add owner field to cards
ALTER TABLE cards ADD COLUMN IF NOT EXISTS owner TEXT;
