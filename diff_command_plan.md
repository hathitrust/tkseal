# TKSeal Diff Command Implementation Plan (TDD)

## Overview
This document outlines the Test-Driven Development (TDD) plan for implementing the `tkseal diff` command. The implementation will follow Python 3.12+ best practices and use pytest for testing.

## Reference Materials
- Ruby implementation: `tkseal_ruby/lib/tkseal/diff.rb`
- Wiki documentation: https://github.com/hathitrust/tkseal/wiki/diff-command
- Project guidelines: `CLAUDE.md`

## Purpose
The `diff` command displays differences between local `plain_secrets.json` and Kubernetes Opaque secrets associated with a Tanka environment. It shows what changes would be pushed to the cluster.

## Architecture

```
CLI (cli.py)
Diff (diff.py)
SecretState (secret_state.py)
    plain_secrets() � local JSON
    kube_secrets() � cluster JSON via kubectl
```

## Implementation Phases

### Phase 1: Core Diff Module (TDD)

#### File: `src/tkseal/diff.py`

**Data Structures:**
```python
@dataclass
class DiffResult:
    """Result of a diff operation."""
    has_differences: bool
    diff_output: str
```

**Main Class:**
```python
class Diff:
    """Handles comparison between local and cluster secrets."""

    def __init__(self, secret_state: SecretState):
        """Initialize with SecretState instance."""

    def plain(self) -> DiffResult:
        """Compare showing what would change in cluster (push mode).

        Compares kube_secrets (old) against plain_secrets (new).
        Shows additions (+) indicating changes to be applied to cluster.
        """

    def pull(self) -> DiffResult:
        """Compare showing what pulling would change locally (pull mode).

        Compares plain_secrets (old) against kube_secrets (new).
        Shows what would change in local file if secrets were pulled.
        """

    def _generate_diff(self, from_text: str, to_text: str,
                      from_label: str, to_label: str) -> DiffResult:
        """Generate unified diff between two texts.

        Uses difflib.unified_diff for comparison.
        Returns DiffResult with has_differences flag and formatted output.
        """
```

**Test File: `tests/test_diff.py`**

Test cases to write (in TDD order):

1. **Test Setup and Fixtures**
   ```python
   @pytest.fixture
   def mock_secret_state(mocker):
       """Create mock SecretState with controlled plain/kube secrets."""

   @pytest.fixture
   def sample_plain_secrets():
       """Sample plain_secrets.json content."""

   @pytest.fixture
   def sample_kube_secrets():
       """Sample kube secrets JSON content."""
   ```

2. **Test: No Differences**
   - `test_plain_no_differences()`: When local and cluster are identical
   - `test_pull_no_differences()`: When local and cluster are identical
   - Expected: `has_differences=False`, output contains "No differences"

3. **Test: Secret Added Locally**
   - `test_plain_shows_addition()`: Local has new secret not in cluster
   - Expected: Diff shows "+" lines for new secret
   - Expected: `has_differences=True`

4. **Test: Secret Removed Locally**
   - `test_plain_shows_removal()`: Local missing secret that's in cluster
   - Expected: Diff shows "-" lines for removed secret
   - Expected: `has_differences=True`

5. **Test: Secret Modified**
   - `test_plain_shows_modification()`: Same secret name, different value
   - Expected: Diff shows "-" old value and "+" new value
   - Expected: `has_differences=True`

6. **Test: Pull Mode Comparison**
   - `test_pull_shows_cluster_changes()`: Pull mode reverses comparison
   - Expected: Shows what would change locally if pulled
   - Expected: Opposite direction from plain mode

7. **Test: Empty Secrets**
   - `test_plain_empty_local_secrets()`: Local file empty or missing
   - `test_plain_empty_cluster_secrets()`: Cluster has no secrets
   - Expected: Appropriate diff output or "No differences"

8. **Test: JSON Formatting**
   - `test_handles_formatted_json()`: Pretty-printed vs compact JSON
   - Expected: Normalized comparison (both formatted consistently)

9. **Test: Multiple Secrets**
   - `test_multiple_secrets_partial_changes()`: Some changed, some not
   - Expected: Only changed secrets appear in diff

10. **Test: Whitespace Handling**
    - `test_trailing_newlines()`: Handles trailing newlines properly
    - Expected: Consistent handling per Ruby behavior

### Phase 2: CLI Integration (TDD)

#### File: `src/tkseal/cli.py`

**CLI Command:**
```python
@cli.command()
@click.argument('path', type=click.Path(exists=True))
def diff(path: str) -> None:
    """Show differences between plain_secrets.json and cluster secrets.

    PATH: Path to Tanka environment directory or .jsonnet file

    This shows what would change in the cluster based on plain_secrets.json
    """
    # 1. Validate dependencies (ready check)
    # 2. Create SecretState from path
    # 3. Create Diff instance
    # 4. Run diff.plain()
    # 5. Display results with appropriate message
    # 6. Exit with correct code (0 if success, 1 if error)
```

**Test File: `tests/test_cli.py` (extend existing)**

Test cases to add:

1. **Test: Successful Diff with Differences**
   - `test_diff_command_shows_differences()`
   - Mock SecretState and Diff to return differences
   - Expected: Diff output printed, exit code 0

2. **Test: Successful Diff No Differences**
   - `test_diff_command_no_differences()`
   - Mock to return no differences
   - Expected: "No differences" printed, exit code 0

3. **Test: Path Validation**
   - `test_diff_invalid_path()`: Non-existent path
   - Expected: Error message, exit code 1 or 2

4. **Test: Missing Dependencies**
   - `test_diff_missing_kubectl()`: kubectl not available
   - Expected: Error message directing to `tkseal ready`
   - Expected: Exit code 1

5. **Test: SecretState Creation Failure**
   - `test_diff_invalid_tanka_env()`: Invalid Tanka environment
   - Expected: Error message, exit code 1

6. **Test: Kubectl Error During Diff**
   - `test_diff_kubectl_fails()`: kubectl command fails
   - Expected: Error message with helpful context, exit code 1

7. **Test: Click Testing Pattern**
   ```python
   from click.testing import CliRunner

   def test_diff_command_output():
       runner = CliRunner()
       with runner.isolated_filesystem():
           # Setup test environment
           result = runner.invoke(cli, ['diff', 'path/to/env'])
           assert result.exit_code == 0
           assert 'No differences' in result.output
   ```

### Phase 3: Integration Tests

#### File: `tests/test_diff_integration.py`

End-to-end tests with real file system (but mocked kubectl):

1. **Test: Full Workflow with Temp Files**
   - `test_diff_with_real_files()`: Create temp Tanka env with plain_secrets.json
   - Mock kubectl responses
   - Run full diff command
   - Verify output format

2. **Test: Path Normalization**
   - `test_diff_with_trailing_slash()`: Path with trailing slash
   - `test_diff_with_jsonnet_file()`: Path to .jsonnet file
   - Expected: Proper normalization, correct file discovery

3. **Test: Error Recovery**
   - `test_diff_handles_invalid_json()`: Malformed plain_secrets.json
   - Expected: Clear error message

## Implementation Guidelines

### Code Quality Standards
- **Type Hints**: Full type annotations on all public methods
- **Docstrings**: Google-style docstrings for classes and public methods
- **Error Handling**: Use custom exceptions from `tkseal.exceptions`
- **Imports**: Absolute imports only (e.g., `from tkseal.secret_state import SecretState`)

### Testing Standards
- **Mocking**: Use `mocker` fixture from pytest-mock
- **Parametrization**: Use `@pytest.mark.parametrize` for test variations
- **Fixtures**: Reusable fixtures in `conftest.py` if used across test files
- **Coverage**: Aim for >90% code coverage on diff module

### Python 3.12+ Features to Use
- `@dataclass` for DiffResult
- Type hints with modern syntax (`list[str]`, not `List[str]`)
- f-strings for all string formatting
- `pathlib.Path` for file operations
- Context managers for resource handling

### Diff Implementation Details

**Using difflib.unified_diff:**
```python
import difflib

def _generate_diff(self, from_text: str, to_text: str,
                  from_label: str, to_label: str) -> DiffResult:
    """Generate unified diff."""
    # Split into lines for difflib
    from_lines = from_text.splitlines(keepends=True)
    to_lines = to_text.splitlines(keepends=True)

    # Generate unified diff
    diff_lines = list(difflib.unified_diff(
        from_lines,
        to_lines,
        fromfile=from_label,
        tofile=to_label,
        lineterm=''
    ))

    # Format output
    if not diff_lines:
        return DiffResult(has_differences=False, diff_output="")

    diff_output = '\n'.join(diff_lines)
    return DiffResult(has_differences=True, diff_output=diff_output)
```

**Handling Ruby Diffy Behavior:**
- Ruby's Diffy returns `"\n"` for no differences
- Python should return empty DiffResult or explicit "No differences" message
- Preserve unified diff format for consistency

### Error Handling Strategy

**Exception Types:**
- `TKSealError`: Base exception (already exists)
- `KubeCtlError`: kubectl command failures (already exists)
- `TKError`: Tanka command failures (already exists)

**Error Messages:**
- User-friendly messages at CLI level
- Technical details in logs (use Python `logging` module)
- Guide users to `tkseal ready` for dependency issues

**Exit Codes:**
- `0`: Success
- `1`: General error (kubectl failure, invalid path, etc.)
- `2`: CLI usage error (invalid arguments)

## Implementation Sequence (TDD Red-Green-Refactor)

### Sprint 1: Core Diff Logic
1. Write test: `test_plain_no_differences()`
2. Implement minimal `Diff.__init__()` and `plain()` to pass
3. Write test: `test_plain_shows_addition()`
4. Implement `_generate_diff()` to pass
5. Refactor: Extract common diff logic
6. Continue with remaining diff tests

### Sprint 2: Edge Cases and Pull Mode
7. Write tests for empty secrets, modifications, removals
8. Implement handling for edge cases
9. Write tests for `pull()` mode
10. Implement `pull()` method
11. Refactor: DRY up code

### Sprint 3: CLI Integration
12. Write CLI tests with mocked Diff class
13. Implement CLI `diff` command
14. Write dependency check tests
15. Implement dependency validation
16. Refactor: Error handling

### Sprint 4: Integration and Polish
17. Write integration tests
18. Run full test suite
19. Fix any issues discovered
20. Code review and documentation
21. Run linting (ruff), formatting (ruff format), type checking (mypy)

## Success Criteria

- [ ] All tests pass with pytest
- [ ] Test coverage >90% for diff.py
- [ ] ruff check passes with no errors
- [ ] ruff format produces no changes
- [ ] mypy passes with no type errors
- [ ] CLI command matches Ruby behavior for standard cases
- [ ] Error messages are user-friendly
- [ ] Documentation is complete (docstrings + README if needed)

## Notes

### Differences from Ruby Implementation
- Ruby uses Diffy gem; Python uses stdlib difflib
- Ruby prints directly; Python returns DiffResult dataclass (better testability)
- Python adds proper type hints and structured error handling
- Python uses Click for CLI; Ruby uses Thor

### Future Enhancements (Out of Scope)
- Color-coded diff output (consider using click.style or rich library)
- Diff output formatting options (--format flag)
- Quiet mode (--quiet flag for exit code only)
- Specific secret filtering (--secret-name flag)

## References
- Python difflib: https://docs.python.org/3/library/difflib.html
- Click testing: https://click.palletsprojects.com/en/8.1.x/testing/
- pytest-mock: https://pytest-mock.readthedocs.io/
- Ruby Diffy: https://github.com/samg/diffy