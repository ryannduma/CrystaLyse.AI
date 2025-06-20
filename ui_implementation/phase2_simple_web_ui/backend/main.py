# CrystaLyse.AI Simple Web UI Backend
# Phase 2: Memory-first approach with REST API

from fastapi import FastAPI, HTTPException, Depends
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel
from typing import Dict, Any, List, Optional
import asyncio
import json
import time
import uuid
from datetime import datetime
import re

app = FastAPI(
    title="CrystaLyse.AI Web API",
    description="Simple REST API for materials discovery with memory integration",
    version="2.0.0"
)

# CORS for development
app.add_middleware(
    CORSMiddleware,
    allow_origins=["http://localhost:3000"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Data Models
class DiscoveryRequest(BaseModel):
    query: str
    mode: str = "creative"  # "creative" or "rigorous"
    session_id: Optional[str] = None

class Material(BaseModel):
    formula: str
    formation_energy: Optional[float] = None
    hull_distance: Optional[float] = None
    space_group: Optional[str] = None
    lattice_params: Optional[Dict[str, float]] = None
    stability: Optional[str] = None

class ToolUsage(BaseModel):
    tool_name: str
    action: str
    result: str
    duration: Optional[float] = None

class DiscoveryResult(BaseModel):
    session_id: str
    query: str
    mode: str
    materials: List[Material]
    tool_usage: List[ToolUsage]
    reasoning_summary: str
    recommendations: List[str]
    total_time: float
    timestamp: datetime

class Memory(BaseModel):
    id: str
    session_id: str
    type: str  # "working", "short_term", "long_term"
    content: str
    metadata: Dict[str, Any]
    timestamp: datetime
    relevance_score: Optional[float] = None

class MemorySearchRequest(BaseModel):
    query: str
    memory_type: Optional[str] = None
    limit: int = 10

# Mock Memory Service (replace with actual implementation)
class MockMemoryService:
    def __init__(self):
        self.memories: List[Memory] = []
        self.sessions: Dict[str, List[Memory]] = {}
    
    async def write_memory(
        self, 
        session_id: str, 
        memory_type: str, 
        content: str, 
        metadata: Dict[str, Any] = None
    ) -> Memory:
        memory = Memory(
            id=str(uuid.uuid4()),
            session_id=session_id,
            type=memory_type,
            content=content,
            metadata=metadata or {},
            timestamp=datetime.now()
        )
        
        self.memories.append(memory)
        if session_id not in self.sessions:
            self.sessions[session_id] = []
        self.sessions[session_id].append(memory)
        
        return memory
    
    async def get_session_memories(self, session_id: str) -> List[Memory]:
        return self.sessions.get(session_id, [])
    
    async def semantic_search(self, query: str, limit: int = 10) -> List[Memory]:
        # Simple keyword matching for demo (replace with pgvector)
        keywords = query.lower().split()
        results = []
        
        for memory in self.memories:
            content_lower = memory.content.lower()
            score = sum(1 for keyword in keywords if keyword in content_lower)
            
            if score > 0:
                memory.relevance_score = score / len(keywords)
                results.append(memory)
        
        # Sort by relevance and return top results
        results.sort(key=lambda x: x.relevance_score, reverse=True)
        return results[:limit]

# Mock Agent Service (replace with actual CrystaLyse integration)
class MockCrystaLyseAgent:
    def __init__(self, memory_service: MockMemoryService):
        self.memory_service = memory_service
    
    async def process_discovery(
        self, 
        query: str, 
        mode: str, 
        session_id: str
    ) -> DiscoveryResult:
        """
        Process discovery request - this would integrate with your actual
        CrystaLyse agent and OpenAI Agents SDK
        """
        start_time = time.time()
        
        # Log query to working memory
        await self.memory_service.write_memory(
            session_id,
            "working",
            f"Discovery request: {query}",
            {"mode": mode, "timestamp": start_time}
        )
        
        # Simulate agent processing
        await asyncio.sleep(2)  # Replace with actual agent call
        
        # Mock agent output (replace with actual agent response)
        mock_output = self._generate_mock_agent_output(query, mode)
        
        # Parse structured results
        result = self._parse_agent_output(mock_output, query, mode, session_id, start_time)
        
        # Save to short-term memory
        await self.memory_service.write_memory(
            session_id,
            "short_term",
            f"Discovery completed: {len(result.materials)} materials found",
            {
                "query": query,
                "mode": mode,
                "materials_count": len(result.materials),
                "result_id": session_id
            }
        )
        
        return result
    
    def _generate_mock_agent_output(self, query: str, mode: str) -> str:
        """Generate realistic agent output based on query type"""
        if "battery" in query.lower():
            return """
            I'll discover novel battery cathode materials using computational analysis.

            SMACT validation for LiFe0.9Mn0.1PO4:
            - Charge balanced: ✓ Valid
            - Ionic radii compatible: ✓ Compatible
            - Electronegativity spread: 1.8 (acceptable)

            Chemeleon structure generation:
            - Space group: Pnma (orthorhombic olivine)
            - Lattice parameters: a=10.34Å, b=6.01Å, c=4.69Å
            - Volume: 291.2 Ų

            MACE energy calculation:
            - Formation energy: -3.45 ± 0.05 eV/atom
            - Hull distance: 0.02 eV/atom (stable)
            - Predicted voltage: 3.52 V vs Li/Li+

            Recommendation: Mn doping improves thermal stability while maintaining high voltage.
            Synthesis: Solid-state reaction at 650°C under Ar atmosphere.
            """
        
        return "Mock agent output for query: " + query
    
    def _parse_agent_output(
        self, 
        output: str, 
        query: str, 
        mode: str, 
        session_id: str, 
        start_time: float
    ) -> DiscoveryResult:
        """Parse agent output into structured data"""
        
        # Extract materials (simplified parsing)
        materials = self._extract_materials(output)
        
        # Extract tool usage
        tool_usage = self._extract_tool_usage(output)
        
        # Extract reasoning
        reasoning = self._extract_reasoning(output)
        
        # Extract recommendations
        recommendations = self._extract_recommendations(output)
        
        return DiscoveryResult(
            session_id=session_id,
            query=query,
            mode=mode,
            materials=materials,
            tool_usage=tool_usage,
            reasoning_summary=reasoning,
            recommendations=recommendations,
            total_time=time.time() - start_time,
            timestamp=datetime.now()
        )
    
    def _extract_materials(self, output: str) -> List[Material]:
        """Extract material information from agent output"""
        materials = []
        
        # Simple regex patterns (improve based on actual agent output format)
        formula_pattern = r'([A-Z][a-z]?(?:\d*\.?\d*[A-Z][a-z]?\d*\.?\d*)*(?:O|N|S|P|F|Cl)\d*\.?\d*)'
        energy_pattern = r'Formation energy:\s*(-?\d+\.?\d*)\s*[±]\s*(\d+\.?\d*)\s*eV'
        space_group_pattern = r'Space group:\s*([A-Za-z0-9/-]+)'
        
        formulas = re.findall(formula_pattern, output)
        energies = re.findall(energy_pattern, output)
        space_groups = re.findall(space_group_pattern, output)
        
        for i, formula in enumerate(formulas[:5]):  # Limit to 5 materials
            material = Material(
                formula=formula,
                formation_energy=float(energies[i][0]) if i < len(energies) else None,
                space_group=space_groups[i] if i < len(space_groups) else None,
                stability="stable" if i < len(energies) and float(energies[i][0]) < -2.0 else "metastable"
            )
            materials.append(material)
        
        return materials
    
    def _extract_tool_usage(self, output: str) -> List[ToolUsage]:
        """Extract tool usage information"""
        tools = []
        
        if "SMACT" in output:
            tools.append(ToolUsage(
                tool_name="SMACT",
                action="validate_composition",
                result="Valid composition with charge balance confirmed"
            ))
        
        if "Chemeleon" in output:
            tools.append(ToolUsage(
                tool_name="Chemeleon",
                action="generate_structure",
                result="Crystal structure generated successfully"
            ))
        
        if "MACE" in output:
            tools.append(ToolUsage(
                tool_name="MACE",
                action="calculate_energy",
                result="Formation energy and stability calculated"
            ))
        
        return tools
    
    def _extract_reasoning(self, output: str) -> str:
        """Extract reasoning summary"""
        lines = output.split('\n')
        reasoning_lines = [line for line in lines if 
                          'discover' in line.lower() or 
                          'analysis' in line.lower() or
                          'recommend' in line.lower()]
        
        return ' '.join(reasoning_lines[:3]) if reasoning_lines else "Computational materials discovery completed."
    
    def _extract_recommendations(self, output: str) -> List[str]:
        """Extract synthesis recommendations"""
        recommendations = []
        lines = output.split('\n')
        
        for line in lines:
            if 'Recommendation:' in line or 'Synthesis:' in line:
                recommendations.append(line.strip())
        
        if not recommendations:
            recommendations = ["Further experimental validation recommended"]
        
        return recommendations

# Service instances
memory_service = MockMemoryService()
agent_service = MockCrystaLyseAgent(memory_service)

# API Endpoints

@app.get("/api/health")
async def health_check():
    return {
        "status": "healthy",
        "service": "CrystaLyse.AI Web API",
        "version": "2.0.0",
        "memory_count": len(memory_service.memories)
    }

@app.post("/api/discovery", response_model=DiscoveryResult)
async def submit_discovery(request: DiscoveryRequest):
    """Submit a materials discovery request"""
    try:
        session_id = request.session_id or str(uuid.uuid4())
        
        result = await agent_service.process_discovery(
            query=request.query,
            mode=request.mode,
            session_id=session_id
        )
        
        return result
        
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Discovery failed: {str(e)}")

@app.get("/api/sessions/{session_id}/memories", response_model=List[Memory])
async def get_session_memories(session_id: str):
    """Get all memories for a session"""
    memories = await memory_service.get_session_memories(session_id)
    return memories

@app.post("/api/memory/search", response_model=List[Memory])
async def search_memory(request: MemorySearchRequest):
    """Search memories using semantic similarity"""
    results = await memory_service.semantic_search(
        query=request.query,
        limit=request.limit
    )
    return results

@app.get("/api/sessions", response_model=List[str])
async def list_sessions():
    """List all active sessions"""
    return list(memory_service.sessions.keys())

@app.post("/api/sessions/{session_id}/export")
async def export_session(session_id: str):
    """Export session data for download"""
    memories = await memory_service.get_session_memories(session_id)
    
    export_data = {
        "session_id": session_id,
        "export_timestamp": datetime.now().isoformat(),
        "memories": [memory.dict() for memory in memories],
        "total_memories": len(memories)
    }
    
    return export_data

# Development endpoints
@app.post("/api/dev/populate-sample-data")
async def populate_sample_data():
    """Populate with sample discovery data for development"""
    
    sample_queries = [
        "Find high-capacity lithium battery cathodes",
        "Novel photocatalysts for water splitting",
        "Self-healing concrete additives",
        "High-temperature supercapacitor materials"
    ]
    
    for i, query in enumerate(sample_queries):
        session_id = f"sample-session-{i}"
        await agent_service.process_discovery(query, "creative", session_id)
    
    return {"message": f"Created {len(sample_queries)} sample discoveries"}

if __name__ == "__main__":
    import uvicorn
    print("🚀 Starting CrystaLyse.AI Simple Web API...")
    print("📚 Memory-first approach with structured results")
    print("🔗 Ready for frontend integration")
    uvicorn.run(app, host="0.0.0.0", port=8000, reload=True)