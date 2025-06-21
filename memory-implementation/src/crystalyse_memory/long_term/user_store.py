# crystalyse_memory/long_term/user_store.py
"""
User Profile Store for CrystaLyse.AI Memory System

SQLite-based storage for user preferences, research history, and personalisation data.
Tracks user behaviour patterns and research interests for agent personalisation.
"""

import sqlite3
import json
import logging
from typing import Dict, List, Optional, Any, Tuple
from datetime import datetime, timedelta
from pathlib import Path
from contextlib import contextmanager
import threading

logger = logging.getLogger(__name__)


class UserProfileStore:
    """
    Persistent storage for user profiles and preferences.
    
    Manages user research patterns, preferences, discovery history,
    and personalisation data for agent behaviour tuning.
    """
    
    def __init__(self, db_path: Optional[Path] = None):
        """
        Initialise user profile store.
        
        Args:
            db_path: Path to SQLite database file
        """
        self.db_path = db_path or Path("./memory/users.db")
        self.db_path.parent.mkdir(parents=True, exist_ok=True)
        
        # Thread-local storage for connections
        self._local = threading.local()
        
        # Initialize database schema
        self._init_database()
        
        logger.info(f"UserProfileStore initialised with database: {self.db_path}")
    
    @contextmanager
    def get_connection(self):
        """Get thread-safe database connection."""
        if not hasattr(self._local, 'connection'):
            self._local.connection = sqlite3.connect(
                str(self.db_path),
                check_same_thread=False,
                timeout=30.0
            )
            self._local.connection.row_factory = sqlite3.Row
            # Enable foreign keys
            self._local.connection.execute("PRAGMA foreign_keys = ON")
        
        try:
            yield self._local.connection
        except Exception:
            self._local.connection.rollback()
            raise
        else:
            self._local.connection.commit()
    
    def _init_database(self):
        """Initialize database schema."""
        with self.get_connection() as conn:
            # User profiles table
            conn.execute("""
                CREATE TABLE IF NOT EXISTS user_profiles (
                    user_id TEXT PRIMARY KEY,
                    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                    last_active TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                    
                    -- Preferences
                    preferred_mode TEXT DEFAULT 'rigorous',
                    output_format TEXT DEFAULT 'detailed',
                    reasoning_depth TEXT DEFAULT 'standard',
                    include_visualisations BOOLEAN DEFAULT 1,
                    
                    -- Research patterns
                    research_interests TEXT,  -- JSON array
                    common_constraints TEXT,  -- JSON array
                    preferred_tools TEXT,     -- JSON array
                    
                    -- Statistics
                    total_sessions INTEGER DEFAULT 0,
                    total_discoveries INTEGER DEFAULT 0,
                    total_queries INTEGER DEFAULT 0,
                    
                    -- Behaviour analysis
                    avg_session_duration_minutes REAL DEFAULT 0,
                    most_used_mode TEXT,
                    discovery_success_rate REAL DEFAULT 0,
                    
                    -- Personalisation data
                    learning_style TEXT,  -- 'exploratory', 'systematic', 'pragmatic'
                    expertise_level TEXT DEFAULT 'intermediate',  -- 'beginner', 'intermediate', 'expert'
                    research_focus TEXT,  -- Current primary research area
                    
                    -- Privacy settings
                    data_retention_days INTEGER DEFAULT 365,
                    share_discoveries BOOLEAN DEFAULT 0
                )
            """)
            
            # User sessions table
            conn.execute("""
                CREATE TABLE IF NOT EXISTS user_sessions (
                    session_id TEXT PRIMARY KEY,
                    user_id TEXT NOT NULL,
                    started_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                    ended_at TIMESTAMP,
                    
                    -- Session context
                    initial_query TEXT,
                    research_focus TEXT,
                    agent_mode TEXT DEFAULT 'rigorous',
                    
                    -- Session outcomes
                    discoveries_made INTEGER DEFAULT 0,
                    queries_processed INTEGER DEFAULT 0,
                    tools_used TEXT,  -- JSON array
                    success_rate REAL DEFAULT 0,
                    
                    -- Performance metrics
                    avg_response_time_seconds REAL DEFAULT 0,
                    cache_hit_rate REAL DEFAULT 0,
                    
                    FOREIGN KEY (user_id) REFERENCES user_profiles(user_id)
                )
            """)
            
            # Research interests tracking
            conn.execute("""
                CREATE TABLE IF NOT EXISTS research_interests (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    user_id TEXT NOT NULL,
                    interest TEXT NOT NULL,
                    confidence REAL DEFAULT 1.0,  -- How confident we are this is an interest
                    frequency INTEGER DEFAULT 1,  -- How often mentioned
                    last_mentioned TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                    
                    FOREIGN KEY (user_id) REFERENCES user_profiles(user_id),
                    UNIQUE(user_id, interest)
                )
            """)
            
            # Common constraints tracking
            conn.execute("""
                CREATE TABLE IF NOT EXISTS user_constraints (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    user_id TEXT NOT NULL,
                    constraint_type TEXT NOT NULL,  -- 'element', 'property', 'application'
                    constraint_value TEXT NOT NULL,
                    frequency INTEGER DEFAULT 1,
                    last_used TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                    
                    FOREIGN KEY (user_id) REFERENCES user_profiles(user_id),
                    UNIQUE(user_id, constraint_type, constraint_value)
                )
            """)
            
            # Discovery history summary
            conn.execute("""
                CREATE TABLE IF NOT EXISTS discovery_history (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    user_id TEXT NOT NULL,
                    session_id TEXT NOT NULL,
                    discovery_id TEXT NOT NULL,
                    formula TEXT NOT NULL,
                    application TEXT,
                    formation_energy REAL,
                    discovered_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                    synthesis_method TEXT,
                    
                    FOREIGN KEY (user_id) REFERENCES user_profiles(user_id),
                    FOREIGN KEY (session_id) REFERENCES user_sessions(session_id)
                )
            """)
            
            # Create indices for performance
            conn.execute("CREATE INDEX IF NOT EXISTS idx_user_sessions_user_id ON user_sessions(user_id)")
            conn.execute("CREATE INDEX IF NOT EXISTS idx_research_interests_user_id ON research_interests(user_id)")
            conn.execute("CREATE INDEX IF NOT EXISTS idx_user_constraints_user_id ON user_constraints(user_id)")
            conn.execute("CREATE INDEX IF NOT EXISTS idx_discovery_history_user_id ON discovery_history(user_id)")
            
        logger.info("Database schema initialised successfully")
    
    async def create_user_profile(self, user_id: str, initial_preferences: Optional[Dict] = None) -> bool:
        """
        Create new user profile.
        
        Args:
            user_id: Unique user identifier
            initial_preferences: Initial user preferences
            
        Returns:
            True if created successfully
        """
        try:
            with self.get_connection() as conn:
                # Check if user already exists
                existing = conn.execute(
                    "SELECT user_id FROM user_profiles WHERE user_id = ?",
                    (user_id,)
                ).fetchone()
                
                if existing:
                    logger.debug(f"User profile {user_id} already exists")
                    return True
                
                # Set defaults
                prefs = initial_preferences or {}
                
                conn.execute("""
                    INSERT INTO user_profiles (
                        user_id, preferred_mode, output_format, reasoning_depth,
                        include_visualisations, research_interests, common_constraints,
                        preferred_tools, expertise_level, research_focus
                    ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
                """, (
                    user_id,
                    prefs.get('preferred_mode', 'rigorous'),
                    prefs.get('output_format', 'detailed'),
                    prefs.get('reasoning_depth', 'standard'),
                    prefs.get('include_visualisations', True),
                    json.dumps(prefs.get('research_interests', [])),
                    json.dumps(prefs.get('common_constraints', [])),
                    json.dumps(prefs.get('preferred_tools', [])),
                    prefs.get('expertise_level', 'intermediate'),
                    prefs.get('research_focus', '')
                ))
                
                logger.info(f"Created user profile: {user_id}")
                return True
                
        except Exception as e:
            logger.error(f"Failed to create user profile {user_id}: {e}")
            return False
    
    async def get_user_profile(self, user_id: str) -> Optional[Dict[str, Any]]:
        """
        Get complete user profile.
        
        Args:
            user_id: User identifier
            
        Returns:
            User profile dictionary or None
        """
        try:
            with self.get_connection() as conn:
                result = conn.execute("""
                    SELECT * FROM user_profiles WHERE user_id = ?
                """, (user_id,)).fetchone()
                
                if not result:
                    return None
                
                # Convert to dict and parse JSON fields
                profile = dict(result)
                
                # Parse JSON fields
                for field in ['research_interests', 'common_constraints', 'preferred_tools']:
                    if profile[field]:
                        try:
                            profile[field] = json.loads(profile[field])
                        except (json.JSONDecodeError, TypeError):
                            profile[field] = []
                    else:
                        profile[field] = []
                
                # Convert boolean
                profile['include_visualisations'] = bool(profile['include_visualisations'])
                profile['share_discoveries'] = bool(profile['share_discoveries'])
                
                return profile
                
        except Exception as e:
            logger.error(f"Failed to get user profile {user_id}: {e}")
            return None
    
    async def update_user_preferences(self, user_id: str, preferences: Dict[str, Any]) -> bool:
        """
        Update user preferences.
        
        Args:
            user_id: User identifier
            preferences: Dictionary of preferences to update
            
        Returns:
            True if updated successfully
        """
        try:
            with self.get_connection() as conn:
                # Build dynamic update query
                updates = []
                values = []
                
                for key, value in preferences.items():
                    if key in ['research_interests', 'common_constraints', 'preferred_tools']:
                        # JSON fields
                        updates.append(f"{key} = ?")
                        values.append(json.dumps(value))
                    elif key in ['include_visualisations', 'share_discoveries']:
                        # Boolean fields
                        updates.append(f"{key} = ?")
                        values.append(1 if value else 0)
                    else:
                        # Regular fields
                        updates.append(f"{key} = ?")
                        values.append(value)
                
                if updates:
                    # Add last_active update
                    updates.append("last_active = CURRENT_TIMESTAMP")
                    values.append(user_id)
                    
                    query = f"UPDATE user_profiles SET {', '.join(updates)} WHERE user_id = ?"
                    conn.execute(query, values)
                    
                    logger.debug(f"Updated preferences for user {user_id}")
                    return True
                
                return False
                
        except Exception as e:
            logger.error(f"Failed to update preferences for {user_id}: {e}")
            return False
    
    async def track_research_interest(self, user_id: str, interest: str, confidence: float = 1.0) -> bool:
        """
        Track user research interest.
        
        Args:
            user_id: User identifier
            interest: Research interest (e.g., "perovskites", "batteries")
            confidence: Confidence level (0.0-1.0)
            
        Returns:
            True if tracked successfully
        """
        try:
            with self.get_connection() as conn:
                conn.execute("""
                    INSERT INTO research_interests (user_id, interest, confidence, frequency, last_mentioned)
                    VALUES (?, ?, ?, 1, CURRENT_TIMESTAMP)
                    ON CONFLICT(user_id, interest) DO UPDATE SET
                        frequency = frequency + 1,
                        confidence = MAX(confidence, excluded.confidence),
                        last_mentioned = CURRENT_TIMESTAMP
                """, (user_id, interest.lower(), confidence))
                
                return True
                
        except Exception as e:
            logger.error(f"Failed to track research interest: {e}")
            return False
    
    async def track_constraint_usage(self, user_id: str, constraint_type: str, constraint_value: str) -> bool:
        """
        Track user constraint usage patterns.
        
        Args:
            user_id: User identifier
            constraint_type: Type of constraint ('element', 'property', 'application')
            constraint_value: Constraint value
            
        Returns:
            True if tracked successfully
        """
        try:
            with self.get_connection() as conn:
                conn.execute("""
                    INSERT INTO user_constraints (user_id, constraint_type, constraint_value, frequency, last_used)
                    VALUES (?, ?, ?, 1, CURRENT_TIMESTAMP)
                    ON CONFLICT(user_id, constraint_type, constraint_value) DO UPDATE SET
                        frequency = frequency + 1,
                        last_used = CURRENT_TIMESTAMP
                """, (user_id, constraint_type, constraint_value.lower()))
                
                return True
                
        except Exception as e:
            logger.error(f"Failed to track constraint usage: {e}")
            return False
    
    async def start_session(self, session_id: str, user_id: str, initial_query: str, agent_mode: str = 'rigorous') -> bool:
        """
        Record the start of a new session.
        
        Args:
            session_id: Session identifier
            user_id: User identifier
            initial_query: User's initial query
            agent_mode: Agent mode for this session
            
        Returns:
            True if recorded successfully
        """
        try:
            with self.get_connection() as conn:
                # Extract research focus from query
                research_focus = self._extract_research_focus(initial_query)
                
                conn.execute("""
                    INSERT INTO user_sessions (
                        session_id, user_id, initial_query, research_focus, agent_mode
                    ) VALUES (?, ?, ?, ?, ?)
                """, (session_id, user_id, initial_query, research_focus, agent_mode))
                
                # Update user profile session count
                conn.execute("""
                    UPDATE user_profiles 
                    SET total_sessions = total_sessions + 1,
                        last_active = CURRENT_TIMESTAMP
                    WHERE user_id = ?
                """, (user_id,))
                
                logger.debug(f"Started session {session_id} for user {user_id}")
                return True
                
        except Exception as e:
            logger.error(f"Failed to start session: {e}")
            return False
    
    async def end_session(self, session_id: str, session_metrics: Dict[str, Any]) -> bool:
        """
        Record the end of a session with metrics.
        
        Args:
            session_id: Session identifier
            session_metrics: Performance and outcome metrics
            
        Returns:
            True if recorded successfully
        """
        try:
            with self.get_connection() as conn:
                # Update session with end metrics
                conn.execute("""
                    UPDATE user_sessions SET
                        ended_at = CURRENT_TIMESTAMP,
                        discoveries_made = ?,
                        queries_processed = ?,
                        tools_used = ?,
                        success_rate = ?,
                        avg_response_time_seconds = ?,
                        cache_hit_rate = ?
                    WHERE session_id = ?
                """, (
                    session_metrics.get('discoveries_made', 0),
                    session_metrics.get('queries_processed', 0),
                    json.dumps(session_metrics.get('tools_used', [])),
                    session_metrics.get('success_rate', 0.0),
                    session_metrics.get('avg_response_time', 0.0),
                    session_metrics.get('cache_hit_rate', 0.0),
                    session_id
                ))
                
                # Update user profile statistics
                session = conn.execute("""
                    SELECT user_id, discoveries_made, 
                           (julianday(ended_at) - julianday(started_at)) * 24 * 60 as duration_minutes
                    FROM user_sessions WHERE session_id = ?
                """, (session_id,)).fetchone()
                
                if session:
                    conn.execute("""
                        UPDATE user_profiles SET
                            total_discoveries = total_discoveries + ?,
                            total_queries = total_queries + ?,
                            avg_session_duration_minutes = (
                                (avg_session_duration_minutes * (total_sessions - 1) + ?) / total_sessions
                            )
                        WHERE user_id = ?
                    """, (
                        session['discoveries_made'],
                        session_metrics.get('queries_processed', 0),
                        session['duration_minutes'],
                        session['user_id']
                    ))
                
                logger.debug(f"Ended session {session_id}")
                return True
                
        except Exception as e:
            logger.error(f"Failed to end session: {e}")
            return False
    
    async def record_discovery(self, user_id: str, session_id: str, discovery: Dict[str, Any]) -> bool:
        """
        Record a discovery in user's history.
        
        Args:
            user_id: User identifier
            session_id: Session identifier
            discovery: Discovery details
            
        Returns:
            True if recorded successfully
        """
        try:
            with self.get_connection() as conn:
                conn.execute("""
                    INSERT INTO discovery_history (
                        user_id, session_id, discovery_id, formula, application,
                        formation_energy, synthesis_method
                    ) VALUES (?, ?, ?, ?, ?, ?, ?)
                """, (
                    user_id,
                    session_id,
                    discovery.get('id', ''),
                    discovery['formula'],
                    discovery.get('application', ''),
                    discovery.get('formation_energy'),
                    discovery.get('synthesis_route', '')
                ))
                
                return True
                
        except Exception as e:
            logger.error(f"Failed to record discovery: {e}")
            return False
    
    async def get_user_context_for_agent(self, user_id: str) -> Dict[str, Any]:
        """
        Get user context formatted for agent personalisation.
        
        Args:
            user_id: User identifier
            
        Returns:
            Context dictionary for agent
        """
        try:
            with self.get_connection() as conn:
                # Get profile
                profile = await self.get_user_profile(user_id)
                if not profile:
                    return {}
                
                # Get top research interests
                interests = conn.execute("""
                    SELECT interest, frequency, confidence
                    FROM research_interests
                    WHERE user_id = ?
                    ORDER BY frequency * confidence DESC
                    LIMIT 5
                """, (user_id,)).fetchall()
                
                # Get common constraints
                constraints = conn.execute("""
                    SELECT constraint_type, constraint_value, frequency
                    FROM user_constraints
                    WHERE user_id = ?
                    ORDER BY frequency DESC
                    LIMIT 10
                """, (user_id,)).fetchall()
                
                # Get recent discoveries
                recent_discoveries = conn.execute("""
                    SELECT formula, application, discovered_at
                    FROM discovery_history
                    WHERE user_id = ?
                    ORDER BY discovered_at DESC
                    LIMIT 5
                """, (user_id,)).fetchall()
                
                return {
                    "user_id": user_id,
                    "preferences": {
                        "mode": profile["preferred_mode"],
                        "output_format": profile["output_format"],
                        "reasoning_depth": profile["reasoning_depth"],
                        "include_visualisations": profile["include_visualisations"]
                    },
                    "research_profile": {
                        "expertise_level": profile["expertise_level"],
                        "learning_style": profile["learning_style"],
                        "current_focus": profile["research_focus"],
                        "interests": [dict(r) for r in interests],
                        "common_constraints": [dict(r) for r in constraints]
                    },
                    "activity": {
                        "total_sessions": profile["total_sessions"],
                        "total_discoveries": profile["total_discoveries"],
                        "avg_session_duration": profile["avg_session_duration_minutes"],
                        "recent_discoveries": [dict(r) for r in recent_discoveries]
                    }
                }
                
        except Exception as e:
            logger.error(f"Failed to get user context: {e}")
            return {}
    
    async def suggest_next_research(self, user_id: str, limit: int = 5) -> List[str]:
        """
        Suggest next research directions based on user history.
        
        Args:
            user_id: User identifier
            limit: Maximum suggestions
            
        Returns:
            List of research suggestions
        """
        try:
            with self.get_connection() as conn:
                # Get user's top interests and recent discoveries
                interests = conn.execute("""
                    SELECT interest, confidence
                    FROM research_interests
                    WHERE user_id = ?
                    ORDER BY frequency * confidence DESC
                    LIMIT 3
                """, (user_id,)).fetchall()
                
                recent_materials = conn.execute("""
                    SELECT DISTINCT formula
                    FROM discovery_history
                    WHERE user_id = ? AND discovered_at > datetime('now', '-30 days')
                    LIMIT 5
                """, (user_id,)).fetchall()
                
                suggestions = []
                
                # Interest-based suggestions
                for interest in interests:
                    suggestions.append(f"Explore new {interest['interest']} compositions")
                
                # Material-based suggestions
                for material in recent_materials:
                    suggestions.append(f"Find materials similar to {material['formula']}")
                
                return suggestions[:limit]
                
        except Exception as e:
            logger.error(f"Failed to generate research suggestions: {e}")
            return []
    
    def _extract_research_focus(self, query: str) -> str:
        """Extract research focus from query text."""
        query_lower = query.lower()
        
        # Common research areas
        areas = {
            'battery': ['battery', 'cathode', 'anode', 'electrolyte', 'li-ion', 'lithium'],
            'solar': ['solar', 'photovoltaic', 'photocat', 'light'],
            'catalyst': ['catalyst', 'catalytic', 'reaction'],
            'superconductor': ['supercond', 'superconduct'],
            'thermoelectric': ['thermoelectric', 'thermoelec'],
            'magnetic': ['magnet', 'ferromagnet', 'antiferromagnet'],
            'structural': ['concrete', 'steel', 'composite', 'construction'],
            'electronic': ['electronic', 'semiconductor', 'conductor']
        }
        
        for area, keywords in areas.items():
            if any(keyword in query_lower for keyword in keywords):
                return area
        
        return 'general'
    
    async def get_user_statistics(self, user_id: str) -> Dict[str, Any]:
        """Get comprehensive user statistics."""
        try:
            with self.get_connection() as conn:
                profile = await self.get_user_profile(user_id)
                if not profile:
                    return {}
                
                # Session statistics
                session_stats = conn.execute("""
                    SELECT 
                        COUNT(*) as total_sessions,
                        AVG(discoveries_made) as avg_discoveries_per_session,
                        AVG(success_rate) as avg_success_rate,
                        MAX(ended_at) as last_session
                    FROM user_sessions WHERE user_id = ?
                """, (user_id,)).fetchone()
                
                # Discovery trends
                discovery_trends = conn.execute("""
                    SELECT 
                        DATE(discovered_at) as date,
                        COUNT(*) as discoveries
                    FROM discovery_history 
                    WHERE user_id = ? AND discovered_at > datetime('now', '-30 days')
                    GROUP BY DATE(discovered_at)
                    ORDER BY date
                """, (user_id,)).fetchall()
                
                return {
                    "profile": profile,
                    "session_statistics": dict(session_stats) if session_stats else {},
                    "discovery_trends": [dict(r) for r in discovery_trends],
                    "generated_at": datetime.now().isoformat()
                }
                
        except Exception as e:
            logger.error(f"Failed to get user statistics: {e}")
            return {}
    
    def cleanup_old_data(self, days: int = 365) -> int:
        """Clean up old user data based on retention policy."""
        try:
            with self.get_connection() as conn:
                cutoff = datetime.now() - timedelta(days=days)
                
                # Clean old sessions
                cursor = conn.execute("""
                    DELETE FROM user_sessions 
                    WHERE ended_at < ? OR (started_at < ? AND ended_at IS NULL)
                """, (cutoff, cutoff))
                
                sessions_cleaned = cursor.rowcount
                
                # Clean old discovery history
                cursor = conn.execute("""
                    DELETE FROM discovery_history WHERE discovered_at < ?
                """, (cutoff,))
                
                discoveries_cleaned = cursor.rowcount
                
                # Clean old research interests (low frequency)
                cursor = conn.execute("""
                    DELETE FROM research_interests 
                    WHERE last_mentioned < ? AND frequency < 3
                """, (cutoff,))
                
                interests_cleaned = cursor.rowcount
                
                total_cleaned = sessions_cleaned + discoveries_cleaned + interests_cleaned
                
                logger.info(f"Cleaned {total_cleaned} old records (sessions: {sessions_cleaned}, "
                           f"discoveries: {discoveries_cleaned}, interests: {interests_cleaned})")
                
                return total_cleaned
                
        except Exception as e:
            logger.error(f"Failed to cleanup old data: {e}")
            return 0
    
    def get_database_stats(self) -> Dict[str, Any]:
        """Get database statistics."""
        try:
            with self.get_connection() as conn:
                stats = {}
                
                # Table counts
                for table in ['user_profiles', 'user_sessions', 'research_interests', 'user_constraints', 'discovery_history']:
                    count = conn.execute(f"SELECT COUNT(*) as count FROM {table}").fetchone()
                    stats[f"{table}_count"] = count['count']
                
                # Database size
                stats["database_path"] = str(self.db_path)
                stats["database_size_mb"] = self.db_path.stat().st_size / (1024 * 1024)
                
                return stats
                
        except Exception as e:
            logger.error(f"Failed to get database stats: {e}")
            return {"error": str(e)}