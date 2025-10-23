"""Configuration constants for TKSeal.

This module defines configuration constants used throughout the application,
particularly for file naming conventions in Tanka environments.

e.g the filename "plain_secrets.json" is always the same - it's a convention in Tanka environments that tkseal follows.
The directory changes based on which Tanka environment you're working with, but the filename itself is constant
and defined in the configuration module.
"""

# File name for plain (unencrypted) secrets JSON file
PLAIN_SECRETS_FILE = "plain_secrets.json"

# File name for sealed (encrypted) secrets JSON file
SEALED_SECRETS_FILE = "sealed_secrets.json"
