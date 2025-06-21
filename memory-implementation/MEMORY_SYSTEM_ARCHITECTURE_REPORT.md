# CrystaLyse.AI Memory System Architecture Report

**Date**: 20 June 2025  
**Author**: CrystaLyse.AI Development Team  
**Version**: 2.0 (Simplified Architecture)

## Executive Summary

This report documents the architectural evolution of the CrystaLyse.AI memory system, focusing on a simplified approach that removes external database dependencies (ICSD) in favour of a self-contained discovery knowledge base. The system now provides computational efficiency through caching and reasoning transparency through an agent scratchpad, while maintaining user context and building institutional knowledge over time.

## 1. Architectural Changes

### 1.1 Previous Architecture (Complex)
```
Memory System v1.0
├── External Dependencies
│   ├── ICSD (200,000+ structures)
│   ├── Local cache databases
│   └── Complex validation pipelines
├── Multiple search paths
└── High latency concerns
```

### 1.2 New Architecture (Simplified)
```
Memory System v2.0
├── Short-Term Memory
│   ├── DualWorkingMemory
│   │   ├── Computational Cache (performance)
│   │   └── Agent Scratchpad (transparency)
│   ├── Conversation Manager (Redis/local)
│   └── Session Context (user state)
│
├── Long-Term Memory
│   ├── Discovery Store (ChromaDB)
│   │   └── Agent's own discoveries only
│   ├── User Profiles (SQLite)
│   └── Knowledge Graph (Neo4j)
│
└── No External Databases
    └── Focused on user's research history
```

### 1.3 Key Simplifications

1. **Removed ICSD Integration**: Eliminated 200,000+ structure database
2. **Single Source of Truth**: Agent's discoveries ARE the knowledge base
3. **Reduced Latency**: No external database lookups
4. **Privacy-First**: User discoveries stay within their workspace

## 2. Where the System Shines

### 2.1 Dual Working Memory Innovation

The dual working memory system is the crown jewel of this architecture:

```python
class DualWorkingMemory:
    def __init__(self):
        self.computational_cache = WorkingMemory()  # Cache expensive calculations
        self.reasoning_scratchpad = AgentScratchpad()  # Transparent reasoning
```

**Why it shines**:
- **Performance**: Caches MACE, Chemeleon, SMACT calculations
- **Transparency**: Users can see agent's thought process
- **Trust Building**: Clear reasoning path in markdown files

### 2.2 Reasoning Transparency

The agent scratchpad provides unprecedented visibility:

```markdown
## 🎯 Current Plan (14:09:46)
1. Validate composition feasibility
2. Generate crystal structures
3. Calculate formation energies
4. Analyse stability

## 🧠 Reasoning Step (14:09:47)
NaCl is ionic. Expecting rock salt structure...

## ✅ Progress Update (14:09:48)
SMACT validation complete. Moving to structure generation...
```

**Benefits**:
- Users understand agent's approach
- Debugging is straightforward
- Builds trust through transparency

### 2.3 Organic Knowledge Growth

```python
# Session 1
discovery = {
    "formula": "Na₂FePO₄F",
    "formation_energy": -2.3,
    "session_id": "001",
    "constraints": ["Na-ion", "earth-abundant"]
}

# Session 10 (weeks later)
User: "What Na-ion cathodes have we explored?"
# Agent instantly recalls all previous Na-ion discoveries
```

**Why this matters**:
- Knowledge base grows with use
- Personalised to user's research
- No irrelevant external data

### 2.4 Seamless Continuity

```python
# Conversation resumes after days
Agent: "Continuing from our Na₂FePO₄F work last week, 
        I found that doping with Mn could improve capacity..."
```

## 3. Potential Blindsides & Testing Requirements

### 3.1 Memory Overflow Scenarios

**Risk**: What happens when vector store gets large?

**Testing Required**:
```python
# Test with 10,000+ discoveries
async def stress_test_vector_store():
    for i in range(10000):
        await memory.store_discovery({
            "formula": f"TestCompound{i}",
            "energy": random.uniform(-5, 0)
        })
    
    # Measure retrieval times
    start = time.time()
    results = await memory.search_similar("perovskite")
    assert time.time() - start < 0.5  # Must stay under 500ms
```

### 3.2 Scratchpad File Management

**Risk**: Scratchpad files accumulating on disk

**Testing Required**:
- Archival strategy for old sessions
- Disk space monitoring
- Cleanup routines

### 3.3 Cache Invalidation

**Risk**: Stale computational cache

**Testing Required**:
```python
# Ensure cache expiry works
def test_cache_expiry():
    cache.max_age_hours = 0.001  # 3.6 seconds
    cache.store_result("test", {"data": "value"})
    time.sleep(5)
    assert cache.get_result("test") is None
```

### 3.4 Context Window Limitations

**Risk**: Memory context exceeding LLM limits

**Testing Required**:
```python
# Test with large conversation histories
def test_context_summarisation():
    # Add 100 messages
    for i in range(100):
        conv_manager.add_message(...)
    
    # Ensure summary stays within token limits
    summary = conv_manager.get_context_summary(max_tokens=1000)
    assert count_tokens(summary) <= 1000
```

## 4. OpenAI Agents SDK Integration

### 4.1 Memory-Enhanced Agent Creation

```python
from openai_agents import Agent
from crystalyse_memory import create_dual_memory, get_all_tools

# Create memory-enhanced agent
async def create_memory_agent(session_id: str, user_id: str):
    # Initialise memory
    dual_memory = create_dual_memory(session_id, user_id)
    
    # Get all memory tools
    memory_tools = get_all_tools()
    
    # Create agent with memory context
    agent = Agent(
        model="gpt-4",
        tools=memory_tools,
        agent_data={"dual_working_memory": dual_memory}
    )
    
    # Add dynamic instructions
    agent.instructions += f"""
    You have access to working memory and scratchpad.
    Current session: {session_id}
    Use write_to_scratchpad for complex reasoning.
    Check cached results before expensive calculations.
    """
    
    return agent
```

### 4.2 Tool Integration Pattern

```python
@function_tool
def search_previous_discoveries(query: str, context) -> str:
    """Search through your previous material discoveries."""
    dual_memory = context.agent_data["dual_working_memory"]
    
    # Log to scratchpad
    dual_memory.log_reasoning_step(f"Searching for: {query}")
    
    # Search discoveries
    results = dual_memory.search_discoveries(query)
    
    # Cache for performance
    dual_memory.cache_result("search", results, query=query)
    
    return format_discoveries(results)
```

### 4.3 Trust-Building Features

**1. Scratchpad Visibility**
```python
# User can always check reasoning
GET /api/session/{id}/scratchpad
Returns: Full markdown of agent's thought process
```

**2. Tool Usage Logging**
```python
# Every tool use is logged
dual_memory.log_tool_usage("smact", 
    parameters={"formula": "NaCl"},
    result_summary="Feasible"
)
```

**3. Progress Indicators**
```python
# Real-time progress updates
await stream_to_user("🔬 Validating composition...")
await stream_to_user("🏗️ Generating structures...")
await stream_to_user("⚡ Calculating energies...")
```

## 5. Implementation Recommendations

### 5.1 Immediate Actions

1. **Remove ICSD References**
   ```python
   # Delete these files:
   - icsd_integration.py
   - icsd_memory_tools.py
   - icsd_cache.db
   
   # Remove from schemas:
   - "icsd_id" fields
   - ICSD validation steps
   ```

2. **Simplify Discovery Schema**
   ```python
   discovery_schema = {
       "formula": str,
       "formation_energy": float,
       "properties": dict,
       "synthesis_route": str,
       "session_id": str,
       "user_id": str,
       "timestamp": datetime,
       "constraints_met": list
   }
   ```

3. **Update Memory Tools**
   - Remove ICSD-specific tools
   - Focus on user discovery search
   - Simplify validation logic

### 5.2 Testing Strategy

```python
# Comprehensive test suite
class TestMemorySystem:
    async def test_discovery_storage_retrieval(self):
        """Test full discovery lifecycle"""
        
    async def test_session_continuity(self):
        """Test memory across sessions"""
        
    async def test_performance_under_load(self):
        """Test with 10k+ discoveries"""
        
    async def test_scratchpad_transparency(self):
        """Ensure reasoning is captured"""
        
    async def test_cache_efficiency(self):
        """Verify cache hit rates >80%"""
```

### 5.3 Monitoring & Metrics

```python
# Key metrics to track
metrics = {
    "cache_hit_rate": prometheus.Gauge(),
    "discovery_retrieval_time": prometheus.Histogram(),
    "scratchpad_write_frequency": prometheus.Counter(),
    "memory_context_size": prometheus.Gauge(),
    "user_satisfaction": prometheus.Gauge()  # From feedback
}
```

## 6. Trust-Building Through Transparency

### 6.1 User-Facing Features

1. **Live Scratchpad View**
   ```html
   <!-- Real-time reasoning display -->
   <div id="agent-thinking">
     <h3>🧠 Agent's Current Thinking</h3>
     <pre>{{ scratchpad_content }}</pre>
   </div>
   ```

2. **Discovery Timeline**
   ```python
   # Show research progression
   GET /api/user/{id}/discovery-timeline
   Returns: Chronological list of all discoveries
   ```

3. **Session Replay**
   ```python
   # Users can replay any session
   GET /api/session/{id}/replay
   Returns: Full conversation with scratchpad states
   ```

### 6.2 Explainability Features

```python
# Agent explains its memory usage
Agent: "I'm checking our previous work on Na-ion cathodes..."
       "Found 3 similar materials from sessions in January..."
       "Using cached MACE calculation from 2 hours ago..."
```

## 7. Conclusion

The simplified memory architecture removes unnecessary complexity while preserving the core value: building a personalised knowledge base of materials discoveries. By eliminating ICSD, we've created a system that is:

- **Faster**: No external database lookups
- **Simpler**: Focused on user's research only  
- **More Transparent**: Clear reasoning paths
- **Privacy-Preserving**: User data stays local
- **Trust-Building**: Full visibility into agent thinking

The dual working memory system (computational cache + reasoning scratchpad) provides both performance and transparency, making it ideal for scientific research where trust and reproducibility are paramount.

## 8. Next Steps

1. **Immediate**: Remove ICSD integration code
2. **Week 1**: Update memory tools and schemas
3. **Week 2**: Implement comprehensive test suite
4. **Week 3**: Deploy monitoring and metrics
5. **Month 1**: Gather user feedback and iterate

This architecture positions CrystaLyse.AI as a trustworthy research assistant that learns and grows with each user, building institutional knowledge while maintaining complete transparency in its reasoning process.