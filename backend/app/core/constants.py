"""
Application constants for Focus Squad.

Centralizes timing values and configuration constants used across the application.
Values derived from SPEC.md requirements.
"""

# Session timing (from SPEC.md § Session Structure)
SESSION_DURATION_MINUTES = 55
PHASE_SETUP_MINUTES = 3
PHASE_WORK_1_MINUTES = 25
PHASE_BREAK_MINUTES = 2
PHASE_WORK_2_MINUTES = 20
PHASE_SOCIAL_MINUTES = 5

# Table configuration
MAX_PARTICIPANTS = 4
MIN_PARTICIPANTS_TO_START = 2

# LiveKit room management
ROOM_CREATION_LEAD_TIME_SECONDS = 30  # Create room T-30s before session
ROOM_CLEANUP_DELAY_MINUTES = 5  # Delete room 5 minutes after session ends
DISCONNECT_GRACE_PERIOD_SECONDS = 120  # 2-minute reconnect window

# Time slot management
SLOT_INTERVAL_MINUTES = 30  # Sessions start at :00 and :30
SLOT_SKIP_THRESHOLD_MINUTES = 3  # Skip slot if less than 3 min away

# Peer Review (from SPEC.md + approved design decisions)
RELIABILITY_HALF_LIFE_DAYS = 30  # Time decay: rating weight halves every 30 days
RELIABILITY_HORIZON_DAYS = 180  # Exclude ratings older than 180 days
RELIABILITY_NEW_USER_THRESHOLD = 5  # Non-skip ratings needed before full score applies
COMMUNITY_AGE_GATE_DAYS = 7  # Account age for Red ratings to carry weight
COMMUNITY_AGE_GATE_SESSIONS = 5  # Completed sessions for Red ratings to carry weight
BAN_DURATION_HOURS = 48
PENALTY_CREDIT_DEDUCTION = 1
RATING_EXPIRY_HOURS = 48  # Pending ratings auto-expire as skip-all

# Dynamic ban thresholds (weighted Red count in rolling 7 days)
PAID_USER_BAN_THRESHOLD = 3.0
FREE_USER_BAN_THRESHOLD = 1.5

# Reporting power multipliers
PAID_RED_WEIGHT = 1.0
FREE_ESTABLISHED_RED_WEIGHT = 0.5  # Free user with 5+ sessions
FREE_NEW_RED_WEIGHT = 0.0  # Free user <5 sessions or <7 days old

# Session Diary
DIARY_TAGS = [
    "productive",
    "distracted",
    "breakthrough",
    "tired",
    "energized",
    "social",
    "deep-focus",
    "struggled",
]
DIARY_NOTE_MAX_LENGTH = 2000

# Content length limits
REFLECTION_MAX_LENGTH = 500
REASON_TEXT_MAX_LENGTH = 500  # rating reasons, leave session reasons
TOPIC_MAX_LENGTH = 100
REFERRAL_CODE_MAX_LENGTH = 20
MAX_RATINGS_PER_BATCH = 3

# Pagination defaults
DEFAULT_PAGE_SIZE = 20
MAX_PAGE_SIZE = 100

# AI companions
AI_COMPANION_NAMES = ["Focus Fox", "Study Owl", "Calm Cat", "Zen Panda"]

# Session completion
MIN_ACTIVE_MINUTES_FOR_COMPLETION = 20

# Pixel Art System
PIXEL_CHARACTERS = [
    "char-1",
    "char-2",
    "char-3",
    "char-4",
    "char-5",
    "char-6",
    "char-7",
    "char-8",
]
PIXEL_ROOMS = [
    "cozy-study",
    "coffee-shop",
    "library",
]

# Find Table — Social proof estimates (Taiwan market, UTC+8)
UPCOMING_SLOTS_COUNT = 6
PEAK_HOUR_ESTIMATE = 25  # 19:00-23:00 local
MODERATE_HOUR_ESTIMATE = 12  # 09:00-18:00 local
OFF_PEAK_HOUR_ESTIMATE = 5  # Other hours

# Moderation
REPORT_DESCRIPTION_MAX_LENGTH = 2000
FLAG_WINDOW_DAYS = 7  # Rolling window for pattern detection
MAX_REPORTS_PER_SESSION = 3  # Prevent report spam per user per session

# Interest Tags (predefined — stored in users.study_interests TEXT[])
INTEREST_TAGS = [
    "coding",
    "writing",
    "design",
    "language_learning",
    "exam_prep",
    "reading",
    "research",
    "music_practice",
    "art",
    "job_hunting",
    "data_science",
    "meditation",
]
MAX_INTEREST_TAGS_PER_USER = 5

# Accountability Partners
MAX_PARTNERS = 50
PARTNER_SEARCH_LIMIT = 20

# Private Tables & Invitations
MIN_PRIVATE_TABLE_SEATS = 2
MAX_PRIVATE_TABLE_SEATS = 4
INVITATION_EXPIRY_HOURS = 24

# Recurring Schedules (Unlimited plan only)
MAX_RECURRING_SCHEDULES = 10
SCHEDULE_LOOKAHEAD_HOURS = 24
SCHEDULE_LABEL_MAX_LENGTH = 100

# Partner Messaging
MESSAGE_MAX_LENGTH = 1000
MESSAGE_RATE_LIMIT_PER_MINUTE = 30
MAX_DIRECT_CONVERSATIONS = 50
MAX_GROUP_CONVERSATIONS = 20
MAX_GROUP_SIZE = 4
MIN_GROUP_SIZE = 2
MESSAGES_PAGE_SIZE = 50
ALLOWED_REACTIONS = [
    "\U0001f44d",
    "\u2764\ufe0f",
    "\U0001f525",
    "\U0001f44f",
    "\U0001f602",
    "\U0001f4af",
]

# Gamification — Room & Companions
ROOM_GRID_WIDTH = 6
ROOM_GRID_HEIGHT = 4
VISITOR_COOLDOWN_HOURS = 24

STARTER_COMPANIONS = ["cat", "dog", "bunny", "hamster"]
DISCOVERABLE_COMPANIONS = ["owl", "fox", "turtle", "raccoon"]

# Gamification — Diary Integration (Phase 4B)

# Companion diary reactions (diary tag -> CSS animation name)
DIARY_TAG_REACTIONS = {
    "productive": "reaction-purr",
    "breakthrough": "reaction-jump",
    "deep-focus": "reaction-nod",
    "energized": "reaction-run",
    "social": "reaction-approach",
    "tired": "reaction-nap",
    "distracted": "reaction-wobble",
    "struggled": "reaction-nudge",
}

# Mood baseline scoring
POSITIVE_DIARY_TAGS = ["productive", "breakthrough", "deep-focus", "energized", "social"]
NEGATIVE_DIARY_TAGS = ["tired", "distracted", "struggled"]
MOOD_POSITIVE_THRESHOLD = 0.3
MOOD_NEGATIVE_THRESHOLD = -0.3
MOOD_WINDOW_DAYS = 7

# Growth timeline milestones
MILESTONE_TYPES = [
    "first_item",
    "session_milestone",
    "companion_discovered",
    "room_unlocked",
    "first_diary",
    "diary_streak_7",
    "first_breakthrough",
]
SESSION_MILESTONE_INTERVAL = 10
SNAPSHOT_MAX_SIZE_BYTES = 2 * 1024 * 1024  # 2MB
DIARY_EXCERPT_MAX_LENGTH = 200

# Weekly streak bonuses
STREAK_BONUS_THRESHOLDS = [
    {"sessions": 3, "bonus_essence": 1, "flag": "bonus_3_awarded"},
    {"sessions": 5, "bonus_essence": 2, "flag": "bonus_5_awarded"},
]

COMPANION_METADATA = {
    "cat": {
        "personality": "Independent, curious",
        "preferred_tags": ["height", "cozy"],
    },
    "dog": {
        "personality": "Loyal, energetic",
        "preferred_tags": ["outdoor", "warm"],
    },
    "bunny": {
        "personality": "Gentle, calm",
        "preferred_tags": ["soft", "cozy"],
    },
    "hamster": {
        "personality": "Playful, tiny",
        "preferred_tags": ["small", "colorful"],
    },
    "owl": {
        "personality": "Wise, nocturnal",
        "preferred_tags": ["height", "shiny"],
        "discovery_hint": "Loves high places and shiny things",
        "threshold": 3,
    },
    "fox": {
        "personality": "Clever, warm-seeking",
        "preferred_tags": ["warm", "soft"],
        "discovery_hint": "Drawn to warmth and soft fabrics",
        "threshold": 3,
    },
    "turtle": {
        "personality": "Calm, patient",
        "preferred_tags": ["water", "calm"],
        "discovery_hint": "Enjoys slow spaces with water nearby",
        "threshold": 3,
    },
    "raccoon": {
        "personality": "Curious, mischievous",
        "preferred_tags": ["colorful", "new"],
        "discovery_hint": "Curious about anything new and colorful",
        "threshold": 3,
    },
}
