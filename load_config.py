import base64
import json
import re
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
ENV_FILE = ROOT / "config.env"
OUTPUT_FILE = ROOT / "backend" / "supabase-client.js"

TEMPLATE = """// This file is created by backend/load_config.py from config.env.
// Do not edit it by hand. Edit config.env and run the script again.
const SUPABASE_URL = {url};
const SUPABASE_KEY = {key};

const sb = supabase.createClient(SUPABASE_URL, SUPABASE_KEY);
"""


def read_env(path):
    values = {}
    for line in path.read_text(encoding="utf-8").splitlines():
        line = line.strip()
        if line == "" or line.startswith("#") or "=" not in line:
            continue
        name, value = line.split("=", 1)
        values[name.strip()] = value.strip().strip('"').strip("'")
    return values


def is_service_role_key(key):
    parts = key.split(".")
    if len(parts) != 3:
        return False
    try:
        payload = parts[1] + "=" * (-len(parts[1]) % 4)
        data = json.loads(base64.urlsafe_b64decode(payload))
        return data.get("role") == "service_role"
    except Exception:
        return False


def check(url, key):
    if "PASTE" in url or "PASTE" in key:
        return "config.env still has the PASTE-... placeholders. Put your real values."
    if not re.fullmatch(r"https://[a-z0-9]+\.supabase\.co", url):
        return "SUPABASE_URL must look like https://abcdefghijklmnop.supabase.co"
    if key.startswith("sb_secret_") or is_service_role_key(key):
        return "STOP: that is a SECRET key. Use the publishable key (sb_publishable_...)."
    if not (key.startswith("sb_publishable_") or key.startswith("eyJ")):
        return "SUPABASE_PUBLISHABLE_KEY must start with sb_publishable_"
    return None


def write_output(text):
    try:
        OUTPUT_FILE.write_text(text, encoding="utf-8")
        return True
    except OSError:
        pass

    try:
        with open(str(OUTPUT_FILE), "wb") as file:
            file.write(text.encode("utf-8"))
        return True
    except OSError as error:
        print("Could not write backend/supabase-client.js: " + str(error))
        print("Copy everything between the lines into that file by hand:")
        print("--------------------------------------------------")
        print(text)
        print("--------------------------------------------------")
        return False


def main():
    if not ENV_FILE.exists():
        print("config.env was not found at " + str(ENV_FILE))
        return 1

    values = read_env(ENV_FILE)
    url = values.get("SUPABASE_URL", "").rstrip("/")
    key = values.get("SUPABASE_PUBLISHABLE_KEY", "")

    problem = check(url, key)
    if problem:
        print("Error: " + problem)
        return 1

    text = TEMPLATE.format(url=json.dumps(url), key=json.dumps(key))
    if not write_output(text):
        return 1

    print("Done. backend/supabase-client.js now uses " + url)
    return 0


if __name__ == "__main__":
    sys.exit(main())
