"""
Agent Laboratory-style telemetry for CrystaLyse.AI
Tracks cost, latency, and performance metrics for all tool calls
"""

import time
import functools
import logging
import csv
from pathlib import Path
from typing import Dict, Any, Callable, Optional, List
from dataclasses import dataclass, asdict
from datetime import datetime

logger = logging.getLogger(__name__)

# OpenAI pricing (as of 2025) - update these as needed
PRICING = {
    "o4-mini": {
        "input": 0.15 / 1_000_000,   # $0.15 per 1M input tokens
        "output": 0.60 / 1_000_000   # $0.60 per 1M output tokens
    },
    "gpt-4o": {
        "input": 2.50 / 1_000_000,
        "output": 10.00 / 1_000_000
    }
}

@dataclass
class ToolCallTelemetry:
    """Single tool call telemetry record"""
    timestamp: str
    tool_name: str
    stage: str  # composition, structure, energy
    duration_seconds: float
    input_tokens: int
    output_tokens: int
    cost_usd: float
    success: bool
    error_type: Optional[str] = None
    model: str = "o4-mini"
    
    def to_dict(self) -> Dict[str, Any]:
        return asdict(self)


class AgentTelemetryCollector:
    """
    Collects telemetry data following Agent Laboratory patterns
    Saves to CSV for analysis and optimisation
    """
    
    def __init__(self, output_dir: Path = None):
        self.output_dir = output_dir or Path.home() / ".crystalyse" / "telemetry"
        self.output_dir.mkdir(parents=True, exist_ok=True)
        
        self.csv_file = self.output_dir / "tool_telemetry.csv"
        self.records = []
        
        # Initialise CSV file with headers
        self._init_csv()
        
    def _init_csv(self):
        """Initialise CSV file with headers if it doesn't exist"""
        if not self.csv_file.exists():
            with open(self.csv_file, 'w', newline='') as f:
                writer = csv.writer(f)
                writer.writerow([
                    'timestamp', 'tool_name', 'stage', 'duration_seconds',
                    'input_tokens', 'output_tokens', 'cost_usd', 'success',
                    'error_type', 'model'
                ])
    
    def record_tool_call(self, tool_name: str, stage: str, duration: float,
                        input_tokens: int, output_tokens: int, success: bool,
                        error_type: str = None, model: str = "o4-mini"):
        """Record a single tool call"""
        
        # Calculate cost
        pricing = PRICING.get(model, PRICING["o4-mini"])
        cost = (input_tokens * pricing["input"]) + (output_tokens * pricing["output"])
        
        record = ToolCallTelemetry(
            timestamp=datetime.now().isoformat(),
            tool_name=tool_name,
            stage=stage,
            duration_seconds=duration,
            input_tokens=input_tokens,
            output_tokens=output_tokens,
            cost_usd=cost,
            success=success,
            error_type=error_type,
            model=model
        )
        
        self.records.append(record)
        
        # Append to CSV
        with open(self.csv_file, 'a', newline='') as f:
            writer = csv.writer(f)
            writer.writerow([
                record.timestamp, record.tool_name, record.stage, record.duration_seconds,
                record.input_tokens, record.output_tokens, record.cost_usd, record.success,
                record.error_type, record.model
            ])
        
        # Log expensive calls
        if cost > 0.10:
            logger.warning(f"Expensive tool call: {tool_name} cost ${cost:.3f}")
        
        logger.info(f"Tool {tool_name}: {duration:.3f}s, ${cost:.4f}, {success}")
    
    def get_summary(self) -> Dict[str, Any]:
        """Get telemetry summary"""
        if not self.records:
            return {"message": "No telemetry data"}
        
        total_cost = sum(r.cost_usd for r in self.records)
        total_time = sum(r.duration_seconds for r in self.records)
        success_rate = sum(1 for r in self.records if r.success) / len(self.records)
        
        # Find bottlenecks
        by_tool = {}
        for record in self.records:
            if record.tool_name not in by_tool:
                by_tool[record.tool_name] = {"calls": 0, "time": 0, "cost": 0}
            by_tool[record.tool_name]["calls"] += 1
            by_tool[record.tool_name]["time"] += record.duration_seconds
            by_tool[record.tool_name]["cost"] += record.cost_usd
        
        # Find most expensive tool
        most_expensive = max(by_tool.items(), key=lambda x: x[1]["cost"])
        slowest_tool = max(by_tool.items(), key=lambda x: x[1]["time"] / x[1]["calls"])
        
        return {
            "total_calls": len(self.records),
            "total_cost_usd": total_cost,
            "total_time_seconds": total_time,
            "success_rate": success_rate,
            "most_expensive_tool": most_expensive[0],
            "most_expensive_cost": most_expensive[1]["cost"],
            "slowest_tool": slowest_tool[0],
            "slowest_avg_time": slowest_tool[1]["time"] / slowest_tool[1]["calls"],
            "by_tool": by_tool
        }
    
    def check_budget_alerts(self, budget_limit: float = 1.0) -> List[str]:
        """Check for budget alerts and return warnings"""
        alerts = []
        total_cost = sum(r.cost_usd for r in self.records)
        
        if total_cost > budget_limit:
            alerts.append(f"Budget exceeded: ${total_cost:.2f} > ${budget_limit:.2f}")
        
        # Check for expensive individual calls
        expensive_calls = [r for r in self.records if r.cost_usd > 0.10]
        if expensive_calls:
            alerts.append(f"{len(expensive_calls)} expensive calls (>$0.10) detected")
        
        return alerts


# Global telemetry collector
_telemetry = AgentTelemetryCollector()


def agent_step(stage: str = "unknown"):
    """
    Decorator to track agent steps with telemetry
    Following Agent Laboratory pattern
    """
    def decorator(func: Callable) -> Callable:
        @functools.wraps(func)
        async def wrapper(*args, **kwargs):
            tool_name = func.__name__
            start_time = time.perf_counter()
            
            try:
                result = await func(*args, **kwargs)
                duration = time.perf_counter() - start_time
                
                # Extract token info from result if available
                input_tokens = getattr(result, 'input_tokens', 500)  # Estimate
                output_tokens = getattr(result, 'output_tokens', 300)  # Estimate
                
                _telemetry.record_tool_call(
                    tool_name=tool_name,
                    stage=stage,
                    duration=duration,
                    input_tokens=input_tokens,
                    output_tokens=output_tokens,
                    success=True
                )
                
                return result
                
            except Exception as e:
                duration = time.perf_counter() - start_time
                
                _telemetry.record_tool_call(
                    tool_name=tool_name,
                    stage=stage,
                    duration=duration,
                    input_tokens=500,  # Estimate for failed calls
                    output_tokens=100,
                    success=False,
                    error_type=type(e).__name__
                )
                
                raise
                
        return wrapper
    return decorator


def get_telemetry_summary() -> Dict[str, Any]:
    """Get current telemetry summary"""
    return _telemetry.get_summary()


def check_budget_alerts(budget: float = 1.0) -> List[str]:
    """Check for budget alerts"""
    return _telemetry.check_budget_alerts(budget)


def reset_telemetry():
    """Reset telemetry for new session"""
    global _telemetry
    _telemetry = AgentTelemetryCollector() 