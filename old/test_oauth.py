#!/usr/bin/env python3
"""
Test Google OAuth Configuration
This attempts to start the OAuth flow to verify credentials are correct
"""

import os
import sys
from dotenv import load_dotenv
from google_auth_oauthlib.flow import Flow

# Color codes
GREEN = '\033[92m'
RED = '\033[91m'
YELLOW = '\033[93m'
BLUE = '\033[94m'
RESET = '\033[0m'

def main():
    print(f"\n{BLUE}{'='*70}{RESET}")
    print(f"{BLUE}Testing Google OAuth Configuration{RESET}")
    print(f"{BLUE}{'='*70}{RESET}\n")
    
    # Load environment
    if not os.path.exists('.env'):
        print(f"{RED}✗ .env file not found{RESET}\n")
        return False
    
    load_dotenv()
    
    client_id = os.getenv("GOOGLE_CLIENT_ID")
    client_secret = os.getenv("GOOGLE_CLIENT_SECRET")
    
    # Check if set
    if not client_id or not client_secret:
        print(f"{RED}✗ GOOGLE_CLIENT_ID or GOOGLE_CLIENT_SECRET not set in .env{RESET}\n")
        return False
    
    # Check for placeholders
    if "your-" in client_id.lower() or "your-" in client_secret.lower():
        print(f"{RED}✗ Placeholder values detected in .env{RESET}")
        print(f"{YELLOW}Replace with actual credentials from Google Cloud Console{RESET}\n")
        return False
    
    print(f"{BLUE}Testing credentials...{RESET}\n")
    
    # Create client config
    CLIENT_CONFIG = {
        "web": {
            "client_id": client_id,
            "client_secret": client_secret,
            "redirect_uris": ["http://localhost:8082/oauth2callback"],
            "auth_uri": "https://accounts.google.com/o/oauth2/auth",
            "token_uri": "https://oauth2.googleapis.com/token"
        }
    }
    
    SCOPES = [
        'https://www.googleapis.com/auth/gmail.send',
        'https://www.googleapis.com/auth/gmail.readonly',
        'https://www.googleapis.com/auth/drive.readonly',
        'https://www.googleapis.com/auth/calendar.readonly'
    ]
    
    try:
        # Try to create Flow object
        flow = Flow.from_client_config(
            CLIENT_CONFIG,
            scopes=SCOPES,
            redirect_uri="http://localhost:8082/oauth2callback"
        )
        
        # Try to generate authorization URL
        authorization_url, state = flow.authorization_url(
            access_type='offline',
            include_granted_scopes='true',
            prompt='consent'
        )
        
        print(f"{GREEN}✓ Credentials are valid!{RESET}\n")
        print(f"{BLUE}Client ID:{RESET} {client_id[:20]}...{client_id[-20:]}")
        print(f"{BLUE}Client Secret:{RESET} {client_secret[:10]}...{client_secret[-5:]}")
        print()
        print(f"{GREEN}✓ OAuth flow can be initiated{RESET}\n")
        print(f"{BLUE}Test URL (don't open yet):{RESET}")
        print(f"{authorization_url[:100]}...")
        print()
        print(f"{GREEN}{'='*70}{RESET}")
        print(f"{GREEN}SUCCESS! Your OAuth credentials are correctly configured.{RESET}")
        print(f"{GREEN}{'='*70}{RESET}\n")
        print("Next steps:")
        print("  1. Start the Google MCP server: python google_mcp_server.py")
        print("  2. Start the Flask app: python flask_app_integrated.py")
        print("  3. Visit: http://localhost:5000")
        print("  4. Click 'Sign in with Google'")
        print()
        return True
        
    except ValueError as e:
        error_msg = str(e)
        print(f"{RED}✗ OAuth Configuration Error{RESET}\n")
        
        if "client_id" in error_msg.lower():
            print(f"{RED}Problem with Client ID{RESET}")
            print(f"{YELLOW}Current value:{RESET} {client_id[:30]}...")
            print()
            print("Common issues:")
            print("  • Missing .apps.googleusercontent.com suffix")
            print("  • Extra spaces or quotes")
            print("  • Copied incorrectly from Google Cloud Console")
            print()
            print("Fix:")
            print("  1. Go to: https://console.cloud.google.com/apis/credentials")
            print("  2. Click on your OAuth 2.0 Client ID")
            print("  3. Copy the FULL Client ID (should be ~72 characters)")
            print("  4. Paste into .env without quotes")
            
        elif "client_secret" in error_msg.lower():
            print(f"{RED}Problem with Client Secret{RESET}")
            print(f"{YELLOW}Current value:{RESET} {client_secret[:15]}...")
            print()
            print("Common issues:")
            print("  • Wrong secret copied")
            print("  • Old/expired secret")
            print("  • Extra spaces or quotes")
            print()
            print("Fix:")
            print("  1. Go to: https://console.cloud.google.com/apis/credentials")
            print("  2. Click on your OAuth 2.0 Client ID")
            print("  3. Click 'RESET SECRET' to get a new one")
            print("  4. Copy the new secret")
            print("  5. Paste into .env without quotes")
        
        else:
            print(f"{YELLOW}Error message:{RESET} {error_msg}")
            print()
            print("Try:")
            print("  1. Create NEW OAuth credentials in Google Cloud Console")
            print("  2. Make sure redirect URI is: http://localhost:8082/oauth2callback")
            print("  3. Copy BOTH Client ID and Client Secret carefully")
            print("  4. Update .env file")
        
        print()
        return False
        
    except Exception as e:
        print(f"{RED}✗ Unexpected error:{RESET} {e}\n")
        import traceback
        traceback.print_exc()
        return False

if __name__ == "__main__":
    try:
        success = main()
        sys.exit(0 if success else 1)
    except KeyboardInterrupt:
        print(f"\n{YELLOW}Interrupted{RESET}")
        sys.exit(0)