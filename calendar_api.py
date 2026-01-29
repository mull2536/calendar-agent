import os.path
import pickle
from datetime import datetime, timedelta
from google.auth.transport.requests import Request
from google.oauth2.credentials import Credentials
from google.oauth2 import service_account
from google_auth_oauthlib.flow import InstalledAppFlow
from googleapiclient.discovery import build
import pytz
import config

# If modifying these scopes, delete the file token.pickle.
SCOPES = config.SCOPES

def get_calendar_service():
    """
    Authenticate and return Google Calendar service
    Supports both Service Account and OAuth authentication
    """
    creds = None

    # Try Service Account first (preferred for server deployments)
    service_account_file = 'service-account.json'
    if os.path.exists(service_account_file):
        print(f"Using service account authentication from {service_account_file}")
        try:
            creds = service_account.Credentials.from_service_account_file(
                service_account_file, scopes=SCOPES)
            # Service account credentials are always valid, no need to refresh
            service = build('calendar', 'v3', credentials=creds)
            return service
        except Exception as e:
            print(f"Error loading service account: {e}")
            print(f"Falling back to OAuth authentication")
            # Continue to OAuth fallback below

    # Fall back to OAuth if no service account
    print("No service account found, using OAuth authentication")

    # The file token.pickle stores the user's access and refresh tokens
    if os.path.exists('token.pickle'):
        with open('token.pickle', 'rb') as token:
            creds = pickle.load(token)

    # If there are no (valid) credentials available, let the user log in
    if not creds or not creds.valid:
        if creds and creds.expired and creds.refresh_token:
            creds.refresh(Request())
        else:
            if not os.path.exists('credentials.json'):
                raise FileNotFoundError(
                    "credentials.json not found. Please download it from Google Cloud Console."
                )
            flow = InstalledAppFlow.from_client_secrets_file('credentials.json', SCOPES)
            creds = flow.run_local_server(port=0)

        # Save the credentials for the next run
        with open('token.pickle', 'wb') as token:
            pickle.dump(creds, token)

    service = build('calendar', 'v3', credentials=creds)
    return service


def list_events(start_time=None, end_time=None, max_results=10):
    """
    List calendar events within a time range
    
    Args:
        start_time: datetime object (timezone aware)
        end_time: datetime object (timezone aware)
        max_results: maximum number of events to return
    
    Returns:
        List of event dictionaries
    """
    service = get_calendar_service()
    
    # Default to today if no time range specified
    if not start_time:
        tz = pytz.timezone(config.TIMEZONE)
        start_time = datetime.now(tz).replace(hour=0, minute=0, second=0, microsecond=0)
    
    if not end_time:
        end_time = start_time + timedelta(days=1)
    
    # Convert to RFC3339 format
    time_min = start_time.isoformat()
    time_max = end_time.isoformat()
    
    # Call the Calendar API
    events_result = service.events().list(
        calendarId=config.CALENDAR_ID,
        timeMin=time_min,
        timeMax=time_max,
        maxResults=max_results,
        singleEvents=True,
        orderBy='startTime'
    ).execute()
    
    events = events_result.get('items', [])
    return events


def create_event(title, start_time, end_time, location=None, description=None, attendees=None):
    """
    Create a new calendar event
    
    Args:
        title: Event title
        start_time: datetime object (timezone aware)
        end_time: datetime object (timezone aware)
        location: Event location (optional)
        description: Event description (optional)
        attendees: List of email addresses (optional)
    
    Returns:
        Created event object
    """
    service = get_calendar_service()
    
    event = {
        'summary': title,
        'start': {
            'dateTime': start_time.isoformat(),
            'timeZone': config.TIMEZONE,
        },
        'end': {
            'dateTime': end_time.isoformat(),
            'timeZone': config.TIMEZONE,
        },
    }
    
    if location:
        event['location'] = location
    
    if description:
        event['description'] = description
    
    if attendees:
        event['attendees'] = [{'email': email} for email in attendees]
    
    created_event = service.events().insert(calendarId=config.CALENDAR_ID, body=event).execute()
    return created_event


def update_event(event_id, title=None, start_time=None, end_time=None, location=None, description=None, attendees=None):
    """
    Update an existing calendar event
    
    Args:
        event_id: Google Calendar event ID
        (other args same as create_event, all optional)
    
    Returns:
        Updated event object
    """
    service = get_calendar_service()
    
    # Get the existing event
    event = service.events().get(calendarId=config.CALENDAR_ID, eventId=event_id).execute()
    
    # Update fields if provided
    if title:
        event['summary'] = title
    
    if start_time:
        event['start'] = {
            'dateTime': start_time.isoformat(),
            'timeZone': config.TIMEZONE,
        }
    
    if end_time:
        event['end'] = {
            'dateTime': end_time.isoformat(),
            'timeZone': config.TIMEZONE,
        }
    
    if location is not None:
        event['location'] = location
    
    if description is not None:
        event['description'] = description
    
    if attendees is not None:
        event['attendees'] = [{'email': email} for email in attendees]
    
    updated_event = service.events().update(
        calendarId=config.CALENDAR_ID,
        eventId=event_id,
        body=event
    ).execute()
    
    return updated_event


def delete_event(event_id):
    """
    Delete a calendar event
    
    Args:
        event_id: Google Calendar event ID
    
    Returns:
        True if successful
    """
    service = get_calendar_service()
    service.events().delete(calendarId=config.CALENDAR_ID, eventId=event_id).execute()
    return True


def format_event_for_display(event):
    """
    Format a Google Calendar event for display
    
    Args:
        event: Event object from Google Calendar API
    
    Returns:
        Formatted string
    """
    title = event.get('summary', 'No Title')
    
    # Parse start and end times
    start = event.get('start', {})
    end = event.get('end', {})
    
    start_dt_str = start.get('dateTime', start.get('date'))
    end_dt_str = end.get('dateTime', end.get('date'))
    
    # Convert to timezone-aware datetime
    tz = pytz.timezone(config.TIMEZONE)
    
    if 'T' in start_dt_str:  # It's a datetime
        start_dt = datetime.fromisoformat(start_dt_str.replace('Z', '+00:00'))
        start_dt = start_dt.astimezone(tz)
        end_dt = datetime.fromisoformat(end_dt_str.replace('Z', '+00:00'))
        end_dt = end_dt.astimezone(tz)
        
        time_str = f"{start_dt.strftime('%A, %B %d, %Y, %I:%M %p')} - {end_dt.strftime('%I:%M %p')}"
    else:  # It's an all-day event
        start_dt = datetime.fromisoformat(start_dt_str)
        time_str = f"{start_dt.strftime('%A, %B %d, %Y')} (All day)"
    
    # Get organizer
    organizer = event.get('organizer', {})
    organizer_email = organizer.get('email', 'Unknown')
    organizer_name = organizer.get('displayName', organizer_email)
    
    # Get location and description
    location = event.get('location', '')
    description = event.get('description', '')
    
    # Get attendees
    attendees = event.get('attendees', [])
    attendee_emails = [a.get('email') for a in attendees if a.get('email')]
    
    # Build details
    details = []
    if location:
        details.append(f"Location: {location}")
    if description:
        details.append(f"Description: {description}")
    if attendee_emails:
        details.append(f"Attendees: {', '.join(attendee_emails)}")
    
    details_str = ', '.join(details) if details else 'No additional details'
    
    return f"Event: {title}\nTime: {time_str}\nOrganizer: {organizer_name}\nDetails: {details_str}"
