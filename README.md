# TKSeal Python

A Python 3.12 port of the Ruby [tkseal](https://github.com/mlibrary/tkseal) CLI tool for managing sealed secrets in Kubernetes environments using Grafana Tanka configuration repositories.

## Development Environment Setup

### Prerequisites
- Python 3.12+
- Poetry (for dependency management)

### Use poetry to install dev dependencies

```bash
poetry install --with dev
```

### Setup Commands

```bash
# Install dependencies and set up virtual environment
poetry install -E dev

# Verify installation
poetry run tkseal --help
poetry run tkseal version
```

## Running Tests

```bash
# Run all tests
poetry run pytest

# Run specific test file
poetry run pytest tests/test_cli.py

# Run specific test with verbose output
poetry run pytest tests/test_cli.py::TestVersionCommand::test_version_command_returns_version -v

# Run tests with coverage
poetry run pytest --cov=src/tkseal --cov-report=term-missing
```

## Code Quality

```bash
# Run linting
poetry run ruff check src/ tests/

# Format code
poetry run ruff format src/ tests/

# Type checking
poetry run mypy src/
```

## Available Commands

- ✅ `tkseal version` - Show current version
- ✅ `tkseal ready` - Check dependencies (WIP)
- ✅ `tkseal diff PATH` - Show differences between plain_secrets.json and cluster
- 💻 `tkseal pull PATH` - Extracting secrets from cluster to plain_secrets.json
- 🚧 `tkseal seal PATH` - Convert plain_secrets.json to sealed_secrets.json
- 

## Previous logic documentation

### ready Command

  **Core Functionality**

  The ready command checks if three critical external dependencies are installed and available in the system PATH:

  1. `kubectl` - Kubernetes command-line tool
  2. `tk` - Grafana Tanka CLI tool
  3. `kubeseal` - Sealed Secrets controller CLI

  **Implementation Details - Detection Method**

 The `ready command` is essentially a health check that ensures the required Kubernetes ecosystem tools are properly installed before
  attempting any secret management operations. It is the foundation for all other `TKSeal` operations. 
 
 Each dependency checker uses the same pattern:
 
 ``def self.exists?
    `which <tool>` != ""
  end
``
  This runs the shell command `which <tool>` and checks if it returns a non-empty string (meaning the tool was found in PATH). 
 Other commands like `diff`, `pull` and `seal` raise an Exception if some of the external tools are not ready

**What each tool does?**

 1. `kubectl (Kubernetes CLI)`

  - Purpose: Interact with Kubernetes clusters
  - Used for: Fetching existing secrets from the cluster
  - Example usage: `kubectl --context=ctx --namespace=ns get secrets -o yaml`

  2. `tk (Grafana Tanka)`

  - Purpose: Kubernetes configuration management using Jsonnet
  - Used for: Getting environment context and namespace info
  - Example usage: `tk status /path/to/environment`
  - Returns: Context and namespace information for the Tanka environment

  3. `kubeseal (Sealed Secrets)`

  - Purpose: Encrypt Kubernetes Secret manifests into SealedSecret manifests, 
which can then be safely stored in version control systems like Git. 
  - Used for: Converting plain text secrets to sealed secrets
  - Example usage: `printf "secret" | kubeseal --raw --namespace ns --name secret-name --context ctx`


### diff command

**Core Functionality**
The diff command compares the local `plain_secrets.json` file in a specified Tanka environment directory with 
the actual Kubernetes secrets deployed in the cluster.
It shows what changes would be made if the secrets were to be synchronized, without making any changes.

The flow is:
1. Create a `SecretState` object with the `Tanka environment path`
2. Fetch local `plain_secrets.json`
3. Fetch existing Kubernetes secrets from the cluster
4. Compare the two sets of secrets
5. Display differences in a unified diff format or indicate no differences

Usage Example

**Show what would change in cluster**

```tkseal diff /path/to/tanka/environments/production```

**If there are differences, shows a unified diff**

```--- cluster
  +++ plain_secrets.json
  @@ -1,5 +1,5 @@
   [
     {
       "name": "app-secret",
  -    "data": {"password": "old123"}
  +    "data": {"password": "new123"}
     }
   ]
```

**If no differences**

```tkseal diff /path/to/tanka/environments/production    
No differences
```

**Error handling**

```tkseal diff /nonexistent/path
  Error: Path '/nonexistent/path' does not exist.
```

### pull command

**Core Functionality**
The pull command extracts existing Kubernetes secrets from the cluster and writes them to a local plain_secrets.json 
file in the specified Tanka environment directory. This allows users to synchronize their local secret 
definitions with what is currently deployed in the cluster.

The flow is:
1. Create a SecretState object with the Tanka environment path
2. Show a diff of changes (what would change in plain_secrets.json)
3. Prompt user for confirmation
4. Write kube secrets to plain_secrets.json  


### seal command

**Core Functionality**
The seal command reads the local plain_secrets.json file in a specified Tanka environment directory,
seals the secrets using kubeseal, and writes the resulting sealed secrets to sealed_secrets.json. 
This allows users to securely store secrets in version control.

We used the `bitnami.com/v1alpha1` format to be compatible with the Bitnami Sealed Secrets controller, 
which is used in our Kubernetes cluster.

The flow is:
1. Create a SecretState object with the Tanka environment path
2. Read plain_secrets.json
3. Seal each secret using kubeseal
4. Write sealed secrets to sealed_secrets.json
 
# Seal secrets (with confirmation)
`tkseal seal /path/to/tanka/environment`

The command will:
1. Show yellow warning about cluster changes
2. Display diff of what would change
3. Ask for confirmation
4. Seal secrets to sealed_secrets.json


