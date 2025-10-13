"""
Action History Storage
Stores recently executed actions for confirmation/cancellation handling
"""
from datetime import datetime, timedelta
import pytz
import config
from collections import deque

# In-memory storage for recent actions
# Format: {'action_id': str, 'event_id': str, 'timestamp': datetime, 'action_type': str, 'event_data': dict}
_action_history = deque(maxlen=50)  # Keep last 50 actions

def add_action(event_id, action_type, event_data):
    """
    Store an executed action in history

    Args:
        event_id: Google Calendar event ID
        action_type: 'CREATE', 'UPDATE', or 'DELETE'
        event_data: Dict with event details

    Returns:
        action_id: Unique identifier for this action
    """
    import uuid
    action_id = str(uuid.uuid4())[:8]

    action = {
        'action_id': action_id,
        'event_id': event_id,
        'timestamp': datetime.now(pytz.timezone(config.TIMEZONE)),
        'action_type': action_type,
        'event_data': event_data.copy()
    }

    _action_history.append(action)
    print(f"[Action History] Added: {action_type} - {event_id}")
    return action_id

def get_last_action(max_age_seconds=120):
    """
    Get the most recent action within the time window

    Args:
        max_age_seconds: Maximum age of action to retrieve (default 120s)

    Returns:
        Action dict or None if no recent actions
    """
    if not _action_history:
        return None

    now = datetime.now(pytz.timezone(config.TIMEZONE))
    cutoff = now - timedelta(seconds=max_age_seconds)

    # Get most recent action
    last_action = _action_history[-1]

    if last_action['timestamp'] >= cutoff:
        return last_action

    return None

def get_action_by_id(action_id):
    """
    Get a specific action by ID

    Args:
        action_id: The action ID to look up

    Returns:
        Action dict or None
    """
    for action in reversed(_action_history):
        if action['action_id'] == action_id:
            return action
    return None

def clear_old_actions(max_age_seconds=300):
    """
    Remove actions older than max_age_seconds
    Called periodically to clean up memory

    Args:
        max_age_seconds: Maximum age to keep (default 300s / 5 minutes)
    """
    now = datetime.now(pytz.timezone(config.TIMEZONE))
    cutoff = now - timedelta(seconds=max_age_seconds)

    # Create new deque with only recent actions
    recent_actions = deque(
        (action for action in _action_history if action['timestamp'] >= cutoff),
        maxlen=50
    )

    _action_history.clear()
    _action_history.extend(recent_actions)

    print(f"[Action History] Cleaned up old actions. Remaining: {len(_action_history)}")

def get_all_recent_actions(max_age_seconds=120):
    """
    Get all recent actions within the time window

    Args:
        max_age_seconds: Maximum age of actions to retrieve (default 120s)

    Returns:
        List of action dicts (most recent first)
    """
    if not _action_history:
        return []

    now = datetime.now(pytz.timezone(config.TIMEZONE))
    cutoff = now - timedelta(seconds=max_age_seconds)

    recent = [
        action for action in _action_history
        if action['timestamp'] >= cutoff
    ]

    return list(reversed(recent))  # Most recent first
