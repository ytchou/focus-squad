-- Add admin tier to user_tier enum
-- Admin tier is not purchasable, grants debug access and unlimited credits

-- Add the new enum value
ALTER TYPE user_tier ADD VALUE IF NOT EXISTS 'admin';

-- Note: Admin users should be set directly via database:
-- UPDATE credits SET tier = 'admin', credits_remaining = 9999 WHERE user_id = '<user_id>';
