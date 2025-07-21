# Memory Systems

## Overview

CrystaLyse.AI implements sophisticated memory systems that enable agents to maintain context, learn from interactions, and build upon previous discoveries. The memory architecture is designed specifically for materials design research workflows.

## Memory Architecture

### Hierarchical Memory Structure

```
┌────────────────────────────────────────┐
│           User Memory                  │
│    (Preferences, History, Projects)    │
├────────────────────────────────────────┤
│          Session Memory                │
│    (Current Context, Discoveries)      │
├────────────────────────────────────────┤
│         Discovery Memory               │
│    (Important Findings, Insights)      │
├────────────────────────────────────────┤
│          Working Memory                │
│      (Immediate Context, Cache)        │
└────────────────────────────────────────┘
```

## Memory Types

### 1. Working Memory

Short-term memory for immediate context:
- Current material composition being analysed
- Recent tool outputs (SMACT, Chemeleon, MACE)
- Temporary calculations and energy values
- Active materials design hypotheses

**Characteristics:**
- High-speed access
- Limited capacity
- Cleared after each session
- Optimised for performance

### 2. Session Memory

Medium-term memory for ongoing conversations:
- Conversation history
- Analysis progression
- User queries and responses
- Contextual relationships

**Characteristics:**
- Persists during session
- Enables contextual understanding
- Supports follow-up questions
- Tracks analysis flow

### 3. Discovery Memory

Long-term storage for important findings:
- Significant materials discoveries
- Validated crystal structures
- Stable material compositions
- Structure-property relationships

**Characteristics:**
- Permanent storage
- Cross-session accessibility
- Searchable and indexed
- Quality-filtered content

### 4. User Memory

Personalised memory for each user:
- Analysis preferences
- Project history
- Custom configurations
- Frequently analysed materials

**Characteristics:**
- User-specific storage
- Privacy-protected
- Enables personalisation
- Tracks usage patterns

## Memory Implementation

### Storage Backends

CrystaLyse.AI supports multiple storage options:

```python
# In-memory storage (default)
memory = InMemoryStorage()

# Redis for distributed systems
memory = RedisMemoryStorage(
    host="localhost",
    port=6379,
    db=0
)

# PostgreSQL for persistent storage
memory = PostgreSQLMemoryStorage(
    connection_string="postgresql://..."
)

# File-based for simple deployments
memory = FileMemoryStorage(
    base_path="~/.crystalyse/memory"
)
```

### Memory Manager

The central memory management system:

```python
from crystalyse.memory import MemoryManager

manager = MemoryManager(
    working_memory=InMemoryStorage(),
    session_memory=RedisMemoryStorage(),
    discovery_memory=PostgreSQLMemoryStorage(),
    user_memory=FileMemoryStorage()
)
```

## Memory Operations

### Storing Information

```python
# Store in working memory
manager.working.store(
    key="current_material",
    value={
        "smiles": "CC(C)Cc1ccc(cc1)C(C)C(=O)O",
        "name": "Ibuprofen",
        "properties": {...}
    },
    ttl=300  # 5 minutes
)

# Store discovery
manager.discoveries.store(
    discovery={
        "type": "sar_relationship",
        "description": "Higher formation energy stability in perovskite structure",
        "materials": ["CaTiO3", "BaTiO3"],
        "confidence": 0.85
    }
)
```

### Retrieving Information

```python
# Get from working memory
current = manager.working.get("current_material")

# Search discoveries
discoveries = manager.discoveries.search(
    query="anti-inflammatory",
    filters={"confidence": {"$gte": 0.8}}
)

# Get session context
context = manager.session.get_context(
    session_id="session_123",
    last_n_messages=10
)
```

### Memory Queries

Advanced querying capabilities:

```python
# Semantic search in discoveries
results = manager.discoveries.semantic_search(
    "materials with high ionic conductivity",
    top_k=5
)

# Find similar analyses
similar = manager.user.find_similar_analyses(
    material="LiFePO4",
    user_id="user_123"
)
```

## Context Management

### Building Context

The memory system builds context intelligently:

```python
context = manager.build_context(
    current_query="What about its metabolites?",
    session_id="session_123"
)

# Context includes:
# - Current material (from working memory)
# - Recent conversation (from session memory)
# - Relevant discoveries (from discovery memory)
# - User preferences (from user memory)
```

### Context Windows

Manage context size for optimal performance:

```python
# Configure context window
manager.configure_context(
    max_tokens=4000,
    prioritisation="recency",  # or "relevance"
    include_discoveries=True
)

# Prune old context
manager.session.prune_context(
    session_id="session_123",
    keep_last_n=20
)
```

## Discovery System

### Automatic Discovery Detection

The system automatically identifies important findings:

```python
# Configure discovery detection
manager.configure_discovery_detection(
    min_confidence=0.7,
    categories=[
        "structure_property_relationship",
        "novel_material",
        "unexpected_formation_energy",
        "safety_concern"
    ]
)
```

### Discovery Validation

Discoveries are validated before storage:

```python
class DiscoveryValidator:
    def validate(self, discovery):
        # Check scientific validity
        if not self.is_chemically_valid(discovery):
            return False
        
        # Check novelty
        if self.exists_in_literature(discovery):
            discovery.novelty = "known"
        
        # Assign confidence score
        discovery.confidence = self.calculate_confidence(discovery)
        
        return discovery.confidence > threshold
```

## Memory Optimisation

### Caching Strategies

Efficient caching for performance:

```python
# Configure caching
manager.configure_cache(
    strategy="lru",  # Least Recently Used
    max_size=1000,
    ttl=3600  # 1 hour
)

# Cache materials calculations
@manager.cache(key_prefix="mat_props")
def calculate_properties(smiles):
    # Expensive calculation
    return properties
```

### Memory Compression

Reduce storage requirements:

```python
# Enable compression
manager.enable_compression(
    algorithm="zstd",
    level=3,
    min_size=1024  # Only compress entries > 1KB
)
```

### Indexing

Optimise search performance:

```python
# Create indices
manager.discoveries.create_index("material_formula")
manager.discoveries.create_index("discovery_type")
manager.discoveries.create_text_index("description")
```

## Privacy and Security

### Data Isolation

User data is strictly isolated:

```python
# Each user has isolated memory space
user_manager = manager.for_user("user_123")

# No cross-user data access
user_manager.discoveries.search(...)  # Only user's discoveries
```

### Encryption

Sensitive data encryption:

```python
# Enable encryption at rest
manager.enable_encryption(
    key=encryption_key,
    algorithm="AES-256-GCM"
)
```

### Data Retention

Configurable retention policies:

```python
# Set retention policies
manager.set_retention_policy(
    working_memory={"hours": 1},
    session_memory={"days": 7},
    discovery_memory={"days": 365},
    user_memory={"days": 730}
)
```

## Integration with Agents

### Automatic Memory Management

Agents automatically manage memory:

```python
agent = CrystaLyseAgent(memory_manager=manager)

# Agent automatically:
# - Stores queries in session memory
# - Detects and stores discoveries
# - Builds context from all memory types
# - Manages working memory lifecycle
```

### Custom Memory Handlers

Extend memory behaviour:

```python
class CustomMemoryHandler:
    def on_discovery(self, discovery):
        # Custom processing
        if discovery.type == "battery_cathode":
            notify_research_team(discovery)
    
    def on_session_end(self, session):
        # Generate session summary
        summary = generate_summary(session)
        store_summary(summary)

agent.register_memory_handler(CustomMemoryHandler())
```

## Best Practices

### 1. Memory Hygiene

- Clear working memory between unrelated tasks
- Prune session memory periodically
- Validate discoveries before storage
- Archive old user data

### 2. Performance Optimisation

- Use appropriate storage backends
- Enable caching for repeated queries
- Index frequently searched fields
- Monitor memory usage

### 3. Data Management

```python
# Regular maintenance
manager.maintenance.run_cleanup()
manager.maintenance.optimise_indices()
manager.maintenance.validate_integrity()
```

### 4. Backup and Recovery

```python
# Backup critical data
manager.backup(
    types=["discoveries", "user"],
    destination="s3://backups/crystalyse/"
)

# Restore from backup
manager.restore(
    source="s3://backups/crystalyse/20240115/",
    types=["discoveries"]
)
```

## Monitoring and Analytics

### Memory Metrics

Track memory system performance:

```python
metrics = manager.get_metrics()
print(f"Total memories: {metrics.total_count}")
print(f"Storage used: {metrics.storage_gb} GB")
print(f"Query latency: {metrics.avg_latency_ms} ms")
print(f"Cache hit rate: {metrics.cache_hit_rate}%")
```

### Usage Analytics

Understand memory patterns:

```python
analytics = manager.get_analytics()
# Most accessed materials
# Common discovery types
# Peak usage times
# User engagement metrics
```

## Next Steps

- Explore [Session Management](sessions.md) for conversation handling
- Learn about [Agent Integration](agents.md) with memory systems
- Check [API Reference](../reference/memory/) for detailed documentation
- Read [Performance Guide](../guides/performance.md) for optimisation