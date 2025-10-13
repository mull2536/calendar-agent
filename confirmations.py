import uuid
from datetime import datetime, timedelta
import pytz
import config

# In-memory storage for pending actions
# For personal use, this is fine. Resets on server restart.
pending_actions = {}


def create_pending_action(action_type, event_data, original_event_id=None):
    """
    Create a new pending action that requires confirmation
    
    Args:
        action_type: 'CREATE', 'UPDATE', or 'DELETE'
        event_data: Dictionary with event details
        original_event_id: Google Calendar event ID (for UPDATE/DELETE)
    
    Returns:
        action_id: Unique identifier for this pending action
    """
    action_id = str(uuid.uuid4())[:8]  # Short ID for easier handling
    
    tz = pytz.timezone(config.TIMEZONE)
    now = datetime.now(tz)
    expires_at = now + timedelta(seconds=config.CONFIRMATION_TIMEOUT)
    
    pending_actions[action_id] = {
        'action_id': action_id,
        'action_type': action_type,
        'status': 'PENDING',
        'created_at': now,
        'expires_at': expires_at,
        'event_data': event_data,
        'original_event_id': original_event_id
    }
    
    # Clean up expired actions while we're here
    cleanup_expired_actions()
    
    return action_id


def get_pending_action(action_id):
    """
    Retrieve a pending action by ID
    
    Args:
        action_id: Action identifier
    
    Returns:
        Action dictionary or None if not found/expired
    """
    cleanup_expired_actions()
    
    action = pending_actions.get(action_id)
    
    if not action:
        return None
    
    # Check if expired
    tz = pytz.timezone(config.TIMEZONE)
    now = datetime.now(tz)
    
    if now > action['expires_at']:
        del pending_actions[action_id]
        return None
    
    return action


def confirm_action(action_id):
    """
    Mark an action as confirmed
    
    Args:
        action_id: Action identifier
    
    Returns:
        Action dictionary or None if not found
    """
    action = get_pending_action(action_id)
    
    if action:
        action['status'] = 'CONFIRMED'
        return action
    
    return None


def cancel_action(action_id):
    """
    Cancel a pending action
    
    Args:
        action_id: Action identifier
    
    Returns:
        True if cancelled, False if not found
    """
    if action_id in pending_actions:
        del pending_actions[action_id]
        return True
    
    return False


def cleanup_expired_actions():
    """
    Remove expired actions from storage
    """
    tz = pytz.timezone(config.TIMEZONE)
    now = datetime.now(tz)
    
    expired_ids = [
        action_id for action_id, action in pending_actions.items()
        if now > action['expires_at']
    ]
    
    for action_id in expired_ids:
        del pending_actions[action_id]


def format_confirmation_prompt(action_type, event_data):
    """
    Generate a natural language confirmation prompt
    
    Args:
        action_type: 'CREATE', 'UPDATE', or 'DELETE'
        event_data: Event details dictionary
    
    Returns:
        Formatted confirmation prompt string
    """
    title = event_data.get('title', 'Event')
    start_time = event_data.get('start_time')
    end_time = event_data.get('end_time')
    location = event_data.get('location')
    attendees = event_data.get('attendees', [])
    
    # Format time
    if start_time:
        if isinstance(start_time, str):
            from nlp_parser import parse_datetime_string
            start_dt = parse_datetime_string(start_time)
        else:
            start_dt = start_time
        
        time_str = start_dt.strftime('%A, %B %d at %I:%M %p').replace(' 0', ' ')
    else:
        time_str = "unknown time"
    
    if action_type == 'CREATE':
        prompt = f"I'll create '{title}' on {time_str}"
        
        if location:
            prompt += f" at {location}"
        
        if attendees:
            attendee_list = ', '.join(attendees)
            prompt += f" with {attendee_list}"
        
        prompt += ". Should I proceed?"
    
    elif action_type == 'UPDATE':
        prompt = f"I'll update '{title}' to {time_str}"
        
        if location:
            prompt += f" at {location}"
        
        prompt += ". Should I proceed?"
    
    elif action_type == 'DELETE':
        prompt = f"I'll cancel '{title}' scheduled for {time_str}. Should I proceed?"
    
    else:
        prompt = "Should I proceed with this action?"
    
    return prompt


def format_event_summary(event_data):
    """
    Format event data for display in confirmation
    
    Args:
        event_data: Event details dictionary
    
    Returns:
        Formatted string
    """
    lines = []
    
    if 'title' in event_data:
        lines.append(f"Event: {event_data['title']}")
    
    if 'start_time' in event_data:
        from nlp_parser import parse_datetime_string
        start_dt = parse_datetime_string(event_data['start_time'])
        if start_dt:
            lines.append(f"Time: {start_dt.strftime('%A, %B %d, %Y at %I:%M %p')}")
    
    if 'location' in event_data and event_data['location']:
        lines.append(f"Location: {event_data['location']}")
    
    if 'attendees' in event_data and event_data['attendees']:
        lines.append(f"Attendees: {', '.join(event_data['attendees'])}")
    
    if 'description' in event_data and event_data['description']:
        lines.append(f"Description: {event_data['description']}")
    
    return '\n'.join(lines)


def get_pending_actions_count():
    """
    Get count of pending actions (for debugging)
    
    Returns:
        Number of pending actions
    """
    cleanup_expired_actions()
    return len(pending_actions)
