# 🗓️ Calendar Agent with ElevenLabs

A conversational AI calendar assistant that uses natural language to manage your Google Calendar through ElevenLabs voice/text interface.

## ✨ Features

- **Natural Language Processing**: Talk naturally - "What's on my agenda tonight?" or "Book a meeting with John at 9pm"
- **Confirmation Flow**: All create/update/delete operations require confirmation before execution
- **Timezone Aware**: Handles all times in your local timezone
- **Google Calendar Integration**: Full CRUD operations on your personal calendar
- **ElevenLabs Ready**: Webhook endpoints designed for ElevenLabs conversational AI
- **ngrok Tunnel**: Expose your local server securely to the internet

## 📋 Prerequisites

- Python 3.9 or higher
- Google account with Calendar access
- OpenAI API key
- ngrok account (free tier is fine)
- ElevenLabs account (optional, for voice interface)

## 🚀 Quick Start

### 1. Google Calendar API Setup (10 minutes)

1. Go to [Google Cloud Console](https://console.cloud.google.com)
2. Create a new project: "Calendar Agent"
3. Enable the **Google Calendar API**:
   - Go to "APIs & Services" > "Library"
   - Search for "Google Calendar API"
   - Click "Enable"
4. Configure OAuth Consent Screen:
   - Go to "APIs & Services" > "OAuth consent screen"
   - Choose "External" user type
   - Fill in app name and your email
   - **IMPORTANT**: Add yourself to the test user list with your email address (otherwise authentication will fail!)
5. Create OAuth 2.0 Credentials:
   - Go to "APIs & Services" > "Credentials"
   - Click "Create Credentials" > "OAuth client ID"
   - Choose "Desktop app"
   - Download the JSON file
   - Rename it to `credentials.json`
   - Place it in the `calendar-agent` folder

### 2. Install Dependencies

```bash
# Navigate to project folder
cd calendar-agent

# Create virtual environment
python3 -m venv venv

# Activate it
source venv/bin/activate  # On Windows: venv\Scripts\activate

# Install packages
pip install -r requirements.txt
```

### 3. Configure Environment

```bash
# Copy the example env file
cp .env.example .env

# Edit .env with your settings
nano .env  # or use any text editor
```

**Required settings in `.env`:**
```bash
TIMEZONE=America/New_York  # Change to your timezone
OPENAI_API_KEY=sk-your-key-here  # Get from https://platform.openai.com
```

**Find your timezone**: https://en.wikipedia.org/wiki/List_of_tz_database_time_zones

### 4. First Run - Authenticate with Google

```bash
# Run the server for the first time
python main.py
```

A browser window will open asking you to:
1. Choose your Google account
2. Grant calendar access permissions
3. This creates a `token.pickle` file (keep this safe!)

The server will start on `http://localhost:5000`

### 5. Expose with ngrok

**In a separate terminal:**

```bash
# Install ngrok (if not already installed)
# Mac:
brew install ngrok

# Or download from: https://ngrok.com/download

# Run ngrok
ngrok http 5000
```

You'll see output like:
```
Forwarding  https://abc123def456.ngrok.io -> http://localhost:5000
```

**Copy that HTTPS URL** - this is your public webhook URL!

### 6. Test Your Webhook

```bash
# In another terminal, test the query endpoint
curl -X POST https://YOUR-NGROK-URL.ngrok.io/query \
  -H "Content-Type: application/json" \
  -d '{"query": "what meetings do I have today"}'
```

## 🎙️ ElevenLabs Setup

### Configure Your Agent

1. Go to [ElevenLabs Dashboard](https://elevenlabs.io)
2. Create or edit a conversational agent
3. Add these webhook URLs:
   - **Query**: `https://YOUR-NGROK-URL.ngrok.io/query`
   - **Confirm**: `https://YOUR-NGROK-URL.ngrok.io/confirm?action_id={action_id}`
   - **Cancel**: `https://YOUR-NGROK-URL.ngrok.io/cancel?action_id={action_id}`

### Agent Instructions

Add to your ElevenLabs agent system prompt:

```
You are a friendly calendar assistant.

When the user asks about their calendar:
1. Call the /query webhook with their question
2. If the response has "requires_confirmation: true":
   - Read the confirmation message to the user
   - Wait for their response (yes/no/confirm/cancel)
   - If they confirm: call /confirm with the action_id
   - If they decline: call /cancel with the action_id
3. If "requires_confirmation: false":
   - Just read the message to the user

Be conversational and helpful!
```

## 📱 Usage Examples

### Query Events

**You say:** "What's on my agenda tonight?"

**Agent responds:** "You have 2 events tonight:

Event: Team Standup
Time: Sunday, October 12, 2025, 6:00 PM - 6:30 PM
Organizer: sarah@example.com
Details: Conference Room A

Event: Dinner
Time: Sunday, October 12, 2025, 8:00 PM - 10:00 PM
Organizer: You
Details: Location: Home"

### Create Event

**You say:** "Book a meeting with john@email.com at 9pm at my home"

**Agent asks:** "I'll create 'Meeting with John' on Sunday, October 12 at 9:00 PM at my home with john@email.com. Should I proceed?"

**You say:** "Yes"

**Agent confirms:** "Done! Meeting with John created for Sunday, October 12, 2025, 9:00 PM - 10:00 PM."

### Update Event

**You say:** "Reschedule my 3pm meeting to 5pm"

**Agent asks:** "I'll update 'Team Planning' to Sunday, October 12 at 5:00 PM. Should I proceed?"

**You say:** "Yes"

**Agent confirms:** "Event updated successfully!"

### Delete Event

**You say:** "Cancel my 3pm meeting"

**Agent asks:** "I'll cancel 'Team Planning' scheduled for Sunday, October 12 at 3:00 PM. Should I proceed?"

**You say:** "No, actually keep it"

**Agent confirms:** "Action cancelled. No changes were made to your calendar."

## 🔧 API Reference

### POST /query

Process a natural language query.

**Request:**
```json
{
  "query": "what's on my agenda tonight"
}
```

**Response (Read-Only):**
```json
{
  "type": "result",
  "requires_confirmation": false,
  "message": "You have 2 events tonight:\n\n..."
}
```

**Response (Requires Confirmation):**
```json
{
  "type": "confirmation",
  "requires_confirmation": true,
  "action_id": "abc12345",
  "message": "I'll create a meeting... Should I proceed?"
}
```

### POST /confirm?action_id={id}

Confirm and execute a pending action.

**Response:**
```json
{
  "success": true,
  "type": "action_completed",
  "message": "Event created successfully!\n\n..."
}
```

### POST /cancel?action_id={id}

Cancel a pending action.

**Response:**
```json
{
  "success": true,
  "message": "Action cancelled. No changes made."
}
```

### GET /

Health check endpoint.

**Response:**
```json
{
  "status": "running",
  "service": "Calendar Agent",
  "pending_actions": 0
}
```

## 🛠️ Development Tips

### View ngrok Request Logs

Open http://localhost:4040 in your browser to see all webhook requests in real-time.

### Check Server Logs

The Flask server logs all requests and actions. Watch the terminal for:
- 📝 Received queries
- 🎯 Parsed intents
- ✅ Confirmations
- ❌ Errors

### Test Without ElevenLabs

Use curl to test directly:

```bash
# List events
curl -X POST http://localhost:5000/query \
  -H "Content-Type: application/json" \
  -d '{"query": "what meetings do I have today"}'

# Create event (will return action_id)
curl -X POST http://localhost:5000/query \
  -H "Content-Type: application/json" \
  -d '{"query": "book meeting tomorrow at 2pm"}'

# Confirm the action
curl -X POST "http://localhost:5000/confirm?action_id=abc12345"

# Cancel the action
curl -X POST "http://localhost:5000/cancel?action_id=abc12345"
```

## 📁 Project Structure

```
calendar-agent/
├── main.py              # Flask webhook server
├── calendar_api.py      # Google Calendar operations
├── nlp_parser.py        # Natural language processing
├── confirmations.py     # Confirmation flow logic
├── config.py            # Configuration management
├── requirements.txt     # Python dependencies
├── .env                 # Your environment variables (create from .env.example)
├── .env.example         # Template for .env
├── credentials.json     # Google OAuth credentials (download from Cloud Console)
├── token.pickle         # Generated after first auth (don't share!)
└── README.md           # This file
```

## 🔒 Security Notes

- **credentials.json** and **token.pickle** contain sensitive data - keep them private!
- Add to `.gitignore` if using version control
- ngrok free tier changes URL on restart (fine for personal use)
- For production, upgrade to ngrok paid plan for static URL

## 🐛 Troubleshooting

### "credentials.json not found"
- Download OAuth credentials from Google Cloud Console
- Make sure it's named exactly `credentials.json`
- Place it in the `calendar-agent` folder

### "OPENAI_API_KEY is not set"
- Create `.env` file from `.env.example`
- Add your OpenAI API key
- Get one from https://platform.openai.com/api-keys

### "Module not found" errors
- Make sure virtual environment is activated: `source venv/bin/activate`
- Reinstall dependencies: `pip install -r requirements.txt`

### ngrok URL keeps changing
- Free tier resets URL on restart (this is normal)
- Update ElevenLabs webhook URLs with new URL
- Or upgrade to ngrok paid plan ($8/mo) for static URL

### Events not appearing
- Check your timezone in `.env` matches your location
- Verify Google Calendar permissions were granted
- Check server logs for errors

### Confirmation timeout
- Default is 5 minutes (300 seconds)
- Adjust in `.env`: `CONFIRMATION_TIMEOUT=600` (10 minutes)

## 🎯 Next Steps

### Make It Better
- Add support for recurring events
- Implement smart scheduling (find free slots)
- Add conflict detection
- Support multiple calendars
- Add email notifications

### Deploy for 24/7
- Use Railway.app (free tier available)
- Or upgrade to Cloudflare Tunnel (free, permanent URL)
- See README section on deployment options

## 📞 Support

For issues:
1. Check server logs in terminal
2. Check ngrok request logs at http://localhost:4040
3. Verify .env configuration
4. Test with curl before testing with ElevenLabs

## 📄 License

Personal use project - use as you wish!

---

Made with ☕ by you!
