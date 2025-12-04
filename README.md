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
### System Wide Install
Currently the steps for running and testing this are as follows.

1. Navigate to the releases in this repository and download the latest version of the `.whl` file.
    - Open a terminal and navigate to where the file downloaded.

2. Install pipx with the following command:
    - `brew install pipx` or `pip install pipx`

3. Install tkseal with the following command:
    - `pipx install ./tkseal-1.0.0-py3-none-any.whl `

4. To ensure that the install worked correctly run the following commands:
    - `which tkseal`
    - `tkseal version`


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

Note: The file `py.typed`  has been added to the package and specified in pyproject.toml to ensure mypy treats
tkseal as a typed package and avoids "Skipping analyzing 'tkseal': found module but no type hints or library stubs" warnings.
```

## Available Commands

- ✅ `tkseal version` - Show current version
- ✅ `tkseal ready` - Check dependencies (WIP)
- ✅ `tkseal diff PATH` - Show differences between plain_secrets.json and cluster
- ✅ `tkseal pull PATH` - Extracting secrets from cluster to plain_secrets.json
- ✅ `tkseal seal PATH` - Convert plain_secrets.json to sealed_secrets.json


## Logic documentation

### Forbidden Secrets Warning

  **Core Functionality**

  This application allows users to pull different kinds of Kubernetes secrets into their local Tanka environment.
  However, certain types of secrets are considered forbidden for pulling due to their sensitive nature or
  system management roles.

  The pull command includes the `forbidden secrets warning` feature that prevents accidental exposure of sensitive
  system secrets while keeping users informed about what's being filtered out when pulling secrets from a Kubernetes
  namespace into a local Tanka environment using the `tkseal pull` command.

  **Implementation Details**

  The detection method involves checking the types of secrets present in the specified Kubernetes namespace against
  a predefined list of forbidden secret types. These forbidden types typically include:

  - `kubernetes.io/service-account-token`
  - `helm.sh/release.v1`
  - Any other secret types deemed sensitive or system-managed
  - The forbidden and allowed secret types are defined in `/src/tkseal/configuration.py`

  The implementation uses the following logic:

  1. Fetch all secrets from the specified Kubernetes namespace using `kubectl`.
  2. Iterate through each secret and check its type.
  3. If a secret's type matches any in the forbidden list, it is flagged.
  4. Collect all flagged secrets and prepare a warning message.

  **Usage Example**
  When a user runs `tkseal pull`, if there are forbidden secrets (like service-account-tokens, helm releases, etc.)
  in the namespace:

  `tkseal pull environments/testing/`

  This shows how "plain_secrets.json" would change based on what's in the Kubernetes cluster, and it will
  warn about forbidden secrets:

  ```
  These secrets are system-managed and will not be included in plain_secrets.json:
  - oidc-saml-proxy-tls (type: kubernetes.io/tls)
  This shows how "plain_secrets.json" would change based on what's in the Kubernetes cluster
--- plain_secrets.json
+++ cluster
  ```

## ready Command

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


## diff command

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
Use `tkseal diff /path/to/env --format yaml` to output plain secrets in YAML format.

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

## pull command

**Core Functionality**
The pull command extracts existing Kubernetes secrets from the cluster and writes them to a local plain_secrets.json
file in the specified Tanka environment directory. This allows users to synchronize their local secret
definitions with what is currently deployed in the cluster.

The flow is:
1. Create a SecretState object with the Tanka environment path
2. Show a diff of changes (what would change in plain_secrets.json)
3. Prompt user for confirmation
4. Write kube secrets to plain_secrets.json

### pull secrets (with confirmation)
`tkseal pull /path/to/tanka/environment`
Use `tkseal pull /path/to/env --format yaml` to output plain secrets in YAML format.

## seal command

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

### Seal secrets (with confirmation)
`tkseal seal /path/to/tanka/environment`
Use `tkseal seal /path/to/env --format yaml` to output sealed secrets in YAML format.

The command will:
1. Show yellow warning about cluster changes
2. Display diff of what would change
3. Ask for confirmation
4. Seal secrets to sealed_secrets.json

# Example of errors running tkseal commands

This error means that you probably are not in a Tanka environment directory or the directory structure is incorrect.
Remember that Tanka expects a specific directory structure with `main.jsonnet` file in the environment's base directory.

```Error: Failed to initialize Tanka environment: Command failed with exit code 1: Error: Unable to identify the environments base directory.
Tried to find 'main.jsonnet' in the parent directories.
Please refer to https://tanka.dev/directory-structure for more information```
