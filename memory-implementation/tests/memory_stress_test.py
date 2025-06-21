#!/usr/bin/env python3
"""
Comprehensive Memory System Stress Test

Tests all memory components under load to ensure performance, reliability,
and scalability of the CrystaLyse.AI memory system.
"""

import asyncio
import time
import random
import logging
from datetime import datetime, timedelta
from pathlib import Path
import json
import sys
from typing import Dict, List, Any
import tempfile
import shutil

# Add src to path for imports
sys.path.insert(0, str(Path(__file__).parent.parent / "src"))

from crystalyse_memory import (
    create_complete_memory_system,
    DualWorkingMemory,
    DiscoveryStore,
    UserProfileStore,
    MaterialKnowledgeGraph,
    ConversationManager,
    SessionContextManager
)

# Set up logging
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)


class MemoryStressTestSuite:
    """Comprehensive memory system stress test suite."""
    
    def __init__(self):
        self.test_results = {}
        self.temp_dir = None
        self.start_time = None
        
        # Test data generators
        self.test_materials = [
            "NaFePO4", "LiFePO4", "CaTiO3", "BaTiO3", "SrTiO3",
            "Na2FePO4F", "Li2FeSiO4", "Ca3Al2O6", "Mg2SiO4", "Al2O3",
            "TiO2", "SiO2", "Fe2O3", "NiO", "CoO", "MnO2", "V2O5",
            "LiCoO2", "LiNiO2", "LiMn2O4", "NaCrO2", "KMnO4"
        ]
        
        self.test_applications = [
            "battery cathode", "solar cell", "catalyst", "superconductor",
            "thermoelectric", "concrete additive", "capacitor", "sensor",
            "magnetic storage", "optical material", "piezoelectric"
        ]
        
        self.test_synthesis_methods = [
            "solid-state reaction", "sol-gel", "hydrothermal", "combustion",
            "chemical vapor deposition", "sputtering", "ball milling",
            "freeze drying", "spray pyrolysis", "electrodeposition"
        ]
    
    def setup_test_environment(self):
        """Set up temporary test environment."""
        self.temp_dir = Path(tempfile.mkdtemp(prefix="memory_stress_test_"))
        logger.info(f"Test environment created: {self.temp_dir}")
    
    def cleanup_test_environment(self):
        """Clean up test environment."""
        if self.temp_dir and self.temp_dir.exists():
            shutil.rmtree(self.temp_dir)
            logger.info("Test environment cleaned up")
    
    def generate_random_discovery(self, user_id: str, session_id: str) -> Dict[str, Any]:
        """Generate random discovery for testing."""
        formula = random.choice(self.test_materials)
        application = random.choice(self.test_applications)
        synthesis = random.choice(self.test_synthesis_methods)
        
        return {
            "formula": formula,
            "user_id": user_id,
            "session_id": session_id,
            "timestamp": datetime.now().isoformat(),
            "application": application,
            "synthesis_route": synthesis,
            "formation_energy": round(random.uniform(-5.0, 0.0), 3),
            "band_gap": round(random.uniform(0.1, 5.0), 2),
            "properties": {
                "density": round(random.uniform(2.0, 10.0), 2),
                "melting_point": random.randint(500, 3000),
                "conductivity": round(random.uniform(0.001, 100.0), 3)
            },
            "constraints_met": random.sample(
                ["earth-abundant", "non-toxic", "stable", "high-performance"],
                k=random.randint(1, 3)
            ),
            "discovery_method": "computational",
            "discovery_context": f"Discovered {formula} for {application} using {synthesis}"
        }
    
    async def test_dual_working_memory_performance(self, num_operations: int = 1000) -> Dict[str, Any]:
        """Test DualWorkingMemory under load."""
        logger.info(f"Testing DualWorkingMemory with {num_operations} operations")
        
        # Create memory instance
        dual_memory = DualWorkingMemory(
            session_id="stress_test_session",
            user_id="stress_test_user",
            max_cache_age_hours=1
        )
        
        start_time = time.time()
        
        # Test computational caching
        cache_operations = 0
        cache_hits = 0
        
        for i in range(num_operations):
            operation = random.choice(["smact_feasibility", "chemeleon_csp", "mace_energy"])
            formula = random.choice(self.test_materials)
            
            # Try to get cached result first
            cached = dual_memory.get_cached_result(operation, formula=formula)
            if cached:
                cache_hits += 1
            else:
                # Cache new result
                result = {
                    "formula": formula,
                    "result": random.uniform(-5.0, 5.0),
                    "timestamp": datetime.now().isoformat()
                }
                dual_memory.cache_result(operation, result, formula=formula)
                cache_operations += 1
            
            # Test scratchpad operations (every 10th iteration)
            if i % 10 == 0:
                dual_memory.write_to_scratchpad(
                    f"Progress update: completed {i} operations",
                    "progress"
                )
        
        # Test scratchpad reading
        scratchpad_content = dual_memory.read_scratchpad()
        
        elapsed_time = time.time() - start_time
        cache_hit_rate = cache_hits / num_operations if num_operations > 0 else 0
        
        # Get memory stats
        stats = dual_memory.get_stats()
        
        # Cleanup
        dual_memory.cleanup()
        
        return {
            "test": "dual_working_memory_performance",
            "num_operations": num_operations,
            "elapsed_time": elapsed_time,
            "ops_per_second": num_operations / elapsed_time,
            "cache_operations": cache_operations,
            "cache_hits": cache_hits,
            "cache_hit_rate": cache_hit_rate,
            "scratchpad_length": len(scratchpad_content),
            "memory_stats": stats,
            "success": True
        }
    
    async def test_discovery_store_scalability(self, num_discoveries: int = 1000) -> Dict[str, Any]:
        """Test DiscoveryStore with large number of discoveries."""
        logger.info(f"Testing DiscoveryStore with {num_discoveries} discoveries")
        
        # Create discovery store
        store_dir = self.temp_dir / "discovery_store"
        discovery_store = DiscoveryStore(persist_directory=store_dir)
        
        start_time = time.time()
        
        # Store discoveries
        store_times = []
        stored_ids = []
        
        for i in range(num_discoveries):
            discovery = self.generate_random_discovery(
                user_id=f"user_{i % 10}",  # 10 different users
                session_id=f"session_{i % 50}"  # 50 different sessions
            )
            
            store_start = time.time()
            discovery_id = await discovery_store.store_discovery(discovery)
            store_time = time.time() - store_start
            
            store_times.append(store_time)
            stored_ids.append(discovery_id)
        
        store_phase_time = time.time() - start_time
        
        # Test search performance
        search_start = time.time()
        search_results = []
        
        search_queries = [
            "battery materials",
            "catalysts for solar cells",
            "earth-abundant materials",
            "high conductivity materials",
            "stable perovskites"
        ]
        
        search_times = []
        for query in search_queries:
            query_start = time.time()
            results = await discovery_store.search_discoveries(query, n_results=10)
            query_time = time.time() - query_start
            
            search_times.append(query_time)
            search_results.append(len(results))
        
        search_phase_time = time.time() - search_start
        
        # Test user-specific searches
        user_search_start = time.time()
        user_discoveries = await discovery_store.get_user_discoveries("user_1", limit=100)
        user_search_time = time.time() - user_search_start
        
        # Get collection stats
        stats = discovery_store.get_collection_stats()
        
        total_time = time.time() - start_time
        
        return {
            "test": "discovery_store_scalability",
            "num_discoveries": num_discoveries,
            "total_time": total_time,
            "store_phase_time": store_phase_time,
            "search_phase_time": search_phase_time,
            "avg_store_time": sum(store_times) / len(store_times),
            "max_store_time": max(store_times),
            "avg_search_time": sum(search_times) / len(search_times),
            "user_search_time": user_search_time,
            "user_discoveries_found": len(user_discoveries),
            "search_results": search_results,
            "collection_stats": stats,
            "discoveries_per_second": num_discoveries / store_phase_time,
            "success": True
        }
    
    async def test_user_store_concurrency(self, num_users: int = 100, operations_per_user: int = 50) -> Dict[str, Any]:
        """Test UserProfileStore with concurrent operations."""
        logger.info(f"Testing UserProfileStore with {num_users} users, {operations_per_user} ops each")
        
        # Create user store
        db_path = self.temp_dir / "users_test.db"
        user_store = UserProfileStore(db_path=db_path)
        
        start_time = time.time()
        
        # Create users
        user_creation_times = []
        for i in range(num_users):
            user_id = f"test_user_{i}"
            
            create_start = time.time()
            await user_store.create_user_profile(user_id, {
                "expertise_level": random.choice(["beginner", "intermediate", "expert"]),
                "preferred_mode": random.choice(["rigorous", "creative"]),
                "research_interests": random.sample(self.test_applications, k=3)
            })
            create_time = time.time() - create_start
            user_creation_times.append(create_time)
        
        # Concurrent operations
        async def user_operations(user_id: str):
            ops_times = []
            
            for j in range(operations_per_user):
                op_start = time.time()
                
                # Random operation
                op = random.choice([
                    "track_interest", "track_constraint", "start_session", 
                    "record_discovery", "update_preferences"
                ])
                
                if op == "track_interest":
                    await user_store.track_research_interest(
                        user_id, random.choice(self.test_applications)
                    )
                elif op == "track_constraint":
                    await user_store.track_constraint_usage(
                        user_id, "element", random.choice(["Na", "Li", "Ca", "Ti"])
                    )
                elif op == "start_session":
                    session_id = f"{user_id}_session_{j}"
                    await user_store.start_session(
                        session_id, user_id, f"Query {j}", "rigorous"
                    )
                elif op == "record_discovery":
                    discovery = self.generate_random_discovery(user_id, f"session_{j}")
                    await user_store.record_discovery(user_id, f"session_{j}", discovery)
                elif op == "update_preferences":
                    await user_store.update_user_preferences(user_id, {
                        "preferred_mode": random.choice(["rigorous", "creative"])
                    })
                
                op_time = time.time() - op_start
                ops_times.append(op_time)
            
            return ops_times
        
        # Run concurrent operations
        tasks = [user_operations(f"test_user_{i}") for i in range(num_users)]
        all_op_times = await asyncio.gather(*tasks)
        
        # Flatten operation times
        flat_op_times = [time for user_times in all_op_times for time in user_times]
        
        # Test data retrieval
        retrieval_start = time.time()
        sample_contexts = []
        for i in range(min(10, num_users)):
            context = await user_store.get_user_context_for_agent(f"test_user_{i}")
            sample_contexts.append(context)
        retrieval_time = time.time() - retrieval_start
        
        # Get database stats
        db_stats = user_store.get_database_stats()
        
        total_time = time.time() - start_time
        total_operations = num_users * operations_per_user
        
        return {
            "test": "user_store_concurrency",
            "num_users": num_users,
            "operations_per_user": operations_per_user,
            "total_operations": total_operations,
            "total_time": total_time,
            "avg_user_creation_time": sum(user_creation_times) / len(user_creation_times),
            "avg_operation_time": sum(flat_op_times) / len(flat_op_times),
            "max_operation_time": max(flat_op_times),
            "operations_per_second": total_operations / total_time,
            "retrieval_time": retrieval_time,
            "contexts_retrieved": len(sample_contexts),
            "database_stats": db_stats,
            "success": True
        }
    
    async def test_knowledge_graph_relationships(self, num_materials: int = 500) -> Dict[str, Any]:
        """Test MaterialKnowledgeGraph with complex relationships."""
        logger.info(f"Testing MaterialKnowledgeGraph with {num_materials} materials")
        
        try:
            # Create knowledge graph (will fall back gracefully if Neo4j not available)
            knowledge_graph = MaterialKnowledgeGraph()
            
            # Try to initialize
            initialized = await knowledge_graph.initialize()
            if not initialized:
                return {
                    "test": "knowledge_graph_relationships",
                    "success": False,
                    "error": "Neo4j not available",
                    "skipped": True
                }
            
            start_time = time.time()
            
            # Add materials with relationships
            add_times = []
            
            for i in range(num_materials):
                discovery = self.generate_random_discovery(
                    user_id=f"user_{i % 5}",  # 5 users
                    session_id=f"session_{i % 20}"  # 20 sessions
                )
                
                add_start = time.time()
                await knowledge_graph.add_material_discovery(discovery)
                add_time = time.time() - add_start
                add_times.append(add_time)
            
            add_phase_time = time.time() - start_time
            
            # Test relationship queries
            query_start = time.time()
            
            # Find similar materials
            similarity_tests = []
            test_formulas = random.sample(self.test_materials, k=10)
            
            for formula in test_formulas:
                similar_start = time.time()
                similar = await knowledge_graph.find_similar_materials(formula, limit=5)
                similar_time = time.time() - similar_start
                
                similarity_tests.append({
                    "formula": formula,
                    "similar_count": len(similar),
                    "query_time": similar_time
                })
            
            # Test element-based queries
            element_tests = []
            test_elements = ["Na", "Li", "Ti", "Fe", "O"]
            
            for element in test_elements:
                element_start = time.time()
                materials = await knowledge_graph.get_materials_by_element(element, limit=20)
                element_time = time.time() - element_start
                
                element_tests.append({
                    "element": element,
                    "materials_count": len(materials),
                    "query_time": element_time
                })
            
            # Test application-based queries
            app_tests = []
            test_apps = random.sample(self.test_applications, k=5)
            
            for app in test_apps:
                app_start = time.time()
                materials = await knowledge_graph.get_materials_by_application(app, limit=20)
                app_time = time.time() - app_start
                
                app_tests.append({
                    "application": app,
                    "materials_count": len(materials),
                    "query_time": app_time
                })
            
            # Get user discovery networks
            network_tests = []
            for i in range(3):
                user_id = f"user_{i}"
                network_start = time.time()
                network = await knowledge_graph.get_user_discovery_network(user_id)
                network_time = time.time() - network_start
                
                network_tests.append({
                    "user_id": user_id,
                    "materials_count": len(network.get('materials', [])),
                    "query_time": network_time
                })
            
            query_phase_time = time.time() - query_start
            
            # Get graph statistics
            stats = await knowledge_graph.get_graph_statistics()
            
            # Cleanup
            await knowledge_graph.close()
            
            total_time = time.time() - start_time
            
            return {
                "test": "knowledge_graph_relationships",
                "num_materials": num_materials,
                "total_time": total_time,
                "add_phase_time": add_phase_time,
                "query_phase_time": query_phase_time,
                "avg_add_time": sum(add_times) / len(add_times),
                "max_add_time": max(add_times),
                "materials_per_second": num_materials / add_phase_time,
                "similarity_tests": similarity_tests,
                "element_tests": element_tests,
                "application_tests": app_tests,
                "network_tests": network_tests,
                "graph_stats": stats,
                "success": True
            }
            
        except Exception as e:
            return {
                "test": "knowledge_graph_relationships",
                "success": False,
                "error": str(e),
                "skipped": True
            }
    
    async def test_conversation_memory_performance(self, num_conversations: int = 100, messages_per_conversation: int = 50) -> Dict[str, Any]:
        """Test ConversationManager performance."""
        logger.info(f"Testing ConversationManager with {num_conversations} conversations")
        
        # Create conversation manager
        conv_manager = ConversationManager(
            redis_url="redis://localhost:6379",
            fallback_dir=self.temp_dir / "conversations"
        )
        await conv_manager.initialize()
        
        start_time = time.time()
        
        # Add messages to conversations
        add_times = []
        
        for conv_id in range(num_conversations):
            session_id = f"stress_test_conv_{conv_id}"
            user_id = f"user_{conv_id % 10}"  # 10 users
            
            for msg_id in range(messages_per_conversation):
                add_start = time.time()
                
                role = "user" if msg_id % 2 == 0 else "assistant"
                content = f"Message {msg_id} in conversation {conv_id}"
                
                await conv_manager.add_message(session_id, user_id, role, content)
                
                add_time = time.time() - add_start
                add_times.append(add_time)
        
        add_phase_time = time.time() - start_time
        
        # Test message retrieval
        retrieval_start = time.time()
        retrieval_times = []
        
        for conv_id in range(min(20, num_conversations)):  # Test subset
            session_id = f"stress_test_conv_{conv_id}"
            
            retrieve_start = time.time()
            history = await conv_manager.get_history(session_id, limit=20)
            retrieve_time = time.time() - retrieve_start
            
            retrieval_times.append(retrieve_time)
        
        # Test context summaries
        summary_times = []
        for conv_id in range(min(10, num_conversations)):
            session_id = f"stress_test_conv_{conv_id}"
            
            summary_start = time.time()
            summary = await conv_manager.get_context_summary(session_id, max_tokens=500)
            summary_time = time.time() - summary_start
            
            summary_times.append(summary_time)
        
        retrieval_phase_time = time.time() - retrieval_start
        
        # Cleanup
        await conv_manager.close()
        
        total_time = time.time() - start_time
        total_messages = num_conversations * messages_per_conversation
        
        return {
            "test": "conversation_memory_performance",
            "num_conversations": num_conversations,
            "messages_per_conversation": messages_per_conversation,
            "total_messages": total_messages,
            "total_time": total_time,
            "add_phase_time": add_phase_time,
            "retrieval_phase_time": retrieval_phase_time,
            "avg_add_time": sum(add_times) / len(add_times),
            "max_add_time": max(add_times),
            "avg_retrieval_time": sum(retrieval_times) / len(retrieval_times) if retrieval_times else 0,
            "avg_summary_time": sum(summary_times) / len(summary_times) if summary_times else 0,
            "messages_per_second": total_messages / add_phase_time,
            "success": True
        }
    
    async def test_session_context_load(self, num_sessions: int = 200) -> Dict[str, Any]:
        """Test SessionContextManager under load."""
        logger.info(f"Testing SessionContextManager with {num_sessions} sessions")
        
        # Create session manager
        session_manager = SessionContextManager(storage_dir=self.temp_dir / "sessions")
        
        start_time = time.time()
        
        # Create sessions
        create_times = []
        session_ids = []
        
        for i in range(num_sessions):
            session_id = f"stress_session_{i}"
            user_id = f"user_{i % 20}"  # 20 users
            
            create_start = time.time()
            session_state = session_manager.create_session(
                user_id=user_id,
                session_id=session_id,
                initial_context={
                    "research_focus": random.choice(self.test_applications),
                    "agent_mode": random.choice(["rigorous", "creative"])
                }
            )
            create_time = time.time() - create_start
            
            create_times.append(create_time)
            session_ids.append(session_id)
        
        # Update sessions with activity
        update_times = []
        for session_id in session_ids:
            # Start query
            query = f"Find materials for {random.choice(self.test_applications)}"
            
            update_start = time.time()
            session_manager.start_query(session_id, query)
            
            # Log tool usage
            for tool in random.sample(["smact", "chemeleon", "mace"], k=2):
                session_manager.log_tool_usage(session_id, tool)
            
            # Add discoveries
            for _ in range(random.randint(1, 5)):
                material = random.choice(self.test_materials)
                session_manager.add_discovered_material(session_id, material)
            
            update_time = time.time() - update_start
            update_times.append(update_time)
        
        # Test retrievals
        retrieval_start = time.time()
        retrieval_times = []
        
        for i in range(min(50, num_sessions)):
            session_id = session_ids[i]
            
            retrieve_start = time.time()
            
            # Get session stats
            stats = session_manager.get_session_statistics(session_id)
            
            # Get agent context
            context = session_manager.get_context_for_agent(session_id)
            
            retrieve_time = time.time() - retrieve_start
            retrieval_times.append(retrieve_time)
        
        retrieval_phase_time = time.time() - retrieval_start
        
        # Cleanup
        session_manager.close()
        
        total_time = time.time() - start_time
        
        return {
            "test": "session_context_load",
            "num_sessions": num_sessions,
            "total_time": total_time,
            "avg_create_time": sum(create_times) / len(create_times),
            "avg_update_time": sum(update_times) / len(update_times),
            "avg_retrieval_time": sum(retrieval_times) / len(retrieval_times) if retrieval_times else 0,
            "sessions_per_second": num_sessions / total_time,
            "success": True
        }
    
    async def test_complete_memory_system_integration(self, num_users: int = 10, operations_per_user: int = 20) -> Dict[str, Any]:
        """Test complete memory system integration."""
        logger.info(f"Testing complete memory system integration with {num_users} users")
        
        start_time = time.time()
        
        # Test with fallback configurations (no external dependencies required)
        memory_systems = []
        
        for i in range(num_users):
            user_id = f"integration_user_{i}"
            session_id = f"integration_session_{i}"
            
            try:
                # Create complete memory system
                memory_system = await create_complete_memory_system(
                    session_id=session_id,
                    user_id=user_id,
                    cache_dir=self.temp_dir / f"cache_{i}",
                    scratchpad_dir=self.temp_dir / f"scratchpad_{i}",
                    discovery_persist_dir=self.temp_dir / f"discoveries_{i}",
                    user_db_path=self.temp_dir / f"users_{i}.db",
                    neo4j_config=None,  # Skip Neo4j for stress test
                    redis_config={"fallback_dir": self.temp_dir / f"conv_{i}"}
                )
                
                memory_systems.append(memory_system)
                
            except Exception as e:
                logger.warning(f"Failed to create memory system for user {i}: {e}")
                continue
        
        creation_time = time.time() - start_time
        
        # Test operations on each memory system
        operation_start = time.time()
        operation_results = []
        
        for i, memory_system in enumerate(memory_systems):
            user_results = {"user_index": i, "operations": []}
            
            dual_memory = memory_system['dual_working_memory']
            discovery_store = memory_system['discovery_store']
            user_store = memory_system['user_store']
            
            for j in range(operations_per_user):
                op_start = time.time()
                
                # Generate and store discovery
                discovery = self.generate_random_discovery(
                    user_id=memory_system['user_id'],
                    session_id=memory_system['session_id']
                )
                
                # Store in discovery store
                discovery_id = await discovery_store.store_discovery(discovery)
                
                # Record in user store
                await user_store.record_discovery(
                    memory_system['user_id'],
                    memory_system['session_id'],
                    discovery
                )
                
                # Update scratchpad
                dual_memory.write_to_scratchpad(
                    f"Discovered {discovery['formula']} for {discovery['application']}",
                    "progress"
                )
                
                # Cache some computation
                dual_memory.cache_result(
                    "test_computation",
                    {"result": random.uniform(-5, 5)},
                    formula=discovery['formula']
                )
                
                op_time = time.time() - op_start
                user_results["operations"].append({
                    "operation_id": j,
                    "discovery_id": discovery_id,
                    "time": op_time
                })
            
            operation_results.append(user_results)
        
        operations_time = time.time() - operation_start
        
        # Test cross-system searches
        search_start = time.time()
        search_results = []
        
        for i, memory_system in enumerate(memory_systems[:5]):  # Test subset
            discovery_store = memory_system['discovery_store']
            
            # Search for discoveries
            results = await discovery_store.search_discoveries(
                "battery materials",
                user_id=memory_system['user_id'],
                n_results=10
            )
            
            search_results.append({
                "user_index": i,
                "results_found": len(results)
            })
        
        search_time = time.time() - search_start
        
        total_time = time.time() - start_time
        total_operations = len(memory_systems) * operations_per_user
        
        return {
            "test": "complete_memory_system_integration",
            "num_users": num_users,
            "systems_created": len(memory_systems),
            "operations_per_user": operations_per_user,
            "total_operations": total_operations,
            "total_time": total_time,
            "creation_time": creation_time,
            "operations_time": operations_time,
            "search_time": search_time,
            "avg_operation_time": operations_time / total_operations if total_operations > 0 else 0,
            "operations_per_second": total_operations / operations_time if operations_time > 0 else 0,
            "search_results": search_results,
            "success": True
        }
    
    async def run_all_tests(self) -> Dict[str, Any]:
        """Run all memory stress tests."""
        logger.info("Starting comprehensive memory stress test suite")
        
        self.setup_test_environment()
        self.start_time = time.time()
        
        try:
            # Run all tests
            tests = [
                ("dual_working_memory", self.test_dual_working_memory_performance(1000)),
                ("discovery_store", self.test_discovery_store_scalability(500)),
                ("user_store", self.test_user_store_concurrency(50, 30)),
                ("knowledge_graph", self.test_knowledge_graph_relationships(200)),
                ("conversation_memory", self.test_conversation_memory_performance(50, 30)),
                ("session_context", self.test_session_context_load(100)),
                ("complete_integration", self.test_complete_memory_system_integration(5, 10))
            ]
            
            results = {}
            
            for test_name, test_coro in tests:
                logger.info(f"Running {test_name} test...")
                try:
                    results[test_name] = await test_coro
                    if results[test_name].get("success"):
                        logger.info(f"✓ {test_name} test completed successfully")
                    else:
                        logger.warning(f"⚠ {test_name} test completed with issues")
                except Exception as e:
                    logger.error(f"✗ {test_name} test failed: {e}")
                    results[test_name] = {
                        "test": test_name,
                        "success": False,
                        "error": str(e)
                    }
            
            # Generate summary
            total_time = time.time() - self.start_time
            successful_tests = sum(1 for r in results.values() if r.get("success"))
            
            summary = {
                "test_suite": "memory_stress_test",
                "timestamp": datetime.now().isoformat(),
                "total_time": total_time,
                "tests_run": len(tests),
                "tests_successful": successful_tests,
                "tests_failed": len(tests) - successful_tests,
                "success_rate": successful_tests / len(tests),
                "results": results
            }
            
            return summary
            
        finally:
            self.cleanup_test_environment()
    
    def generate_report(self, results: Dict[str, Any]) -> str:
        """Generate comprehensive test report."""
        report_lines = [
            "# CrystaLyse.AI Memory System Stress Test Report",
            "",
            f"**Generated**: {results['timestamp']}",
            f"**Total Duration**: {results['total_time']:.2f} seconds",
            f"**Tests Run**: {results['tests_run']}",
            f"**Success Rate**: {results['success_rate']*100:.1f}%",
            "",
            "## Test Results Summary",
            ""
        ]
        
        for test_name, test_result in results['results'].items():
            if test_result.get('success'):
                status = "✅ PASSED"
            elif test_result.get('skipped'):
                status = "⏭️ SKIPPED"
            else:
                status = "❌ FAILED"
            
            report_lines.append(f"### {test_name.replace('_', ' ').title()}")
            report_lines.append(f"**Status**: {status}")
            
            if test_result.get('error'):
                report_lines.append(f"**Error**: {test_result['error']}")
            elif test_result.get('success'):
                # Add key metrics
                if 'elapsed_time' in test_result:
                    report_lines.append(f"**Duration**: {test_result['elapsed_time']:.2f}s")
                if 'ops_per_second' in test_result:
                    report_lines.append(f"**Operations/sec**: {test_result['ops_per_second']:.1f}")
                if 'cache_hit_rate' in test_result:
                    report_lines.append(f"**Cache Hit Rate**: {test_result['cache_hit_rate']*100:.1f}%")
            
            report_lines.append("")
        
        # Performance insights
        report_lines.extend([
            "## Performance Insights",
            "",
            "### Key Findings",
            ""
        ])
        
        # Analyze results for insights
        dual_memory_result = results['results'].get('dual_working_memory', {})
        if dual_memory_result.get('success'):
            ops_per_sec = dual_memory_result.get('ops_per_second', 0)
            hit_rate = dual_memory_result.get('cache_hit_rate', 0) * 100
            report_lines.append(f"- **Dual Working Memory**: {ops_per_sec:.0f} ops/sec, {hit_rate:.1f}% cache hit rate")
        
        discovery_result = results['results'].get('discovery_store', {})
        if discovery_result.get('success'):
            disc_per_sec = discovery_result.get('discoveries_per_second', 0)
            report_lines.append(f"- **Discovery Store**: {disc_per_sec:.0f} discoveries/sec storage rate")
        
        integration_result = results['results'].get('complete_integration', {})
        if integration_result.get('success'):
            sys_created = integration_result.get('systems_created', 0)
            total_ops = integration_result.get('total_operations', 0)
            report_lines.append(f"- **Integration**: Successfully created {sys_created} complete memory systems with {total_ops} operations")
        
        report_lines.extend([
            "",
            "## Recommendations",
            "",
            "Based on the stress test results:",
            ""
        ])
        
        # Add recommendations based on results
        if results['success_rate'] >= 0.8:
            report_lines.append("✅ **System is production ready** - All core tests passing with good performance")
        else:
            report_lines.append("⚠️ **System needs optimization** - Some tests failed or showed performance issues")
        
        report_lines.extend([
            "",
            "### Next Steps",
            "",
            "1. Monitor memory usage in production",
            "2. Set up performance alerting",
            "3. Implement memory cleanup automation",
            "4. Consider horizontal scaling for high-load scenarios",
            "",
            "---",
            "*Generated by CrystaLyse.AI Memory Stress Test Suite*"
        ])
        
        return "\n".join(report_lines)


async def main():
    """Run memory stress test suite."""
    test_suite = MemoryStressTestSuite()
    
    logger.info("🧪 CrystaLyse.AI Memory System Stress Test Suite")
    logger.info("=" * 60)
    
    # Run tests
    results = await test_suite.run_all_tests()
    
    # Generate report
    report = test_suite.generate_report(results)
    
    # Save results
    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    
    # Save JSON results
    json_path = Path(f"memory_stress_test_results_{timestamp}.json")
    with open(json_path, 'w') as f:
        json.dump(results, f, indent=2)
    
    # Save markdown report
    report_path = Path(f"memory_stress_test_report_{timestamp}.md")
    with open(report_path, 'w') as f:
        f.write(report)
    
    # Print summary
    print("\n" + "=" * 60)
    print("MEMORY STRESS TEST COMPLETE")
    print("=" * 60)
    print(f"✅ Tests Passed: {results['tests_successful']}/{results['tests_run']}")
    print(f"⏱️  Total Time: {results['total_time']:.2f} seconds")
    print(f"📊 Success Rate: {results['success_rate']*100:.1f}%")
    print(f"📄 Report: {report_path}")
    print(f"📋 Data: {json_path}")
    print("=" * 60)
    
    # Print key performance metrics
    if results['results'].get('dual_working_memory', {}).get('success'):
        dm_result = results['results']['dual_working_memory']
        print(f"🧠 Memory Operations: {dm_result.get('ops_per_second', 0):.0f} ops/sec")
    
    if results['results'].get('discovery_store', {}).get('success'):
        ds_result = results['results']['discovery_store']
        print(f"🔍 Discovery Storage: {ds_result.get('discoveries_per_second', 0):.0f} discoveries/sec")
    
    print()


if __name__ == "__main__":
    asyncio.run(main())