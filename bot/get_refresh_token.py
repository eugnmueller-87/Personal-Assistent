"""
Run this locally to get a fresh GOOGLE_REFRESH_TOKEN.

Steps:
  1. Get GOOGLE_CLIENT_ID and GOOGLE_CLIENT_SECRET from Railway → Icarus → Variables
  2. Set them as env vars:
       $env:GOOGLE_CLIENT_ID = "..."
       $env:GOOGLE_CLIENT_SECRET = "..."
  3. Run:  python bot/get_refresh_token.py
  4. Browser opens → log in with eugnmueller@googlemail.com → approve
  5. Copy the printed refresh_token
  6. In Railway → Icarus → Variables → update GOOGLE_REFRESH_TOKEN
  7. Redeploy Icarus
"""

import os
from google_auth_oauthlib.flow import InstalledAppFlow

SCOPES = [
    "https://www.googleapis.com/auth/calendar",
    "https://www.googleapis.com/auth/gmail.modify",
]

client_id = os.environ.get("GOOGLE_CLIENT_ID", "1098132567527-27cbs3pkkfuvd3a5qv62f5jnl95tscjd.apps.googleusercontent.com")
client_secret = os.environ.get("GOOGLE_CLIENT_SECRET", "")

client_config = {
    "installed": {
        "client_id": client_id,
        "client_secret": client_secret,
        "auth_uri": "https://accounts.google.com/o/oauth2/auth",
        "token_uri": "https://oauth2.googleapis.com/token",
        "redirect_uris": ["http://localhost"],
    }
}

flow = InstalledAppFlow.from_client_config(client_config, SCOPES)
creds = flow.run_local_server(port=0, prompt="consent", access_type="offline")

print("\n✓ New refresh token:")
print(creds.refresh_token)
print("\nCopy this into Railway → Icarus → GOOGLE_REFRESH_TOKEN → redeploy.")
