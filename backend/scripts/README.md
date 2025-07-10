# Lint Enforcement Scripts

## get_nodes_by_query Usage Restriction

### Overview
The `check_get_nodes_by_query.sh` script enforces restrictions on the usage of `get_nodes_by_query()` method to prevent regressions and ensure proper abstraction usage.

### Rules
- `get_nodes_by_query()` should only be used in:
  - `GraphitiManager._run_cypher_query` method (controlled escape hatch)
  - Test files (`test_*.py`, `*_test.py`, or files in `/tests/` directory)

### Usage

#### Manual check:
```bash
./scripts/check_get_nodes_by_query.sh
```

#### Pre-commit hook:
```bash
# Install pre-commit
pip install pre-commit

# Install the hooks
pre-commit install

# Run on all files
pre-commit run --all-files
```

### CI Integration
The script is automatically run in CI via GitHub Actions on push/PR to main/develop branches.

### Rationale
This helps prevent direct usage of low-level Graphiti methods and encourages proper use of GraphitiManager abstractions, while still allowing controlled access for debugging and testing purposes.
