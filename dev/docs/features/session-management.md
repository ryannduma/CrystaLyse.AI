# Session Management

## Overview

CrystaLyse.AI v1.2 introduces comprehensive session management for persistent research workflows. Sessions enable multi-day materials discovery projects with full conversation context retention.

## Core Features

### Session Persistence
- **SQLite Storage**: Conversations stored in `crystalyse_sessions.db`
- **Multi-user Support**: Isolated sessions per user
- **Context Retention**: Full conversation history maintained
- **Cross-session Memory**: Research insights carried forward

### CLI Commands

#### Starting a New Session
```bash
crystalyse chat -u researcher1 -s battery_project -m rigorous
```

#### Resuming Existing Sessions
```bash
crystalyse resume battery_project -u researcher1
```

#### Listing Sessions
```bash
crystalyse sessions -u researcher1
```

#### Demo Mode
```bash
crystalyse demo  # Pre-configured demonstration session
```

### In-Session Commands

- `/history` - View conversation history
- `/clear` - Clear current conversation
- `/undo` - Remove last interaction
- `/sessions` - List all sessions for current user
- `/help` - Show available commands
- `/exit` - Exit current session

### Memory Integration

Sessions integrate with the 4-layer memory system:

1. **Session Memory**: Current conversation context
2. **Discovery Cache**: Cached computational results
3. **User Memory**: Personal preferences and notes
4. **Cross-Session Context**: Research patterns and insights

### Usage Patterns

#### Research Project Workflow
```bash
# Day 1: Start exploring battery materials
crystalyse chat -u researcher1 -s li_ion_cathodes

# Day 2: Continue with specific compositions
crystalyse resume li_ion_cathodes -u researcher1

# Day 3: Compare with previous findings
crystalyse chat -u researcher1 -s comparison_study
```

#### Multi-user Collaboration
```bash
# Principal investigator starts project
crystalyse chat -u prof_smith -s solar_perovskites

# Graduate student continues analysis  
crystalyse chat -u grad_student -s solar_perovskites_detailed

# Each user maintains isolated workspace
```

### Implementation Details

- **Session IDs**: Unique identifiers per user/project combination
- **Database Schema**: SQLite with conversation threading
- **Memory Persistence**: Automatic save/load on session start/end
- **Error Recovery**: Graceful handling of interrupted sessions

### Best Practices

1. **Descriptive Session Names**: Use clear, project-specific identifiers
2. **User Separation**: Maintain distinct user IDs for different researchers
3. **Regular Resumption**: Sessions automatically save progress
4. **Memory Management**: System handles cache cleanup automatically