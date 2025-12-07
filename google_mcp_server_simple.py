"""
Google Services MCP Server - API Key Based (No OAuth)
Uses service account for Gmail, Drive, and Calendar access
"""

from fastapi import FastAPI, HTTPException
from pydantic import BaseModel
from google.oauth2 import service_account
from googleapiclient.discovery import build
from googleapiclient.errors import HttpError
from email.mime.text import MIMEText
from email.mime.multipart import MIMEMultipart
import base64
import json
import os
from datetime import datetime, timedelta
from typing import Dict, Any, List, Optional
from dotenv import load_dotenv
import smtplib

load_dotenv()

app = FastAPI(title="Google Services MCP Server - Simple API")

# Simple email configuration (using SMTP - no OAuth needed)
SMTP_SERVER = "smtp.gmail.com"
SMTP_PORT = 587
GMAIL_ADDRESS = os.getenv("GMAIL_ADDRESS")  # Your Gmail address
GMAIL_APP_PASSWORD = os.getenv("GMAIL_APP_PASSWORD")  # App-specific password
DEFAULT_RECIPIENT = os.getenv("DEFAULT_EMAIL_RECIPIENT", GMAIL_ADDRESS)  # Default to your own email

class ToolRequest(BaseModel):
    tool_name: str
    arguments: Dict[str, Any]

class Tool(BaseModel):
    name: str
    description: str
    inputSchema: Dict[str, Any]

@app.get("/")
async def root():
    return {
        "message": "Google Services MCP Server - API Key Based",
        "note": "No OAuth required - uses Gmail App Passwords",
        "setup": "Set GMAIL_ADDRESS and GMAIL_APP_PASSWORD in .env",
        "endpoints": {
            "tools": "/tools",
            "execute": "/execute",
            "health": "/health"
        }
    }

@app.get("/tools")
async def list_tools() -> List[Tool]:
    """List all available tools"""
    return [
        Tool(
            name="email_me",
            description=f"Send data to your email ({DEFAULT_RECIPIENT}). Use this when user says 'email me', 'send me', etc.",
            inputSchema={
                "type": "object",
                "properties": {
                    "subject": {
                        "type": "string",
                        "description": "Email subject"
                    },
                    "data": {
                        "type": "string",
                        "description": "Data to send (will be formatted nicely)"
                    },
                    "message": {
                        "type": "string",
                        "description": "Optional message to include",
                        "default": "Here is the data you requested:"
                    }
                },
                "required": ["subject", "data"]
            }
        ),
        Tool(
            name="send_email",
            description="Send an email via Gmail using SMTP (no OAuth needed)",
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
                        "description": "Email body (plain text or HTML)"
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
            name="send_email_with_data",
            description="Format data nicely and send via email",
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
                    "data": {
                        "type": "string",
                        "description": "Data to include in email (can be JSON, text, etc.)"
                    },
                    "message": {
                        "type": "string",
                        "description": "Additional message to include",
                        "default": ""
                    }
                },
                "required": ["to", "subject", "data"]
            }
        )
    ]

def send_email_smtp(to: str, subject: str, body: str, is_html: bool = False):
    """Send email using SMTP (no OAuth needed)"""
    
    if not GMAIL_ADDRESS or not GMAIL_APP_PASSWORD:
        return {
            "error": "Gmail not configured",
            "setup_instructions": {
                "step_1": "Go to https://myaccount.google.com/apppasswords",
                "step_2": "Generate an App Password for 'Mail'",
                "step_3": "Add to .env file:",
                "env_vars": {
                    "GMAIL_ADDRESS": "your-email@gmail.com",
                    "GMAIL_APP_PASSWORD": "your-16-char-app-password"
                }
            }
        }
    
    try:
        # Create message
        msg = MIMEMultipart('alternative')
        msg['From'] = GMAIL_ADDRESS
        msg['To'] = to
        msg['Subject'] = subject
        
        # Attach body
        if is_html:
            msg.attach(MIMEText(body, 'html'))
        else:
            msg.attach(MIMEText(body, 'plain'))
        
        # Send via SMTP
        with smtplib.SMTP(SMTP_SERVER, SMTP_PORT) as server:
            server.starttls()
            server.login(GMAIL_ADDRESS, GMAIL_APP_PASSWORD)
            server.send_message(msg)
        
        return {
            "success": True,
            "from": GMAIL_ADDRESS,
            "to": to,
            "subject": subject,
            "message": "Email sent successfully"
        }
        
    except smtplib.SMTPAuthenticationError:
        return {
            "error": "Authentication failed",
            "solution": "Check your Gmail App Password is correct",
            "help": "Generate new one at: https://myaccount.google.com/apppasswords"
        }
    except Exception as e:
        return {
            "error": str(e),
            "help": "Make sure 2-Step Verification is enabled and you're using an App Password"
        }

@app.post("/execute")
async def execute_tool(request: ToolRequest):
    """Execute a tool"""
    try:
        print(f"📨 Executing tool: {request.tool_name}")
        print(f"📦 Arguments: {request.arguments}")
        
        if request.tool_name == "email_me":
            # Automatically send to default recipient (user's own email)
            subject = request.arguments.get("subject")
            data = request.arguments.get("data")
            message = request.arguments.get("message", "Here is the data you requested:")
            
            # Validate required fields
            if not subject:
                return {"result": json.dumps({"error": "Missing required field: subject"})}
            if not data:
                return {"result": json.dumps({"error": "Missing required field: data"})}
            
            # Format the email body nicely
            body = f"""
{message}

{'='*60}
DATA:
{'='*60}

{data}

{'='*60}
Sent from AI Assistant
            """
            
            print(f"📧 Sending email to: {DEFAULT_RECIPIENT}")
            print(f"📋 Subject: {subject}")
            
            result = send_email_smtp(DEFAULT_RECIPIENT, subject, body.strip(), False)
            print(f"✅ Email result: {result}")
            return {"result": json.dumps(result, indent=2)}
        
        elif request.tool_name == "send_email":
            to = request.arguments.get("to")
            subject = request.arguments.get("subject")
            body = request.arguments.get("body")
            is_html = request.arguments.get("is_html", False)
            
            if not to or not subject or not body:
                return {"result": json.dumps({"error": "Missing required fields: to, subject, body"})}
            
            result = send_email_smtp(to, subject, body, is_html)
            return {"result": json.dumps(result, indent=2)}
        
        elif request.tool_name == "send_email_with_data":
            to = request.arguments.get("to")
            subject = request.arguments.get("subject")
            data = request.arguments.get("data")
            message = request.arguments.get("message", "")
            
            if not to or not subject or not data:
                return {"result": json.dumps({"error": "Missing required fields: to, subject, data"})}
            
            # Format the email body nicely
            body = f"""
{message}

{'='*60}
DATA:
{'='*60}

{data}

{'='*60}
Sent from AI Assistant
            """
            
            result = send_email_smtp(to, subject, body.strip(), False)
            return {"result": json.dumps(result, indent=2)}
        
        else:
            error_msg = f"Unknown tool: {request.tool_name}"
            print(f"❌ {error_msg}")
            return {"result": json.dumps({"error": error_msg})}
    
    except Exception as e:
        error_msg = f"Error executing {request.tool_name}: {str(e)}"
        print(f"❌ {error_msg}")
        import traceback
        traceback.print_exc()
        return {"result": json.dumps({"error": error_msg})}

@app.get("/health")
async def health():
    gmail_configured = bool(GMAIL_ADDRESS and GMAIL_APP_PASSWORD)
    
    return {
        "status": "healthy",
        "server": "google-mcp-simple",
        "gmail_configured": gmail_configured,
        "setup_url": "https://myaccount.google.com/apppasswords" if not gmail_configured else None
    }

if __name__ == "__main__":
    import uvicorn
    print("🚀 Starting Google MCP Server (Simple - No OAuth)...")
    print("📍 Server: http://localhost:8082")
    print()
    if not GMAIL_ADDRESS or not GMAIL_APP_PASSWORD:
        print("⚠️  Gmail not configured!")
        print("📖 Setup instructions:")
        print("   1. Enable 2-Step Verification: https://myaccount.google.com/security")
        print("   2. Generate App Password: https://myaccount.google.com/apppasswords")
        print("      - Select app: Mail")
        print("      - Select device: Other (Custom name)")
        print("      - Name it: AI Assistant")
        print("   3. Copy the 16-character password")
        print("   4. Add to .env:")
        print("      GMAIL_ADDRESS=your-email@gmail.com")
        print("      GMAIL_APP_PASSWORD=your-16-char-password")
        print()
    else:
        print(f"✅ Gmail configured: {GMAIL_ADDRESS}")
        print()
    
    uvicorn.run(app, host="0.0.0.0", port=8082)