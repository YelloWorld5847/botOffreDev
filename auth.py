import os
import json
import base64
import urllib.parse
import subprocess
from pathlib import Path
from datetime import datetime, timezone
from typing import Tuple, Optional, Dict, Any
import httpx
from config import settings

DISCORD_CLIENT_ID = "1120361809396912218"
DISCORD_SCOPE = "identify email guilds guilds.join"

def get_token_info(token: str) -> Optional[Dict[str, Any]]:
    if not token:
        return None
    try:
        parts = token.split(".")
        if len(parts) != 3:
            return None
        payload = parts[1]
        payload += "=" * (-len(payload) % 4)
        data = json.loads(base64.b64decode(payload))
        exp = data.get("exp")
        exp_dt = None
        remaining_hours = 0.0
        is_expired = True
        if exp:
            exp_dt = datetime.fromtimestamp(exp, tz=timezone.utc)
            remaining_seconds = (exp_dt - datetime.now(timezone.utc)).total_seconds()
            remaining_hours = remaining_seconds / 3600.0
            is_expired = remaining_seconds <= 0

        return {
            "user_id": data.get("_id"),
            "email": data.get("email"),
            "discord_id": data.get("discord_id"),
            "exp": exp_dt,
            "remaining_hours": remaining_hours,
            "is_expired": is_expired,
            "raw": data
        }
    except Exception:
        return None

def update_env_variable(key: str, value: str, env_file_path: Optional[Path] = None) -> None:
    path = env_file_path or (Path(__file__).parent / ".env")
    if not path.exists():
        path.write_text(f"{key}={value}\n", encoding="utf-8")
        return

    content = path.read_text(encoding="utf-8")
    lines = content.splitlines()
    found = False
    new_lines = []
    for line in lines:
        stripped = line.strip()
        if stripped.startswith(f"{key}=") or stripped == key:
            new_lines.append(f"{key}={value}")
            found = True
        else:
            new_lines.append(line)
    if not found:
        new_lines.append(f"{key}={value}")

    path.write_text("\n".join(new_lines) + "\n", encoding="utf-8")

def restart_pm2_if_available():
    # reload pm2 environment if running under pm2
    try:
        res = subprocess.run(["pm2", "restart", "creators-bot", "--update-env"], capture_output=True, text=True, timeout=5)
        if res.returncode == 0:
            return True
    except Exception:
        pass
    return False

async def login_with_discord(discord_user_token: str) -> Tuple[bool, str]:
    token = discord_user_token.strip().strip('"').strip("'")
    if not token:
        return False, "Token Discord vide."

    url = (
        f"https://discord.com/api/v9/oauth2/authorize"
        f"?client_id={DISCORD_CLIENT_ID}"
        f"&response_type=code"
        f"&scope={urllib.parse.quote(DISCORD_SCOPE)}"
    )

    headers = {
        "Authorization": token,
        "Content-Type": "application/json",
        "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/130.0.0.0 Safari/537.36",
    }
    payload = {
        "authorize": True,
        "permissions": "0"
    }

    async with httpx.AsyncClient(timeout=15.0) as client:
        try:
            r = await client.post(url, json=payload, headers=headers)
        except Exception as e:
            return False, f"Erreur de connexion a Discord: {e}"

        if r.status_code == 401:
            return False, "Token Discord invalide ou expire."

        if r.status_code not in (200, 204):
            return False, f"Reponse inattendue de Discord ({r.status_code}): {r.text}"

        try:
            data = r.json()
        except Exception:
            return False, f"Reponse non JSON de Discord: {r.text}"

        location = data.get("location")
        if not location:
            # check if captcha or MFA is required
            if "captcha_key" in data:
                return False, "Discord demande un captcha (connexion manuelle requise)."
            return False, f"Discord n'a pas renvoye d'URL de redirection: {data}"

        parsed = urllib.parse.urlparse(location)
        query = urllib.parse.parse_qs(parsed.query)
        codes = query.get("code")
        if not codes or not codes[0]:
            return False, f"Code OAuth introuvable dans la redirection: {location}"

        oauth_code = codes[0]

        # exchange code on creatorsarea.fr
        ca_url = "https://creatorsarea.fr/api/login/code"
        ca_headers = {
            "Content-Type": "application/json",
            "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/130.0.0.0 Safari/537.36",
            "Referer": location,
            "Origin": "https://creatorsarea.fr"
        }

        try:
            ca_resp = await client.post(ca_url, json={"code": oauth_code}, headers=ca_headers)
        except Exception as e:
            return False, f"Erreur de connexion a CreatorsArea: {e}"

        if ca_resp.status_code != 200:
            return False, f"Echec validation code CreatorsArea ({ca_resp.status_code}): {ca_resp.text}"

        new_ca_token = ""
        try:
            ca_data = ca_resp.json()
            new_ca_token = ca_data.get("token", "")
        except Exception:
            pass

        if not new_ca_token:
            new_ca_token = ca_resp.cookies.get("creators_area_token", "")

        if not new_ca_token:
            return False, f"Token absent de la reponse CreatorsArea: {ca_resp.text}"

        # update in .env and settings
        update_env_variable("CREATORS_AREA_TOKEN", new_ca_token)
        settings.creators_area_token = new_ca_token
        return True, new_ca_token
