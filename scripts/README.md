# Quick Fix Scripts for Secret Management

This directory contains automated scripts to improve secret management and environment variable handling in the CineGraph project.

## Scripts Overview

### 1. `fix_env_secrets.py`
Comprehensive script for detecting and fixing secret management issues.

**Features:**
- Scans codebase for hard-coded secrets and API keys
- Identifies missing environment variables in `.env.example`
- Replaces hard-coded secrets with `os.getenv()` references
- Automatically adds missing environment variables to `.env.example`
- Generates detailed reports of all changes

**Usage:**
```bash
# Dry run to see what would be changed
python scripts/fix_env_secrets.py --dry-run --verbose

# Apply fixes
python scripts/fix_env_secrets.py --verbose

# Adjust confidence threshold for secret detection
python scripts/fix_env_secrets.py --min-confidence 0.8
```

### 2. `generate_secret_patches.py`
Generates git patches for specific secret management improvements.

**Features:**
- Creates reviewable git patches for secret replacements
- Targets specific hard-coded password fallbacks
- Standardizes environment variable usage
- Generates unified diffs for easy review

**Usage:**
```bash
# Generate patches for review
python scripts/generate_secret_patches.py

# Apply patches directly
python scripts/generate_secret_patches.py --apply

# Target specific file
python scripts/generate_secret_patches.py --target-file setup_enhanced_agent.py
```

## Environment Variables Added

The scripts automatically add these missing environment variables to `.env.example`:

```bash
# Database Configuration
DATABASE_URL=postgresql://user:password@localhost:5432/cinegraph
DB_PASSWORD=your_database_password_here
SUPABASE_DB_PASSWORD=your_supabase_db_password_here

# Security
SECRET_KEY=your_secret_key_here
JWT_SECRET_KEY=your_jwt_secret_key_here
ENCRYPTION_KEY=your_encryption_key_here
```

## Security Improvements Applied

### 1. Hard-coded Password Removal
**Before:**
```python
password=os.getenv("GRAPHITI_DATABASE_PASSWORD", "password")
```

**After:**
```python
password=os.getenv("GRAPHITI_DATABASE_PASSWORD")
```

### 2. Environment Variable Validation
Added validation to ensure required environment variables are set:

```python
# Validate required environment variables
required_env_vars = ["SUPABASE_URL", "SUPABASE_SERVICE_ROLE_KEY"]
missing_vars = [var for var in required_env_vars if not os.getenv(var)]
if missing_vars:
    raise ValueError(f"Missing required environment variables: {', '.join(missing_vars)}")
```

### 3. Standardized Environment Variable Usage
- All database connections use consistent environment variable names
- Fallback values are only used for non-sensitive configuration
- Clear error messages for missing required variables

## Files Modified

### Primary Targets:
- `backend/setup_enhanced_agent.py` - Removed hard-coded password fallbacks
- `backend/.env.example` - Added missing environment variables
- `backend/app/auth.py` - Enhanced environment variable validation
- `backend/core/graphiti_manager.py` - Standardized database configuration

### Detection Patterns:
- OpenAI API keys (`sk-...`)
- Supabase JWT tokens (`eyJ...`)
- Hard-coded passwords and secrets
- Missing environment variable usage

## Output Files

### Reports:
- `scripts/fix_report.json` - Detailed JSON report of all changes
- `patches/secret_fix_*.patch` - Git patches for manual review

### Logs:
- Console output shows all changes made
- Verbose mode provides detailed information about each fix

## Usage in CI/CD

These scripts can be integrated into CI/CD pipelines:

```yaml
# Example GitHub Actions workflow
- name: Check Secret Management
  run: |
    python scripts/fix_env_secrets.py --dry-run
    python scripts/generate_secret_patches.py
```

## Security Best Practices Applied

1. **No Hard-coded Secrets**: All secrets must come from environment variables
2. **Required Variable Validation**: Application fails fast if required variables are missing
3. **Consistent Naming**: Standardized environment variable names across the codebase
4. **Comprehensive Documentation**: Clear `.env.example` with all required variables
5. **Automated Detection**: Scripts can detect new secret management issues

## Future Improvements

- Integration with secret management services (AWS Secrets Manager, HashiCorp Vault)
- Automated rotation of environment variables
- Enhanced pattern detection for new secret types
- Integration with pre-commit hooks
- Continuous monitoring for secret leaks

## Troubleshooting

### Common Issues:

1. **Permission Errors**: Ensure scripts have write access to files
2. **Import Errors**: Run scripts from project root directory
3. **Pattern Matching**: Adjust confidence thresholds for better detection
4. **False Positives**: Review generated patches before applying

### Debug Mode:
```bash
# Enable verbose debugging
python scripts/fix_env_secrets.py --verbose --dry-run
```

## Contributing

When adding new secret detection patterns:

1. Update the `secret_patterns` dictionary in `fix_env_secrets.py`
2. Add corresponding placeholders to `_get_placeholder_for_var()`
3. Test with `--dry-run` flag first
4. Update this documentation

## Security Considerations

- Always review generated patches before applying
- Test changes in development environment first
- Verify no secrets are committed to version control
- Use different secrets for different environments
- Rotate secrets regularly using automated tools
