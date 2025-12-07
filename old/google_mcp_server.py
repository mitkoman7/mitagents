from fastapi import FastAPI, HTTPException, Request
from fastapi.responses import RedirectResponse, HTMLResponse
from pydantic import BaseModel
from google.oauth2.credentials import Credentials
from google_auth_oauthlib.flow import Flow
from googleapiclient.discovery import build
from googleapiclient.errors import HttpError
from email.mime.text import MIMEText
from email.mime.multipart import MIMEMultipart
import base64
import json
import os
from datetime import datetime, timedelta
from typing import Dict, Any, List, Optional
import secrets
from dotenv import load_dotenv

# Load environment variables
load_dotenv()

app = FastAPI(title="Google Services MCP Server")

# OAuth Configuration
SCOPES = [
    'https://www.googleapis.com/auth/gmail.send',
    'https://www.googleapis.com/auth/gmail.readonly',
    'https://www.googleapis.com/auth/drive.readonly',
    'https://www.googleapis.com/auth/calendar.readonly'
]

CLIENT_CONFIG = {
    "web": {
        "client_id": os.getenv("GOOGLE_CLIENT_ID"),
        "client_secret": os.getenv("GOOGLE_CLIENT_SECRET"),
        "redirect_uris": ["http://localhost:8082/oauth2callback"],
        "auth_uri": "https://accounts.google.com/o/oauth2/auth",
        "token_uri": "https://oauth2.googleapis.com/token"
    }
}

# Store credentials in memory (use database in production)
user_credentials = {}
session_tokens = {}

class ToolRequest(BaseModel):
    tool_name: str
    arguments: Dict[str, Any]
    session_token: Optional[str] = None

class Tool(BaseModel):
    name: str
    description: str
    inputSchema: Dict[str, Any]

def get_credentials(session_token: str) -> Optional[Credentials]:
    """Get user credentials from session token"""
    if not session_token or session_token not in session_tokens:
        return None
    user_id = session_tokens[session_token]
    return user_credentials.get(user_id)

def save_credentials(user_id: str, creds: Credentials):
    """Save user credentials"""
    user_credentials[user_id] = creds

@app.get("/")
async def root():
    return HTMLResponse("""
    <!DOCTYPE html>
    <html>
    <head>
        <title>Google MCP Server</title>
        <style>
            body { font-family: Arial; max-width: 800px; margin: 50px auto; padding: 20px; }
            .card { background: white; padding: 30px; border-radius: 10px; box-shadow: 0 2px 10px rgba(0,0,0,0.1); }
            h1 { color: #4285f4; }
            .btn { background: #4285f4; color: white; padding: 12px 24px; border: none; 
                   border-radius: 5px; cursor: pointer; text-decoration: none; display: inline-block; }
            .btn:hover { background: #357ae8; }
            .status { padding: 10px; margin: 10px 0; border-radius: 5px; }
            .success { background: #e8f5e9; color: #2e7d32; }
            .error { background: #ffebee; color: #c62828; }
        </style>
    </head>
    <body>
        <div class="card">
            <h1>🔐 Google Services MCP Server</h1>
            <p>This server provides access to Gmail, Google Drive, and Google Calendar via OAuth SSO.</p>
            
            <h3>Available Services:</h3>
            <ul>
                <li>📧 <strong>Gmail</strong>: Send emails, search messages</li>
                <li>📁 <strong>Google Drive</strong>: Search and retrieve files</li>
                <li>📅 <strong>Google Calendar</strong>: View upcoming events</li>
            </ul>
            
            <a href="/auth/login" class="btn">🔑 Sign in with Google</a>
            
            <h3 style="margin-top: 30px;">API Endpoints:</h3>
            <ul>
                <li><code>GET /tools</code> - List available tools</li>
                <li><code>POST /execute</code> - Execute a tool</li>
                <li><code>GET /auth/login</code> - Start OAuth flow</li>
                <li><code>GET /auth/status</code> - Check auth status</li>
            </ul>
        </div>
    </body>
    </html>
    """)

@app.get("/auth/login")
async def login():
    """Start OAuth flow"""
    try:
        flow = Flow.from_client_config(
            CLIENT_CONFIG,
            scopes=SCOPES,
            redirect_uri="http://localhost:8082/oauth2callback"
        )
        
        authorization_url, state = flow.authorization_url(
            access_type='offline',
            include_granted_scopes='true',
            prompt='consent'
        )
        
        # Store state for verification
        session_tokens[state] = state
        
        return RedirectResponse(url=authorization_url)
    except Exception as e:
        return HTMLResponse(f"""
        <html><body>
            <h2>Error starting OAuth flow</h2>
            <p>{str(e)}</p>
            <p>Make sure GOOGLE_CLIENT_ID and GOOGLE_CLIENT_SECRET are set in your .env file</p>
            <a href="/">Back to home</a>
        </body></html>
        """)

@app.get("/oauth2callback")
async def oauth2callback(request: Request):
    """Handle OAuth callback"""
    try:
        state = request.query_params.get('state')
        code = request.query_params.get('code')
        
        if not code:
            raise HTTPException(status_code=400, detail="No authorization code received")
        
        flow = Flow.from_client_config(
            CLIENT_CONFIG,
            scopes=SCOPES,
            redirect_uri="http://localhost:8082/oauth2callback",
            state=state
        )
        
        flow.fetch_token(code=code)
        credentials = flow.credentials
        
        # Generate session token
        session_token = secrets.token_urlsafe(32)
        user_id = credentials.token[:20]  # Use part of token as user ID
        
        save_credentials(user_id, credentials)
        session_tokens[session_token] = user_id
        
        return HTMLResponse(f"""
        <html>
        <head>
            <style>
                body {{ font-family: Arial; max-width: 600px; margin: 50px auto; padding: 20px; }}
                .success {{ background: #e8f5e9; padding: 20px; border-radius: 10px; border-left: 4px solid #4caf50; }}
                .token {{ background: #f5f5f5; padding: 10px; border-radius: 5px; word-break: break-all; 
                         font-family: monospace; margin: 10px 0; }}
                .btn {{ background: #4285f4; color: white; padding: 10px 20px; border: none; 
                       border-radius: 5px; text-decoration: none; display: inline-block; margin-top: 15px; }}
            </style>
        </head>
        <body>
            <div class="success">
                <h2>✅ Authentication Successful!</h2>
                <p>Your session token:</p>
                <div class="token">{session_token}</div>
                <p><small>Copy this token to use in your Flask app's requests</small></p>
                <a href="/" class="btn">Back to Home</a>
            </div>
        </body>
        </html>
        """)
    except Exception as e:
        return HTMLResponse(f"""
        <html><body>
            <h2>❌ Authentication Failed</h2>
            <p>{str(e)}</p>
            <a href="/auth/login">Try Again</a>
        </body></html>
        """)

@app.get("/auth/status")
async def auth_status(session_token: Optional[str] = None):
    """Check authentication status"""
    if not session_token:
        return {"authenticated": False, "message": "No session token provided"}
    
    creds = get_credentials(session_token)
    if not creds:
        return {"authenticated": False, "message": "Invalid session token"}
    
    return {
        "authenticated": True,
        "valid": creds.valid,
        "expired": creds.expired if hasattr(creds, 'expired') else False
    }

@app.get("/tools")
async def list_tools() -> List[Tool]:
    """List all available Google tools"""
    return [
        Tool(
            name="send_email",
            description="Send an email via Gmail with optional HTML content",
            inputSchema={
                "type": "object",
                "properties": {
                    "to": {
                        "type": "string",
                        "description": "Recipient email address"
                    },
                    "subject": {
                        "type": "string",
                        "description": "Email subject"
                    },
                    "body": {
                        "type": "string",
                        "description": "Email body (can include HTML)"
                    },
                    "is_html": {
                        "type": "boolean",
                        "description": "Whether body is HTML",
                        "default": False
                    }
                },
                "required": ["to", "subject", "body"]
            }
        ),
        Tool(
            name="search_gmail",
            description="Search Gmail messages",
            inputSchema={
                "type": "object",
                "properties": {
                    "query": {
                        "type": "string",
                        "description": "Search query (e.g., 'from:example@gmail.com', 'subject:meeting')"
                    },
                    "max_results": {
                        "type": "integer",
                        "description": "Maximum number of results",
                        "default": 10
                    }
                },
                "required": ["query"]
            }
        ),
        Tool(
            name="search_drive",
            description="Search Google Drive for files",
            inputSchema={
                "type": "object",
                "properties": {
                    "query": {
                        "type": "string",
                        "description": "Search query (e.g., 'name contains \"report\"')"
                    },
                    "max_results": {
                        "type": "integer",
                        "description": "Maximum number of results",
                        "default": 10
                    }
                },
                "required": ["query"]
            }
        ),
        Tool(
            name="get_calendar_events",
            description="Get upcoming calendar events",
            inputSchema={
                "type": "object",
                "properties": {
                    "days_ahead": {
                        "type": "integer",
                        "description": "Number of days to look ahead",
                        "default": 7
                    },
                    "max_results": {
                        "type": "integer",
                        "description": "Maximum number of events",
                        "default": 10
                    }
                }
            }
        ),
        Tool(
            name="get_email_content",
            description="Get the full content of a specific email by ID",
            inputSchema={
                "type": "object",
                "properties": {
                    "message_id": {
                        "type": "string",
                        "description": "Gmail message ID"
                    }
                },
                "required": ["message_id"]
            }
        )
    ]

def create_email_message(to: str, subject: str, body: str, is_html: bool = False):
    """Create email message"""
    message = MIMEMultipart('alternative') if is_html else MIMEText(body)
    
    if is_html:
        message.attach(MIMEText(body, 'plain'))
        message.attach(MIMEText(body, 'html'))
    
    message['to'] = to
    message['subject'] = subject
    
    raw_message = base64.urlsafe_b64encode(message.as_bytes()).decode('utf-8')
    return {'raw': raw_message}

@app.post("/execute")
async def execute_tool(request: ToolRequest):
    """Execute a Google tool"""
    try:
        # Check authentication
        creds = get_credentials(request.session_token)
        if not creds:
            return {"result": json.dumps({
                "error": "Not authenticated. Please visit http://localhost:8082/auth/login to sign in with Google",
                "auth_url": "http://localhost:8082/auth/login"
            }, indent=2)}
        
        # Execute tool based on name
        if request.tool_name == "send_email":
            service = build('gmail', 'v1', credentials=creds)
            
            to = request.arguments.get("to")
            subject = request.arguments.get("subject")
            body = request.arguments.get("body")
            is_html = request.arguments.get("is_html", False)
            
            message = create_email_message(to, subject, body, is_html)
            
            try:
                sent_message = service.users().messages().send(
                    userId='me',
                    body=message
                ).execute()
                
                return {"result": json.dumps({
                    "success": True,
                    "message_id": sent_message['id'],
                    "to": to,
                    "subject": subject
                }, indent=2)}
            except HttpError as error:
                return {"result": json.dumps({
                    "error": f"Gmail API error: {str(error)}"
                }, indent=2)}
        
        elif request.tool_name == "search_gmail":
            service = build('gmail', 'v1', credentials=creds)
            query = request.arguments.get("query", "")
            max_results = request.arguments.get("max_results", 10)
            
            try:
                results = service.users().messages().list(
                    userId='me',
                    q=query,
                    maxResults=max_results
                ).execute()
                
                messages = results.get('messages', [])
                
                if not messages:
                    return {"result": json.dumps({
                        "message": "No messages found",
                        "query": query
                    }, indent=2)}
                
                message_data = []
                for msg in messages:
                    message = service.users().messages().get(
                        userId='me',
                        id=msg['id'],
                        format='metadata',
                        metadataHeaders=['From', 'Subject', 'Date']
                    ).execute()
                    
                    headers = {h['name']: h['value'] for h in message['payload']['headers']}
                    
                    message_data.append({
                        "id": msg['id'],
                        "from": headers.get('From', 'Unknown'),
                        "subject": headers.get('Subject', 'No subject'),
                        "date": headers.get('Date', 'Unknown'),
                        "snippet": message.get('snippet', '')
                    })
                
                return {"result": json.dumps({
                    "query": query,
                    "total_found": len(message_data),
                    "messages": message_data
                }, indent=2)}
            except HttpError as error:
                return {"result": json.dumps({
                    "error": f"Gmail API error: {str(error)}"
                }, indent=2)}
        
        elif request.tool_name == "get_email_content":
            service = build('gmail', 'v1', credentials=creds)
            message_id = request.arguments.get("message_id")
            
            try:
                message = service.users().messages().get(
                    userId='me',
                    id=message_id,
                    format='full'
                ).execute()
                
                headers = {h['name']: h['value'] for h in message['payload']['headers']}
                
                # Extract body
                body = ""
                if 'parts' in message['payload']:
                    for part in message['payload']['parts']:
                        if part['mimeType'] == 'text/plain':
                            body = base64.urlsafe_b64decode(
                                part['body']['data']
                            ).decode('utf-8')
                            break
                else:
                    if 'data' in message['payload']['body']:
                        body = base64.urlsafe_b64decode(
                            message['payload']['body']['data']
                        ).decode('utf-8')
                
                return {"result": json.dumps({
                    "id": message_id,
                    "from": headers.get('From'),
                    "to": headers.get('To'),
                    "subject": headers.get('Subject'),
                    "date": headers.get('Date'),
                    "body": body[:1000]  # First 1000 chars
                }, indent=2)}
            except HttpError as error:
                return {"result": json.dumps({
                    "error": f"Gmail API error: {str(error)}"
                }, indent=2)}
        
        elif request.tool_name == "search_drive":
            service = build('drive', 'v3', credentials=creds)
            query = request.arguments.get("query", "")
            max_results = request.arguments.get("max_results", 10)
            
            try:
                results = service.files().list(
                    q=query,
                    pageSize=max_results,
                    fields="files(id, name, mimeType, modifiedTime, webViewLink, size)"
                ).execute()
                
                files = results.get('files', [])
                
                if not files:
                    return {"result": json.dumps({
                        "message": "No files found",
                        "query": query
                    }, indent=2)}
                
                file_data = []
                for file in files:
                    file_data.append({
                        "id": file['id'],
                        "name": file['name'],
                        "type": file['mimeType'],
                        "modified": file.get('modifiedTime', 'Unknown'),
                        "size": file.get('size', 'N/A'),
                        "link": file.get('webViewLink', 'N/A')
                    })
                
                return {"result": json.dumps({
                    "query": query,
                    "total_found": len(file_data),
                    "files": file_data
                }, indent=2)}
            except HttpError as error:
                return {"result": json.dumps({
                    "error": f"Drive API error: {str(error)}"
                }, indent=2)}
        
        elif request.tool_name == "get_calendar_events":
            service = build('calendar', 'v3', credentials=creds)
            days_ahead = request.arguments.get("days_ahead", 7)
            max_results = request.arguments.get("max_results", 10)
            
            try:
                now = datetime.utcnow().isoformat() + 'Z'
                end_date = (datetime.utcnow() + timedelta(days=days_ahead)).isoformat() + 'Z'
                
                events_result = service.events().list(
                    calendarId='primary',
                    timeMin=now,
                    timeMax=end_date,
                    maxResults=max_results,
                    singleEvents=True,
                    orderBy='startTime'
                ).execute()
                
                events = events_result.get('items', [])
                
                if not events:
                    return {"result": json.dumps({
                        "message": f"No events found in the next {days_ahead} days"
                    }, indent=2)}
                
                event_data = []
                for event in events:
                    start = event['start'].get('dateTime', event['start'].get('date'))
                    end = event['end'].get('dateTime', event['end'].get('date'))
                    
                    event_data.append({
                        "summary": event.get('summary', 'No title'),
                        "start": start,
                        "end": end,
                        "location": event.get('location', 'No location'),
                        "description": event.get('description', '')[:200]
                    })
                
                return {"result": json.dumps({
                    "days_ahead": days_ahead,
                    "total_events": len(event_data),
                    "events": event_data
                }, indent=2)}
            except HttpError as error:
                return {"result": json.dumps({
                    "error": f"Calendar API error: {str(error)}"
                }, indent=2)}
        
        else:
            raise HTTPException(status_code=400, detail=f"Unknown tool: {request.tool_name}")
    
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

@app.get("/health")
async def health():
    return {
        "status": "healthy",
        "server": "google-mcp",
        "authenticated_users": len(user_credentials)
    }

if __name__ == "__main__":
    import uvicorn
    print("🚀 Starting Google MCP Server with OAuth...")
    print("📍 Server: http://localhost:8082")
    print("🔐 Auth: http://localhost:8082/auth/login")
    print("\n⚠️  Make sure to set in .env:")
    print("   GOOGLE_CLIENT_ID=your-client-id")
    print("   GOOGLE_CLIENT_SECRET=your-client-secret")
    print("\n📖 Get credentials at: https://console.cloud.google.com/apis/credentials")
    uvicorn.run(app, host="0.0.0.0", port=8082)