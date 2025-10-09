# GitHub Copilot Instructions for tkseal

## Purpose
- Give Copilot concise, project-specific guidance so its suggestions align with the project's style, testing practices, and goals.
- Language: Python (mainly CLI utilities around kubectl and kubeseal).
- Layout: Source code lives in `src/tkseal/`, tests live in `tests/`.
- Packaging: Managed with Poetry (`pyproject.toml`).

## Repository context
- Repo:**tkseal** is a Python 3.12 port of the Ruby [tkseal_ruby](https://github.com/mlibrary/tkseal) CLI tool. TKSeal is a command-line utility for managing sealed secrets in Kubernetes environments using Grafana Tanka configuration repositories.

### Key Files to Understand to migrate the project from Ruby to Python

When implementing features, refer to these Ruby files for behavior:
- `lib/tkseal/cli.rb:6-80` - Main CLI commands and flow
- `lib/tkseal/secret.rb:1-48` - Secret data structures and processing
- `lib/tkseal/seal.rb:1-38` - Sealing algorithm and SealedSecret generation
- `lib/tkseal/tk.rb:18-37` - Tanka environment parsing
- `lib/tkseal/secret_state.rb:1-23` - State coordination between files and cluster


### Original Ruby Project Analysis

The original tkseal provides these core commands:
- `tkseal diff PATH` - Shows differences between `plain_secrets.json` and Kubernetes Opaque secrets
- `tkseal pull PATH` - Extracts secrets from Kubernetes cluster to `plain_secrets.json`
- `tkseal seal PATH` - Converts `plain_secrets.json` to `sealed_secrets.json` using kubeseal
- `tkseal ready` - Checks if dependencies (kubectl, tk, kubeseal) are installed
- `tkseal version` - Shows current version


### Development Environment

- **Python Version**: 3.12
- **Package Manager**: pip with pyproject.toml (modern Python packaging)
- **CLI Framework**: Click (replacing Ruby Thor)
- **Testing**: pytest
- **Code Quality**: ruff (linting), black (formatting), mypy (type checking)
- **GitHub Actions**: CI for linting, testing, and type checking on PRs and main branch

## Dependencies

### External Tools (Required at Runtime)
- `kubectl` - Kubernetes command-line tool
- `tk` - Grafana Tanka ([install instructions](https://tanka.dev/install/))
- `kubeseal` - Sealed Secrets CLI ([install instructions](https://github.com/bitnami-labs/sealed-secrets))

## Implementation Guidelines

### Python Dependencies
- `click` - CLI framework (replaces Ruby Thor)
- `pyyaml` - YAML parsing (replaces Ruby yaml)
- `subprocess` - External command execution (built-in)
- `pathlib` - Path handling (built-in)
- `base64`, `json` - Data processing (built-in)

### Ruby to Python Mapping
- **Thor CLI** → **Click CLI**: Use Click's decorator pattern for commands
- **OpenStruct** → **SimpleNamespace or @dataclass**: Use Python's structured data approaches
- **Forwardable** → **Property delegation**: Use Python properties or explicit delegation
- **Diffy** → **difflib**: Use Python's built-in diff functionality
- **Shell commands** → **subprocess**: Use subprocess with proper error handling

### Python 3.12 Features to Leverage
- **Type hints**: Full type annotations including generics
- **Dataclasses**: For structured data representation
- **Pathlib**: Modern path handling
- **f-strings**: String formatting
- **Context managers**: Resource management
- **Exception groups**: Better error handling (if needed)

### Coding style & conventions
- Target Python version: 3.12+.
- Use `@dataclass` for data containers (Secret, etc.)
- Follow PEP 8 for style; prefer short, readable functions.
- Use type annotations for public functions and methods.
- Keep CLI argument parsing in `cli.py` and business logic in separate modules.
- For shell/OS interactions (kubectl/kubeseal), prefer using subprocess utilities from `subprocess` with timeouts and clear error handling.
- Avoid network calls during unit tests.
- For code quality use ruff (linting), black (formatting) and mypy (type checking)
- Use absolute imports that specified the full path to a module or package, starting from the project’s root directory. e.g. from tkseal.kubectl import KubeCtl
- Avoid relative imports e.g. from . import kubectl
- Use `pathlib.Path` instead of string manipulation for file paths
- Implement proper error handling with custom exception classes

### Testing Strategy
- Port existing RSpec tests to pytest
- Use pytest parameterization for test variations
- Use mocker fixture (from pytest-mock plugin) for payching external commands.
- Test CLI commands using Click's testing utilities
- Tests live in `tests/` and use pytest.
- Each module should have unit tests that cover happy paths and at least one error path.
- Use fixtures for repeated setups; prefer small focused tests.

Error handling and logging
- Use custom exceptions defined in `exceptions.py` for predictable failure modes.
- CLI entrypoints should catch known exceptions and print user-friendly messages and non-zero exit codes.
- Use logging for debug/info; avoid printing in library functions.

Security
- Treat shell-constructed commands carefully; do not concatenate user input into shell=True calls.
- Sanitize inputs passed to subprocess; prefer argument lists (list[str]) instead of joined shell strings.

Prompt examples (use these when asking Copilot for changes)
- "Refactor `src/tkseal/kubectl.py` to extract subprocess invocation into a reusable helper with timeout, retry, and clean error messages. Add unit tests in `tests/test_kubectl.py`."
- "Add type annotations to public functions in `src/tkseal/kubeseal.py` and update tests to use type hints where helpful."
- "Write pytest fixtures to mock subprocess calls used by `tkseal.kubectl` so tests don't call real kubectl."

Do and Don't summary
- Do: Suggest small, testable changes. Recommend adding or updating unit tests for any behavioral change.
- Do: Prefer explicit over implicit — explicit errors, explicit return types, explicit timeouts.
- Don't: Introduce heavy new dependencies without a good reason (mention in PR description if necessary).
- Don't: Add relative imports.

Maintainers
- Keep changes backward-compatible for CLI flags unless there is a clear migration plan.

License & attribution
- Keep contributions under the project's license (see `LICENSE.txt` files in repo root or subprojects).

