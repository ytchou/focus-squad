-- Migration: 026_gamification_room_system.sql
-- Description: Gamification Phase 4A — Room, Companions, Item Shop
-- Extends existing items/user_items tables, adds user_room and user_companions

-- ===========================================
-- ALTER EXISTING ITEMS TABLE (add gamification columns)
-- ===========================================

-- Item tier for pricing brackets
ALTER TABLE items ADD COLUMN IF NOT EXISTS tier TEXT DEFAULT 'basic'
    CHECK (tier IN ('basic', 'standard', 'premium'));

-- Grid size for room placement
ALTER TABLE items ADD COLUMN IF NOT EXISTS size_w INTEGER DEFAULT 1 CHECK (size_w >= 1 AND size_w <= 3);
ALTER TABLE items ADD COLUMN IF NOT EXISTS size_h INTEGER DEFAULT 1 CHECK (size_h >= 1 AND size_h <= 3);

-- Attraction tags for companion discovery (Neko Atsume mechanic)
ALTER TABLE items ADD COLUMN IF NOT EXISTS attraction_tags JSONB DEFAULT '[]';

-- Whether item is currently available in shop (for seasonal rotation)
ALTER TABLE items ADD COLUMN IF NOT EXISTS is_available BOOLEAN DEFAULT true;

-- ===========================================
-- ALTER USER_ITEMS TABLE (allow duplicate ownership)
-- ===========================================

-- Drop the UNIQUE constraint so users can own multiple copies of the same item
ALTER TABLE user_items DROP CONSTRAINT IF EXISTS user_items_user_id_item_id_key;

-- ===========================================
-- USER ROOM TABLE (one row per user)
-- ===========================================

CREATE TABLE user_room (
    user_id UUID PRIMARY KEY REFERENCES users(id) ON DELETE CASCADE,
    room_type TEXT DEFAULT 'starter' CHECK (room_type IN ('starter', 'study_loft', 'rooftop_garden', 'cozy_cabin')),
    layout JSONB DEFAULT '[]',  -- [{inventory_id, grid_x, grid_y, rotation}]
    active_companion TEXT,
    updated_at TIMESTAMPTZ DEFAULT NOW()
);

-- Auto-update updated_at on changes
CREATE TRIGGER user_room_updated_at
    BEFORE UPDATE ON user_room
    FOR EACH ROW EXECUTE FUNCTION update_updated_at();

-- ===========================================
-- USER COMPANIONS TABLE
-- ===========================================

CREATE TABLE user_companions (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    user_id UUID NOT NULL REFERENCES users(id) ON DELETE CASCADE,
    companion_type TEXT NOT NULL CHECK (companion_type IN (
        'cat', 'dog', 'bunny', 'hamster',
        'owl', 'fox', 'turtle', 'raccoon'
    )),
    is_starter BOOLEAN DEFAULT false,
    discovered_at TIMESTAMPTZ,          -- when attraction threshold was first met
    visit_scheduled_at TIMESTAMPTZ,     -- discovered_at + 24hrs (cooldown)
    adopted_at TIMESTAMPTZ,             -- null = visiting/scheduled, set = adopted
    created_at TIMESTAMPTZ DEFAULT NOW(),

    UNIQUE(user_id, companion_type)
);

CREATE INDEX idx_user_companions_user ON user_companions(user_id);

-- ===========================================
-- ROW LEVEL SECURITY
-- ===========================================

-- items table: already exists, ensure RLS is enabled and catalog is public
ALTER TABLE items ENABLE ROW LEVEL SECURITY;

-- Drop existing policies if any, then create
DROP POLICY IF EXISTS "Items catalog is public" ON items;
CREATE POLICY "Items catalog is public"
    ON items FOR SELECT
    USING (true);

-- user_items: users can view and manage their own items
ALTER TABLE user_items ENABLE ROW LEVEL SECURITY;

DROP POLICY IF EXISTS "Users can view own items" ON user_items;
CREATE POLICY "Users can view own items"
    ON user_items FOR SELECT
    USING (user_id IN (SELECT id FROM users WHERE auth_id = auth.uid()));

DROP POLICY IF EXISTS "Users can insert own items" ON user_items;
CREATE POLICY "Users can insert own items"
    ON user_items FOR INSERT
    WITH CHECK (user_id IN (SELECT id FROM users WHERE auth_id = auth.uid()));

-- user_room: users can view and update their own room
ALTER TABLE user_room ENABLE ROW LEVEL SECURITY;

CREATE POLICY "Users can view own room"
    ON user_room FOR SELECT
    USING (user_id IN (SELECT id FROM users WHERE auth_id = auth.uid()));

CREATE POLICY "Users can insert own room"
    ON user_room FOR INSERT
    WITH CHECK (user_id IN (SELECT id FROM users WHERE auth_id = auth.uid()));

CREATE POLICY "Users can update own room"
    ON user_room FOR UPDATE
    USING (user_id IN (SELECT id FROM users WHERE auth_id = auth.uid()));

-- user_companions: users can view and manage their own companions
ALTER TABLE user_companions ENABLE ROW LEVEL SECURITY;

CREATE POLICY "Users can view own companions"
    ON user_companions FOR SELECT
    USING (user_id IN (SELECT id FROM users WHERE auth_id = auth.uid()));

CREATE POLICY "Users can insert own companions"
    ON user_companions FOR INSERT
    WITH CHECK (user_id IN (SELECT id FROM users WHERE auth_id = auth.uid()));

CREATE POLICY "Users can update own companions"
    ON user_companions FOR UPDATE
    USING (user_id IN (SELECT id FROM users WHERE auth_id = auth.uid()));

-- ===========================================
-- SEED DATA: ~36 items across 3 tiers + 4 free starter beds
-- ===========================================

-- ---- FREE STARTER BEDS (one per companion type) ----
INSERT INTO items (id, name, name_zh, description, description_zh, category, rarity, image_url, essence_cost, tier, size_w, size_h, attraction_tags, is_purchasable, is_available)
VALUES
    (gen_random_uuid(), 'Cat Bed', '貓床', 'A cozy little bed for your cat companion', '一張舒適的小貓床', 'pet_accessory', 'common', 'cat-bed.png', 0, 'basic', 1, 1, '["cozy", "soft"]', true, true),
    (gen_random_uuid(), 'Dog Bed', '狗床', 'A warm bed for your loyal dog', '一張溫暖的狗狗床', 'pet_accessory', 'common', 'dog-bed.png', 0, 'basic', 1, 1, '["warm", "outdoor"]', true, true),
    (gen_random_uuid(), 'Bunny Cushion', '兔子軟墊', 'A soft cushion for your gentle bunny', '一個柔軟的兔子墊', 'pet_accessory', 'common', 'bunny-cushion.png', 0, 'basic', 1, 1, '["soft", "cozy"]', true, true),
    (gen_random_uuid(), 'Hamster Nest', '倉鼠窩', 'A tiny cozy nest for your hamster', '一個迷你倉鼠窩', 'pet_accessory', 'common', 'hamster-nest.png', 0, 'basic', 1, 1, '["small", "cozy"]', true, true);

-- ---- BASIC TIER (3-5 essence) ----
INSERT INTO items (id, name, name_zh, description, description_zh, category, rarity, image_url, essence_cost, tier, size_w, size_h, attraction_tags, is_purchasable, is_available)
VALUES
    -- Furniture
    (gen_random_uuid(), 'Simple Desk', '簡約書桌', 'A modest wooden desk for studying', '一張簡樸的木書桌', 'furniture', 'common', 'simple-desk.png', 3, 'basic', 2, 1, '["height"]', true, true),
    (gen_random_uuid(), 'Basic Chair', '基本椅子', 'A simple wooden chair', '一把簡單的木椅', 'furniture', 'common', 'basic-chair.png', 3, 'basic', 1, 1, '[]', true, true),
    (gen_random_uuid(), 'Small Bookshelf', '小書架', 'A small shelf for a few books', '一個放幾本書的小架子', 'furniture', 'common', 'small-bookshelf.png', 4, 'basic', 1, 2, '["height"]', true, true),
    (gen_random_uuid(), 'Wooden Stool', '木凳', 'A sturdy little stool', '一張結實的小木凳', 'furniture', 'common', 'wooden-stool.png', 3, 'basic', 1, 1, '[]', true, true),
    (gen_random_uuid(), 'Side Table', '邊桌', 'A handy little side table', '一張方便的小邊桌', 'furniture', 'common', 'side-table.png', 3, 'basic', 1, 1, '[]', true, true),
    -- Decor
    (gen_random_uuid(), 'Small Lamp', '小檯燈', 'A warm little desk lamp', '一盞溫暖的小檯燈', 'decor', 'common', 'small-lamp.png', 3, 'basic', 1, 1, '["warm", "shiny"]', true, true),
    (gen_random_uuid(), 'Plain Rug', '素色地毯', 'A simple woven rug', '一條簡單的編織地毯', 'decor', 'common', 'plain-rug.png', 4, 'basic', 2, 2, '["soft", "warm"]', true, true),
    (gen_random_uuid(), 'Wall Clock', '掛鐘', 'A small round wall clock', '一個圓形小掛鐘', 'decor', 'common', 'wall-clock.png', 3, 'basic', 1, 1, '["shiny"]', true, true),
    (gen_random_uuid(), 'Simple Poster', '簡單海報', 'A motivational study poster', '一張勵志學習海報', 'decor', 'common', 'simple-poster.png', 3, 'basic', 1, 1, '["colorful"]', true, true),
    (gen_random_uuid(), 'Small Mirror', '小鏡子', 'A round wall mirror', '一面圓形壁鏡', 'decor', 'common', 'small-mirror.png', 4, 'basic', 1, 1, '["shiny"]', true, true),
    -- Plants
    (gen_random_uuid(), 'Potted Plant', '盆栽', 'A small green potted plant', '一盆小綠植', 'plant', 'common', 'potted-plant.png', 4, 'basic', 1, 1, '["calm", "outdoor"]', true, true),
    (gen_random_uuid(), 'Tiny Cactus', '小仙人掌', 'A tiny desk cactus', '一棵小仙人掌', 'plant', 'common', 'tiny-cactus.png', 3, 'basic', 1, 1, '["calm"]', true, true),
    (gen_random_uuid(), 'Bamboo Stick', '竹子', 'A single lucky bamboo in water', '一根幸運竹泡在水裡', 'plant', 'common', 'bamboo-stick.png', 4, 'basic', 1, 1, '["water", "calm"]', true, true),
    -- Pet Accessories
    (gen_random_uuid(), 'Water Bowl', '水碗', 'A small ceramic water bowl', '一個小陶瓷水碗', 'pet_accessory', 'common', 'water-bowl.png', 3, 'basic', 1, 1, '["water"]', true, true),
    (gen_random_uuid(), 'Yarn Ball', '毛線球', 'A colorful ball of yarn', '一顆彩色毛線球', 'pet_accessory', 'common', 'yarn-ball.png', 5, 'basic', 1, 1, '["colorful", "soft"]', true, true);

-- ---- STANDARD TIER (10-30 essence) ----
INSERT INTO items (id, name, name_zh, description, description_zh, category, rarity, image_url, essence_cost, tier, size_w, size_h, attraction_tags, is_purchasable, is_available)
VALUES
    -- Furniture
    (gen_random_uuid(), 'Full Bookshelf', '大書架', 'A full-sized bookshelf with colorful spines', '一個擺滿彩色書脊的大書架', 'furniture', 'uncommon', 'full-bookshelf.png', 15, 'standard', 2, 2, '["height", "colorful"]', true, true),
    (gen_random_uuid(), 'Comfy Couch', '舒適沙發', 'A plush two-seater couch', '一張柔軟的雙人沙發', 'furniture', 'uncommon', 'comfy-couch.png', 20, 'standard', 2, 1, '["soft", "cozy"]', true, true),
    (gen_random_uuid(), 'Coffee Table', '咖啡桌', 'A low wooden coffee table', '一張木製矮咖啡桌', 'furniture', 'uncommon', 'coffee-table.png', 12, 'standard', 2, 1, '["warm"]', true, true),
    (gen_random_uuid(), 'Study Desk', '學習桌', 'A proper study desk with drawers', '一張有抽屜的正式書桌', 'furniture', 'uncommon', 'study-desk.png', 18, 'standard', 2, 1, '["height"]', true, true),
    -- Decor
    (gen_random_uuid(), 'Floor Lamp', '落地燈', 'A tall standing floor lamp', '一盞高挑落地燈', 'decor', 'uncommon', 'floor-lamp.png', 15, 'standard', 1, 1, '["warm", "shiny", "height"]', true, true),
    (gen_random_uuid(), 'Woven Rug', '編織地毯', 'A large patterned woven rug', '一條大型圖案編織地毯', 'decor', 'uncommon', 'woven-rug.png', 18, 'standard', 2, 2, '["soft", "warm", "colorful"]', true, true),
    (gen_random_uuid(), 'String Lights', '串燈', 'Warm fairy lights for the wall', '溫暖的牆面裝飾串燈', 'decor', 'uncommon', 'string-lights.png', 12, 'standard', 2, 1, '["warm", "shiny"]', true, true),
    (gen_random_uuid(), 'Art Print', '藝術畫', 'A framed art print', '一幅裝框藝術畫', 'decor', 'uncommon', 'art-print.png', 10, 'standard', 1, 1, '["colorful"]', true, true),
    -- Plants
    (gen_random_uuid(), 'Hanging Vine', '垂吊藤蔓', 'A lush hanging vine plant', '一株茂盛的垂吊藤蔓', 'plant', 'uncommon', 'hanging-vine.png', 15, 'standard', 1, 1, '["outdoor", "calm", "height"]', true, true),
    (gen_random_uuid(), 'Flower Vase', '花瓶', 'Fresh flowers in a ceramic vase', '陶瓷花瓶裡的鮮花', 'plant', 'uncommon', 'flower-vase.png', 12, 'standard', 1, 1, '["colorful", "water"]', true, true),
    -- Pet Accessories
    (gen_random_uuid(), 'Cat Tower', '貓跳台', 'A two-tier cat climbing tower', '一座雙層貓跳台', 'pet_accessory', 'uncommon', 'cat-tower.png', 25, 'standard', 1, 2, '["height", "cozy"]', true, true),
    (gen_random_uuid(), 'Exercise Wheel', '運動滾輪', 'A spinning wheel for small pets', '一個給小寵物的旋轉滾輪', 'pet_accessory', 'uncommon', 'exercise-wheel.png', 20, 'standard', 1, 1, '["small", "colorful"]', true, true);

-- ---- PREMIUM TIER (80-100+ essence) ----
INSERT INTO items (id, name, name_zh, description, description_zh, category, rarity, image_url, essence_cost, tier, size_w, size_h, attraction_tags, is_purchasable, is_available)
VALUES
    (gen_random_uuid(), 'Ornate Bookshelf', '華麗書架', 'A grand bookshelf with fairy lights and a built-in cat perch', '一座有仙女燈和貓咪棲息處的華麗大書架', 'furniture', 'rare', 'ornate-bookshelf.png', 85, 'premium', 2, 2, '["height", "shiny", "cozy", "warm"]', true, true),
    (gen_random_uuid(), 'Mini Aquarium', '迷你水族箱', 'A beautiful desktop aquarium with colorful fish', '一個有彩色魚的美麗桌面水族箱', 'decor', 'rare', 'mini-aquarium.png', 90, 'premium', 2, 1, '["water", "calm", "shiny", "colorful"]', true, true),
    (gen_random_uuid(), 'Window Garden', '窗台花園', 'A lush window garden with herbs and flowers', '一個種滿香草和花卉的窗台花園', 'plant', 'rare', 'window-garden.png', 80, 'premium', 2, 1, '["outdoor", "water", "colorful", "calm"]', true, true),
    (gen_random_uuid(), 'Cozy Reading Nook', '舒適閱讀角', 'A plush reading corner with pillows and blankets', '一個有靠墊和毯子的舒適閱讀角落', 'furniture', 'rare', 'reading-nook.png', 95, 'premium', 2, 2, '["soft", "cozy", "warm"]', true, true),
    (gen_random_uuid(), 'Pet Playground', '寵物樂園', 'A multi-level playground for all companions', '一座多層的全寵物遊樂場', 'pet_accessory', 'rare', 'pet-playground.png', 100, 'premium', 2, 2, '["height", "colorful", "small", "outdoor"]', true, true);
