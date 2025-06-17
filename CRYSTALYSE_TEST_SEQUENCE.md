# CrystaLyse.AI Comprehensive Test Sequence

**Date:** December 16, 2024  
**Version:** 1.0.0  
**Purpose:** Manual testing guide to verify all CrystaLyse.AI functionality

## 🚀 Pre-Test Setup

### 1. Environment Verification
```bash
# Check Python version (should be 3.10+)
python --version

# Verify installation
pip list | grep crystalyse

# Check API key is set
echo $OPENAI_MDG_API_KEY | head -c 10  # Should show first 10 chars
```

### 2. Clean Start
```bash
# Remove any old session files
rm -f ~/.crystalyse_history
rm -f crystalyse_session_*.json

# Navigate to project directory
cd /home/ryan/crystalyseai/CrystaLyse.AI
```

## 📋 Test Sequence

### Test 1: Basic CLI Commands

#### 1.1 Help Command
```bash
crystalyse --help
```
**Expected:** Shows command list without startup messages

#### 1.2 Status Command
```bash
crystalyse status
```
**Expected:** Shows configuration table with API status

#### 1.3 Examples Command
```bash
crystalyse examples
```
**Expected:** Lists example queries

#### 1.4 One-time Analysis
```bash
crystalyse analyse "Design a simple oxide material" --temperature 0.3
```
**Expected:** 
- Progress spinner
- Analysis results
- No interactive shell

### Test 2: Interactive Shell Startup

#### 2.1 Default Shell Launch
```bash
crystalyse
```
**Expected:**
- ASCII art banner (no API messages before it)
- "Materials Intelligence at Your Fingertips"
- Available commands listed
- `🔬 crystalyse (rigorous) >` prompt

#### 2.2 Shell Help
```
/help
```
**Expected:** Detailed help panel with all commands

#### 2.3 Examples in Shell
```
/examples
```
**Expected:** Example queries panel

### Test 3: Creative Mode Testing

#### 3.1 Switch to Creative Mode
```
/mode creative
```
**Expected:** 
- "✅ Mode set to: creative"
- Prompt changes to `🎨 crystalyse (creative) >`

#### 3.2 Creative Analysis
```
Design a novel superconducting material
```
**Expected:**
- Fast analysis (~30-60 seconds)
- Uses Chemeleon CSP only
- No SMACT validation messages
- Results show generated structures

#### 3.3 Check Status
```
/status
```
**Expected:** Shows current mode as "creative"

### Test 4: Rigorous Mode Testing

#### 4.1 Switch to Rigorous Mode
```
/mode rigorous
```
**Expected:** Prompt changes back to `🔬 crystalyse (rigorous) >`

#### 4.2 Rigorous Analysis with Full Pipeline
```
Create a lead-free ferroelectric material
```
**Expected:**
- Longer analysis (2-5 minutes)
- INFO messages showing:
  - SMACT validation tools being used
  - Chemeleon CSP generating structures
  - MACE calculating energies
- Results include validation status

#### 4.3 Another Rigorous Test
```
Design a cathode material for sodium-ion batteries with voltage > 3V
```
**Expected:**
- Full pipeline execution
- Multiple candidates with energy calculations
- Recommendations based on MACE stability

### Test 5: Structure Visualization

#### 5.1 Generate Structure First
```
Create a simple perovskite structure
```
**Expected:** Analysis completes with structure generation

#### 5.2 View Structure
```
/view
```
**Expected:**
- "✅ Structure viewer opened in browser"
- Browser opens with 3D interactive viewer
- Controls work (rotate, zoom, style toggle)

#### 5.3 No Structure Available
```
/clear
What is the band gap of silicon?
/view
```
**Expected:** "⚠️ No structure available. Run an analysis first."

### Test 6: Session Management

#### 6.1 Check History
```
/history
```
**Expected:** Table showing all queries from this session

#### 6.2 Export Session
```
/export test_session.json
```
**Expected:** 
- "✅ Session exported to: test_session.json"
- File contains all queries and results

#### 6.3 Exit with Save
```
/exit
```
**Expected:** 
- "Save session before exiting? (y/n)"
- Type `y`
- Session saved
- "👋 Goodbye! Happy materials discovery!"

### Test 7: Error Handling

#### 7.1 Start New Session
```bash
crystalyse shell
```

#### 7.2 Invalid Command
```
/invalid_command
```
**Expected:** "❌ Unknown command: /invalid_command"

#### 7.3 Invalid Mode
```
/mode invalid
```
**Expected:** "❌ Invalid mode. Use 'creative' or 'rigorous'"

#### 7.4 Complex Query Error Recovery
```
Create a material with impossible properties like negative mass
```
**Expected:** 
- Graceful error handling
- Shell remains responsive
- Can continue with next query

### Test 8: Advanced Features

#### 8.1 Multiple Queries
```
Design a battery cathode
Find a transparent conductor
Create a magnetic semiconductor
/history
```
**Expected:** All three queries shown in history

#### 8.2 Streaming Analysis
```bash
crystalyse analyse "Design a complex multi-component alloy" --stream
```
**Expected:** Real-time output during analysis

#### 8.3 JSON Output
```bash
crystalyse analyse "Find a photovoltaic material" -o pv_result.json
```
**Expected:** 
- Results displayed
- "Results saved to pv_result.json"

### Test 9: MCP Server Integration

#### 9.1 Check MCP Servers
Look for these messages during rigorous mode analysis:
- `INFO:chemeleon_mcp.server:Starting chemeleon-csp`
- `INFO:mcp.server.lowlevel.server:Processing request`
- `INFO:chemeleon_mcp.tools:Generating X structures`
- SMACT validation messages
- MACE energy calculation messages

### Test 10: Final Verification

#### 10.1 Complete Workflow
```bash
crystalyse
```
Then in shell:
```
/mode rigorous
Design a lithium-ion battery cathode with capacity > 150 mAh/g
/view
/export final_test.json
/exit
y
```

#### 10.2 Verify Files
```bash
ls -la ~/.crystalyse_history
ls -la *.json
cat final_test.json | jq '.session_id'
```

## ✅ Success Criteria

### All Tests Pass If:
1. **No startup messages** before banner
2. **ASCII art displays** correctly
3. **Both modes work** (creative fast, rigorous comprehensive)
4. **MCP servers connect** (see INFO logs)
5. **3D viewer opens** in browser
6. **Session management** works (history, export)
7. **Error handling** is graceful
8. **No Node.js errors** or references

### Performance Benchmarks:
- Creative mode: 30-90 seconds per query
- Rigorous mode: 2-5 minutes per query
- Shell startup: < 2 seconds
- Command response: Immediate

## 🐛 Troubleshooting

### If Shell Doesn't Start:
```bash
# Check for missing dependencies
pip install prompt-toolkit rich

# Run with debug
CRYSTALYSE_DEBUG=true crystalyse
```

### If Analysis Fails:
```bash
# Check API key
crystalyse status

# Try simpler query
crystalyse analyse "NaCl structure"
```

### If Visualization Fails:
```bash
# Check browser is set
echo $BROWSER

# Try manual open
python -c "import webbrowser; webbrowser.open('https://google.com')"
```

## 📝 Test Report Template

```markdown
## CrystaLyse.AI Test Report

**Date:** [DATE]
**Tester:** [NAME]
**Version:** 1.0.0

### Test Results Summary
- [ ] Basic CLI Commands: PASS/FAIL
- [ ] Interactive Shell: PASS/FAIL
- [ ] Creative Mode: PASS/FAIL
- [ ] Rigorous Mode: PASS/FAIL
- [ ] Visualization: PASS/FAIL
- [ ] Session Management: PASS/FAIL
- [ ] Error Handling: PASS/FAIL
- [ ] MCP Integration: PASS/FAIL

### Issues Found:
1. [Issue description]
2. [Issue description]

### Notes:
[Any observations or suggestions]
```

## 🎯 Expected Output Examples

### Successful Rigorous Analysis:
```
INFO:chemeleon_mcp.server:Starting chemeleon-csp v0.1.0
INFO:chemeleon_mcp.tools:Generating 3 structures for LiFePO4
Sampling: 100%|████████| 256/256 [00:03<00:00, 78.52it/s]
INFO:mace_mcp.tools:Calculating formation energy for structure
```

### Creative Mode (No SMACT/MACE):
```
INFO:chemeleon_mcp.server:Starting chemeleon-csp v0.1.0
INFO:chemeleon_mcp.tools:Generating 5 structures for novel composition
```

---

**Remember:** The goal is a smooth, professional experience with no Node.js artifacts and full computational pipeline in rigorous mode!