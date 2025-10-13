import json
from datetime import datetime, timedelta
from openai import OpenAI
import pytz
from dateutil import parser as date_parser
import config

client = OpenAI(api_key=config.OPENAI_API_KEY)

def parse_query(query_text):
    """
    Parse a natural language query into structured intent and entities
    
    Args:
        query_text: Natural language query string
    
    Returns:
        Dictionary with:
        - intent: 'list', 'create', 'update', 'delete'
        - entities: dict with parsed information
    """
    
    # Get current date/time for context
    tz = pytz.timezone(config.TIMEZONE)
    now = datetime.now(tz)
    
    system_prompt = f"""You are a calendar assistant that parses natural language queries into structured data.

Current date and time: {now.strftime('%A, %B %d, %Y, %I:%M %p %Z')}
User's timezone: {config.TIMEZONE}

Parse the user's query and respond with JSON containing:
1. "intent": one of "list", "create", "update", "delete", "confirm", "cancel"
2. "entities": object with relevant fields:
   - For "list": start_time, end_time (ISO format with timezone)
   - For "create": title, start_time, end_time, location (optional), attendees (optional, list of emails), description (optional)
   - For "update": query to find event, changes to make
   - For "delete": query to find event

Time parsing rules:
- "tonight" = 6pm to 11:59pm today
- "today" = rest of today
- "tomorrow" = tomorrow all day
- "9pm" without date = 9pm today (if future) or tomorrow (if past)
- Default event duration = 1 hour if not specified

Examples:
Query: "what's on my agenda tonight"
Response: {{"intent": "list", "entities": {{"start_time": "2025-10-12T18:00:00-04:00", "end_time": "2025-10-12T23:59:59-04:00"}}}}

Query: "book meeting with john@email.com at 9pm at my home"
Response: {{"intent": "create", "entities": {{"title": "Meeting with John", "start_time": "2025-10-12T21:00:00-04:00", "end_time": "2025-10-12T22:00:00-04:00", "location": "my home", "attendees": ["john@email.com"]}}}}

Query: "cancel my 3pm meeting"
Response: {{"intent": "delete", "entities": {{"query": "3pm meeting today"}}}}

Query: "reschedule my 3pm meeting to 5pm"
Response: {{"intent": "update", "entities": {{"query": "3pm meeting today", "changes": {{"start_time": "2025-10-12T17:00:00-04:00", "end_time": "2025-10-12T18:00:00-04:00"}}}}}}

Query: "yes" or "confirm" or "ok" or "correct" or "that's right"
Response: {{"intent": "confirm", "entities": {{}}}}

Query: "no" or "cancel" or "don't do that" or "undo" or "delete that"
Response: {{"intent": "cancel", "entities": {{}}}}

Only respond with valid JSON, no explanations."""

    try:
        response = client.chat.completions.create(
            model="gpt-4-turbo-preview",
            messages=[
                {"role": "system", "content": system_prompt},
                {"role": "user", "content": query_text}
            ],
            temperature=0.3,
            response_format={"type": "json_object"}
        )
        
        result = json.loads(response.choices[0].message.content)
        return result
    
    except Exception as e:
        print(f"Error parsing query: {e}")
        # Fallback: try to determine intent from keywords
        return fallback_parse(query_text)


def fallback_parse(query_text):
    """
    Simple fallback parser if OpenAI fails
    """
    query_lower = query_text.lower()
    
    # Detect intent from keywords
    if any(word in query_lower for word in ['yes', 'confirm', 'ok', 'correct', 'proceed', 'do it', 'go ahead']):
        intent = 'confirm'
    elif any(word in query_lower for word in ['no', 'cancel', 'undo', 'dont', 'stop', 'nevermind']):
        intent = 'cancel'
    elif any(word in query_lower for word in ['list', 'show', 'what', 'agenda', 'schedule', 'calendar']):
        intent = 'list'
    elif any(word in query_lower for word in ['create', 'book', 'schedule', 'add', 'make']):
        intent = 'create'
    elif any(word in query_lower for word in ['update', 'change', 'reschedule', 'move']):
        intent = 'update'
    elif any(word in query_lower for word in ['delete', 'remove']):
        intent = 'delete'
    else:
        intent = 'list'  # Default to list
    
    return {
        "intent": intent,
        "entities": {},
        "fallback": True
    }


def find_event_by_query(query, events):
    """
    Find an event in a list based on a natural language query
    
    Args:
        query: Natural language description of event
        events: List of event objects from Google Calendar
    
    Returns:
        Matching event object or None
    """
    query_lower = query.lower()
    
    # Simple matching based on time and title
    for event in events:
        title = event.get('summary', '').lower()
        start = event.get('start', {})
        start_dt_str = start.get('dateTime', start.get('date', ''))
        
        # Check if time matches
        if start_dt_str:
            try:
                tz = pytz.timezone(config.TIMEZONE)
                if 'T' in start_dt_str:
                    start_dt = datetime.fromisoformat(start_dt_str.replace('Z', '+00:00'))
                    start_dt = start_dt.astimezone(tz)
                    time_str = start_dt.strftime('%I%p').lstrip('0').lower()
                    
                    if time_str in query_lower or start_dt.strftime('%I:%M%p').lstrip('0').lower() in query_lower:
                        return event
            except:
                pass
        
        # Check if title matches
        if title and title in query_lower:
            return event
    
    return None


def parse_datetime_string(dt_string):
    """
    Parse an ISO datetime string to a timezone-aware datetime object
    
    Args:
        dt_string: ISO format datetime string
    
    Returns:
        timezone-aware datetime object
    """
    try:
        dt = datetime.fromisoformat(dt_string.replace('Z', '+00:00'))
        tz = pytz.timezone(config.TIMEZONE)
        return dt.astimezone(tz)
    except:
        return None
