#!/usr/bin/env python3
"""Django's command-line utility for administrative tasks."""
import os
import sys
from pathlib import Path

from settings.conf import ALLOWED_ENV_IDS, ENV_ID #adv django

BLOG_ENV_ID = [
    'settings/.env'
]

def read_blog_env_id() -> str:
    env_id = "local"  # default
    env_path = Path(__file__).resolve().parent / "settings" / ".env"
    if not env_path.exists():
        return env_id


        

    for line in env_path.read_text().splitlines():
        line = line.strip()
        if not line or line.startswith("#") or "=" not in line:
            continue
        key, val = line.split("=", 1)
        if key.strip() == "BLOG_ENV_ID":
            env_id = val.strip()
            break
    return env_id



def main():
    """Run administrative tasks."""
    env_id = read_blog_env_id()
    assert env_id in ALLOWED_ENV_IDS, f"Invalid ENV_ID: {env_id}. Allowed values are: {ALLOWED_ENV_IDS}"
    os.environ.setdefault('DJANGO_SETTINGS_MODULE', f"settings.env.{env_id}")
    try:
        from django.core.management import execute_from_command_line
    except ImportError as exc:
        raise ImportError(
            "Couldn't import Django. Are you sure it's installed and "
            "available on your PYTHONPATH environment variable? Did you "
            "forget to activate a virtual environment?"
        ) from exc
    execute_from_command_line(sys.argv)


if __name__ == '__main__':
    main()
