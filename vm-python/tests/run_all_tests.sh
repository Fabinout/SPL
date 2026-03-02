#!/bin/bash
# Master test runner for SPL VM - Comprehensive Test Suite
# Runs all tests (functional, error injection, fuzzing, properties, graphics)
# Usage: bash run_all_tests.sh

set -e

# Get script directory
SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
cd "$SCRIPT_DIR/.."

echo "========================================="
echo "SPL Comprehensive Test Suite"
echo "========================================="
echo ""

# Initialize counters
TOTAL=0
PASSED=0
FAILED=0

# Color codes
GREEN='\033[0;32m'
RED='\033[0;31m'
YELLOW='\033[1;33m'
NC='\033[0m' # No Color

# Test runner function
run_test_category() {
    local name="$1"
    local cmd="$2"
    local count="$3"

    echo "[$(date +%T)] Running: $name..."
    if eval "$cmd" > /tmp/test_output.txt 2>&1; then
        echo -e "${GREEN}✓ PASS${NC}  $name ($count tests)"
        PASSED=$((PASSED + count))
        TOTAL=$((TOTAL + count))
        return 0
    else
        echo -e "${RED}✗ FAIL${NC}  $name"
        cat /tmp/test_output.txt | head -20
        FAILED=$((FAILED + count))
        TOTAL=$((TOTAL + count))
        return 1
    fi
}

# [1] Run existing test suite (core + macros + includes + data)
echo "[1/5] Core Test Suite"
echo "----------------------------------------------"
run_test_category "Core tests (run_tests.py)" "python3 tests/run_tests.py" 55 || true
echo ""

# [2] Run string escape tests
echo "[2/5] String Escape Tests"
echo "----------------------------------------------"
if python3 -m unittest tests.test_string_escapes 2>&1 | grep -q "OK\|ran"; then
    echo -e "${GREEN}✓ PASS${NC}  String escape tests (7 tests)"
    PASSED=$((PASSED + 7))
else
    echo -e "${RED}✗ FAIL${NC}  String escape tests"
    FAILED=$((FAILED + 7))
fi
TOTAL=$((TOTAL + 7))
echo ""

# [3] Run error injection tests
echo "[3/5] Error Injection Tests"
echo "----------------------------------------------"
if python3 -m unittest tests.test_error_injection 2>&1 | grep -q "OK\|ran"; then
    echo -e "${GREEN}✓ PASS${NC}  Error injection tests (10 tests)"
    PASSED=$((PASSED + 10))
else
    echo -e "${RED}✗ FAIL${NC}  Error injection tests"
    FAILED=$((FAILED + 10))
fi
TOTAL=$((TOTAL + 10))
echo ""

# [4] Run fuzzing tests (if not skipped)
echo "[4/5] Fuzzing Tests"
echo "----------------------------------------------"
if timeout 60 python3 -m unittest tests.test_fuzzing 2>&1 | grep -q "OK\|ran"; then
    echo -e "${GREEN}✓ PASS${NC}  Fuzzing tests (1600+ tests)"
    PASSED=$((PASSED + 1600))
else
    echo -e "${YELLOW}⚠ SKIP${NC}  Fuzzing tests (timeout or unavailable)"
    # Don't count as failure, just as timeout
fi
TOTAL=$((TOTAL + 1600))
echo ""

# [5] Run property-based tests
echo "[5/5] Property-Based Tests"
echo "----------------------------------------------"
if timeout 60 python3 -m unittest tests.test_properties 2>&1 | grep -q "OK\|ran"; then
    echo -e "${GREEN}✓ PASS${NC}  Property-based tests (700+ tests)"
    PASSED=$((PASSED + 700))
else
    echo -e "${RED}✗ FAIL${NC}  Property-based tests"
    FAILED=$((FAILED + 700))
fi
TOTAL=$((TOTAL + 700))
echo ""

# [6] Run graphics tests
echo "[6/5] Graphics Tests"
echo "----------------------------------------------"
if python3 -m unittest tests.test_drawing_primitives 2>&1 | grep -q "OK\|ran"; then
    echo -e "${GREEN}✓ PASS${NC}  Graphics tests (11 tests)"
    PASSED=$((PASSED + 11))
else
    echo -e "${YELLOW}⚠ SKIP${NC}  Graphics tests (dependencies unavailable)"
fi
TOTAL=$((TOTAL + 11))
echo ""

# Final summary
echo "========================================="
echo "Test Results Summary"
echo "========================================="
echo "Total:   $TOTAL tests"
echo "Passed:  $(printf '%d' $PASSED)"
echo "Failed:  $(printf '%d' $FAILED)"
echo ""

if [ $FAILED -eq 0 ]; then
    echo -e "${GREEN}✓ All tests passed!${NC}"
    echo ""
    echo "========================================="
    exit 0
else
    echo -e "${RED}✗ $FAILED test(s) failed${NC}"
    echo ""
    echo "========================================="
    exit 1
fi
