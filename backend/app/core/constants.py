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
