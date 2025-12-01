# Memory System

## Overview

Crystalyse v1.2 implements a sophisticated 4-layer memory system using a "simple files + smart context" philosophy. This replaces complex database architectures with efficient file-based storage.

## Architecture

### 1. Session Memory
**Location**: In-memory  
**Purpose**: Current conversation context  
**Retention**: Last 10 interactions by default

```python
from crystalyse.memory import SessionMemory

session = SessionMemory(max_interactions=10)
session.add_interaction("user", "Find perovskites for solar cells")
session.add_interaction("assistant", "I'll search for lead-free perovskites...")
```

### 2. Discovery Cache
**Location**: `~/.crystalyse/discoveries.json`  
**Purpose**: Expensive computational results  
**Benefits**: Avoids re-computation of MACE energies, SMACT validations

```json
{
  "LiCoO2": {
    "formation_energy": -2.45,
    "structure_source": "chemeleon",
    "validation_status": "valid",
    "timestamp": "2025-07-27T10:30:00Z"
  }
}
```

### 3. User Memory
**Location**: `~/.crystalyse/memory_{user_id}.md`  
**Purpose**: User preferences, research interests, important notes  
**Format**: Human-readable Markdown

```markdown
# Research Preferences - researcher1

## Materials of Interest
- Lead-free perovskites for solar applications
- High-entropy alloys for catalysis
- Solid electrolytes for batteries

## Preferred Analysis Parameters
- Formation energy threshold: < -1.0 eV
- Stability requirement: Above convex hull
- Synthesis temperature: < 800°C

## Important Discoveries
- Ba2NbTaO5N showed promising photovoltaic properties
- CaTiO3 family needs further investigation
```

### 4. Cross-Session Context
**Location**: `~/.crystalyse/insights_{user_id}.md`  
**Purpose**: Auto-generated research summaries and patterns  
**Update**: Weekly automatic generation

```markdown
# Research Insights - researcher1
Generated: 2025-07-27

## Recent Focus Areas
- 67% queries related to battery materials
- 23% focus on solar applications
- 10% structural analysis

## Successful Discovery Patterns
- Oxide perovskites consistently show good stability
- Quaternary compositions often more stable than ternary
- MACE predictions align well with experimental trends

## Recommended Next Steps
- Explore Ti-based perovskites for photovoltaics
- Investigate high-entropy oxide stability
- Consider defect chemistry in promising candidates
```

## Memory Tools Integration

Eight function tools provide seamless memory access for the OpenAI Agents SDK:

### Core Tools
```python
@function_tool
def save_to_memory(fact: str, section: str = "Important Notes") -> str:
    """Save important information to user memory"""

@function_tool  
def search_memory(query: str) -> str:
    """Search user memory for relevant information"""

@function_tool
def save_discovery(formula: str, properties: str) -> str:
    """Cache computational results to avoid re-computation"""

@function_tool
def search_discoveries(query: str) -> str:
    """Find previously computed materials"""
```

### Advanced Tools
```python
@function_tool
def get_session_context() -> str:
    """Retrieve current session conversation history"""

@function_tool
def save_research_note(topic: str, content: str) -> str:
    """Save structured research observations"""

@function_tool
def get_cross_session_insights() -> str:
    """Access research patterns and recommendations"""

@function_tool
def update_user_preferences(preferences: dict) -> str:
    """Update user research preferences"""
```

## Usage Examples

### Caching Expensive Calculations
```bash
# First query - performs full computation
User: "Calculate formation energy of LiCoO2"
Agent: [Calls MACE, saves result to cache]

# Later query - retrieves from cache
User: "What was the formation energy of LiCoO2?"
Agent: [Retrieves cached result in <100ms]
```

### Cross-Session Learning
```bash
# Session 1: Battery research
User: "Find cathode materials for Li-ion batteries"
Agent: [Saves research focus and successful patterns]

# Session 2: Weeks later
User: "I need more battery materials"
Agent: "Based on your previous research into Li-ion cathodes, 
        I recommend exploring these Ti-based alternatives..."
```

### Personalised Recommendations  
```bash
# System learns user preferences
User consistently asks about:
- Formation energies < -1.0 eV
- Earth-abundant elements
- Synthesis temperatures < 800°C

# Future recommendations automatically apply these constraints
```

## File Management

### Automatic Cleanup
- Discovery cache: 30-day expiration for unused entries
- User memory: Manual management, human-readable format
- Session memory: Automatic cleanup on session end
- Cross-session insights: Weekly regeneration

### Backup and Sync
- Files are human-readable and version-control friendly
- Simple backup: copy `~/.crystalyse/` directory
- Cloud sync: Works with Dropbox, Google Drive, etc.

### Performance Characteristics
- **Memory retrieval**: <100ms average
- **Cache hit rate**: >80% for repeated queries
- **Storage efficiency**: ~1MB per 1000 materials
- **Search speed**: <50ms for memory queries