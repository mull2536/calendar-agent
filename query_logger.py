import json
import os
from datetime import datetime
import pytz
import config

LOGS_DIR = "logs"
if not os.path.exists(LOGS_DIR):
    os.makedirs(LOGS_DIR)

def log_query_middleware(app):
    """Middleware to log all /query requests and responses"""
    @app.after_request
    def log_request(response):
        from flask import request
        
        # Log both /query endpoint and root endpoint with query parameter
        if request.path == '/query' or (request.path == '/' and request.args.get('query')):
            try:
                # Get query from POST body or GET parameter
                if request.method == 'POST':
                    query_data = request.get_json() if request.is_json else {}
                    query_text = query_data.get('query', '')
                else:  # GET
                    query_text = request.args.get('query', '')
                
                response_data = response.get_json() if response.is_json else {}
                
                log_entry = {
                    "timestamp": datetime.now(pytz.timezone(config.TIMEZONE)).isoformat(),
                    "method": request.method,
                    "path": request.path,
                    "query": query_text,
                    "response": response_data,
                    "status_code": response.status_code
                }
                
                log_file = os.path.join(LOGS_DIR, f"queries_{datetime.now().strftime('%Y%m%d')}.json")
                
                # Append to daily log file
                logs = []
                if os.path.exists(log_file):
                    with open(log_file, 'r', encoding='utf-8') as f:
                        try:
                            logs = json.load(f)
                        except:
                            logs = []
                
                logs.append(log_entry)
                
                with open(log_file, 'w', encoding='utf-8') as f:
                    json.dump(logs, f, indent=2, ensure_ascii=False)
            except Exception as e:
                print(f"Logging error: {e}")
        
        return response
    
    return app
