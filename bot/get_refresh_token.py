"""
Run this locally to get a fresh GOOGLE_REFRESH_TOKEN.
No local server needed — just copy-paste from the browser.

Usage:
  $env:GOOGLE_CLIENT_ID = "..."
  $env:GOOGLE_CLIENT_SECRET = "..."
  python bot/get_refresh_token.py
"""

import os
import requests
from urllib.parse import urlparse, parse_qs, urlencode

CLIENT_ID = os.environ["GOOGLE_CLIENT_ID"]
CLIENT_SECRET = os.environ["GOOGLE_CLIENT_SECRET"]
REDIRECT_URI = "http://localhost:7777"
SCOPES = "https://www.googleapis.com/auth/calendar"

auth_url = "https://accounts.google.com/o/oauth2/auth?" + urlencode({
    "client_id": CLIENT_ID,
    "redirect_uri": REDIRECT_URI,
    "response_type": "code",
    "scope": SCOPES,
    "access_type": "offline",
    "prompt": "consent",
})

print("Open this URL in your browser:\n")
print(auth_url)
print("\nAfter approving, the browser will show 'This site can't be reached'.")
print("Copy the FULL URL from the address bar and paste it here.\n")

redirect_url = input("Paste the full redirect URL: ").strip()
code = parse_qs(urlparse(redirect_url).query).get("code", [None])[0]

if not code:
    print("No code found in URL.")
    raise SystemExit(1)

r = requests.post("https://oauth2.googleapis.com/token", data={
    "code": code,
    "client_id": CLIENT_ID,
    "client_secret": CLIENT_SECRET,
    "redirect_uri": REDIRECT_URI,
    "grant_type": "authorization_code",
})

data = r.json()
if "refresh_token" in data:
    print("\n✓ New refresh token:")
    print(data["refresh_token"])
    print("\nCopy into Railway -> Icarus -> GOOGLE_REFRESH_TOKEN -> redeploy.")
else:
    print("Error:", data)
