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
