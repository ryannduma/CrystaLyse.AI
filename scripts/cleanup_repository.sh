#!/bin/bash
# CrystaLyse.AI Repository Cleanup Script
# Removes old test files, cache files, and temporary artifacts

echo "🧹 Starting CrystaLyse.AI Repository Cleanup..."

# 1. Remove Python cache directories
echo "Removing Python cache files..."
find . -type d -name "__pycache__" -exec rm -rf {} + 2>/dev/null || true
find . -name "*.pyc" -delete 2>/dev/null || true
find . -name "*.pyo" -delete 2>/dev/null || true

# 2. Remove egg-info directories (development artifacts)
echo "Removing egg-info directories..."
rm -rf crystalyse.egg-info/ 2>/dev/null || true
rm -rf smact/SMACT.egg-info/ 2>/dev/null || true
rm -rf chemeleon-dng/chemeleon_rl.egg-info/ 2>/dev/null || true

# 3. Remove old test files
echo "Removing old test files..."
rm -rf tests/ 2>/dev/null || true
rm -rf essential-tests/ 2>/dev/null || true

# 4. Remove test artifacts from complete_workflow
echo "Removing complete_workflow test artifacts..."
rm -f complete_workflow/integration_test_full.py 2>/dev/null || true
rm -f complete_workflow/simple_mace_test.py 2>/dev/null || true
rm -f complete_workflow/test_*.py 2>/dev/null || true
rm -f complete_workflow/integration_test_summary_*.json 2>/dev/null || true
rm -f complete_workflow/mode_comparison_*.json 2>/dev/null || true
rm -rf complete_workflow/mace_test_results_*/ 2>/dev/null || true

# 5. Remove MCP server test files
echo "Removing MCP server test files..."
rm -f mace-mcp-server/test_*.py 2>/dev/null || true

# 6. Remove results directory (old test outputs)
echo "Removing results directory..."
rm -rf results/ 2>/dev/null || true

# 7. Remove historical documentation
echo "Removing historical documentation..."
rm -f CRYSTALYSE_FIXES_SUMMARY.md 2>/dev/null || true
rm -f CRYSTALYSE_MVP_STATUS.md 2>/dev/null || true
rm -f FINAL_STATUS_GPT4O.md 2>/dev/null || true
rm -f heavytestingcliandcrystalyse.md 2>/dev/null || true
rm -f rystestsequence.md 2>/dev/null || true
rm -f mcp-how-to.md 2>/dev/null || true

# 8. Remove any temporary files
echo "Removing temporary files..."
rm -f *.tmp 2>/dev/null || true
rm -f *_temp.* 2>/dev/null || true
rm -f .DS_Store 2>/dev/null || true
find . -name ".DS_Store" -delete 2>/dev/null || true

# 9. Remove empty directories
echo "Removing empty directories..."
find . -type d -empty -delete 2>/dev/null || true

# 10. Remove any JSON result files from testing
echo "Removing JSON test result files..."
rm -f rigor_mode_test_report_*.json 2>/dev/null || true
rm -f test_python_cli.py 2>/dev/null || true

echo "✅ Repository cleanup complete!"
echo ""
echo "📊 Cleanup Summary:"
echo "  - Removed Python cache files (__pycache__)"
echo "  - Removed development artifacts (egg-info)"
echo "  - Removed old test directories"
echo "  - Removed historical documentation"
echo "  - Removed temporary and result files"
echo ""
echo "🎯 Repository is now clean and production-ready!"