-- Migration: 013_pixel_art_system.sql
-- Add pixel art avatar and room type support

-- Add pixel avatar selection to users
ALTER TABLE users ADD COLUMN IF NOT EXISTS pixel_avatar_id TEXT;

-- Add room type to sessions (randomly assigned on creation)
ALTER TABLE sessions ADD COLUMN IF NOT EXISTS room_type TEXT;
