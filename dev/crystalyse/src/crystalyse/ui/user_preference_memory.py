"""
User Preference Memory for CrystaLyse.AI

Implements cross-session learning to personalize the clarification and mode selection
experience based on user interaction patterns and preferences.
"""

import json
import logging
from pathlib import Path
from typing import Dict, Any, List, Optional
from dataclasses import dataclass, asdict, field
from datetime import datetime

from ..workspace.workspace_tools import QueryAnalysis

logger = logging.getLogger(__name__)


@dataclass
class UserInteractionRecord:
    """Records a single user interaction for learning"""
    timestamp: datetime
    query: str
    expertise_detected: str
    specificity_score: float
    clarification_method: str
    chosen_mode: str
    adaptations_made: List[str] = field(default_factory=list)
    completion_time_seconds: float = 0.0
    user_satisfaction: float = 0.5  # 0.0 to 1.0
    domain_area: str = ""


@dataclass
class UserProfile:
    """Comprehensive user profile for personalisation"""
    user_id: str
    creation_date: datetime
    last_updated: datetime
    
    # Expertise tracking
    average_expertise_level: float = 0.5  # 0.0=novice, 1.0=expert
    domain_expertise: Dict[str, float] = field(default_factory=dict)
    
    # Preference tracking
    preferred_clarification_style: str = "focused_questions"
    preferred_mode: str = "adaptive"
    speed_preference: float = 0.5  # 0.0=thorough, 1.0=fast
    
    # Usage patterns
    interaction_count: int = 0
    successful_modes: Dict[str, List[float]] = field(default_factory=dict)
    adaptation_patterns: Dict[str, int] = field(default_factory=dict)
    
    # Learning metrics
    confidence_threshold: float = 0.75
    skip_clarification_rate: float = 0.0
    

class UserPreferenceMemory:
    """
    Manages user preference learning and personalisation across sessions.
    """
    
    def __init__(self, memory_dir: Optional[Path] = None):
        # Use CrystaLyse's standard memory location
        if memory_dir is None:
            memory_dir = Path.home() / ".crystalyse" / "user_preferences"
        
        self.memory_dir = memory_dir
        self.memory_dir.mkdir(parents=True, exist_ok=True)
        
        self.profiles: Dict[str, UserProfile] = {}
        self.interaction_history: List[UserInteractionRecord] = []
        
        # Load existing profiles
        self._load_profiles()
    
    def _load_profiles(self):
        """Load existing user profiles from disk."""
        try:
            profiles_file = self.memory_dir / "user_profiles.json"
            if profiles_file.exists():
                with open(profiles_file, 'r') as f:
                    data = json.load(f)
                    
                for user_id, profile_data in data.items():
                    # Convert string dates back to datetime
                    profile_data['creation_date'] = datetime.fromisoformat(profile_data['creation_date'])
                    profile_data['last_updated'] = datetime.fromisoformat(profile_data['last_updated'])
                    
                    self.profiles[user_id] = UserProfile(**profile_data)
                    
                logger.info(f"Loaded {len(self.profiles)} user profiles")
        except Exception as e:
            logger.warning(f"Failed to load user profiles: {e}")
    
    def _save_profiles(self):
        """Save user profiles to disk."""
        try:
            profiles_file = self.memory_dir / "user_profiles.json"
            
            # Convert profiles to serializable format
            profiles_data = {}
            for user_id, profile in self.profiles.items():
                profile_dict = asdict(profile)
                # Convert datetime to string
                profile_dict['creation_date'] = profile.creation_date.isoformat()
                profile_dict['last_updated'] = profile.last_updated.isoformat()
                profiles_data[user_id] = profile_dict
            
            with open(profiles_file, 'w') as f:
                json.dump(profiles_data, f, indent=2)
                
            logger.debug(f"Saved {len(self.profiles)} user profiles")
        except Exception as e:
            logger.error(f"Failed to save user profiles: {e}")
    
    def get_or_create_profile(self, user_id: str) -> UserProfile:
        """Get existing profile or create new one."""
        if user_id not in self.profiles:
            self.profiles[user_id] = UserProfile(
                user_id=user_id,
                creation_date=datetime.now(),
                last_updated=datetime.now()
            )
            logger.info(f"Created new user profile for {user_id}")
        
        return self.profiles[user_id]
    
    def learn_from_interaction(self, user_id: str, interaction: UserInteractionRecord):
        """Update user profile based on a completed interaction."""
        profile = self.get_or_create_profile(user_id)
        
        # Update basic metrics
        profile.interaction_count += 1
        profile.last_updated = datetime.now()
        
        # Update expertise level (running average)
        expertise_numeric = self._expertise_to_numeric(interaction.expertise_detected)
        if profile.interaction_count == 1:
            profile.average_expertise_level = expertise_numeric
        else:
            # Weighted average favoring recent interactions
            weight = min(0.3, 1.0 / profile.interaction_count)
            profile.average_expertise_level = (
                (1 - weight) * profile.average_expertise_level + 
                weight * expertise_numeric
            )
        
        # Update domain expertise
        if interaction.domain_area:
            if interaction.domain_area not in profile.domain_expertise:
                profile.domain_expertise[interaction.domain_area] = expertise_numeric
            else:
                # Running average for domain
                current = profile.domain_expertise[interaction.domain_area]
                profile.domain_expertise[interaction.domain_area] = (
                    0.8 * current + 0.2 * expertise_numeric
                )
        
        # Update mode preferences
        if interaction.user_satisfaction > 0.7:
            if interaction.chosen_mode not in profile.successful_modes:
                profile.successful_modes[interaction.chosen_mode] = []
            profile.successful_modes[interaction.chosen_mode].append(interaction.user_satisfaction)
        
        # Update speed preferences
        if interaction.adaptations_made:
            for adaptation in interaction.adaptations_made:
                if "faster" in adaptation.lower() or "speed" in adaptation.lower():
                    profile.speed_preference = min(1.0, profile.speed_preference + 0.1)
                elif "thorough" in adaptation.lower() or "detail" in adaptation.lower():
                    profile.speed_preference = max(0.0, profile.speed_preference - 0.1)
        
        # Update clarification preferences
        if interaction.user_satisfaction > 0.8:
            profile.preferred_clarification_style = interaction.clarification_method
        
        # Record the interaction
        self.interaction_history.append(interaction)
        
        # Save updated profile
        self._save_profiles()
        
        logger.debug(f"Updated profile for {user_id}: expertise={profile.average_expertise_level:.2f}, speed_pref={profile.speed_preference:.2f}")
    
    def get_personalized_strategy(self, user_id: str, analysis) -> Dict[str, Any]:
        """Get personalized clarification strategy based on user history."""
        profile = self.get_or_create_profile(user_id)
        
        # Start with defaults
        strategy = {
            "clarification_method": "focused_questions",
            "initial_mode": "adaptive",
            "confidence_threshold": 0.75,
            "skip_clarification": False,
            "personalization_confidence": 0.0
        }
        
        # Don't personalize for new users (< 3 interactions)
        if profile.interaction_count < 3:
            return strategy
        
        # Adjust based on learned preferences
        strategy["personalization_confidence"] = min(1.0, profile.interaction_count / 10.0)
        
        # Use preferred clarification style
        if profile.interaction_count > 5:
            strategy["clarification_method"] = profile.preferred_clarification_style
        
        # Adjust initial mode based on successful patterns
        if profile.successful_modes:
            best_mode = max(profile.successful_modes.keys(), 
                          key=lambda m: sum(profile.successful_modes[m]) / len(profile.successful_modes[m]))
            strategy["initial_mode"] = best_mode
        
        # Skip clarification for experienced users with consistent patterns
        if (profile.interaction_count > 10 and 
            profile.average_expertise_level > 0.8 and
            profile.skip_clarification_rate < 0.2):  # Low frustration with skipping
            
            # More aggressive skipping for learned experts
            if (analysis and 
                analysis.expertise_level == "expert" and 
                analysis.specificity_score > 0.7 and
                analysis.domain_confidence > 0.7):
                strategy["skip_clarification"] = True
                strategy["confidence_threshold"] = 0.6  # Lower threshold
        
        # Adjust for speed preferences
        if profile.speed_preference > 0.8:
            strategy["initial_mode"] = "creative"
            strategy["skip_clarification"] = True
        elif profile.speed_preference < 0.2:
            strategy["initial_mode"] = "rigorous"
        
        logger.info(f"Personalized strategy for {user_id}: {strategy}")
        return strategy
    
    def get_domain_expertise(self, user_id: str, domain: str) -> float:
        """Get user's expertise level for a specific domain."""
        profile = self.get_or_create_profile(user_id)
        return profile.domain_expertise.get(domain, profile.average_expertise_level)
    
    def record_user_satisfaction(self, user_id: str, satisfaction: float):
        """Record user satisfaction with the latest interaction."""
        if self.interaction_history:
            # Update the most recent interaction
            self.interaction_history[-1].user_satisfaction = satisfaction
            
            # Re-run learning with updated satisfaction
            self.learn_from_interaction(user_id, self.interaction_history[-1])
    
    def _expertise_to_numeric(self, expertise_level: str) -> float:
        """Convert expertise level string to numeric value."""
        mapping = {
            "novice": 0.2,
            "intermediate": 0.6,
            "expert": 0.9
        }
        return mapping.get(expertise_level, 0.5)
    
    def _numeric_to_expertise(self, numeric_level: float) -> str:
        """Convert numeric expertise to string level."""
        if numeric_level < 0.4:
            return "novice"
        elif numeric_level < 0.75:
            return "intermediate"
        else:
            return "expert"
    
    def get_user_statistics(self, user_id: str) -> Dict[str, Any]:
        """Get comprehensive statistics for a user."""
        profile = self.get_or_create_profile(user_id)
        
        stats = {
            "user_id": user_id,
            "interaction_count": profile.interaction_count,
            "expertise_level": self._numeric_to_expertise(profile.average_expertise_level),
            "expertise_score": profile.average_expertise_level,
            "preferred_mode": profile.preferred_mode,
            "speed_preference": profile.speed_preference,
            "domain_expertise": profile.domain_expertise,
            "successful_modes": {
                mode: sum(scores) / len(scores) 
                for mode, scores in profile.successful_modes.items()
            },
            "days_since_creation": (datetime.now() - profile.creation_date).days,
            "personalization_active": profile.interaction_count >= 3
        }
        
        return stats