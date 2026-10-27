"""Snowflake connection for Live mode.

There is no app login. Live runs use one named connection from ~/.snowflake/connections.toml
(SNOWFLAKE_CONNECTION_NAME, default ONTOLOGY_DEMO_CONN), opened lazily on the first Live call and
reused afterwards. With authenticator = externalbrowser that is one browser login per backend process.
The session runs as APP_ROLE (default ONTOLOGY_APP_ROLE) with no secondary roles, like the batch eval.
Recorded mode, Setup and Analysis never open a connection.
"""
import os
import threading

import snowflake.connector

CONNECTION_NAME = os.getenv("SNOWFLAKE_CONNECTION_NAME", "ONTOLOGY_DEMO_CONN")
APP_ROLE = os.getenv("APP_ROLE", "ONTOLOGY_APP_ROLE")
WAREHOUSE = os.getenv("APP_WAREHOUSE", "COMPUTE_WH")

_lock = threading.Lock()
_conn = None


def is_connected() -> bool:
    return _conn is not None and not _conn.is_closed()


def get_connection():
    """Return the shared connection, opening it (browser login) on first use."""
    global _conn
    with _lock:
        if not is_connected():
            conn = snowflake.connector.connect(connection_name=CONNECTION_NAME, role=APP_ROLE,
                                               warehouse=WAREHOUSE, client_session_keep_alive=True)
            conn.cursor().execute("USE SECONDARY ROLES NONE")
            _conn = conn
        return _conn


def reset() -> None:
    """Drop the shared connection (e.g. after its session expired); the next call reconnects."""
    global _conn
    with _lock:
        if _conn is not None:
            try:
                _conn.close()
            except Exception:
                pass
        _conn = None


def info() -> dict:
    return {"connected": is_connected(), "connection": CONNECTION_NAME, "role": APP_ROLE, "warehouse": WAREHOUSE}
