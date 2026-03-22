"""
Utility script to rotate the Team API Key.
This generates a new secure token and updates the .env file automatically.
"""

import secrets
import os
import re

def rotate_key():
    # 1. Generate new 32-character URL-safe token
    new_key = secrets.token_urlsafe(32)
    env_path = ".env"

    if not os.path.exists(env_path):
        print(f"❌ Error: {env_path} not found. Are you in the project root?")
        return

    # 2. Update the .env file
    with open(env_path, "r") as f:
        content = f.read()

    # Search for TEAM_API_KEY using regex
    pattern = r"TEAM_API_KEY=.*"
    replacement = f"TEAM_API_KEY={new_key}"
    
    if re.search(pattern, content):
        new_content = re.sub(pattern, replacement, content)
        with open(env_path, "w") as f:
            f.write(new_content)
        print("✅ Success! Your TEAM_API_KEY has been rotated in .env")
        print(f"🚀 New Key: {new_key}")
        print("⚠️  Remember to share this new key with your team!")
    else:
        print("❌ Error: Could not find TEAM_API_KEY in your .env file.")

if __name__ == "__main__":
    rotate_key()
