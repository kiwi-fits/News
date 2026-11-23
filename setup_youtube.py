#!/usr/bin/env python3
"""
Interactive 1-Click YouTube Authorization Helper
Automatically generates your permanent YOUTUBE_REFRESH_TOKEN and updates your .env file!
"""

import os
import sys
import webbrowser
import urllib.parse
from http.server import HTTPServer, BaseHTTPRequestHandler
import requests

BASE_DIR = os.path.dirname(os.path.abspath(__file__))
ENV_FILE = os.path.join(BASE_DIR, ".env")

REDIRECT_PORT = 8080
REDIRECT_URI = f"http://localhost:{REDIRECT_PORT}/"
AUTH_CODE = None

class OAuthHandler(BaseHTTPRequestHandler):
    def do_GET(self):
        global AUTH_CODE
        parsed = urllib.parse.urlparse(self.path)
        params = urllib.parse.parse_qs(parsed.query)

        if "code" in params:
            AUTH_CODE = params["code"][0]
            self.send_response(200)
            self.send_header("Content-Type", "text/html; charset=utf-8")
            self.end_headers()
            html_content = """
                <html>
                <body style="font-family: -apple-system, sans-serif; text-align: center; padding: 50px; background: #0f172a; color: white;">
                    <div style="font-size: 48px; margin-bottom: 20px;">🎉</div>
                    <h2 style="color: #4ade80;">YouTube Authorization Successful!</h2>
                    <p style="color: #94a3b8;">You can close this browser tab and return to your terminal.</p>
                </body>
                </html>
            """
            self.wfile.write(html_content.encode("utf-8"))
        else:
            self.send_response(400)
            self.send_header("Content-Type", "text/html; charset=utf-8")
            self.end_headers()
            self.wfile.write(b"Failed to capture authorization code. Please try again.")

    def log_message(self, format, *args):
        # Suppress noisy HTTP server logs
        return

def update_env_file(key_values):
    """Updates or appends keys in the local .env file."""
    lines = []
    if os.path.exists(ENV_FILE):
        with open(ENV_FILE, "r", encoding="utf-8") as f:
            lines = f.readlines()

    existing_keys = set()
    new_lines = []
    for line in lines:
        matched = False
        for k, v in key_values.items():
            if line.strip().startswith(f"{k}="):
                new_lines.append(f"{k}={v}\n")
                existing_keys.add(k)
                matched = True
                break
        if not matched:
            new_lines.append(line)

    for k, v in key_values.items():
        if k not in existing_keys:
            new_lines.append(f"{k}={v}\n")

    with open(ENV_FILE, "w", encoding="utf-8") as f:
        f.writelines(new_lines)

def main():
    print("\n========================================================")
    print("📺 YouTube Shorts 1-Click Authorization Helper")
    print("========================================================\n")

    # Read from environment or prompt
    from dotenv import load_dotenv
    load_dotenv(ENV_FILE)

    print("Select Channel to Connect:")
    print("1. Jesus Hears You (Christian Devotional)")
    print("2. செய்தி மையம் / Seithi Maiyam (Tamil News)")
    choice = input("Enter 1 or 2 [Default: 1]: ").strip() or "1"
    is_news = (choice == "2")
    channel_name = "செய்தி மையம் (Tamil News)" if is_news else "Jesus Hears You (Christian Devotional)"
    print(f"\n👉 Setting up channel: {channel_name}\n")

    if is_news:
        client_id = os.getenv("NEWS_YOUTUBE_CLIENT_ID", "").strip() or os.getenv("YOUTUBE_CLIENT_ID", "").strip()
        client_secret = os.getenv("NEWS_YOUTUBE_CLIENT_SECRET", "").strip() or os.getenv("YOUTUBE_CLIENT_SECRET", "").strip()
    else:
        client_id = os.getenv("YOUTUBE_CLIENT_ID", "").strip()
        client_secret = os.getenv("YOUTUBE_CLIENT_SECRET", "").strip()

    if not client_id:
        client_id = input("1. Enter your Google Client ID: ").strip()
    else:
        print(f"1. Using existing Client ID: {client_id[:16]}...{client_id[-8:]}")

    if not client_secret:
        client_secret = input("2. Enter your Google Client Secret: ").strip()
    else:
        print(f"2. Using existing Client Secret: {client_secret[:4]}...{client_secret[-4:]}")

    if not client_id or not client_secret:
        print("❌ Client ID and Client Secret are required. Aborting.")
        sys.exit(1)

    # Construct OAuth Consent URL
    params = {
        "client_id": client_id,
        "redirect_uri": REDIRECT_URI,
        "response_type": "code",
        "scope": "https://www.googleapis.com/auth/youtube.upload https://www.googleapis.com/auth/youtube.force-ssl",
        "access_type": "offline",
        "prompt": "consent"
    }
    auth_url = f"https://accounts.google.com/o/oauth2/v2/auth?{urllib.parse.urlencode(params)}"

    print("\n🌐 Opening Google login in your browser...")
    print(f"If it doesn't open automatically, click this link:\n{auth_url}\n")
    try:
        webbrowser.open(auth_url)
    except Exception:
        pass

    # Start local temporary server to listen for callback
    print(f"⏳ Waiting for authorization on {REDIRECT_URI}...")
    server = HTTPServer(("localhost", REDIRECT_PORT), OAuthHandler)
    server.handle_request()

    if not AUTH_CODE:
        print("❌ Did not receive authorization code.")
        sys.exit(1)

    print("\n🔑 Exchanging authorization code for permanent Refresh Token...")
    token_url = "https://oauth2.googleapis.com/token"
    token_payload = {
        "client_id": client_id,
        "client_secret": client_secret,
        "code": AUTH_CODE,
        "grant_type": "authorization_code",
        "redirect_uri": REDIRECT_URI
    }

    try:
        resp = requests.post(token_url, data=token_payload, timeout=15)
        if resp.status_code == 200:
            data = resp.json()
            refresh_token = data.get("refresh_token")
            if refresh_token:
                print(f"\n🎉 SUCCESS! Permanent YouTube Refresh Token received for {channel_name}!")
                print(f"Refresh Token: {refresh_token[:15]}...{refresh_token[-10:]}")

                if is_news:
                    update_env_file({
                        "ENABLE_YOUTUBE_NEWS_PUBLISH": "true",
                        "NEWS_YOUTUBE_CLIENT_ID": client_id,
                        "NEWS_YOUTUBE_CLIENT_SECRET": client_secret,
                        "NEWS_YOUTUBE_REFRESH_TOKEN": refresh_token,
                        "NEWS_YOUTUBE_PRIVACY_STATUS": "public"
                    })
                    print(f"✅ Automatically updated your local {ENV_FILE} file for News Channel!\n")
                    print("Tip: If using GitHub Actions, add these repository secrets:")
                    print("1. NEWS_YOUTUBE_CLIENT_ID")
                    print("2. NEWS_YOUTUBE_CLIENT_SECRET")
                    print("3. NEWS_YOUTUBE_REFRESH_TOKEN")
                    print("4. ENABLE_YOUTUBE_NEWS_PUBLISH=true\n")
                else:
                    update_env_file({
                        "ENABLE_YOUTUBE_CHRISTIAN_PUBLISH": "true",
                        "YOUTUBE_CLIENT_ID": client_id,
                        "YOUTUBE_CLIENT_SECRET": client_secret,
                        "YOUTUBE_REFRESH_TOKEN": refresh_token,
                        "YOUTUBE_PRIVACY_STATUS": "public"
                    })
                    print(f"✅ Automatically updated your local {ENV_FILE} file for Christian Channel!\n")
                    print("Tip: If using GitHub Actions, add these repository secrets:")
                    print("1. YOUTUBE_CLIENT_ID")
                    print("2. YOUTUBE_CLIENT_SECRET")
                    print("3. YOUTUBE_REFRESH_TOKEN")
                    print("4. ENABLE_YOUTUBE_CHRISTIAN_PUBLISH=true\n")
            else:
                print("⚠️ No refresh token in response. If you already authorized previously, revoke access in Google Account and re-run.")
        else:
            print(f"❌ Failed to exchange code: {resp.status_code} {resp.text}")
    except Exception as e:
        print(f"❌ Token exchange error: {e}")

if __name__ == "__main__":
    main()
