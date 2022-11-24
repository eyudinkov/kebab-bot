import os
from typing import Dict, Optional


def get_debug() -> bool:
    return os.getenv("DEBUG", "False").lower() == "true"


def get_debugger() -> Optional[str]:
    return os.getenv("DEBUGGER", "")


def get_project_id() -> Optional[str]:
    return os.getenv("GOOGLE_PROJECT_ID", "")


def get_group_chat_id() -> Optional[str]:
    chat_id = os.getenv("CHAT_ID", None)
    if chat_id is None:
        raise ValueError("can't get CHAT_ID")
    return chat_id


def get_token() -> Optional[str]:
    token = os.getenv("TOKEN", None)
    if token is None:
        raise ValueError("can't get tg token")
    return token


def get_mongo_user():
    user = os.getenv("MONGO_INITDB_ROOT_USERNAME", None)
    if user is None:
        raise ValueError("can't get mongodb username")
    return user


def get_mongo_pass():
    user = os.getenv("MONGO_INITDB_ROOT_PASSWORD", None)
    if user is None:
        raise ValueError("can't get mongodb password")
    return user


def get_config() -> Dict:
    return {
        "DEBUG": get_debug(),
        "DEBUGGER": get_debugger(),
        "TOKEN": get_token(),
        "GROUP_CHAT_ID": get_group_chat_id(),
        "MONGO_USER": get_mongo_user(),
        "MONGO_PASS": get_mongo_pass(),
        "GOOGLE_PROJECT_ID": get_project_id(),
        "MONGO_HOST": os.getenv("MONGO_HOST", "mongo"),
        "MONGO_PORT": os.getenv("MONGO_PORT", "27017"),
        "SENTRY_DSN": os.getenv("SENTRY_DSN", None),
    }
