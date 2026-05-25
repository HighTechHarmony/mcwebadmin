#!/usr/bin/env python3
"""
Generate a Werkzeug password hash for the ADMIN_PASSWORD_HASH .env variable.

Usage:
    python3 scripts/set_password.py
"""

import getpass
import sys

try:
    from werkzeug.security import generate_password_hash
except ImportError:
    print("werkzeug not found. Activate the venv first:")
    print("  source .venv/bin/activate")
    sys.exit(1)

password = getpass.getpass("Enter admin password: ")
if not password:
    print("Password cannot be empty.")
    sys.exit(1)

confirm = getpass.getpass("Confirm password: ")
if password != confirm:
    print("Passwords do not match.")
    sys.exit(1)

phash = generate_password_hash(password)
print()
print(f"ADMIN_PASSWORD_HASH={phash}")
print()
print("Add (or replace) that line in your .env file.")
