# Crystalyse Session-Based User Guide

## Overview

Crystalyse's interactive chat is session-based: every conversation is backed by
a SQLite database that survives restarts, so a long-running investigation can be
picked up where it left off. This guide shows how that helps complex research
workflows, and is precise about what a session does and does not keep.

## 🌟 Key Features

### **Session-Based Conversations**
- **Automatic conversation history** - the chat loop keeps the turns and hands
  them to the agent; no manual `.to_input_list()` bookkeeping
- **Persistent memory** - the OpenAI Agents SDK `SQLiteSession` writes each turn
  to disk, so a session survives restarts and can be resumed
- **Context continuity** - multi-turn conversations with the earlier turns in
  context

### **Enhanced Workflow Benefits**
- **Long-running research projects** - work on complex problems over days/weeks
- **Session resumption** - pick up exactly where you left off
- **Mode and model switching mid-session** - `/mode` and `/model` recreate the
  agent in place without losing the conversation
- **Provenance per query** - each query in the session still produces its own
  audit trail

What a session does **not** do: no computational results are cached, and no user
preferences or expertise profiles are learned. Repeating a calculation runs it
again; what carries over is the conversation.

## 📋 Available Commands

### Core Session Commands
```bash
# Start a new session-based chat
crystalyse chat -u <user_id> -s <session_id>

# Start a session in a specific mode (mode is a global option, so it goes first)
crystalyse --mode validate chat -u <user_id> -s <session_id>

# Resume a previous session (same --project, same -s, same mode)
crystalyse chat -s <session_id> -u <user_id>
```

### In-Session Commands
```bash
/help                            # Show the command table
/tools [desc|nodesc]             # Chemistry and visualisation tool reference
/mcp [status|servers|desc]        # MCP server reference
/stats                           # Session duration and configuration
/memory [show|clear|refresh]      # Inspect or wipe conversation memory
/mode [show|explore|validate|auto] # View or change the operating mode
/model [show|<name>]             # View or change the language model
/about                           # Version and system information
/clear                           # Clear the terminal screen
/quit, /exit                     # Exit the chat session
```

Typing `quit` or `exit` (without a slash) also ends the session. Note that
`/clear` clears the *screen*; to wipe the conversation itself use
`/memory clear`, which asks for confirmation and then deletes and recreates the
session database.

### Alternative Commands
```bash
# One-shot discovery (no session persistence)
crystalyse discover "query" --mode validate

# Check which model backbones are available to you
crystalyse models list
crystalyse models check
```

## 🔋 Enhanced Workflow Example: LiCoO₂ Battery Analysis

Let's demonstrate how the session system enhances a complex LiCoO₂ battery analysis workflow:

### **Traditional Approach (Without Sessions)**
```bash
# Each query is independent - no context preservation
crystalyse discover "Reproduce Materials Project battery properties for LiCoO₂"
crystalyse discover "Calculate volume changes during delithiation"
crystalyse discover "Compare with MP data for mp-552024_Li"
```

**Problems:**
- No context between queries
- No conversation history
- Manual coordination required

### **Enhanced Session-Based Approach**
```bash
# Start a battery research session
crystalyse --mode validate chat -u battery_researcher -s licoo2_analysis
```

**Session 1: Initial Analysis**
```
➤ Reproduce the Materials Project battery properties for LiCoO₂ → CoO₂, assuming full delithiation (i.e., 1 mol Li removed per formula unit).

Match the following predicted properties from MP (for mp-552024_Li):
- Total Gravimetric Capacity: ~209.09 mAh/g
- Total Volumetric Capacity: ~955.53 Ah/l
- Volume Change: ~0.05%
- Specific Energy: ~663.75 Wh/kg
- Energy Density: ~3033.38 Wh/l

Please generate relaxed structures for LiCoO₂ and CoO₂, compute volumes, formation energies, and calculate all battery metrics.
```

**Session continues with context awareness:**
```
➤ What causes the large volume change difference between my calculations and MP? You calculated 15.5% vs MP's 0.05%.

➤ Can you analyze the structural differences between the polymorphs? Why did Chemeleon generate P1 triclinic instead of the expected R3̄m layered structure?

➤ How would using the correct layered structure affect the voltage calculations? Can you estimate the impact?
```

**Key Benefits Demonstrated:**
- **Context preservation** - each query builds on the previous analysis
- **Iterative refinement** - you can dig deeper into discrepancies
- **Research continuity** - natural conversation flow
- **Traceability** - each turn still writes its own provenance run

### **Session Resumption After Days**
```bash
# Resume the same session days later - the same project, session name and mode
crystalyse --mode validate chat -s licoo2_analysis -u battery_researcher
```

**Continued analysis:**
```
➤ I've been thinking about our discussion on structural polymorphs. Can you now compare the P1 triclinic results with literature values for layered LiCoO₂?

➤ What other cathode materials show similar polymorph-dependent volume changes? Let's compare with LiMn₂O₄ and LiFePO₄.

➤ Based on our complete analysis, what are the key recommendations for improving computational predictions of battery materials?
```

**Advanced Session Features:**
- **Persistent conversation** - `/memory show` reports the session ID and the
  size of the database on disk
- **Fresh start when you want one** - `/memory clear` wipes the conversation
  without leaving the session
- **Switchable depth** - `/mode validate` when a rough answer needs firming up

## 🧪 Advanced Workflow Patterns

### **1. Multi-Day Research Projects**
```bash
# Day 1: Initial discovery
crystalyse --mode validate chat -s perovskite_project -u researcher
➤ Find stable perovskite materials for next-generation solar cells

# Day 2: Property analysis (same mode, or the session key changes)
crystalyse --mode validate chat -s perovskite_project -u researcher
➤ What are the optical properties of the materials we identified yesterday?

# Day 3: Experimental validation
crystalyse --mode validate chat -s perovskite_project -u researcher
➤ How do our computational predictions compare with recent experimental data?
```

### **2. Shared Session Thread**
```bash
# Researcher A starts the investigation
crystalyse chat -s team_project -u researcher_a
➤ Analyze defect formation in 2D materials

# Researcher B continues the same thread on the same machine and project
crystalyse chat -s team_project -u researcher_b
➤ Building on the defect analysis, what about electronic transport properties?
```

The conversation is keyed on the project, session name and mode - not on the
user ID - so both commands above continue the same conversation. Sessions live
in the local home directory, so this is a same-machine handover, not remote
collaboration.

### **3. Comparative Studies**
```bash
crystalyse chat -s material_comparison -u materials_scientist
➤ Compare thermoelectric properties of Bi₂Te₃ and SnSe

# The session keeps the earlier turns in context
➤ How do these compare with newer materials like MgAgSb?
➤ What structural factors drive the performance differences?
➤ Can we predict better thermoelectric materials based on these insights?
```

## 🛠️ Technical Implementation Details

### **Session Management**
- **Database storage** - one SQLite database per session, at
  `~/.crystalyse/sessions/<session_id>.db`
- **Session key** - `<session_id>` is `<project_name>_<mode>`, where
  `project_name` is the global `--project` value (default `crystalyse_session`)
  with `_<session>` appended when `-s` is given. Switching mode opens a
  different database.
- **Conversation persistence** - the SDK writes each turn as the run proceeds
- **Clearing** - `/memory clear` deletes the database and its `-shm`/`-wal`
  siblings, then recreates it empty

### **Python Surface**
```python
from crystalyse.agents import EnhancedCrystaLyseAgent

agent = EnhancedCrystaLyseAgent(
    project_name="battery_study",
    mode="validate",          # explore | validate | auto
    model="openai_o3",        # optional; defaults to the mode's model
)

# One turn.  `history` is a plain list of {"role": ..., "content": ...} dicts
# kept by the caller; the SDK session persists turns independently.
results = await agent.discover(
    "Analyse LiCoO2 cathode properties",
    history=history,
)

agent.clear_session_memory()   # delete and recreate the session database
```

### **What Is Not Persisted**
- **No result caching** - structures and energies are recomputed on request
- **No user profiles** - `--user` labels the session but nothing is learned from
  it
- **No cross-session sharing** - each `<project>_<session>_<mode>` combination is
  its own database

## 🎯 Best Practices

### **Session Organization**
```bash
# Use descriptive session IDs
crystalyse chat -s battery_cathodes_2025 -u researcher
crystalyse chat -s solar_perovskites -u researcher
crystalyse chat -s 2d_materials_transport -u researcher
```

### **Keeping a Session Resumable**
```bash
# Keep --project, -s and --mode identical to resume the same conversation
crystalyse --project thermo_study --mode explore chat -s snse_screen

# Check what the agent thinks it is using
➤ /memory show
```

### **Mode Selection**
```bash
# Explore mode for fast exploration
crystalyse --mode explore chat -u researcher

# Validate mode for the full validation pipeline
crystalyse --mode validate chat -u researcher

# Or switch inside the session
➤ /mode validate
```

The legacy names `creative`, `rigorous` and `adaptive` still resolve to
`explore`, `validate` and `auto`, but they emit a `DeprecationWarning` and will
be removed in v2.0.

### **Model Selection**
```bash
# Pick a backbone from the registry for the whole session
crystalyse --model anthropic_claude_sonnet chat -s screening -u researcher

# See what is available and which keys are set
crystalyse models list

# Or switch inside the session (overrides the mode's default model)
➤ /model openai_o3
```

## 🔄 Migration from Legacy System

### **From Manual History Management**
```python
# OLD WAY - the caller assembled the history for every call
results = await agent.discover(query, history=my_history_list)

# NEW WAY - run a chat session and let it manage the turns
# crystalyse chat -u user -s session_id
```

The programmatic entry point is still `await agent.discover(query,
history=..., trace_handler=...)`; the chat session is what removes the
bookkeeping.

### **From One-Shot Analysis**
```bash
# OLD WAY (no context preservation)
crystalyse discover "query 1"
crystalyse discover "query 2"  # No context from query 1

# NEW WAY (full context continuity)
crystalyse chat -u user
➤ query 1
➤ query 2  # Query 1 is in context
```

## 📊 Practical Benefits

### **Research Productivity**
- **Seamless continuation** - no context loss between sessions
- **Iterative refinement** - build on previous insights
- **Natural workflow** - conversation-based research progression

### **Session Persistence**
- **Survives restarts** - the conversation is on disk, not in process memory
- **Recoverable** - a corrupted database can be removed and recreated
- **Inspectable** - the session ID and file size are visible via `/memory show`

## 🚀 Getting Started

### **Quick Start**
```bash
# 1. Start your first session
crystalyse chat -u your_username

# 2. Resume it later
crystalyse chat -s <session_id> -u your_username
```

### **Advanced Usage**
```bash
# Complex research project in validate mode
crystalyse --mode validate chat -s complex_project -u researcher

# Get help
crystalyse chat --help
```

## 📈 Future Enhancements

### **Planned Features**
- **Session sharing** - collaborate on shared sessions
- **Export capabilities** - generate research reports from sessions
- **Result caching** - reuse expensive computations across turns
- **AI-assisted session management** - smart session organisation

### **Integration Opportunities**
- **Jupyter notebooks** - export sessions to notebooks
- **Research databases** - integration with materials databases
- **Collaboration platforms** - team-based session management

---

## 🔗 Quick Reference

### **Essential Commands**
```bash
crystalyse chat -u <user> -s <session>                  # Start session
crystalyse --mode validate chat -u <user> -s <session>  # Start in validate mode
crystalyse chat -s <session> -u <user>                  # Resume session
```

### **In-Session Commands**
```bash
/memory show     # Session ID and database size
/memory clear    # Wipe the conversation (with confirmation)
/mode validate   # Change operating mode
/model <name>    # Change language model
/help            # Show help
/exit            # Exit session
```

### **Key Benefits**
- ✅ **Automatic conversation history**
- ✅ **Persistent conversations across restarts**
- ✅ **Context continuity for complex research**
- ✅ **Mode and model switching mid-session**
- ✅ **Per-query provenance**
- ✅ **Multi-day research project support**

**Ready to start? Run `crystalyse chat -u your_username` - or just `crystalyse`, which starts a chat session by default.**
