# crystalyse_memory/long_term/knowledge_graph.py
"""
Material Knowledge Graph for CrystaLyse.AI Memory System

Neo4j-based graph database for storing relationships between discovered materials,
their properties, synthesis routes, and applications.
"""

from typing import Dict, List, Optional, Any, Tuple
from datetime import datetime
import logging
import json
import asyncio

try:
    from neo4j import AsyncGraphDatabase, AsyncDriver
    NEO4J_AVAILABLE = True
except ImportError:
    NEO4J_AVAILABLE = False
    AsyncGraphDatabase = None
    AsyncDriver = None

logger = logging.getLogger(__name__)


class MaterialKnowledgeGraph:
    """
    Graph database for material relationships and knowledge.
    
    Stores materials as nodes with properties as attributes,
    connected by relationships like SIMILAR_TO, SYNTHESIZED_BY,
    USED_FOR, CONTAINS_ELEMENT, etc.
    """
    
    def __init__(
        self,
        uri: str = "bolt://localhost:7687",
        username: str = "neo4j",
        password: str = "password",
        database: str = "neo4j"
    ):
        """
        Initialise knowledge graph.
        
        Args:
            uri: Neo4j database URI
            username: Database username
            password: Database password
            database: Database name
        """
        if not NEO4J_AVAILABLE:
            raise ImportError("Neo4j driver not available. Install with: pip install neo4j")
        
        self.uri = uri
        self.username = username
        self.password = password
        self.database = database
        self.driver: Optional[AsyncDriver] = None
        
        logger.info(f"MaterialKnowledgeGraph configured for: {uri}")
    
    async def initialize(self) -> bool:
        """Initialize connection and create constraints."""
        try:
            self.driver = AsyncGraphDatabase.driver(
                self.uri,
                auth=(self.username, self.password)
            )
            
            # Test connection
            await self.driver.verify_connectivity()
            
            # Create constraints and indices
            await self._create_constraints()
            
            logger.info("MaterialKnowledgeGraph initialized successfully")
            return True
            
        except Exception as e:
            logger.error(f"Failed to initialize MaterialKnowledgeGraph: {e}")
            return False
    
    async def close(self):
        """Close database connection."""
        if self.driver:
            await self.driver.close()
    
    async def _create_constraints(self):
        """Create database constraints and indices."""
        constraints = [
            # Unique constraints
            "CREATE CONSTRAINT material_formula IF NOT EXISTS FOR (m:Material) REQUIRE m.formula IS UNIQUE",
            "CREATE CONSTRAINT element_symbol IF NOT EXISTS FOR (e:Element) REQUIRE e.symbol IS UNIQUE",
            "CREATE CONSTRAINT application_name IF NOT EXISTS FOR (a:Application) REQUIRE a.name IS UNIQUE",
            "CREATE CONSTRAINT synthesis_method IF NOT EXISTS FOR (s:SynthesisMethod) REQUIRE s.method IS UNIQUE",
            "CREATE CONSTRAINT user_id IF NOT EXISTS FOR (u:User) REQUIRE u.user_id IS UNIQUE",
            
            # Indices for performance
            "CREATE INDEX material_formation_energy IF NOT EXISTS FOR (m:Material) ON (m.formation_energy)",
            "CREATE INDEX material_band_gap IF NOT EXISTS FOR (m:Material) ON (m.band_gap)",
            "CREATE INDEX material_discovered_at IF NOT EXISTS FOR (m:Material) ON (m.discovered_at)",
            "CREATE INDEX discovery_session IF NOT EXISTS FOR (m:Material) ON (m.session_id)",
        ]
        
        async with self.driver.session(database=self.database) as session:
            for constraint in constraints:
                try:
                    await session.run(constraint)
                except Exception as e:
                    # Constraint might already exist, that's ok
                    logger.debug(f"Constraint creation note: {e}")
    
    async def add_material_discovery(self, discovery: Dict[str, Any]) -> bool:
        """
        Add a discovered material to the knowledge graph.
        
        Args:
            discovery: Discovery data with formula, properties, context
            
        Returns:
            True if added successfully
        """
        try:
            async with self.driver.session(database=self.database) as session:
                # Create or update material node
                await session.run("""
                    MERGE (m:Material {formula: $formula})
                    ON CREATE SET
                        m.discovered_at = $discovered_at,
                        m.discovery_id = $discovery_id,
                        m.user_id = $user_id,
                        m.session_id = $session_id,
                        m.formation_energy = $formation_energy,
                        m.band_gap = $band_gap,
                        m.synthesis_route = $synthesis_route,
                        m.application = $application,
                        m.properties = $properties,
                        m.discovery_method = $discovery_method
                    ON MATCH SET
                        m.last_seen = $discovered_at,
                        m.formation_energy = COALESCE($formation_energy, m.formation_energy),
                        m.band_gap = COALESCE($band_gap, m.band_gap),
                        m.synthesis_route = COALESCE($synthesis_route, m.synthesis_route),
                        m.application = COALESCE($application, m.application)
                """, {
                    'formula': discovery['formula'],
                    'discovered_at': discovery.get('timestamp', datetime.now().isoformat()),
                    'discovery_id': discovery.get('id', ''),
                    'user_id': discovery['user_id'],
                    'session_id': discovery['session_id'],
                    'formation_energy': discovery.get('formation_energy'),
                    'band_gap': discovery.get('band_gap'),
                    'synthesis_route': discovery.get('synthesis_route', ''),
                    'application': discovery.get('application', ''),
                    'properties': json.dumps(discovery.get('properties', {})),
                    'discovery_method': discovery.get('discovery_method', 'computational')
                })
                
                # Create user node and relationship
                await session.run("""
                    MERGE (u:User {user_id: $user_id})
                    WITH u
                    MATCH (m:Material {formula: $formula})
                    MERGE (u)-[:DISCOVERED]->(m)
                """, {
                    'user_id': discovery['user_id'],
                    'formula': discovery['formula']
                })
                
                # Add element relationships
                await self._add_element_relationships(session, discovery['formula'])
                
                # Add application relationship
                if discovery.get('application'):
                    await self._add_application_relationship(session, discovery['formula'], discovery['application'])
                
                # Add synthesis relationship
                if discovery.get('synthesis_route'):
                    await self._add_synthesis_relationship(session, discovery['formula'], discovery['synthesis_route'])
                
                logger.debug(f"Added material {discovery['formula']} to knowledge graph")
                return True
                
        except Exception as e:
            logger.error(f"Failed to add material discovery: {e}")
            return False
    
    async def _add_element_relationships(self, session, formula: str):
        """Add relationships between material and its constituent elements."""
        # Simple element extraction (can be enhanced)
        import re
        elements = re.findall(r'([A-Z][a-z]?)', formula)
        
        for element in set(elements):  # Remove duplicates
            await session.run("""
                MERGE (e:Element {symbol: $element})
                WITH e
                MATCH (m:Material {formula: $formula})
                MERGE (m)-[:CONTAINS_ELEMENT]->(e)
            """, {'element': element, 'formula': formula})
    
    async def _add_application_relationship(self, session, formula: str, application: str):
        """Add relationship between material and application."""
        await session.run("""
            MERGE (a:Application {name: $application})
            WITH a
            MATCH (m:Material {formula: $formula})
            MERGE (m)-[:USED_FOR]->(a)
        """, {'application': application.lower(), 'formula': formula})
    
    async def _add_synthesis_relationship(self, session, formula: str, synthesis_route: str):
        """Add relationship between material and synthesis method."""
        await session.run("""
            MERGE (s:SynthesisMethod {method: $method})
            WITH s
            MATCH (m:Material {formula: $formula})
            MERGE (m)-[:SYNTHESIZED_BY]->(s)
        """, {'method': synthesis_route.lower(), 'formula': formula})
    
    async def find_similar_materials(
        self,
        formula: str,
        user_id: Optional[str] = None,
        similarity_types: Optional[List[str]] = None,
        limit: int = 10
    ) -> List[Dict[str, Any]]:
        """
        Find materials similar to given formula.
        
        Args:
            formula: Reference material formula
            user_id: Filter by specific user's discoveries
            similarity_types: Types of similarity to consider
            limit: Maximum results
            
        Returns:
            List of similar materials with relationships
        """
        try:
            # Default similarity types
            if similarity_types is None:
                similarity_types = ['shared_elements', 'same_application', 'similar_synthesis']
            
            similar_materials = []
            
            async with self.driver.session(database=self.database) as session:
                # Find materials with shared elements
                if 'shared_elements' in similarity_types:
                    result = await session.run("""
                        MATCH (ref:Material {formula: $formula})-[:CONTAINS_ELEMENT]->(e:Element)
                        MATCH (similar:Material)-[:CONTAINS_ELEMENT]->(e)
                        WHERE similar.formula <> $formula
                        AND ($user_id IS NULL OR similar.user_id = $user_id)
                        WITH similar, COUNT(e) as shared_elements
                        ORDER BY shared_elements DESC
                        LIMIT $limit
                        RETURN similar, shared_elements, 'shared_elements' as similarity_type
                    """, {'formula': formula, 'user_id': user_id, 'limit': limit})
                    
                    async for record in result:
                        material = dict(record['similar'])
                        material['similarity_score'] = record['shared_elements']
                        material['similarity_type'] = record['similarity_type']
                        similar_materials.append(material)
                
                # Find materials with same application
                if 'same_application' in similarity_types:
                    result = await session.run("""
                        MATCH (ref:Material {formula: $formula})-[:USED_FOR]->(app:Application)
                        MATCH (similar:Material)-[:USED_FOR]->(app)
                        WHERE similar.formula <> $formula
                        AND ($user_id IS NULL OR similar.user_id = $user_id)
                        RETURN similar, app.name as application, 'same_application' as similarity_type
                        LIMIT $limit
                    """, {'formula': formula, 'user_id': user_id, 'limit': limit})
                    
                    async for record in result:
                        material = dict(record['similar'])
                        material['shared_application'] = record['application']
                        material['similarity_type'] = record['similarity_type']
                        similar_materials.append(material)
                
                # Find materials with similar synthesis
                if 'similar_synthesis' in similarity_types:
                    result = await session.run("""
                        MATCH (ref:Material {formula: $formula})-[:SYNTHESIZED_BY]->(method:SynthesisMethod)
                        MATCH (similar:Material)-[:SYNTHESIZED_BY]->(method)
                        WHERE similar.formula <> $formula
                        AND ($user_id IS NULL OR similar.user_id = $user_id)
                        RETURN similar, method.method as synthesis_method, 'similar_synthesis' as similarity_type
                        LIMIT $limit
                    """, {'formula': formula, 'user_id': user_id, 'limit': limit})
                    
                    async for record in result:
                        material = dict(record['similar'])
                        material['shared_synthesis'] = record['synthesis_method']
                        material['similarity_type'] = record['similarity_type']
                        similar_materials.append(material)
            
            # Parse JSON properties and remove duplicates
            unique_materials = {}
            for material in similar_materials:
                formula = material['formula']
                if formula not in unique_materials:
                    if material.get('properties'):
                        try:
                            material['properties'] = json.loads(material['properties'])
                        except (json.JSONDecodeError, TypeError):
                            material['properties'] = {}
                    unique_materials[formula] = material
            
            return list(unique_materials.values())[:limit]
            
        except Exception as e:
            logger.error(f"Failed to find similar materials: {e}")
            return []
    
    async def get_material_relationships(self, formula: str) -> Dict[str, Any]:
        """
        Get all relationships for a specific material.
        
        Args:
            formula: Material formula
            
        Returns:
            Dictionary with all relationships
        """
        try:
            relationships = {
                'formula': formula,
                'elements': [],
                'applications': [],
                'synthesis_methods': [],
                'discovered_by': [],
                'similar_materials': []
            }
            
            async with self.driver.session(database=self.database) as session:
                # Get basic material info
                result = await session.run("""
                    MATCH (m:Material {formula: $formula})
                    RETURN m
                """, {'formula': formula})
                
                material_record = await result.single()
                if not material_record:
                    return relationships
                
                material = dict(material_record['m'])
                if material.get('properties'):
                    try:
                        material['properties'] = json.loads(material['properties'])
                    except (json.JSONDecodeError, TypeError):
                        material['properties'] = {}
                
                relationships['material_info'] = material
                
                # Get constituent elements
                result = await session.run("""
                    MATCH (m:Material {formula: $formula})-[:CONTAINS_ELEMENT]->(e:Element)
                    RETURN e.symbol as element
                """, {'formula': formula})
                
                relationships['elements'] = [record['element'] async for record in result]
                
                # Get applications
                result = await session.run("""
                    MATCH (m:Material {formula: $formula})-[:USED_FOR]->(a:Application)
                    RETURN a.name as application
                """, {'formula': formula})
                
                relationships['applications'] = [record['application'] async for record in result]
                
                # Get synthesis methods
                result = await session.run("""
                    MATCH (m:Material {formula: $formula})-[:SYNTHESIZED_BY]->(s:SynthesisMethod)
                    RETURN s.method as method
                """, {'formula': formula})
                
                relationships['synthesis_methods'] = [record['method'] async for record in result]
                
                # Get discoverers
                result = await session.run("""
                    MATCH (u:User)-[:DISCOVERED]->(m:Material {formula: $formula})
                    RETURN u.user_id as user_id
                """, {'formula': formula})
                
                relationships['discovered_by'] = [record['user_id'] async for record in result]
                
                # Get similar materials (simplified)
                similar = await self.find_similar_materials(formula, limit=5)
                relationships['similar_materials'] = [
                    {'formula': m['formula'], 'similarity_type': m.get('similarity_type', 'unknown')}
                    for m in similar
                ]
            
            return relationships
            
        except Exception as e:
            logger.error(f"Failed to get material relationships: {e}")
            return {'error': str(e)}
    
    async def get_materials_by_element(self, element: str, user_id: Optional[str] = None, limit: int = 20) -> List[Dict[str, Any]]:
        """Get materials containing specific element."""
        try:
            async with self.driver.session(database=self.database) as session:
                result = await session.run("""
                    MATCH (e:Element {symbol: $element})<-[:CONTAINS_ELEMENT]-(m:Material)
                    WHERE $user_id IS NULL OR m.user_id = $user_id
                    RETURN m
                    ORDER BY m.discovered_at DESC
                    LIMIT $limit
                """, {'element': element, 'user_id': user_id, 'limit': limit})
                
                materials = []
                async for record in result:
                    material = dict(record['m'])
                    if material.get('properties'):
                        try:
                            material['properties'] = json.loads(material['properties'])
                        except (json.JSONDecodeError, TypeError):
                            material['properties'] = {}
                    materials.append(material)
                
                return materials
                
        except Exception as e:
            logger.error(f"Failed to get materials by element: {e}")
            return []
    
    async def get_materials_by_application(self, application: str, user_id: Optional[str] = None, limit: int = 20) -> List[Dict[str, Any]]:
        """Get materials for specific application."""
        try:
            async with self.driver.session(database=self.database) as session:
                result = await session.run("""
                    MATCH (a:Application {name: $application})<-[:USED_FOR]-(m:Material)
                    WHERE $user_id IS NULL OR m.user_id = $user_id
                    RETURN m
                    ORDER BY m.discovered_at DESC
                    LIMIT $limit
                """, {'application': application.lower(), 'user_id': user_id, 'limit': limit})
                
                materials = []
                async for record in result:
                    material = dict(record['m'])
                    if material.get('properties'):
                        try:
                            material['properties'] = json.loads(material['properties'])
                        except (json.JSONDecodeError, TypeError):
                            material['properties'] = {}
                    materials.append(material)
                
                return materials
                
        except Exception as e:
            logger.error(f"Failed to get materials by application: {e}")
            return []
    
    async def find_synthesis_alternatives(self, formula: str, limit: int = 5) -> List[Dict[str, Any]]:
        """Find alternative synthesis routes for a material."""
        try:
            async with self.driver.session(database=self.database) as session:
                # Find materials with similar composition and their synthesis methods
                result = await session.run("""
                    MATCH (target:Material {formula: $formula})-[:CONTAINS_ELEMENT]->(e:Element)
                    MATCH (similar:Material)-[:CONTAINS_ELEMENT]->(e)
                    MATCH (similar)-[:SYNTHESIZED_BY]->(s:SynthesisMethod)
                    WHERE similar.formula <> $formula
                    WITH s, COUNT(e) as shared_elements
                    ORDER BY shared_elements DESC
                    RETURN s.method as synthesis_method, shared_elements
                    LIMIT $limit
                """, {'formula': formula, 'limit': limit})
                
                alternatives = []
                async for record in result:
                    alternatives.append({
                        'synthesis_method': record['synthesis_method'],
                        'similarity_score': record['shared_elements']
                    })
                
                return alternatives
                
        except Exception as e:
            logger.error(f"Failed to find synthesis alternatives: {e}")
            return []
    
    async def get_user_discovery_network(self, user_id: str) -> Dict[str, Any]:
        """Get user's discovery network and patterns."""
        try:
            async with self.driver.session(database=self.database) as session:
                # Get user's materials and their connections
                result = await session.run("""
                    MATCH (u:User {user_id: $user_id})-[:DISCOVERED]->(m:Material)
                    OPTIONAL MATCH (m)-[:CONTAINS_ELEMENT]->(e:Element)
                    OPTIONAL MATCH (m)-[:USED_FOR]->(a:Application)
                    OPTIONAL MATCH (m)-[:SYNTHESIZED_BY]->(s:SynthesisMethod)
                    RETURN m, COLLECT(DISTINCT e.symbol) as elements, 
                           COLLECT(DISTINCT a.name) as applications,
                           COLLECT(DISTINCT s.method) as synthesis_methods
                """, {'user_id': user_id})
                
                network = {
                    'user_id': user_id,
                    'materials': [],
                    'element_frequency': {},
                    'application_frequency': {},
                    'synthesis_frequency': {}
                }
                
                async for record in result:
                    material = dict(record['m'])
                    if material.get('properties'):
                        try:
                            material['properties'] = json.loads(material['properties'])
                        except (json.JSONDecodeError, TypeError):
                            material['properties'] = {}
                    
                    material['elements'] = record['elements']
                    material['applications'] = record['applications']
                    material['synthesis_methods'] = record['synthesis_methods']
                    
                    network['materials'].append(material)
                    
                    # Count frequencies
                    for element in record['elements']:
                        network['element_frequency'][element] = network['element_frequency'].get(element, 0) + 1
                    
                    for app in record['applications']:
                        if app:  # Filter out None/empty
                            network['application_frequency'][app] = network['application_frequency'].get(app, 0) + 1
                    
                    for method in record['synthesis_methods']:
                        if method:  # Filter out None/empty
                            network['synthesis_frequency'][method] = network['synthesis_frequency'].get(method, 0) + 1
                
                return network
                
        except Exception as e:
            logger.error(f"Failed to get user discovery network: {e}")
            return {'error': str(e)}
    
    async def get_graph_statistics(self) -> Dict[str, Any]:
        """Get knowledge graph statistics."""
        try:
            stats = {}
            
            async with self.driver.session(database=self.database) as session:
                # Node counts
                for label in ['Material', 'Element', 'Application', 'SynthesisMethod', 'User']:
                    result = await session.run(f"MATCH (n:{label}) RETURN count(n) as count")
                    record = await result.single()
                    stats[f"{label.lower()}_count"] = record['count'] if record else 0
                
                # Relationship counts
                result = await session.run("MATCH ()-[r]->() RETURN count(r) as count")
                record = await result.single()
                stats['total_relationships'] = record['count'] if record else 0
                
                # Recent activity
                result = await session.run("""
                    MATCH (m:Material)
                    WHERE m.discovered_at > datetime('2024-01-01')
                    RETURN count(m) as recent_discoveries
                """)
                record = await result.single()
                stats['recent_discoveries'] = record['recent_discoveries'] if record else 0
                
                # Most common elements
                result = await session.run("""
                    MATCH (e:Element)<-[:CONTAINS_ELEMENT]-(m:Material)
                    RETURN e.symbol as element, count(m) as frequency
                    ORDER BY frequency DESC
                    LIMIT 10
                """)
                
                stats['top_elements'] = [
                    {'element': record['element'], 'frequency': record['frequency']}
                    async for record in result
                ]
                
                # Most common applications
                result = await session.run("""
                    MATCH (a:Application)<-[:USED_FOR]-(m:Material)
                    RETURN a.name as application, count(m) as frequency
                    ORDER BY frequency DESC
                    LIMIT 10
                """)
                
                stats['top_applications'] = [
                    {'application': record['application'], 'frequency': record['frequency']}
                    async for record in result
                ]
            
            return stats
            
        except Exception as e:
            logger.error(f"Failed to get graph statistics: {e}")
            return {'error': str(e)}
    
    async def clear_user_data(self, user_id: str) -> bool:
        """Clear all data for a specific user."""
        try:
            async with self.driver.session(database=self.database) as session:
                # Remove user's materials and relationships
                await session.run("""
                    MATCH (u:User {user_id: $user_id})-[:DISCOVERED]->(m:Material)
                    DETACH DELETE m
                """, {'user_id': user_id})
                
                # Remove user node
                await session.run("""
                    MATCH (u:User {user_id: $user_id})
                    DELETE u
                """, {'user_id': user_id})
                
                logger.info(f"Cleared all data for user {user_id}")
                return True
                
        except Exception as e:
            logger.error(f"Failed to clear user data: {e}")
            return False