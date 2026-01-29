from flask import Flask, request, jsonify, abort
from datetime import datetime, timedelta
import pytz
import config
import calendar_api
import nlp_parser
import confirmations
import query_logger
import action_history
import json
import os
# Validate configuration
if not config.validate_config():
    exit(1)
app = Flask(__name__)
# Enable logging middleware
query_logger.log_query_middleware(app)
# Setup logging
LOGS_DIR = "logs"
if not os.path.exists(LOGS_DIR):
    os.makedirs(LOGS_DIR)
# Simple security check
def verify_request():
    """Verify webhook requests (optional security)"""
    if config.WEBHOOK_SECRET:
        token = request.headers.get('X-Webhook-Token')
        if token != config.WEBHOOK_SECRET:
            abort(403, description="Invalid webhook token")
@app.route('/debug', methods=['GET'])
def debug():
    """Debug endpoint to check credentials status"""
    import os
    debug_info = {
        "service_account_exists": os.path.exists('service-account.json'),
        "credentials_exists": os.path.exists('credentials.json'),
        "token_exists": os.path.exists('token.pickle'),
        "env_vars_set": {
            "GOOGLE_SERVICE_ACCOUNT_BASE64": bool(os.getenv('GOOGLE_SERVICE_ACCOUNT_BASE64')),
            "GOOGLE_CREDENTIALS_BASE64": bool(os.getenv('GOOGLE_CREDENTIALS_BASE64')),
            "GOOGLE_TOKEN_BASE64": bool(os.getenv('GOOGLE_TOKEN_BASE64')),
            "OPENAI_API_KEY": bool(os.getenv('OPENAI_API_KEY')),
            "CALENDAR_ID": os.getenv('CALENDAR_ID', 'not set')
        }
    }
    if os.path.exists('service-account.json'):
        debug_info["service_account_size"] = os.path.getsize('service-account.json')
    if os.path.exists('credentials.json'):
        debug_info["credentials_size"] = os.path.getsize('credentials.json')
    if os.path.exists('token.pickle'):
        debug_info["token_size"] = os.path.getsize('token.pickle')
    return jsonify(debug_info)

@app.route('/', methods=['GET', 'POST'])
def home():
    """Health check endpoint - also handles ElevenLabs calls with query parameter"""
    # If there's a query parameter (ElevenLabs sends /?query=...), process it
    query_text = request.args.get('query')
    if query_text:
        # Process the query using the same logic as /query endpoint
        try:
            # Parse the natural language query
            parsed = nlp_parser.parse_query(query_text)
            intent = parsed.get('intent')
            entities = parsed.get('entities', {})
            
            print(f"Received query (from root): {query_text}")
            print(f" Intent: {intent}")
            print(f" Entities: {entities}")
            
            # Handle based on intent
            if intent == "list":
                return handle_list_query(entities)
            elif intent == "create":
                return handle_create_query(entities, auto_confirm=True)
            elif intent == "update":
                return handle_update_query(entities, auto_confirm=True)
            elif intent == "delete":
                return handle_delete_query(entities, auto_confirm=True)
            elif intent == "confirm":
                return handle_confirm_last_action()
            elif intent == "cancel":
                return handle_cancel_last_action()
            else:
                return jsonify({
                    "type": "error",
                    "message": "I couldn't understand that request. Please try rephrasing."
                }), 400
        except Exception as e:
            print(f"Error processing query: {e}")
            import traceback
            traceback.print_exc()
            return jsonify({
                "type": "error",
                "message": f"An error occurred: {str(e)}"
            }), 500
    
    # Otherwise return health check
    return jsonify({
        "status": "ok",
        "service": "Calendar Agent",
        "timestamp": datetime.now(pytz.timezone(config.TIMEZONE)).isoformat()
    })
@app.route('/query', methods=['POST', 'GET'])
def query():
    """
    Process natural language calendar queries
    Request body:
    {
        "query": "what's on my calendar today?"
    }
    """
    try:
        # Support both POST (JSON body) and GET (URL parameter)
        if request.method == 'POST':
            data = request.get_json()
            if not data or 'query' not in data:
                return jsonify({
                    "type": "error",
                    "error": "Missing 'query' field in request"
                }), 400
            query_text = data['query']
        else:  # GET
            query_text = request.args.get('query')
            if not query_text:
                return jsonify({
                    "type": "error",
                    "error": "Missing 'query' parameter in URL"
                }), 400
        print(f"Received query: {query_text}")
        # Parse the natural language query
        parsed = nlp_parser.parse_query(query_text)
        intent = parsed.get('intent')
        entities = parsed.get('entities', {})
        print(f"Intent: {intent}")
        print(f"Entities: {entities}")
        # Handle based on intent
        if intent == "list":
            return handle_list_query(entities)
        elif intent == "create":
            return handle_create_query(entities)
        elif intent == "update":
            return handle_update_query(entities)
        elif intent == "delete":
            return handle_delete_query(entities)
        else:
            return jsonify({
                "type": "error",
                "message": "I couldn't understand that request. Please try rephrasing."
            }), 400
    except Exception as e:
        print(f"Error processing query: {e}")
        import traceback
        traceback.print_exc()
        return jsonify({
            "type": "error",
            "message": f"An error occurred: {str(e)}"
        }), 500
@app.route('/confirm', methods=['POST'])
def confirm():
    """
    Confirm a pending action
    Query parameter:
    ?action_id=12345
    """
    try:
        action_id = request.args.get('action_id')
        if not action_id:
            return jsonify({
                "error": "Missing action_id parameter"
            }), 400
        print(f"\nConfirming action: {action_id}")
        # Get the pending action
        action = confirmations.confirm_action(action_id)
        if not action:
            return jsonify({
                "success": False,
                "message": "Action not found or has expired. Please make a new request."
            }), 404
        # Execute the action
        action_type = action['action_type']
        event_data = action['event_data']
        if action_type == 'CREATE':
            result = execute_create(event_data)
        elif action_type == 'UPDATE':
            result = execute_update(action['original_event_id'], event_data)
        elif action_type == 'DELETE':
            result = execute_delete(action['original_event_id'], event_data)
        else:
            return jsonify({
                "success": False,
                "message": "Unknown action type"
            }), 400
        # Clean up the pending action
        confirmations.cancel_action(action_id)
        return jsonify(result)
    except Exception as e:
        print(f"Error confirming action: {e}")
        import traceback
        traceback.print_exc()
        return jsonify({
            "success": False,
            "message": f"Error executing action: {str(e)}"
        }), 500
@app.route('/cancel', methods=['POST'])
def cancel():
    """
    Cancel a pending action
    Query parameter:
    ?action_id=12345
    """
    try:
        action_id = request.args.get('action_id')
        if not action_id:
            return jsonify({
                "error": "Missing action_id parameter"
            }), 400
        print(f"\nCancelling action: {action_id}")
        success = confirmations.cancel_action(action_id)
        if success:
            return jsonify({
                "success": True,
                "message": "Action cancelled. No changes were made to your calendar."
            })
        else:
            return jsonify({
                "success": False,
                "message": "Action not found or already expired."
            }), 404
    except Exception as e:
        print(f"Error cancelling action: {e}")
        return jsonify({
            "success": False,
            "message": f"Error: {str(e)}"
        }), 500
# ============= Handler Functions =============
def handle_list_query(entities):
    """Handle LIST intent - query calendar events"""
    # Parse time range
    start_time = entities.get('start_time')
    end_time = entities.get('end_time')
    if start_time:
        start_dt = nlp_parser.parse_datetime_string(start_time)
    else:
        # Default to today
        tz = pytz.timezone(config.TIMEZONE)
        start_dt = datetime.now(tz).replace(hour=0, minute=0, second=0, microsecond=0)
    if end_time:
        end_dt = nlp_parser.parse_datetime_string(end_time)
    else:
        # Default to end of day
        end_dt = start_dt.replace(hour=23, minute=59, second=59)
    # Query calendar
    events = calendar_api.list_events(start_dt, end_dt, max_results=20)
    if not events:
        # Determine time period for message
        if start_dt.date() == datetime.now(pytz.timezone(config.TIMEZONE)).date():
            period = "today"
        else:
            period = f"on {start_dt.strftime('%A, %B %d')}"
        message = f"You have no events scheduled {period}."
    else:
        # Format events
        event_count = len(events)
        period = ""
        if start_dt.date() == datetime.now(pytz.timezone(config.TIMEZONE)).date():
            period = "today"
        else:
            period = f"on {start_dt.strftime('%A, %B %d')}"
        if event_count == 1:
            message = f"You have 1 event {period}:\n\n"
        else:
            message = f"You have {event_count} events {period}:\n\n"
        event_strings = [calendar_api.format_event_for_display(event) for event in events]
        message += "\n\n".join(event_strings)
    return jsonify({
        "type": "result",
        "requires_confirmation": False,
        "message": message
    })
def handle_create_query(entities, auto_confirm=False):
    """Handle CREATE intent - create new event (needs confirmation)"""
    # Extract event details
    title = entities.get('title', 'New Event')
    start_time = entities.get('start_time')
    end_time = entities.get('end_time')
    location = entities.get('location')
    attendees = entities.get('attendees', [])
    description = entities.get('description')
    if not start_time:
        return jsonify({
            "type": "error",
            "message": "I couldn't determine when you want to schedule this event. Please specify a time."
        }), 400
    # Create pending action
    event_data = {
        'title': title,
        'start_time': start_time,
        'end_time': end_time or start_time,
        'location': location,
        'attendees': attendees,
        'description': description
    }
    
    # Auto-confirm if called from root endpoint (ElevenLabs)
    if auto_confirm:
        result = execute_create(event_data)
        # Store in action history for potential cancellation
        if result.get('success') and result.get('event_id'):
            action_history.add_action(result['event_id'], 'CREATE', event_data)
        # Add requires_confirmation flag for ElevenLabs
        result['requires_confirmation'] = True
        return jsonify(result)
    
    action_id = confirmations.create_pending_action('CREATE', event_data)
    # Generate confirmation prompt
    prompt = confirmations.format_confirmation_prompt('CREATE', event_data)
    return jsonify({
        "type": "confirmation",
        "requires_confirmation": True,
        "action_id": action_id,
        "message": prompt
    })
def handle_update_query(entities, auto_confirm=False):
    """Handle UPDATE intent - update existing event (needs confirmation)"""
    query_str = entities.get('query', '')
    changes = entities.get('changes', {})
    if not query_str:
        return jsonify({
            "type": "error",
            "message": "I need more information about which event to update."
        }), 400
    # Find the event
    tz = pytz.timezone(config.TIMEZONE)
    today_start = datetime.now(tz).replace(hour=0, minute=0, second=0, microsecond=0)
    today_end = today_start + timedelta(days=1)
    events = calendar_api.list_events(today_start, today_end, max_results=50)
    event = nlp_parser.find_event_by_query(query_str, events)
    if not event:
        return jsonify({
            "type": "error",
            "message": f"I couldn't find an event matching '{query_str}'. Can you be more specific?"
        }), 404
    # Prepare update data
    event_data = {
        'title': changes.get('title', event.get('summary')),
        'start_time': changes.get('start_time'),
        'end_time': changes.get('end_time'),
        'location': changes.get('location'),
        'attendees': changes.get('attendees'),
        'description': changes.get('description')
    }
    
    # Auto-confirm if called from root endpoint (ElevenLabs)
    if auto_confirm:
        result = execute_update(event['id'], event_data)
        # Store in action history for potential cancellation
        if result.get('success') and result.get('event_id'):
            action_history.add_action(result['event_id'], 'UPDATE', event_data)
        # Add requires_confirmation flag for ElevenLabs
        result['requires_confirmation'] = True
        return jsonify(result)
    
    action_id = confirmations.create_pending_action('UPDATE', event_data, event['id'])
    # Generate confirmation prompt
    prompt = confirmations.format_confirmation_prompt('UPDATE', event_data)
    return jsonify({
        "type": "confirmation",
        "requires_confirmation": True,
        "action_id": action_id,
        "message": prompt
    })
def handle_delete_query(entities, auto_confirm=False):
    """Handle DELETE intent - delete event (needs confirmation)"""
    query_str = entities.get('query', '')
    if not query_str:
        return jsonify({
            "type": "error",
            "message": "I need more information about which event to cancel."
        }), 400
    # Find the event
    tz = pytz.timezone(config.TIMEZONE)
    today_start = datetime.now(tz).replace(hour=0, minute=0, second=0, microsecond=0)
    week_end = today_start + timedelta(days=7)
    events = calendar_api.list_events(today_start, week_end, max_results=50)
    event = nlp_parser.find_event_by_query(query_str, events)
    if not event:
        return jsonify({
            "type": "error",
            "message": f"I couldn't find an event matching '{query_str}'. Can you be more specific?"
        }), 404
    # Prepare event data for display
    event_data = {
        'title': event.get('summary', 'Event'),
        'start_time': event['start'].get('dateTime', event['start'].get('date'))
    }
    
    # Auto-confirm if called from root endpoint (ElevenLabs)
    if auto_confirm:
        result = execute_delete(event['id'], event_data)
        # Store in action history for potential cancellation
        if result.get('success') and result.get('event_id'):
            action_history.add_action(result['event_id'], 'DELETE', event_data)
        # Add requires_confirmation flag for ElevenLabs
        result['requires_confirmation'] = True
        return jsonify(result)
    
    action_id = confirmations.create_pending_action('DELETE', event_data, event['id'])
    # Generate confirmation prompt
    prompt = confirmations.format_confirmation_prompt('DELETE', event_data)
    return jsonify({
        "type": "confirmation",
        "requires_confirmation": True,
        "action_id": action_id,
        "message": prompt
    })

def handle_confirm_last_action():
    """Handle confirmation of last action (already executed)"""
    last_action = action_history.get_last_action(max_age_seconds=120)

    if not last_action:
        return jsonify({
            "type": "result",
            "message": "I don't have any recent actions to confirm. Everything is already done!"
        })

    action_type = last_action['action_type']
    event_data = last_action['event_data']
    title = event_data.get('title', 'Event')

    if action_type == 'CREATE':
        message = f"Confirmed! I've already created '{title}' in your calendar."
    elif action_type == 'UPDATE':
        message = f"Confirmed! I've already updated '{title}' in your calendar."
    elif action_type == 'DELETE':
        message = f"Confirmed! I've already deleted '{title}' from your calendar."
    else:
        message = "Confirmed! The action has been completed."

    return jsonify({
        "type": "result",
        "message": message
    })

def handle_cancel_last_action():
    """Handle cancellation of last action (revert it)"""
    last_action = action_history.get_last_action(max_age_seconds=120)

    if not last_action:
        return jsonify({
            "type": "result",
            "message": "I don't have any recent actions to cancel."
        })

    action_type = last_action['action_type']
    event_id = last_action['event_id']
    event_data = last_action['event_data']
    title = event_data.get('title', 'Event')

    try:
        if action_type == 'CREATE':
            calendar_api.delete_event(event_id)
            message = f"Cancelled! I've removed '{title}' from your calendar."
        elif action_type == 'DELETE':
            message = f"I can't restore '{title}' as it has already been deleted."
        elif action_type == 'UPDATE':
            message = f"I can't automatically revert the changes to '{title}'."
        else:
            message = "I couldn't cancel that action."

        return jsonify({
            "type": "result",
            "message": message
        })
    except Exception as e:
        print(f"Error cancelling action: {e}")
        return jsonify({
            "type": "error",
            "message": f"I couldn't cancel that action: {str(e)}"
        }), 500

# ============= Execution Functions =============
def execute_create(event_data):
    """Execute CREATE action"""
    start_dt = nlp_parser.parse_datetime_string(event_data['start_time'])
    end_dt = nlp_parser.parse_datetime_string(event_data['end_time'])
    if not end_dt:
        end_dt = start_dt + timedelta(hours=1)
    created_event = calendar_api.create_event(
        title=event_data['title'],
        start_time=start_dt,
        end_time=end_dt,
        location=event_data.get('location'),
        description=event_data.get('description'),
        attendees=event_data.get('attendees')
    )
    formatted = calendar_api.format_event_for_display(created_event)
    return {
        "success": True,
        "event_id": created_event.get('id'),
        "type": "action_completed",
        "message": f"Event created successfully!\n\n{formatted}"
    }
def execute_update(event_id, event_data):
    """Execute UPDATE action"""
    start_dt = None
    end_dt = None
    if event_data.get('start_time'):
        start_dt = nlp_parser.parse_datetime_string(event_data['start_time'])
    if event_data.get('end_time'):
        end_dt = nlp_parser.parse_datetime_string(event_data['end_time'])
    updated_event = calendar_api.update_event(
        event_id=event_id,
        title=event_data.get('title'),
        start_time=start_dt,
        end_time=end_dt,
        location=event_data.get('location'),
        description=event_data.get('description'),
        attendees=event_data.get('attendees')
    )
    formatted = calendar_api.format_event_for_display(updated_event)
    return {
        "success": True,
        "event_id": event_id,
        "type": "action_completed",
        "message": f"Event updated successfully!\n\n{formatted}"
    }
def execute_delete(event_id, event_data):
    """Execute DELETE action"""
    calendar_api.delete_event(event_id)
    title = event_data.get('title', 'Event')
    return {
        "success": True,
        "event_id": event_id,
        "type": "action_completed",
        "message": f"Event cancelled successfully!\n\nDeleted: {title}"
    }
if __name__ == '__main__':
    print("\n" + "="*60)
    print("Calendar Agent Starting...")
    print("="*60)
    print(f"Timezone: {config.TIMEZONE}")
    print(f"Confirmation timeout: {config.CONFIRMATION_TIMEOUT} seconds")
    print("\nEndpoints:")
    print("  POST /query   - Process natural language queries")
    print("  POST /confirm - Confirm pending actions")
    print("  POST /cancel  - Cancel pending actions")
    print("  GET  /        - Health check")
    print("\nDon't forget to run ngrok in another terminal:")
    print("   ngrok http 5000")
    print("="*60 + "\n")
    app.run(host='0.0.0.0', port=5000, debug=config.FLASK_DEBUG)
