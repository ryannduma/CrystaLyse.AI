"""
Dynamic Mode Adaptation for Crystalyse

Monitors execution and enables runtime mode switching based on user feedback
and execution context. This creates a truly responsive system that adapts
to user needs in real-time.
"""

import logging
from collections.abc import Callable
from dataclasses import dataclass
from datetime import datetime
from typing import Any

# Import the global mode manager to check if mode is locked
try:
    from ..agents.mode_injector import DynamicModeSuppressor, GlobalModeManager
except ImportError:
    # Fallback if mode injector is not available
    class GlobalModeManager:
        @classmethod
        def is_locked(cls):
            return False

    class DynamicModeSuppressor:
        @staticmethod
        def should_suppress_dynamic_switching():
            return False

        @staticmethod
        def log_suppressed_switch(attempted_mode, reason):
            pass


logger = logging.getLogger(__name__)


@dataclass
class AdaptationEvent:
    """Records a mode adaptation event for learning"""

    timestamp: datetime
    previous_mode: str
    new_mode: str
    trigger: str  # user_feedback, confidence_low, error_rate, etc.
    reason: str
    confidence: float


class DynamicModeAdapter:
    """
    Handles mode switching during execution based on user feedback
    and execution context signals.
    """

    def __init__(self):
        self.adaptation_history: list[AdaptationEvent] = []
        self.current_execution_id: str | None = None

        # Adaptation signal patterns
        self.adaptation_signals = {
            "wants_speed": {
                "patterns": [
                    "faster",
                    "quicker",
                    "taking too long",
                    "speed up",
                    "just give me",
                    "hurry",
                    "quick results",
                    "skip details",
                ],
                "target_mode": "creative",
                "confidence": 0.8,
            },
            "wants_depth": {
                "patterns": [
                    "more detail",
                    "deeper",
                    "validate",
                    "verify",
                    "research",
                    "thorough",
                    "comprehensive",
                    "explain more",
                    "check this",
                ],
                "target_mode": "rigorous",
                "confidence": 0.85,
            },
            "wants_simplicity": {
                "patterns": [
                    "simpler",
                    "confusing",
                    "too technical",
                    "basic",
                    "easier",
                    "don't understand",
                    "lost",
                    "explain simply",
                    "layman",
                ],
                "target_mode": "creative",
                "confidence": 0.7,
            },
            "satisfied": {
                "patterns": [
                    "perfect",
                    "exactly",
                    "that's right",
                    "good",
                    "thanks",
                    "great",
                    "awesome",
                    "yes that's it",
                ],
                "target_mode": None,  # No change
                "confidence": 0.9,
            },
            "frustrated": {
                "patterns": [
                    "wrong",
                    "not what I",
                    "incorrect",
                    "no that's not",
                    "frustrated",
                    "annoying",
                    "useless",
                ],
                "target_mode": "adaptive",  # Reset to balanced
                "confidence": 0.6,
            },
        }

    async def monitor_and_adapt(
        self,
        current_mode: str,
        execution_context: dict[str, Any],
        user_feedback: str | None = None,
    ) -> dict[str, Any] | None:
        """
        Monitor execution and suggest mode switches when beneficial.

        Args:
            current_mode: Current execution mode
            execution_context: Context about current execution
            user_feedback: Optional user feedback text

        Returns:
            None if no switch needed, or dict with new mode configuration
        """
        # FIRST CHECK: If mode is locked (explicitly set by user), suppress all dynamic switching
        if DynamicModeSuppressor.should_suppress_dynamic_switching():
            logger.info(f"Dynamic mode switching suppressed - mode is locked to '{current_mode}'")
            return None

        # Check automatic switching conditions first
        auto_switch = self._check_automatic_conditions(current_mode, execution_context)
        if auto_switch:
            DynamicModeSuppressor.log_suppressed_switch(
                auto_switch["new_mode"], auto_switch["reason"]
            )
            return auto_switch

        # If user provided feedback, analyse it
        if user_feedback:
            feedback_switch = self._analyze_user_feedback(user_feedback, current_mode)
            if feedback_switch:
                DynamicModeSuppressor.log_suppressed_switch(
                    feedback_switch["new_mode"], "user_feedback"
                )
                return feedback_switch

        # Check execution performance metrics
        performance_switch = self._check_performance_metrics(current_mode, execution_context)
        if performance_switch:
            DynamicModeSuppressor.log_suppressed_switch(
                performance_switch["new_mode"], "performance_metrics"
            )
            return performance_switch

        return None

    def _check_automatic_conditions(
        self, current_mode: str, context: dict[str, Any]
    ) -> dict[str, Any] | None:
        """Check for conditions that warrant automatic mode switching."""

        # Low confidence in creative mode → Switch to rigorous
        if (
            current_mode == "creative"
            and context.get("confidence_score", 1.0) < 0.5
            and not context.get("time_critical", False)
        ):
            return {
                "new_mode": "rigorous",
                "new_model": "o3",
                "reason": "Low confidence in results, switching to thorough validation",
                "trigger": "confidence_low",
                "confidence": 0.85,
            }

        # Novel chemistry detected → Switch to rigorous
        if current_mode != "rigorous" and context.get("novel_chemistry_detected", False):
            return {
                "new_mode": "rigorous",
                "new_model": "o3",
                "reason": "Novel chemistry detected requiring careful validation",
                "trigger": "novel_chemistry",
                "confidence": 0.9,
            }

        # Error rate too high → Switch to more careful mode
        error_rate = context.get("error_rate", 0.0)
        if error_rate > 0.3 and current_mode == "creative":
            return {
                "new_mode": "adaptive",
                "new_model": "o4-mini",
                "reason": f"High error rate ({error_rate:.1%}), switching to balanced approach",
                "trigger": "error_rate",
                "confidence": 0.7,
            }

        # Safety critical detected mid-execution
        if context.get("safety_critical_detected", False) and current_mode != "rigorous":
            return {
                "new_mode": "rigorous",
                "new_model": "o3",
                "reason": "Safety-critical aspects detected, requires rigorous validation",
                "trigger": "safety_critical",
                "confidence": 0.95,
            }

        return None

    def _analyze_user_feedback(self, feedback: str, current_mode: str) -> dict[str, Any] | None:
        """Detect mode switching signals in user feedback."""

        feedback_lower = feedback.lower()

        # Check each signal type
        best_match = None
        highest_confidence = 0.0

        for signal_type, config in self.adaptation_signals.items():
            patterns = config["patterns"]
            matches = sum(1 for pattern in patterns if pattern in feedback_lower)

            if matches > 0:
                # Calculate match confidence based on pattern strength, not just count
                # Single strong match should be sufficient
                base_confidence = config["confidence"]
                # Boost confidence for multiple matches, but don't penalize single matches
                match_confidence = min(0.95, base_confidence + (matches - 1) * 0.1)

                if match_confidence > highest_confidence:
                    highest_confidence = match_confidence
                    best_match = signal_type

        # Apply the best matching signal
        if best_match and highest_confidence > 0.5:  # Lower threshold for better responsiveness
            config = self.adaptation_signals[best_match]
            target_mode = config["target_mode"]

            # Don't suggest switching if already in target mode or no change needed
            if target_mode is None or target_mode == current_mode:
                return None

            # Determine the appropriate model for the mode
            model_map = {"creative": "o4-mini", "rigorous": "o3", "adaptive": "o4-mini"}

            return {
                "new_mode": target_mode,
                "new_model": model_map.get(target_mode, "o4-mini"),
                "reason": f"User feedback indicates desire for {best_match.replace('_', ' ')}",
                "trigger": f"user_feedback_{best_match}",
                "confidence": highest_confidence,
            }

        return None

    def _check_performance_metrics(
        self, current_mode: str, context: dict[str, Any]
    ) -> dict[str, Any] | None:
        """Check execution performance metrics for adaptation needs."""

        # Execution taking too long
        execution_time = context.get("execution_time_seconds", 0)
        expected_time = context.get("expected_time_seconds", 60)

        if (
            execution_time > expected_time * 2
            and current_mode == "rigorous"
            and not context.get("complexity_acknowledged", False)
        ):
            return {
                "new_mode": "adaptive",
                "new_model": "o4-mini",
                "reason": "Execution time exceeding expectations, offering faster approach",
                "trigger": "performance_time",
                "confidence": 0.7,
            }

        # Memory usage concerns
        memory_usage = context.get("memory_usage_mb", 0)
        if memory_usage > 2000 and current_mode == "rigorous":
            return {
                "new_mode": "adaptive",
                "new_model": "o4-mini",
                "reason": "High memory usage detected, switching to more efficient approach",
                "trigger": "performance_memory",
                "confidence": 0.65,
            }

        return None

    def record_adaptation(
        self, previous_mode: str, new_mode: str, trigger: str, reason: str, confidence: float
    ):
        """Record an adaptation event for learning."""

        event = AdaptationEvent(
            timestamp=datetime.now(),
            previous_mode=previous_mode,
            new_mode=new_mode,
            trigger=trigger,
            reason=reason,
            confidence=confidence,
        )

        self.adaptation_history.append(event)
        logger.info(f"Mode adaptation: {previous_mode} → {new_mode} ({reason})")

    def get_adaptation_statistics(self) -> dict[str, Any]:
        """Get statistics about adaptation patterns."""

        if not self.adaptation_history:
            return {"total_adaptations": 0}

        stats = {
            "total_adaptations": len(self.adaptation_history),
            "triggers": {},
            "mode_transitions": {},
            "average_confidence": 0.0,
        }

        # Count triggers
        for event in self.adaptation_history:
            stats["triggers"][event.trigger] = stats["triggers"].get(event.trigger, 0) + 1

            # Count mode transitions
            transition = f"{event.previous_mode}→{event.new_mode}"
            stats["mode_transitions"][transition] = stats["mode_transitions"].get(transition, 0) + 1

        # Calculate average confidence
        stats["average_confidence"] = sum(e.confidence for e in self.adaptation_history) / len(
            self.adaptation_history
        )

        return stats


class AdaptiveExecutionMonitor:
    """
    Monitors agent execution and provides adaptation hooks.
    """

    def __init__(self, mode_adapter: DynamicModeAdapter):
        self.mode_adapter = mode_adapter
        self.current_mode: str = "adaptive"
        self.current_model: str = "o4-mini"
        self.execution_context: dict[str, Any] = {}
        self.adaptation_callback: Callable | None = None

    async def check_adaptation_needed(
        self, checkpoint: str, metrics: dict[str, Any]
    ) -> dict[str, Any] | None:
        """
        Check if mode adaptation is needed at a specific checkpoint.

        Args:
            checkpoint: Name of the execution checkpoint
            metrics: Current execution metrics

        Returns:
            Adaptation configuration if switch needed
        """
        # Update execution context
        self.execution_context.update(metrics)
        self.execution_context["checkpoint"] = checkpoint

        # Check for adaptation
        adaptation = await self.mode_adapter.monitor_and_adapt(
            self.current_mode, self.execution_context
        )

        if adaptation and self.adaptation_callback:
            # Notify about adaptation
            await self.adaptation_callback(adaptation)

        return adaptation

    async def apply_user_feedback(self, feedback: str) -> dict[str, Any] | None:
        """
        Process user feedback and check for adaptation needs.

        Args:
            feedback: User feedback text

        Returns:
            Adaptation configuration if switch needed
        """
        adaptation = await self.mode_adapter.monitor_and_adapt(
            self.current_mode, self.execution_context, user_feedback=feedback
        )

        if adaptation:
            # Record the adaptation
            self.mode_adapter.record_adaptation(
                self.current_mode,
                adaptation["new_mode"],
                adaptation["trigger"],
                adaptation["reason"],
                adaptation["confidence"],
            )

            # Update current state
            self.current_mode = adaptation["new_mode"]
            self.current_model = adaptation["new_model"]

            if self.adaptation_callback:
                await self.adaptation_callback(adaptation)

        return adaptation
