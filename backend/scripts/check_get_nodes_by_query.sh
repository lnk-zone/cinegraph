#!/bin/bash

# Script to check for improper usage of get_nodes_by_query()
# This ensures get_nodes_by_query() is only used in GraphitiManager._run_cypher_query or tests

set -e

# Colors for output
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
NC='\033[0m' # No Color

echo -e "${YELLOW}Checking get_nodes_by_query() usage restrictions...${NC}"

# Find all Python files that contain get_nodes_by_query( but are not test files or legitimate usage
# Exclude test files, venv, and the legitimate usage in GraphitiManager._run_cypher_query
violations=$(grep -rn "get_nodes_by_query(" --include="*.py" . | \
    grep -v "test" | \
    grep -v "_test.py" | \
    grep -v "/tests/" | \
    grep -v "venv/" | \
    grep -v "__pycache__" | \
    grep -v "core/graphiti_manager.py:1078" || true)

if [ -n "$violations" ]; then
    echo -e "${RED}❌ VIOLATION: get_nodes_by_query() usage found outside of allowed contexts!${NC}"
    echo -e "${RED}get_nodes_by_query() should only be used in:${NC}"
    echo -e "${RED}  - GraphitiManager._run_cypher_query method${NC}"
    echo -e "${RED}  - Test files${NC}"
    echo ""
    echo -e "${RED}Found violations:${NC}"
    echo "$violations"
    echo ""
    echo -e "${YELLOW}Please use proper GraphitiManager methods instead of direct get_nodes_by_query() calls.${NC}"
    exit 1
else
    echo -e "${GREEN}✅ No improper get_nodes_by_query() usage found${NC}"
fi
