"""Snowflake credentials and connections for the local app.

Every call runs as the signed-in user with the OAuth access token from oauth.py:
REST (Cortex Agents :run) sends it as a Bearer token; SQL uses authenticator="oauth".
Settings come from backend/.env (see .env.example).
"""
import os
from dataclasses import dataclass
from pathlib import Path

import snowflake.connector
from dotenv import load_dotenv

load_dotenv(Path(__file__).parent / ".env")


@dataclass
class Credential:
    token: str
    token_type: str  # OAUTH
    is_caller: bool


def base_url() -> str:
    return os.environ["SNOWFLAKE_ACCOUNT_URL"].rstrip("/")


def rest_headers(cred: Credential) -> dict:
    return {
        "Authorization": f"Bearer {cred.token}",
        "X-Snowflake-Authorization-Token-Type": cred.token_type,
        "Content-Type": "application/json",
        "Accept": "text/event-stream",
    }


def sql_connection(cred: Credential, warehouse: str | None = None):
    """Open a connector session with the user's OAuth token (role comes from the token scope)."""
    wh = warehouse or os.getenv("SNOWFLAKE_WAREHOUSE")
    return snowflake.connector.connect(
        account=os.environ["SNOWFLAKE_ACCOUNT"],
        authenticator="oauth",
        token=cred.token,
        **({"warehouse": wh} if wh else {}),
    )
