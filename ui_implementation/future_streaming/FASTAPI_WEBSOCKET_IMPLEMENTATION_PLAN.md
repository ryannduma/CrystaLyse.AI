# CrystaLyse.AI FastAPI + WebSocket Implementation Plan

## Executive Summary

This plan outlines the architecture for a real-time web interface that provides transparency into CrystaLyse.AI's computational materials discovery process. Based on analysis of the comprehensive stress test data, the system will stream agent reasoning, tool usage, and results through WebSocket connections while maintaining scientific credibility.

## 1. Architecture Overview

### 1.1 Core Components

```
┌─────────────────────────────────────────────────────────────────┐
│                         Frontend (React/Vue)                     │
├─────────────────────────────────────────────────────────────────┤
│                     WebSocket Connection Layer                   │
├─────────────────────────────────────────────────────────────────┤
│                         FastAPI Backend                          │
├─────────────────────────────────────────────────────────────────┤
│  Agent Layer  │  MCP Servers  │  Memory Store  │  Vis Engine   │
└─────────────────────────────────────────────────────────────────┘
```

### 1.2 Technology Stack

- **Backend**: FastAPI 0.104+ with Python 3.11+
- **WebSocket**: Native FastAPI WebSocket support
- **Frontend**: React 18+ with TypeScript (or Vue 3 Composition API)
- **3D Visualisation**: Three.js for crystal structures
- **State Management**: Zustand/Pinia for reactive state
- **Database**: PostgreSQL with pgvector for memory embeddings
- **Cache**: Redis for session management
- **Message Queue**: Redis Streams for event buffering

## 2. WebSocket Event Architecture

### 2.1 Event Types

Based on the stress test analysis, we need these WebSocket event types:

```python
from enum import Enum
from pydantic import BaseModel
from typing import Optional, Dict, Any, List

class EventType(Enum):
    # Agent Events
    REASONING_START = "reasoning_start"
    REASONING_UPDATE = "reasoning_update"
    REASONING_END = "reasoning_end"
    
    # Tool Events
    TOOL_CALL_START = "tool_call_start"
    TOOL_CALL_PROGRESS = "tool_call_progress"
    TOOL_CALL_RESULT = "tool_call_result"
    
    # Memory Events
    MEMORY_WRITE = "memory_write"
    MEMORY_READ = "memory_read"
    MEMORY_SEARCH = "memory_search"
    
    # Result Events
    STRUCTURE_GENERATED = "structure_generated"
    ENERGY_CALCULATED = "energy_calculated"
    VALIDATION_COMPLETE = "validation_complete"
    
    # System Events
    SESSION_START = "session_start"
    SESSION_END = "session_end"
    ERROR = "error"

class AgentEvent(BaseModel):
    id: str
    timestamp: float
    type: EventType
    agent_name: str
    mode: str  # "creative" or "rigorous"
    data: Dict[str, Any]
    metadata: Optional[Dict[str, Any]] = None
```

### 2.2 Event Stream Design

```python
# WebSocket endpoint design
@app.websocket("/ws/discovery/{session_id}")
async def discovery_websocket(websocket: WebSocket, session_id: str):
    await websocket.accept()
    
    # Create agent session
    session = await create_discovery_session(session_id)
    
    # Setup event streaming
    async with session.event_stream() as stream:
        async for event in stream:
            # Transform agent events to UI events
            ui_event = transform_agent_event(event)
            await websocket.send_json(ui_event.dict())
```

## 3. Backend Implementation

### 3.1 FastAPI Application Structure

```
crystalyse-api/
├── app/
│   ├── __init__.py
│   ├── main.py
│   ├── api/
│   │   ├── __init__.py
│   │   ├── websocket.py
│   │   ├── discovery.py
│   │   ├── visualisation.py
│   │   └── memory.py
│   ├── core/
│   │   ├── __init__.py
│   │   ├── config.py
│   │   ├── security.py
│   │   └── events.py
│   ├── services/
│   │   ├── __init__.py
│   │   ├── agent_service.py
│   │   ├── mcp_service.py
│   │   ├── memory_service.py
│   │   └── visualisation_service.py
│   ├── models/
│   │   ├── __init__.py
│   │   ├── events.py
│   │   ├── materials.py
│   │   └── memory.py
│   └── utils/
│       ├── __init__.py
│       ├── cif_parser.py
│       └── structure_converter.py
├── tests/
├── requirements.txt
└── docker-compose.yml
```

### 3.2 Core Services Implementation

#### Agent Service Integration

```python
# app/services/agent_service.py
from openai import AsyncOpenAI
from agents.mcp.server import MCPServerStdio
import asyncio
from typing import AsyncGenerator

class CrystaLyseAgentService:
    def __init__(self):
        self.client = AsyncOpenAI()
        self.mcp_servers = {
            'smact': MCPServerStdio(...),
            'chemeleon': MCPServerStdio(...),
            'mace': MCPServerStdio(...)
        }
        
    async def process_discovery_request(
        self,
        query: str,
        mode: str,
        event_callback: callable
    ) -> AsyncGenerator[AgentEvent, None]:
        """Process materials discovery request with event streaming"""
        
        # Emit reasoning start
        await event_callback(AgentEvent(
            id=generate_id(),
            timestamp=time.time(),
            type=EventType.REASONING_START,
            agent_name="CrystaLyse",
            mode=mode,
            data={"query": query}
        ))
        
        # Setup agent with event hooks
        agent = await self._create_agent(mode)
        agent.on_tool_call = lambda tool, args: event_callback(
            self._create_tool_event(tool, args)
        )
        
        # Process query
        async for item in agent.process_async(query):
            yield self._transform_to_event(item)
```

#### Memory Service

```python
# app/services/memory_service.py
from pgvector.asyncpg import register_vector
import asyncpg
from typing import List, Dict, Any

class MemoryService:
    def __init__(self, db_url: str):
        self.db_url = db_url
        self.embedding_model = "text-embedding-ada-002"
        
    async def init_db(self):
        self.pool = await asyncpg.create_pool(self.db_url)
        async with self.pool.acquire() as conn:
            await register_vector(conn)
            await conn.execute('''
                CREATE TABLE IF NOT EXISTS memories (
                    id UUID PRIMARY KEY,
                    session_id TEXT NOT NULL,
                    type TEXT NOT NULL,  -- working, short_term, long_term
                    content TEXT NOT NULL,
                    embedding vector(1536),
                    metadata JSONB,
                    created_at TIMESTAMP DEFAULT NOW()
                )
            ''')
    
    async def write_memory(
        self,
        session_id: str,
        memory_type: str,
        content: str,
        metadata: Dict[str, Any]
    ):
        embedding = await self._generate_embedding(content)
        async with self.pool.acquire() as conn:
            await conn.execute('''
                INSERT INTO memories (id, session_id, type, content, embedding, metadata)
                VALUES ($1, $2, $3, $4, $5, $6)
            ''', uuid.uuid4(), session_id, memory_type, content, embedding, metadata)
    
    async def search_memories(
        self,
        query: str,
        session_id: str,
        limit: int = 10
    ) -> List[Dict[str, Any]]:
        query_embedding = await self._generate_embedding(query)
        async with self.pool.acquire() as conn:
            rows = await conn.fetch('''
                SELECT content, metadata, 
                       1 - (embedding <=> $1) as similarity
                FROM memories
                WHERE session_id = $2
                ORDER BY embedding <=> $1
                LIMIT $3
            ''', query_embedding, session_id, limit)
        return [dict(row) for row in rows]
```

### 3.3 WebSocket Handler

```python
# app/api/websocket.py
from fastapi import WebSocket, WebSocketDisconnect
from app.services import CrystaLyseAgentService, MemoryService
import asyncio
import json

class ConnectionManager:
    def __init__(self):
        self.active_connections: Dict[str, WebSocket] = {}
        
    async def connect(self, session_id: str, websocket: WebSocket):
        await websocket.accept()
        self.active_connections[session_id] = websocket
        
    async def disconnect(self, session_id: str):
        self.active_connections.pop(session_id, None)
        
    async def send_event(self, session_id: str, event: AgentEvent):
        if websocket := self.active_connections.get(session_id):
            await websocket.send_json(event.dict())

manager = ConnectionManager()

@app.websocket("/ws/discovery/{session_id}")
async def discovery_websocket(websocket: WebSocket, session_id: str):
    await manager.connect(session_id, websocket)
    
    agent_service = CrystaLyseAgentService()
    memory_service = MemoryService(settings.DATABASE_URL)
    
    try:
        while True:
            # Receive message from client
            data = await websocket.receive_json()
            
            if data["type"] == "discovery_request":
                # Process discovery request
                async def event_callback(event: AgentEvent):
                    await manager.send_event(session_id, event)
                    
                    # Log to memory if significant
                    if event.type in [EventType.REASONING_END, EventType.TOOL_CALL_RESULT]:
                        await memory_service.write_memory(
                            session_id,
                            "working",
                            json.dumps(event.data),
                            {"event_type": event.type.value}
                        )
                
                # Stream results
                async for event in agent_service.process_discovery_request(
                    query=data["query"],
                    mode=data.get("mode", "creative"),
                    event_callback=event_callback
                ):
                    await manager.send_event(session_id, event)
                    
            elif data["type"] == "memory_search":
                # Search memories
                results = await memory_service.search_memories(
                    query=data["query"],
                    session_id=session_id
                )
                await websocket.send_json({
                    "type": "memory_results",
                    "data": results
                })
                
    except WebSocketDisconnect:
        await manager.disconnect(session_id)
```

## 4. Frontend Implementation

### 4.1 React Component Architecture

```typescript
// components/DiscoveryInterface.tsx
import React, { useState, useEffect } from 'react';
import { useWebSocket } from '../hooks/useWebSocket';
import { AgentReasoningPanel } from './AgentReasoningPanel';
import { ToolUsagePanel } from './ToolUsagePanel';
import { ResultsPanel } from './ResultsPanel';
import { CrystalViewer } from './CrystalViewer';
import { MemoryPanel } from './MemoryPanel';

interface DiscoveryInterfaceProps {
  sessionId: string;
}

export const DiscoveryInterface: React.FC<DiscoveryInterfaceProps> = ({ sessionId }) => {
  const { events, sendMessage, connectionState } = useWebSocket(
    `/ws/discovery/${sessionId}`
  );
  
  const [activeTools, setActiveTools] = useState<Map<string, ToolCall>>(new Map());
  const [reasoning, setReasoning] = useState<ReasoningState>({ active: false, content: '' });
  const [results, setResults] = useState<DiscoveryResult[]>([]);
  const [memories, setMemories] = useState<Memory[]>([]);
  
  useEffect(() => {
    // Process incoming events
    events.forEach(event => {
      switch (event.type) {
        case 'reasoning_start':
          setReasoning({ active: true, content: event.data.content });
          break;
          
        case 'tool_call_start':
          setActiveTools(prev => new Map(prev).set(event.data.toolId, {
            name: event.data.toolName,
            status: 'running',
            args: event.data.args
          }));
          break;
          
        case 'structure_generated':
          // Update crystal viewer
          break;
          
        case 'memory_write':
          setMemories(prev => [...prev, event.data.memory]);
          break;
      }
    });
  }, [events]);
  
  return (
    <div className="discovery-interface">
      <div className="main-panel">
        <QueryInput onSubmit={(query) => sendMessage({ type: 'discovery_request', query })} />
        <AgentReasoningPanel reasoning={reasoning} />
        <ToolUsagePanel activeTools={activeTools} />
      </div>
      
      <div className="results-panel">
        <CrystalViewer structures={results.map(r => r.structure)} />
        <ResultsPanel results={results} />
      </div>
      
      <div className="memory-panel">
        <MemoryPanel memories={memories} onSearch={(query) => 
          sendMessage({ type: 'memory_search', query })
        } />
      </div>
    </div>
  );
};
```

### 4.2 Real-time Visualisation Components

```typescript
// components/CrystalViewer.tsx
import React, { useRef, useEffect } from 'react';
import * as THREE from 'three';
import { parseCIF } from '../utils/cifParser';

interface CrystalViewerProps {
  structures: CrystalStructure[];
  activeIndex: number;
}

export const CrystalViewer: React.FC<CrystalViewerProps> = ({ structures, activeIndex }) => {
  const mountRef = useRef<HTMLDivElement>(null);
  const sceneRef = useRef<THREE.Scene>();
  
  useEffect(() => {
    if (!structures[activeIndex]) return;
    
    // Parse structure data
    const atomData = parseCIF(structures[activeIndex].cifData);
    
    // Create/update Three.js scene
    if (!sceneRef.current) {
      const scene = new THREE.Scene();
      const camera = new THREE.PerspectiveCamera(75, 1, 0.1, 1000);
      const renderer = new THREE.WebGLRenderer({ antialias: true });
      
      // Add atoms and bonds
      atomData.atoms.forEach(atom => {
        const geometry = new THREE.SphereGeometry(atom.radius);
        const material = new THREE.MeshPhongMaterial({ 
          color: atom.color,
          specular: 0x111111,
          shininess: 100
        });
        const mesh = new THREE.Mesh(geometry, material);
        mesh.position.set(atom.x, atom.y, atom.z);
        scene.add(mesh);
      });
      
      // Add bonds
      atomData.bonds.forEach(bond => {
        const geometry = new THREE.CylinderGeometry(0.1, 0.1, bond.length);
        const material = new THREE.MeshPhongMaterial({ color: 0x666666 });
        const mesh = new THREE.Mesh(geometry, material);
        
        // Position and orient bond
        mesh.position.copy(bond.center);
        mesh.lookAt(bond.end);
        scene.add(mesh);
      });
      
      // Lighting
      const ambientLight = new THREE.AmbientLight(0xffffff, 0.6);
      const directionalLight = new THREE.DirectionalLight(0xffffff, 0.4);
      scene.add(ambientLight, directionalLight);
      
      mountRef.current?.appendChild(renderer.domElement);
      sceneRef.current = scene;
    }
    
    // Animate structure changes
    animateStructureTransition(sceneRef.current, atomData);
    
  }, [structures, activeIndex]);
  
  return (
    <div className="crystal-viewer" ref={mountRef}>
      <div className="viewer-controls">
        <button onClick={() => rotateView('x')}>Rotate X</button>
        <button onClick={() => rotateView('y')}>Rotate Y</button>
        <button onClick={() => exportStructure()}>Export CIF</button>
      </div>
    </div>
  );
};
```

## 5. Memory System Integration

### 5.1 Memory Architecture

```python
# app/models/memory.py
from enum import Enum
from pydantic import BaseModel
from typing import Optional, List, Dict, Any
from datetime import datetime

class MemoryType(Enum):
    WORKING = "working"      # Current session scratchpad
    SHORT_TERM = "short_term"  # Recent sessions (7 days)
    LONG_TERM = "long_term"   # Persistent knowledge

class Memory(BaseModel):
    id: str
    session_id: str
    type: MemoryType
    content: str
    context: Dict[str, Any]  # Material formulas, energies, etc.
    embedding: Optional[List[float]] = None
    created_at: datetime
    accessed_at: datetime
    relevance_score: float = 1.0
    
class MemoryOperation(BaseModel):
    operation: str  # "write", "read", "search", "consolidate"
    memory_type: MemoryType
    content: Optional[str] = None
    query: Optional[str] = None
    results: Optional[List[Memory]] = None
```

### 5.2 Memory UI Components

```typescript
// components/MemoryPanel.tsx
import React from 'react';
import { Memory, MemoryType } from '../types';

interface MemoryPanelProps {
  memories: Memory[];
  onSearch: (query: string) => void;
}

export const MemoryPanel: React.FC<MemoryPanelProps> = ({ memories, onSearch }) => {
  const groupedMemories = groupMemoriesByType(memories);
  
  return (
    <div className="memory-panel">
      <h3>Agent Memory</h3>
      
      {/* Working Memory - Scratchpad */}
      <div className="memory-section working-memory">
        <h4>Working Memory (Current Session)</h4>
        <div className="scratchpad">
          {groupedMemories.working.map(mem => (
            <MemoryItem key={mem.id} memory={mem} highlight />
          ))}
        </div>
      </div>
      
      {/* Short-term Memory */}
      <div className="memory-section short-term">
        <h4>Short-term Memory</h4>
        <MemoryList memories={groupedMemories.shortTerm} />
      </div>
      
      {/* Long-term Memory */}
      <div className="memory-section long-term">
        <h4>Long-term Memory</h4>
        <MemorySearch onSearch={onSearch} />
        <MemoryList memories={groupedMemories.longTerm} />
      </div>
    </div>
  );
};
```

## 6. Real-time Features

### 6.1 Progress Tracking

```python
# app/services/progress_tracker.py
class ProgressTracker:
    def __init__(self, websocket_manager):
        self.manager = websocket_manager
        self.active_tasks = {}
        
    async def start_task(self, session_id: str, task_id: str, task_type: str, total_steps: int):
        self.active_tasks[task_id] = {
            "type": task_type,
            "total_steps": total_steps,
            "completed_steps": 0,
            "status": "running"
        }
        
        await self.manager.send_event(session_id, AgentEvent(
            type=EventType.TASK_START,
            data={
                "task_id": task_id,
                "task_type": task_type,
                "total_steps": total_steps
            }
        ))
    
    async def update_progress(self, session_id: str, task_id: str, step: int, details: str):
        if task := self.active_tasks.get(task_id):
            task["completed_steps"] = step
            
            await self.manager.send_event(session_id, AgentEvent(
                type=EventType.TASK_PROGRESS,
                data={
                    "task_id": task_id,
                    "progress": step / task["total_steps"],
                    "details": details
                }
            ))
```

### 6.2 Error Handling and Recovery

```python
# app/core/error_handler.py
class AgentErrorHandler:
    async def handle_tool_error(self, session_id: str, tool_name: str, error: Exception):
        await self.manager.send_event(session_id, AgentEvent(
            type=EventType.ERROR,
            data={
                "error_type": "tool_failure",
                "tool_name": tool_name,
                "message": str(error),
                "recovery_suggestions": self._get_recovery_suggestions(tool_name, error)
            }
        ))
    
    def _get_recovery_suggestions(self, tool_name: str, error: Exception) -> List[str]:
        if tool_name == "smact":
            return ["Try simpler composition", "Check element oxidation states"]
        elif tool_name == "chemeleon":
            return ["Reduce structure complexity", "Try different space group"]
        elif tool_name == "mace":
            return ["Use smaller unit cell", "Check convergence parameters"]
        return ["Retry with modified parameters"]
```

## 7. Deployment Architecture

### 7.1 Docker Compose Setup

```yaml
# docker-compose.yml
version: '3.8'

services:
  api:
    build: .
    ports:
      - "8000:8000"
    environment:
      - DATABASE_URL=postgresql://user:pass@db:5432/crystalyse
      - REDIS_URL=redis://redis:6379
      - OPENAI_API_KEY=${OPENAI_API_KEY}
    depends_on:
      - db
      - redis
      
  db:
    image: pgvector/pgvector:pg15
    environment:
      - POSTGRES_DB=crystalyse
      - POSTGRES_USER=user
      - POSTGRES_PASSWORD=pass
    volumes:
      - postgres_data:/var/lib/postgresql/data
      
  redis:
    image: redis:7-alpine
    volumes:
      - redis_data:/data
      
  nginx:
    image: nginx:alpine
    ports:
      - "80:80"
      - "443:443"
    volumes:
      - ./nginx.conf:/etc/nginx/nginx.conf
      - ./ssl:/etc/nginx/ssl
    depends_on:
      - api

volumes:
  postgres_data:
  redis_data:
```

### 7.2 Scaling Considerations

```python
# app/core/scaling.py
from redis import asyncio as aioredis
import asyncio

class SessionManager:
    """Manage distributed sessions across multiple workers"""
    
    def __init__(self, redis_url: str):
        self.redis = aioredis.from_url(redis_url)
        self.pubsub = self.redis.pubsub()
        
    async def broadcast_event(self, session_id: str, event: AgentEvent):
        """Broadcast event to all connected clients"""
        channel = f"session:{session_id}"
        await self.redis.publish(channel, event.json())
        
    async def subscribe_to_session(self, session_id: str):
        """Subscribe to session events"""
        channel = f"session:{session_id}"
        await self.pubsub.subscribe(channel)
        
        async for message in self.pubsub.listen():
            if message["type"] == "message":
                yield AgentEvent.parse_raw(message["data"])
```

## 8. Security Considerations

### 8.1 Authentication and Authorisation

```python
# app/core/security.py
from fastapi import HTTPException, Depends
from fastapi.security import HTTPBearer, HTTPAuthorizationCredentials
import jwt

security = HTTPBearer()

async def verify_token(credentials: HTTPAuthorizationCredentials = Depends(security)):
    token = credentials.credentials
    try:
        payload = jwt.decode(token, settings.SECRET_KEY, algorithms=["HS256"])
        return payload["user_id"]
    except jwt.InvalidTokenError:
        raise HTTPException(status_code=401, detail="Invalid token")

# WebSocket authentication
async def verify_websocket_token(token: str) -> str:
    try:
        payload = jwt.decode(token, settings.SECRET_KEY, algorithms=["HS256"])
        return payload["user_id"]
    except:
        return None
```

## 9. Performance Optimisation

### 9.1 Event Batching

```python
# app/utils/event_batcher.py
class EventBatcher:
    def __init__(self, batch_size: int = 10, max_wait: float = 0.1):
        self.batch_size = batch_size
        self.max_wait = max_wait
        self.buffer = []
        self.last_flush = time.time()
        
    async def add_event(self, event: AgentEvent):
        self.buffer.append(event)
        
        if len(self.buffer) >= self.batch_size or \
           time.time() - self.last_flush > self.max_wait:
            await self.flush()
    
    async def flush(self):
        if self.buffer:
            batch = self.buffer[:]
            self.buffer.clear()
            self.last_flush = time.time()
            
            # Send batched events
            await self.send_batch(batch)
```

### 9.2 Structure Data Optimisation

```python
# app/utils/structure_optimiser.py
import numpy as np
from typing import Dict, List

class StructureOptimiser:
    """Optimise structure data for web transmission"""
    
    def compress_structure(self, structure_data: Dict) -> Dict:
        """Compress structure data for efficient transmission"""
        
        # Convert coordinates to typed arrays
        positions = np.array(structure_data["positions"])
        
        # Quantise positions to reduce precision
        quantised = np.round(positions * 1000) / 1000
        
        # Delta encode for better compression
        deltas = np.diff(quantised, axis=0, prepend=0)
        
        return {
            "format": "compressed",
            "deltas": deltas.flatten().tolist(),
            "atoms": structure_data["atoms"],
            "cell": structure_data["cell"]
        }
```

## 10. Testing Strategy

### 10.1 WebSocket Testing

```python
# tests/test_websocket.py
import pytest
from httpx import AsyncClient
from fastapi.testclient import TestClient
import asyncio

@pytest.mark.asyncio
async def test_discovery_websocket_flow():
    async with AsyncClient(app=app, base_url="http://test") as client:
        with client.websocket_connect("/ws/discovery/test-session") as websocket:
            # Send discovery request
            websocket.send_json({
                "type": "discovery_request",
                "query": "Find novel battery materials",
                "mode": "creative"
            })
            
            # Collect events
            events = []
            start_time = asyncio.get_event_loop().time()
            
            while asyncio.get_event_loop().time() - start_time < 30:
                try:
                    message = websocket.receive_json(timeout=1)
                    events.append(message)
                    
                    if message["type"] == "discovery_complete":
                        break
                except:
                    continue
            
            # Verify event sequence
            assert any(e["type"] == "reasoning_start" for e in events)
            assert any(e["type"] == "tool_call_start" for e in events)
            assert any(e["type"] == "structure_generated" for e in events)
```

## Implementation Timeline

**Phase 1 (Weeks 1-2)**: Basic WebSocket infrastructure
- FastAPI setup with WebSocket endpoints
- Basic event streaming
- Simple frontend to display events

**Phase 2 (Weeks 3-4)**: Agent integration
- Connect OpenAI Agents SDK
- Implement tool call monitoring
- Add progress tracking

**Phase 3 (Weeks 5-6)**: Visualisation
- Three.js crystal viewer
- Real-time structure updates
- Energy/property graphs

**Phase 4 (Weeks 7-8)**: Memory system
- PostgreSQL + pgvector setup
- Memory UI components
- Search functionality

**Phase 5 (Weeks 9-10)**: Polish and optimisation
- Performance tuning
- Error handling
- Documentation

This architecture provides the real-time transparency needed while maintaining scientific rigour and scalability for the CrystaLyse.AI platform.