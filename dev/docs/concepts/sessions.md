# Session Management

## Overview

CrystaLyse.AI's session-based architecture enables persistent, contextual interactions for materials design research. Sessions maintain state across multiple queries, allowing for deep, exploratory analysis that builds upon previous findings.

## Session Architecture

### Session Lifecycle

```
┌─────────────┐     ┌──────────────┐     ┌─────────────┐
│   Created   │ --> │    Active    │ --> │   Paused    │
└─────────────┘     └──────────────┘     └─────────────┘
                           │                      │
                           v                      v
                    ┌──────────────┐     ┌─────────────┐
                    │   Resumed    │ <-- │  Archived   │
                    └──────────────┘     └─────────────┘
```

### Session Components

```
Session
├── Metadata
│   ├── ID
│   ├── User
│   ├── Created/Updated
│   └── Configuration
├── Context
│   ├── Conversation History
│   ├── Active Materials
│   ├── Tool States
│   └── Discoveries
├── Memory
│   ├── Working Memory
│   ├── Session Memory
│   └── Discovery Links
└── State
    ├── Current Focus
    ├── Active Hypotheses
    └── Pending Tasks
```

## Session Types

### 1. Interactive Sessions

Real-time conversational analysis:
```python
session = agent.create_interactive_session(
    name="battery_materials_project",
    config={
        "memory_enabled": True,
        "discovery_detection": True,
        "context_window": 4000
    }
)
```

### 2. Batch Sessions

Process multiple analyses with shared context:
```python
batch_session = agent.create_batch_session(
    name="materials_library_screening",
    materials=materials_list,
    shared_context=True
)
```

### 3. Research Sessions

Long-running research projects:
```python
research_session = agent.create_research_session(
    name="solid_state_battery_design",
    duration_days=30,
    checkpoint_frequency="daily"
)
```

### 4. Collaborative Sessions

Multi-user research collaboration:
```python
collab_session = agent.create_collaborative_session(
    name="team_materials_exploration",
    users=["researcher1", "researcher2"],
    permissions="shared_write"
)
```

## Working with Sessions

### Creating Sessions

```python
from crystalyse import SessionManager

# Create a new session
session = SessionManager.create_session(
    user_id="user_123",
    session_type="interactive",
    metadata={
        "project": "cathode_materials_discovery",
        "phase": "structure_optimization"
    }
)

print(f"Session ID: {session.id}")
print(f"Created: {session.created_at}")
```

### Session Interaction

```python
# Start conversation
response = session.query("Analyse LiFePO4")

# Follow-up with context
response = session.query("What about its ionic conductivity?")

# The session maintains context of LiFePO4
response = session.query("Show me similar cathode materials")
```

### Managing Session State

```python
# Save current state
session.save_checkpoint("after_lifepo4_analysis")

# Pause session
session.pause()

# Resume later
session = SessionManager.resume_session(session_id)

# Restore from checkpoint
session.restore_checkpoint("after_lifepo4_analysis")
```

## Context Management

### Context Building

Sessions intelligently build context:

```python
# Automatic context includes:
context = session.get_context()
print(context.recent_materials)     # Recently analysed materials
print(context.active_tools)         # Currently active tools
print(context.discoveries)          # Session discoveries
print(context.conversation[-10:])   # Last 10 exchanges
```

### Context Control

Fine-tune context behaviour:

```python
# Configure context
session.configure_context(
    max_history=50,          # Maximum conversation history
    material_memory=10,      # Remember last N materials
    auto_summarise=True,     # Summarise old context
    relevance_threshold=0.7  # Include relevant past findings
)

# Manually add to context
session.add_context(
    "important_finding",
    "This crystal structure shows enhanced stability"
)

# Clear specific context
session.clear_context("tool_outputs")
```

## Discovery Tracking

### Automatic Discovery Detection

```python
# Configure discovery detection
session.configure_discoveries(
    auto_detect=True,
    min_confidence=0.75,
    categories=[
        "structure_property",
        "novel_synthesis",
        "stability_insight",
        "phase_relationship"
    ]
)

# Discoveries are automatically tracked
response = session.query(
    "The olivine structure seems crucial for Li+ mobility"
)
# System detects and stores this structure-property insight
```

### Manual Discovery Recording

```python
# Explicitly mark a discovery
session.record_discovery(
    type="structure_property",
    description="Olivine structure increases ionic conductivity 10-fold",
    materials=["LiFePO4", "LiMnPO4"],
    evidence=response.analysis,
    confidence=0.9
)

# Link discoveries
session.link_discoveries(
    discovery_ids=["disc1", "disc2"],
    relationship="supports",
    notes="Both show same structure-property pattern"
)
```

## Session Persistence

### Saving Sessions

```python
# Auto-save configuration
session.configure_autosave(
    enabled=True,
    frequency_minutes=5,
    on_discovery=True,
    on_pause=True
)

# Manual save
session.save()

# Export session
session.export(
    format="json",
    include_discoveries=True,
    include_molecules=True,
    output_path="session_export.json"
)
```

### Loading Sessions

```python
# List user sessions
sessions = SessionManager.list_sessions(
    user_id="user_123",
    status="active",
    project="cathode_materials_discovery"
)

# Load specific session
session = SessionManager.load_session(session_id)

# Search sessions
results = SessionManager.search_sessions(
    query="olivine structure analysis",
    user_id="user_123"
)
```

## Advanced Features

### Session Branching

Create exploration branches:

```python
# Create a branch to explore alternative hypothesis
branch = session.create_branch("explore_different_structure")

# Work in branch
branch.query("What if we use a spinel structure instead?")

# Merge successful branch
session.merge_branch(branch.id)

# Or discard unsuccessful exploration
branch.discard()
```

### Session Templates

Use templates for common workflows:

```python
# Create from template
session = SessionManager.create_from_template(
    template="materials_discovery_workflow",
    parameters={
        "application": "solid state battery",
        "structure": "perovskite"
    }
)

# Save custom template
SessionManager.save_template(
    name="my_materials_screening_workflow",
    from_session=session.id
)
```

### Session Analytics

Track session metrics:

```python
# Get session statistics
stats = session.get_statistics()
print(f"Duration: {stats.duration_minutes} minutes")
print(f"Queries: {stats.query_count}")
print(f"Materials analysed: {stats.material_count}")
print(f"Discoveries: {stats.discovery_count}")
print(f"Tools used: {stats.tool_usage}")

# Generate session summary
summary = session.generate_summary()
print(summary.key_findings)
print(summary.materials_of_interest)
print(summary.next_steps)
```

## Collaborative Features

### Multi-User Sessions

```python
# Create collaborative session
collab = SessionManager.create_collaborative_session(
    name="team_materials_design",
    owner="lead_researcher",
    members=["materials_scientist1", "physicist1", "data_scientist1"]
)

# Set permissions
collab.set_permissions(
    user="materials_scientist1",
    permissions=["read", "write", "add_materials"]
)

# Track contributions
contributions = collab.get_contributions()
for user, stats in contributions.items():
    print(f"{user}: {stats.queries} queries, {stats.discoveries} discoveries")
```

### Session Sharing

```python
# Share read-only view
share_link = session.create_share_link(
    permissions="read",
    expires_in_days=7
)

# Share with specific user
session.share_with_user(
    user_id="collaborator_123",
    permissions=["read", "comment"]
)
```

## Integration with Tools

### Tool State Management

```python
# Tools maintain state within session
session.query("Load protein structure 1ABC")
# Visualization tool now has 1ABC loaded

session.query("Dock the current molecule")
# Docking tool uses loaded protein and current molecule

# Check tool states
tool_states = session.get_tool_states()
print(tool_states["visualization"])  # Shows loaded protein
print(tool_states["docking"])        # Shows docking results
```

### Custom Tool Integration

```python
# Register session-aware tool
class SessionAwareTool:
    def execute(self, query, session_context):
        # Access session data
        recent_materials = session_context.recent_materials
        discoveries = session_context.discoveries
        
        # Tool logic here
        return results

session.register_tool(SessionAwareTool())
```

## Best Practices

### 1. Session Hygiene

```python
# Regular cleanup
session.cleanup_old_context(days=7)
session.compress_history()
session.archive_completed_tasks()
```

### 2. Efficient Context Management

- Keep context focused on current research
- Summarise old conversations
- Archive completed explorations
- Use branching for hypotheses

### 3. Discovery Management

- Review and validate auto-detected discoveries
- Link related discoveries
- Export important findings
- Tag discoveries for easy retrieval

### 4. Collaboration Guidelines

- Define clear permissions
- Use session templates for consistency
- Track contributions
- Regular synchronisation points

## Error Handling

### Session Recovery

```python
try:
    session.query("complex analysis")
except SessionError as e:
    # Attempt recovery
    if e.recoverable:
        session.recover_from_checkpoint()
    else:
        # Create new session from last good state
        new_session = SessionManager.create_from_backup(
            session.last_backup
        )
```

### Conflict Resolution

```python
# Handle collaborative conflicts
try:
    session.save()
except ConflictError as e:
    # Show conflicts
    for conflict in e.conflicts:
        print(f"Conflict in {conflict.field}")
        print(f"Your version: {conflict.local}")
        print(f"Remote version: {conflict.remote}")
    
    # Resolve
    session.resolve_conflicts(strategy="merge")
```

## Performance Optimisation

### Session Caching

```python
# Configure session cache
session.configure_cache(
    enabled=True,
    cache_discoveries=True,
    cache_molecules=True,
    ttl_minutes=30
)
```

### Lazy Loading

```python
# Load session without full history
session = SessionManager.load_session(
    session_id,
    lazy_load=True
)

# Load history on demand
history = session.get_history(last_n=50)
```

## Next Steps

- Learn about [Tool Integration](tools.md) in sessions
- Explore [Memory Systems](memory.md) for persistence
- Check [API Reference](../reference/sessions/) for detailed documentation
- Read [Collaboration Guide](../guides/collaboration.md) for team usage
