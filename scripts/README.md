# CrystaLyse.AI Scripts Directory

This directory contains various utility scripts for testing, validation, and maintenance of the CrystaLyse.AI platform.

## Directory Structure

### `/testing/`
Contains comprehensive testing scripts for the CrystaLyse system:

- **`comprehensive_stress_test.py`**: Complete stress testing suite with 10 complex materials discovery queries
- **`debug_agent_behaviour.py`**: Debug script for analysing agent behaviour patterns
- **`test_system_prompt.py`**: Tests the system prompt implementation and behaviour

### `/validation/`
Contains validation scripts for system components:

- **`quick_validation_test.py`**: Fast validation tests for basic functionality
- **`test_prompt_loading.py`**: Validates system prompt loading and mode configurations
- **`validate_prompt_behaviour.py`**: Comprehensive validation of prompt-driven behaviours

### Root Scripts

- **`cleanup_repository.sh`**: Repository maintenance and cleanup utilities

## Usage Examples

### Running Comprehensive Tests
```bash
cd /path/to/CrystaLyse.AI
python scripts/testing/comprehensive_stress_test.py
```

### Quick Validation
```bash
python scripts/validation/quick_validation_test.py
```

### Debugging Agent Behaviour
```bash
python scripts/testing/debug_agent_behaviour.py
```

## Requirements

All scripts require:
- Python 3.11+
- CrystaLyse.AI environment properly configured
- MCP servers (SMACT, Chemeleon, MACE) available
- Required API keys set in environment variables

## Output

Test results and reports are automatically saved to `/test_reports/` and `/reports/` directories with timestamps.