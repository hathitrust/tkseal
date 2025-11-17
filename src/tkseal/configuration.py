"""Configuration constants for TKSeal.

This module defines configuration constants used throughout the application,
particularly for file naming conventions in Tanka environments.

e.g the filename "plain_secrets.json" is always the same - it's a convention in Tanka environments that tkseal follows.
The directory changes based on which Tanka environment you're working with, but the filename itself is constant
and defined in the configuration module.
"""

# File name for plain (unencrypted) secrets JSON/YAML file
PLAIN_SECRETS_FILE = "plain_secrets"

# File name for sealed (encrypted) secrets JSON file
SEALED_SECRETS_FILE = "sealed_secrets"

# Allowed secret types that tkseal can manage
MANAGED_SECRET_TYPES = {
    "Opaque",  # Standard application secrets
    "kubernetes.io/basic-auth",  # HTTP basic auth
    "kubernetes.io/ssh-auth",  # SSH keys
}

# Allowed secret types that tkseal can manage but with extra caution - showing warnings in the CLI
MANAGED_SECRET_CAREFULLY_TYPES = {
    "kubernetes.io/dockerconfigjson",  # Docker registry credentials. Users manage all these secrets manually,
    # so is safe to handle by tkseal.
}

# Never allow these (system-managed, high risk)
FORBIDDEN_SECRET_TYPES = {
    "kubernetes.io/service-account-token",  # Cluster API tokens
    "bootstrap.kubernetes.io/token",  # Bootstrap tokens
    "helm.sh/release.v1",  # Helm release data
    "kubernetes.io/tls",  # TLS certificates
}
