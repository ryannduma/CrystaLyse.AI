# Example FastAPI WebSocket Backend for CrystaLyse.AI
# This demonstrates the core architecture for real-time agent transparency

from fastapi import FastAPI, WebSocket, WebSocketDisconnect, Depends
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel
from typing import Dict, Any, List, Optional, AsyncGenerator
from enum import Enum
import asyncio
import json
import time
import uuid
from datetime import datetime

app = FastAPI(title="CrystaLyse.AI WebSocket API")

# CORS middleware for development
app.add_middleware(
    CORSMiddleware,
    allow_origins=["http://localhost:3000"],  # React dev server
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Event Models
class EventType(Enum):
    # Agent Events
    REASONING_START = "reasoning_start"
    REASONING_UPDATE = "reasoning_update"
    REASONING_END = "reasoning_end"
    
    # Tool Events  
    TOOL_CALL_START = "tool_call_start"
    TOOL_CALL_PROGRESS = "tool_call_progress"
    TOOL_CALL_RESULT = "tool_call_result"
    
    # Structure Events
    STRUCTURE_GENERATED = "structure_generated"
    ENERGY_CALCULATED = "energy_calculated"
    VALIDATION_COMPLETE = "validation_complete"
    
    # Memory Events
    MEMORY_WRITE = "memory_write"
    MEMORY_READ = "memory_read"
    
    # System Events
    SESSION_START = "session_start"
    DISCOVERY_COMPLETE = "discovery_complete"
    ERROR = "error"

class AgentEvent(BaseModel):
    id: str
    timestamp: float
    type: EventType
    agent_name: str
    mode: str  # "creative" or "rigorous"
    data: Dict[str, Any]
    metadata: Optional[Dict[str, Any]] = None

# Connection Manager
class ConnectionManager:
    def __init__(self):
        self.active_connections: Dict[str, WebSocket] = {}
        
    async def connect(self, session_id: str, websocket: WebSocket):
        await websocket.accept()
        self.active_connections[session_id] = websocket
        print(f"✓ Connected to session {session_id}")
        
    async def disconnect(self, session_id: str):
        if session_id in self.active_connections:
            del self.active_connections[session_id]
            print(f"✗ Disconnected from session {session_id}")
        
    async def send_event(self, session_id: str, event: AgentEvent):
        if websocket := self.active_connections.get(session_id):
            try:
                await websocket.send_json(event.dict())
                print(f"📤 Sent {event.type.value} to {session_id}")
            except Exception as e:
                print(f"❌ Failed to send event: {e}")
                await self.disconnect(session_id)

manager = ConnectionManager()

# Mock Agent Service (simulates CrystaLyse.AI behaviour)
class MockCrystaLyseService:
    """Simulates the CrystaLyse.AI agent with realistic timing and events"""
    
    async def process_discovery_request(
        self,
        query: str,
        mode: str,
        session_id: str,
        event_callback: callable
    ) -> AsyncGenerator[AgentEvent, None]:
        """Simulate materials discovery workflow with realistic events"""
        
        # Start reasoning
        yield AgentEvent(
            id=str(uuid.uuid4()),
            timestamp=time.time(),
            type=EventType.REASONING_START,
            agent_name="CrystaLyse",
            mode=mode,
            data={
                "query": query,
                "reasoning": f"Analysing materials discovery request: '{query}'"
            }
        )
        
        await asyncio.sleep(1)  # Simulate thinking time
        
        # Determine material formulas to explore
        formulas = self._generate_formulas(query)
        
        yield AgentEvent(
            id=str(uuid.uuid4()),
            timestamp=time.time(),
            type=EventType.REASONING_UPDATE,
            agent_name="CrystaLyse",
            mode=mode,
            data={
                "reasoning": f"Generated {len(formulas)} candidate compositions for validation",
                "formulas": formulas
            }
        )
        
        # Process each formula
        for i, formula in enumerate(formulas):
            # SMACT Validation
            yield AgentEvent(
                id=str(uuid.uuid4()),
                timestamp=time.time(),
                type=EventType.TOOL_CALL_START,
                agent_name="CrystaLyse",
                mode=mode,
                data={
                    "tool": "SMACT",
                    "action": "validate_composition",
                    "formula": formula,
                    "progress": f"{i+1}/{len(formulas)}"
                }
            )
            
            await asyncio.sleep(0.5)  # Simulate SMACT time
            
            validation_result = self._mock_smact_validation(formula)
            
            yield AgentEvent(
                id=str(uuid.uuid4()),
                timestamp=time.time(),
                type=EventType.TOOL_CALL_RESULT,
                agent_name="CrystaLyse",
                mode=mode,
                data={
                    "tool": "SMACT",
                    "formula": formula,
                    "result": validation_result,
                    "valid": validation_result["charge_balanced"]
                }
            )
            
            if not validation_result["charge_balanced"]:
                continue
                
            # Chemeleon Structure Generation
            yield AgentEvent(
                id=str(uuid.uuid4()),
                timestamp=time.time(),
                type=EventType.TOOL_CALL_START,
                agent_name="CrystaLyse",
                mode=mode,
                data={
                    "tool": "Chemeleon",
                    "action": "generate_structure",
                    "formula": formula
                }
            )
            
            await asyncio.sleep(2)  # Simulate Chemeleon time
            
            structure = self._mock_chemeleon_structure(formula)
            
            yield AgentEvent(
                id=str(uuid.uuid4()),
                timestamp=time.time(),
                type=EventType.STRUCTURE_GENERATED,
                agent_name="CrystaLyse",
                mode=mode,
                data={
                    "tool": "Chemeleon",
                    "formula": formula,
                    "structure": structure
                }
            )
            
            # MACE Energy Calculation
            yield AgentEvent(
                id=str(uuid.uuid4()),
                timestamp=time.time(),
                type=EventType.TOOL_CALL_START,
                agent_name="CrystaLyse",
                mode=mode,
                data={
                    "tool": "MACE",
                    "action": "calculate_energy",
                    "formula": formula
                }
            )
            
            await asyncio.sleep(1.5)  # Simulate MACE time
            
            energy_result = self._mock_mace_energy(formula)
            
            yield AgentEvent(
                id=str(uuid.uuid4()),
                timestamp=time.time(),
                type=EventType.ENERGY_CALCULATED,
                agent_name="CrystaLyse",
                mode=mode,
                data={
                    "tool": "MACE",
                    "formula": formula,
                    "formation_energy": energy_result["formation_energy"],
                    "hull_distance": energy_result["hull_distance"],
                    "uncertainty": energy_result["uncertainty"]
                }
            )
        
        # Final reasoning and recommendations
        yield AgentEvent(
            id=str(uuid.uuid4()),
            timestamp=time.time(),
            type=EventType.REASONING_END,
            agent_name="CrystaLyse",
            mode=mode,
            data={
                "reasoning": "Completed computational analysis of all candidates",
                "summary": f"Validated {len(formulas)} materials with full computational workflow",
                "recommendations": self._generate_recommendations(formulas)
            }
        )
        
        # Signal completion
        yield AgentEvent(
            id=str(uuid.uuid4()),
            timestamp=time.time(),
            type=EventType.DISCOVERY_COMPLETE,
            agent_name="CrystaLyse",
            mode=mode,
            data={
                "total_materials": len(formulas),
                "valid_materials": len([f for f in formulas if "Fe" in f or "Li" in f]),  # Mock filter
                "elapsed_time": 10.5
            }
        )
    
    def _generate_formulas(self, query: str) -> List[str]:
        """Generate realistic formula candidates based on query"""
        if "battery" in query.lower():
            return ["LiFePO4", "LiMnPO4", "LiNiPO4", "NaFePO4", "LiCoO2"]
        elif "concrete" in query.lower():
            return ["Ca3Al2O6", "Ca2SiO4", "CaSiO3", "Ca(OH)2", "CaCO3"]
        elif "photocatalyst" in query.lower():
            return ["TiO2", "ZnO", "CdS", "BiVO4", "Ta3N5"]
        else:
            return ["LiFePO4", "TiO2", "CaO", "SiO2", "Al2O3"]
    
    def _mock_smact_validation(self, formula: str) -> Dict[str, Any]:
        """Mock SMACT validation results"""
        return {
            "charge_balanced": True,  # Most pass for demo
            "electronegativity_check": True,
            "ionic_radius_compatible": True,
            "oxidation_states": "valid",
            "probability": 0.85
        }
    
    def _mock_chemeleon_structure(self, formula: str) -> Dict[str, Any]:
        """Mock Chemeleon structure generation"""
        return {
            "space_group": "Pnma" if "PO4" in formula else "Fm-3m",
            "lattice_parameters": {
                "a": 10.2 + hash(formula) % 100 / 100,
                "b": 6.1 + hash(formula) % 50 / 100,
                "c": 4.7 + hash(formula) % 30 / 100,
                "alpha": 90.0,
                "beta": 90.0,
                "gamma": 90.0
            },
            "atom_positions": [
                {"element": "Li", "x": 0.0, "y": 0.0, "z": 0.0},
                {"element": "Fe", "x": 0.5, "y": 0.5, "z": 0.0},
                {"element": "P", "x": 0.25, "y": 0.25, "z": 0.5},
                {"element": "O", "x": 0.1, "y": 0.3, "z": 0.2}
            ],
            "volume": 286.5,
            "density": 3.62
        }
    
    def _mock_mace_energy(self, formula: str) -> Dict[str, Any]:
        """Mock MACE energy calculations"""
        base_energy = -3.2 - hash(formula) % 100 / 100
        return {
            "formation_energy": base_energy,
            "hull_distance": abs(hash(formula) % 50) / 1000,  # 0-0.05 eV
            "uncertainty": 0.05,
            "stable": abs(hash(formula) % 50) / 1000 < 0.03
        }
    
    def _generate_recommendations(self, formulas: List[str]) -> List[str]:
        """Generate synthesis recommendations"""
        return [
            f"Synthesis route for {formulas[0]}: Solid-state reaction at 650°C under Ar",
            f"Carbon coating recommended for improved conductivity",
            f"Optimal particle size: 100-200 nm for best electrochemical performance"
        ]

# Mock Memory Service
class MockMemoryService:
    def __init__(self):
        self.memories = []
    
    async def write_memory(self, session_id: str, memory_type: str, content: str):
        memory = {
            "id": str(uuid.uuid4()),
            "session_id": session_id,
            "type": memory_type,
            "content": content,
            "timestamp": time.time()
        }
        self.memories.append(memory)
        return memory
    
    async def search_memories(self, query: str, session_id: str) -> List[Dict[str, Any]]:
        # Simple keyword search for demo
        return [m for m in self.memories 
                if session_id in m["session_id"] and 
                any(word in m["content"].lower() for word in query.lower().split())]

# WebSocket endpoint
@app.websocket("/ws/discovery/{session_id}")
async def discovery_websocket(websocket: WebSocket, session_id: str):
    await manager.connect(session_id, websocket)
    
    agent_service = MockCrystaLyseService()
    memory_service = MockMemoryService()
    
    # Send session start event
    await manager.send_event(session_id, AgentEvent(
        id=str(uuid.uuid4()),
        timestamp=time.time(),
        type=EventType.SESSION_START,
        agent_name="CrystaLyse",
        mode="ready",
        data={"session_id": session_id, "capabilities": ["SMACT", "Chemeleon", "MACE"]}
    ))
    
    try:
        while True:
            # Receive message from client
            data = await websocket.receive_json()
            print(f"📥 Received: {data}")
            
            if data["type"] == "discovery_request":
                # Process discovery request with event streaming
                async def event_callback(event: AgentEvent):
                    await manager.send_event(session_id, event)
                    
                    # Store significant events in memory
                    if event.type in [EventType.REASONING_END, EventType.DISCOVERY_COMPLETE]:
                        await memory_service.write_memory(
                            session_id,
                            "working",
                            json.dumps(event.data)
                        )
                
                # Stream discovery events
                async for event in agent_service.process_discovery_request(
                    query=data["query"],
                    mode=data.get("mode", "creative"),
                    session_id=session_id,
                    event_callback=event_callback
                ):
                    await manager.send_event(session_id, event)
                    
            elif data["type"] == "memory_search":
                # Search memories
                results = await memory_service.search_memories(
                    query=data["query"],
                    session_id=session_id
                )
                
                await manager.send_event(session_id, AgentEvent(
                    id=str(uuid.uuid4()),
                    timestamp=time.time(),
                    type=EventType.MEMORY_READ,
                    agent_name="CrystaLyse",
                    mode="memory",
                    data={
                        "query": data["query"],
                        "results": results,
                        "count": len(results)
                    }
                ))
                
    except WebSocketDisconnect:
        await manager.disconnect(session_id)

# REST endpoints for additional functionality
@app.get("/api/health")
async def health_check():
    return {"status": "healthy", "service": "CrystaLyse.AI WebSocket API"}

@app.get("/api/sessions/{session_id}/status")
async def get_session_status(session_id: str):
    is_connected = session_id in manager.active_connections
    return {
        "session_id": session_id,
        "connected": is_connected,
        "connection_count": len(manager.active_connections)
    }

if __name__ == "__main__":
    import uvicorn
    print("🚀 Starting CrystaLyse.AI WebSocket Server...")
    uvicorn.run(app, host="0.0.0.0", port=8000, reload=True)