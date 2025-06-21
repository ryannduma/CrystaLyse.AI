# crystalyse_memory/long_term/discovery_store.py
"""
Discovery Store for CrystaLyse.AI Memory System

Vector database for storing and semantically searching agent's material discoveries.
Uses ChromaDB for fast semantic search and persistent storage.
"""

from typing import Dict, List, Optional, Any, Tuple
from datetime import datetime
import json
import logging
from pathlib import Path
import hashlib

try:
    import chromadb
    from chromadb.config import Settings
    CHROMADB_AVAILABLE = True
except ImportError:
    CHROMADB_AVAILABLE = False
    chromadb = None

logger = logging.getLogger(__name__)


class DiscoveryStore:
    """
    Vector store for agent's material discoveries.
    
    Stores discoveries with semantic embeddings for fast similarity search.
    Each discovery includes formula, properties, synthesis info, and context.
    """
    
    def __init__(self, persist_directory: Optional[Path] = None, embedding_model: str = "all-MiniLM-L6-v2"):
        """
        Initialise discovery store.
        
        Args:
            persist_directory: Directory for persistent storage
            embedding_model: Model for generating embeddings
        """
        if not CHROMADB_AVAILABLE:
            raise ImportError("ChromaDB not available. Install with: pip install chromadb")
        
        self.persist_dir = persist_directory or Path("./memory/discoveries")
        self.persist_dir.mkdir(parents=True, exist_ok=True)
        
        self.embedding_model = embedding_model
        
        # Initialize ChromaDB client
        self.client = chromadb.PersistentClient(
            path=str(self.persist_dir),
            settings=Settings(
                anonymized_telemetry=False,
                allow_reset=True
            )
        )
        
        # Get or create collection
        self.collection = self.client.get_or_create_collection(
            name="material_discoveries",
            metadata={"description": "Agent's material discoveries with semantic embeddings"}
        )
        
        logger.info(f"DiscoveryStore initialised with {self.collection.count()} existing discoveries")
    
    def _generate_discovery_id(self, discovery: Dict[str, Any]) -> str:
        """Generate unique ID for discovery."""
        # Use formula + session + timestamp for uniqueness
        id_string = f"{discovery['formula']}_{discovery['session_id']}_{discovery['timestamp']}"
        return hashlib.md5(id_string.encode()).hexdigest()[:16]
    
    def _create_discovery_text(self, discovery: Dict[str, Any]) -> str:
        """Create searchable text representation of discovery."""
        parts = [
            f"Formula: {discovery['formula']}",
            f"Application: {discovery.get('application', 'general materials discovery')}",
        ]
        
        # Add properties
        properties = discovery.get('properties', {})
        if properties:
            prop_text = []
            for key, value in properties.items():
                if isinstance(value, (int, float)):
                    prop_text.append(f"{key}: {value}")
                else:
                    prop_text.append(f"{key}: {value}")
            parts.append(f"Properties: {', '.join(prop_text)}")
        
        # Add formation energy if available
        if discovery.get('formation_energy'):
            parts.append(f"Formation energy: {discovery['formation_energy']} eV/atom")
        
        # Add band gap if available
        if discovery.get('band_gap'):
            parts.append(f"Band gap: {discovery['band_gap']} eV")
        
        # Add synthesis information
        if discovery.get('synthesis_route'):
            parts.append(f"Synthesis: {discovery['synthesis_route']}")
        
        # Add constraints met
        if discovery.get('constraints_met'):
            parts.append(f"Meets constraints: {', '.join(discovery['constraints_met'])}")
        
        # Add discovery context
        if discovery.get('discovery_context'):
            parts.append(f"Context: {discovery['discovery_context']}")
        
        return " ".join(parts)
    
    def _create_metadata(self, discovery: Dict[str, Any]) -> Dict[str, Any]:
        """Create metadata for ChromaDB storage."""
        metadata = {
            "formula": discovery["formula"],
            "user_id": discovery["user_id"],
            "session_id": discovery["session_id"],
            "timestamp": discovery["timestamp"],
            "application": discovery.get("application", ""),
            "synthesis_route": discovery.get("synthesis_route", ""),
            "discovery_method": discovery.get("discovery_method", ""),
        }
        
        # Add numerical properties as metadata
        if discovery.get('formation_energy') is not None:
            metadata["formation_energy"] = float(discovery['formation_energy'])
        
        if discovery.get('band_gap') is not None:
            metadata["band_gap"] = float(discovery['band_gap'])
        
        # Add constraints as JSON string
        if discovery.get('constraints_met'):
            metadata["constraints_met"] = json.dumps(discovery['constraints_met'])
        
        # Add properties as JSON string
        if discovery.get('properties'):
            metadata["properties"] = json.dumps(discovery['properties'])
        
        return metadata
    
    async def store_discovery(self, discovery: Dict[str, Any]) -> str:
        """
        Store a new material discovery.
        
        Args:
            discovery: Discovery data with formula, properties, context, etc.
            
        Returns:
            Discovery ID
        """
        # Add timestamp if not present
        if 'timestamp' not in discovery:
            discovery['timestamp'] = datetime.now().isoformat()
        
        # Generate unique ID
        discovery_id = self._generate_discovery_id(discovery)
        
        # Create searchable text
        text = self._create_discovery_text(discovery)
        
        # Create metadata
        metadata = self._create_metadata(discovery)
        
        try:
            # Check if discovery already exists
            existing = self.collection.get(ids=[discovery_id])
            if existing['ids']:
                logger.debug(f"Discovery {discovery_id} already exists, updating...")
                # Update existing discovery
                self.collection.update(
                    ids=[discovery_id],
                    documents=[text],
                    metadatas=[metadata]
                )
            else:
                # Add new discovery
                self.collection.add(
                    ids=[discovery_id],
                    documents=[text],
                    metadatas=[metadata]
                )
            
            logger.info(f"Stored discovery: {discovery['formula']} (ID: {discovery_id})")
            return discovery_id
            
        except Exception as e:
            logger.error(f"Failed to store discovery {discovery['formula']}: {e}")
            raise
    
    async def search_discoveries(
        self,
        query: str,
        user_id: Optional[str] = None,
        n_results: int = 10,
        filter_constraints: Optional[Dict[str, Any]] = None
    ) -> List[Dict[str, Any]]:
        """
        Search through stored discoveries using semantic similarity.
        
        Args:
            query: Search query (natural language)
            user_id: Filter by specific user
            n_results: Maximum number of results
            filter_constraints: Additional metadata filters
            
        Returns:
            List of matching discoveries with similarity scores
        """
        try:
            # Build where clause for filtering
            where_clause = {}
            if user_id:
                where_clause["user_id"] = user_id
            
            if filter_constraints:
                where_clause.update(filter_constraints)
            
            # Perform semantic search
            results = self.collection.query(
                query_texts=[query],
                n_results=n_results,
                where=where_clause if where_clause else None,
                include=["metadatas", "documents", "distances"]
            )
            
            # Format results
            discoveries = []
            for i, doc_id in enumerate(results['ids'][0]):
                metadata = results['metadatas'][0][i]
                document = results['documents'][0][i]
                distance = results['distances'][0][i]
                
                # Parse JSON fields
                constraints_met = []
                if metadata.get('constraints_met'):
                    try:
                        constraints_met = json.loads(metadata['constraints_met'])
                    except (json.JSONDecodeError, TypeError):
                        pass
                
                properties = {}
                if metadata.get('properties'):
                    try:
                        properties = json.loads(metadata['properties'])
                    except (json.JSONDecodeError, TypeError):
                        pass
                
                discovery = {
                    "id": doc_id,
                    "formula": metadata["formula"],
                    "user_id": metadata["user_id"],
                    "session_id": metadata["session_id"],
                    "timestamp": metadata["timestamp"],
                    "application": metadata.get("application", ""),
                    "synthesis_route": metadata.get("synthesis_route", ""),
                    "formation_energy": metadata.get("formation_energy"),
                    "band_gap": metadata.get("band_gap"),
                    "constraints_met": constraints_met,
                    "properties": properties,
                    "discovery_context": document,
                    "similarity_score": 1.0 - distance,  # Convert distance to similarity
                    "discovery_method": metadata.get("discovery_method", "")
                }
                
                discoveries.append(discovery)
            
            logger.debug(f"Found {len(discoveries)} discoveries for query: {query}")
            return discoveries
            
        except Exception as e:
            logger.error(f"Failed to search discoveries: {e}")
            return []
    
    async def get_discovery_by_id(self, discovery_id: str) -> Optional[Dict[str, Any]]:
        """Get specific discovery by ID."""
        try:
            result = self.collection.get(
                ids=[discovery_id],
                include=["metadatas", "documents"]
            )
            
            if not result['ids']:
                return None
            
            metadata = result['metadatas'][0]
            document = result['documents'][0]
            
            # Parse JSON fields
            constraints_met = []
            if metadata.get('constraints_met'):
                try:
                    constraints_met = json.loads(metadata['constraints_met'])
                except (json.JSONDecodeError, TypeError):
                    pass
            
            properties = {}
            if metadata.get('properties'):
                try:
                    properties = json.loads(metadata['properties'])
                except (json.JSONDecodeError, TypeError):
                    pass
            
            return {
                "id": discovery_id,
                "formula": metadata["formula"],
                "user_id": metadata["user_id"],
                "session_id": metadata["session_id"],
                "timestamp": metadata["timestamp"],
                "application": metadata.get("application", ""),
                "synthesis_route": metadata.get("synthesis_route", ""),
                "formation_energy": metadata.get("formation_energy"),
                "band_gap": metadata.get("band_gap"),
                "constraints_met": constraints_met,
                "properties": properties,
                "discovery_context": document,
                "discovery_method": metadata.get("discovery_method", "")
            }
            
        except Exception as e:
            logger.error(f"Failed to get discovery {discovery_id}: {e}")
            return None
    
    async def get_user_discoveries(
        self,
        user_id: str,
        limit: int = 50,
        sort_by: str = "timestamp"
    ) -> List[Dict[str, Any]]:
        """
        Get all discoveries for a specific user.
        
        Args:
            user_id: User identifier
            limit: Maximum number of discoveries
            sort_by: Sort criteria (timestamp, formula)
            
        Returns:
            List of user's discoveries
        """
        try:
            result = self.collection.get(
                where={"user_id": user_id},
                limit=limit,
                include=["metadatas", "documents"]
            )
            
            discoveries = []
            for i, doc_id in enumerate(result['ids']):
                metadata = result['metadatas'][i]
                document = result['documents'][i]
                
                # Parse JSON fields
                constraints_met = []
                if metadata.get('constraints_met'):
                    try:
                        constraints_met = json.loads(metadata['constraints_met'])
                    except (json.JSONDecodeError, TypeError):
                        pass
                
                properties = {}
                if metadata.get('properties'):
                    try:
                        properties = json.loads(metadata['properties'])
                    except (json.JSONDecodeError, TypeError):
                        pass
                
                discovery = {
                    "id": doc_id,
                    "formula": metadata["formula"],
                    "user_id": metadata["user_id"],
                    "session_id": metadata["session_id"],
                    "timestamp": metadata["timestamp"],
                    "application": metadata.get("application", ""),
                    "synthesis_route": metadata.get("synthesis_route", ""),
                    "formation_energy": metadata.get("formation_energy"),
                    "band_gap": metadata.get("band_gap"),
                    "constraints_met": constraints_met,
                    "properties": properties,
                    "discovery_context": document,
                    "discovery_method": metadata.get("discovery_method", "")
                }
                
                discoveries.append(discovery)
            
            # Sort results
            if sort_by == "timestamp":
                discoveries.sort(key=lambda x: x["timestamp"], reverse=True)
            elif sort_by == "formula":
                discoveries.sort(key=lambda x: x["formula"])
            
            logger.debug(f"Retrieved {len(discoveries)} discoveries for user {user_id}")
            return discoveries
            
        except Exception as e:
            logger.error(f"Failed to get user discoveries: {e}")
            return []
    
    async def find_similar_materials(
        self,
        formula: str,
        user_id: Optional[str] = None,
        n_results: int = 5
    ) -> List[Dict[str, Any]]:
        """Find materials similar to given formula."""
        query = f"material similar to {formula} with comparable properties and structure"
        
        # Exclude the exact formula
        results = await self.search_discoveries(
            query=query,
            user_id=user_id,
            n_results=n_results + 1  # Get extra in case exact match is included
        )
        
        # Filter out exact matches
        similar = [r for r in results if r["formula"] != formula]
        return similar[:n_results]
    
    async def get_discoveries_by_application(
        self,
        application: str,
        user_id: Optional[str] = None,
        n_results: int = 10
    ) -> List[Dict[str, Any]]:
        """Get discoveries for specific application."""
        return await self.search_discoveries(
            query=f"materials for {application}",
            user_id=user_id,
            n_results=n_results
        )
    
    async def get_discoveries_by_constraint(
        self,
        constraint: str,
        user_id: Optional[str] = None,
        n_results: int = 10
    ) -> List[Dict[str, Any]]:
        """Get discoveries that meet specific constraint."""
        return await self.search_discoveries(
            query=f"materials that {constraint}",
            user_id=user_id,
            n_results=n_results
        )
    
    def get_collection_stats(self) -> Dict[str, Any]:
        """Get statistics about the discovery collection."""
        try:
            count = self.collection.count()
            
            # Get some sample metadata to analyze
            sample = self.collection.get(
                limit=min(100, count),
                include=["metadatas"]
            )
            
            # Analyze users and applications
            users = set()
            applications = set()
            methods = set()
            
            for metadata in sample['metadatas']:
                if metadata.get('user_id'):
                    users.add(metadata['user_id'])
                if metadata.get('application'):
                    applications.add(metadata['application'])
                if metadata.get('discovery_method'):
                    methods.add(metadata['discovery_method'])
            
            return {
                "total_discoveries": count,
                "unique_users": len(users),
                "unique_applications": len(applications),
                "discovery_methods": len(methods),
                "sample_applications": list(applications)[:10],
                "sample_methods": list(methods)[:10],
                "persist_directory": str(self.persist_dir),
                "embedding_model": self.embedding_model
            }
            
        except Exception as e:
            logger.error(f"Failed to get collection stats: {e}")
            return {"error": str(e)}
    
    async def delete_discovery(self, discovery_id: str) -> bool:
        """Delete a specific discovery."""
        try:
            self.collection.delete(ids=[discovery_id])
            logger.info(f"Deleted discovery: {discovery_id}")
            return True
        except Exception as e:
            logger.error(f"Failed to delete discovery {discovery_id}: {e}")
            return False
    
    async def delete_user_discoveries(self, user_id: str) -> int:
        """Delete all discoveries for a user."""
        try:
            # Get all user discovery IDs
            result = self.collection.get(
                where={"user_id": user_id},
                include=["metadatas"]
            )
            
            if result['ids']:
                self.collection.delete(ids=result['ids'])
                logger.info(f"Deleted {len(result['ids'])} discoveries for user {user_id}")
                return len(result['ids'])
            
            return 0
            
        except Exception as e:
            logger.error(f"Failed to delete user discoveries: {e}")
            return 0
    
    def clear_all_discoveries(self) -> bool:
        """Clear all discoveries (use with caution)."""
        try:
            self.client.delete_collection("material_discoveries")
            self.collection = self.client.create_collection(
                name="material_discoveries",
                metadata={"description": "Agent's material discoveries with semantic embeddings"}
            )
            logger.warning("Cleared all discoveries from collection")
            return True
        except Exception as e:
            logger.error(f"Failed to clear discoveries: {e}")
            return False