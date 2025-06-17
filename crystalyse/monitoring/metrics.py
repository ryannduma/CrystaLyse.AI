"""
Performance metrics and monitoring for CrystaLyse.AI
"""

import time
import asyncio
import json
import logging
from typing import Dict, Any, List, Optional
from dataclasses import dataclass, field, asdict
from collections import defaultdict
from pathlib import Path
from datetime import datetime, timedelta
import psutil
import threading

logger = logging.getLogger(__name__)

@dataclass
class ToolMetrics:
    """Metrics for individual tool calls with cost tracking"""
    name: str
    calls: int = 0
    successes: int = 0
    failures: int = 0
    total_time: float = 0.0
    min_time: float = float('inf')
    max_time: float = 0.0
    total_cost: float = 0.0  # USD
    total_tokens: int = 0
    error_types: Dict[str, int] = field(default_factory=dict)
    
    @property
    def success_rate(self) -> float:
        return self.successes / self.calls if self.calls > 0 else 0.0
    
    @property
    def avg_time(self) -> float:
        return self.total_time / self.calls if self.calls > 0 else 0.0
    
    def add_call(self, duration: float, success: bool, error_type: str = None, 
                 cost: float = 0.0, tokens: int = 0):
        """Add a tool call to metrics with cost tracking"""
        self.calls += 1
        self.total_time += duration
        self.total_cost += cost
        self.total_tokens += tokens
        self.min_time = min(self.min_time, duration)
        self.max_time = max(self.max_time, duration)
        
        if success:
            self.successes += 1
        else:
            self.failures += 1
            if error_type:
                self.error_types[error_type] = self.error_types.get(error_type, 0) + 1

@dataclass
class WorkflowMetrics:
    """Metrics for entire workflow execution"""
    start_time: float
    end_time: float = 0.0
    total_steps: int = 0
    successful_steps: int = 0
    failed_steps: int = 0
    tool_sequence: List[str] = field(default_factory=list)
    mode: str = "unknown"
    query: str = ""
    
    @property
    def duration(self) -> float:
        end = self.end_time or time.time()
        return end - self.start_time
    
    @property
    def success_rate(self) -> float:
        return self.successful_steps / self.total_steps if self.total_steps > 0 else 0.0

class MetricsCollector:
    """Collect and analyse performance metrics with persistence"""
    
    def __init__(self, persistence_path: Optional[Path] = None):
        self.tool_metrics = defaultdict(lambda: ToolMetrics("unknown"))
        self.workflow_metrics: Optional[WorkflowMetrics] = None
        self.system_metrics = {"cpu_usage": [], "memory_usage": [], "gpu_usage": []}
        
        # Persistence
        self.persistence_path = persistence_path or Path.home() / ".crystalyse" / "metrics"
        self.persistence_path.mkdir(parents=True, exist_ok=True)
        
        # System monitoring
        self._monitoring_thread = None
        self._stop_monitoring = threading.Event()
        
    def start_workflow(self, query: str, mode: str = "unknown"):
        """Start a new workflow tracking session"""
        self.workflow_metrics = WorkflowMetrics(
            start_time=time.time(),
            query=query,
            mode=mode
        )
        
        # Start system monitoring
        self._start_system_monitoring()
        
        logger.info(f"Started workflow tracking: {mode} mode, query: {query[:50]}...")
    
    def end_workflow(self):
        """End workflow tracking"""
        if self.workflow_metrics:
            self.workflow_metrics.end_time = time.time()
            
        # Stop system monitoring
        self._stop_system_monitoring()
        
        logger.info(f"Ended workflow tracking. Duration: {self.workflow_metrics.duration:.2f}s")
    
    async def track_tool_call(self, tool_name: str, coro, *args, **kwargs):
        """Track a tool call with timing and error handling"""
        if not self.workflow_metrics:
            logger.warning("Tool call tracked without active workflow")
            
        metrics = self.tool_metrics[tool_name]
        if metrics.name == "unknown":
            metrics.name = tool_name
            
        start_time = time.time()
        
        try:
            result = await coro(*args, **kwargs)
            duration = time.time() - start_time
            
            # Record success
            metrics.add_call(duration, True)
            
            if self.workflow_metrics:
                self.workflow_metrics.total_steps += 1
                self.workflow_metrics.successful_steps += 1
                self.workflow_metrics.tool_sequence.append(tool_name)
            
            logger.debug(f"Tool {tool_name} succeeded in {duration:.3f}s")
            return result
            
        except Exception as e:
            duration = time.time() - start_time
            error_type = type(e).__name__
            
            # Record failure
            metrics.add_call(duration, False, error_type)
            
            if self.workflow_metrics:
                self.workflow_metrics.total_steps += 1
                self.workflow_metrics.failed_steps += 1
                self.workflow_metrics.tool_sequence.append(f"{tool_name}_FAILED")
            
            logger.error(f"Tool {tool_name} failed in {duration:.3f}s: {error_type}")
            raise
    
    def _start_system_monitoring(self):
        """Start background system monitoring"""
        if self._monitoring_thread and self._monitoring_thread.is_alive():
            return
            
        self._stop_monitoring.clear()
        self._monitoring_thread = threading.Thread(target=self._monitor_system)
        self._monitoring_thread.daemon = True
        self._monitoring_thread.start()
    
    def _stop_system_monitoring(self):
        """Stop background system monitoring"""
        if self._monitoring_thread and self._monitoring_thread.is_alive():
            self._stop_monitoring.set()
            self._monitoring_thread.join(timeout=1.0)
    
    def _monitor_system(self):
        """Background system monitoring loop"""
        while not self._stop_monitoring.wait(1.0):  # Sample every second
            try:
                # CPU and memory
                cpu_percent = psutil.cpu_percent()
                memory = psutil.virtual_memory()
                
                self.system_metrics["cpu_usage"].append({
                    "timestamp": time.time(),
                    "value": cpu_percent
                })
                
                self.system_metrics["memory_usage"].append({
                    "timestamp": time.time(),
                    "value": memory.percent
                })
                
                # GPU usage (if available)
                try:
                    import GPUtil
                    gpus = GPUtil.getGPUs()
                    if gpus:
                        gpu_usage = sum(gpu.load * 100 for gpu in gpus) / len(gpus)
                        self.system_metrics["gpu_usage"].append({
                            "timestamp": time.time(),
                            "value": gpu_usage
                        })
                except ImportError:
                    pass  # GPU monitoring not available
                    
            except Exception as e:
                logger.warning(f"System monitoring error: {e}")
    
    def get_summary(self) -> Dict[str, Any]:
        """Get current metrics summary"""
        summary = {
            "tools": {},
            "workflow": {},
            "system": {},
            "timestamp": datetime.utcnow().isoformat()
        }
        
        # Tool-level metrics
        for tool_name, metrics in self.tool_metrics.items():
            if metrics.calls > 0:  # Only include tools that were used
                summary["tools"][tool_name] = {
                    "calls": metrics.calls,
                    "success_rate": metrics.success_rate,
                    "avg_time": metrics.avg_time,
                    "total_time": metrics.total_time,
                    "min_time": metrics.min_time if metrics.min_time != float('inf') else 0,
                    "max_time": metrics.max_time,
                    "error_types": dict(metrics.error_types)
                }
        
        # Workflow metrics
        if self.workflow_metrics:
            summary["workflow"] = {
                "duration": self.workflow_metrics.duration,
                "total_steps": self.workflow_metrics.total_steps,
                "success_rate": self.workflow_metrics.success_rate,
                "tool_sequence": self.workflow_metrics.tool_sequence,
                "unique_tools": len(set(self.workflow_metrics.tool_sequence)),
                "mode": self.workflow_metrics.mode,
                "query": self.workflow_metrics.query
            }
            
            # Identify bottlenecks
            if self.tool_metrics:
                slowest_tool = max(
                    self.tool_metrics.items(), 
                    key=lambda x: x[1].avg_time if x[1].calls > 0 else 0
                )
                summary["workflow"]["bottleneck"] = {
                    "tool": slowest_tool[0],
                    "avg_time": slowest_tool[1].avg_time
                }
        
        # System metrics summary
        for metric_type, measurements in self.system_metrics.items():
            if measurements:
                values = [m["value"] for m in measurements]
                summary["system"][metric_type] = {
                    "current": values[-1] if values else 0,
                    "average": sum(values) / len(values),
                    "max": max(values),
                    "samples": len(values)
                }
        
        return summary
    
    def save_metrics(self, workflow_id: Optional[str] = None):
        """Persist metrics to disk"""
        if not workflow_id:
            workflow_id = datetime.utcnow().strftime("%Y%m%d_%H%M%S")
            
        metrics_file = self.persistence_path / f"workflow_{workflow_id}.json"
        
        # Prepare data for serialisation
        data = {
            "workflow_id": workflow_id,
            "timestamp": datetime.utcnow().isoformat(),
            "summary": self.get_summary(),
            "detailed_tools": {
                name: asdict(metrics) 
                for name, metrics in self.tool_metrics.items() 
                if metrics.calls > 0
            },
            "workflow_details": asdict(self.workflow_metrics) if self.workflow_metrics else None,
            "system_metrics": self.system_metrics
        }
        
        with open(metrics_file, "w") as f:
            json.dump(data, f, indent=2, default=str)
            
        logger.info(f"Saved metrics to {metrics_file}")
        return metrics_file
    
    def load_historical_metrics(self, last_n: int = 10) -> List[Dict[str, Any]]:
        """Load recent workflow metrics for analysis"""
        metric_files = sorted(self.persistence_path.glob("workflow_*.json"))[-last_n:]
        
        historical_data = []
        for metric_file in metric_files:
            try:
                with open(metric_file) as f:
                    data = json.load(f)
                    historical_data.append(data)
            except Exception as e:
                logger.warning(f"Failed to load {metric_file}: {e}")
                
        return historical_data

@dataclass 
class PerformanceReport:
    """Generate performance analysis reports"""
    
    @staticmethod
    def generate_workflow_report(metrics: MetricsCollector) -> str:
        """Generate a human-readable workflow performance report"""
        summary = metrics.get_summary()
        
        report = ["=== CrystaLyse.AI Performance Report ===\n"]
        
        # Workflow overview
        if "workflow" in summary:
            wf = summary["workflow"]
            report.append(f"Workflow Summary:")
            report.append(f"  Mode: {wf.get('mode', 'unknown')}")
            report.append(f"  Duration: {wf.get('duration', 0):.2f} seconds")
            report.append(f"  Total steps: {wf.get('total_steps', 0)}")
            report.append(f"  Success rate: {wf.get('success_rate', 0)*100:.1f}%")
            report.append(f"  Unique tools used: {wf.get('unique_tools', 0)}")
            
            if "bottleneck" in wf:
                report.append(f"  Bottleneck: {wf['bottleneck']['tool']} ({wf['bottleneck']['avg_time']:.2f}s avg)")
            report.append("")
        
        # Tool performance
        if "tools" in summary and summary["tools"]:
            report.append("Tool Performance:")
            for tool_name, metrics in summary["tools"].items():
                report.append(f"  {tool_name}:")
                report.append(f"    Calls: {metrics['calls']}")
                report.append(f"    Success rate: {metrics['success_rate']*100:.1f}%")
                report.append(f"    Avg time: {metrics['avg_time']:.3f}s")
                report.append(f"    Total time: {metrics['total_time']:.2f}s")
                if metrics['error_types']:
                    report.append(f"    Errors: {metrics['error_types']}")
                report.append("")
        
        # System resource usage
        if "system" in summary and summary["system"]:
            report.append("System Resources:")
            for resource, stats in summary["system"].items():
                report.append(f"  {resource.replace('_', ' ').title()}:")
                report.append(f"    Current: {stats['current']:.1f}%")
                report.append(f"    Average: {stats['average']:.1f}%")
                report.append(f"    Peak: {stats['max']:.1f}%")
            report.append("")
        
        # Performance recommendations
        report.append("Recommendations:")
        
        if "tools" in summary:
            # Find slow tools
            slow_tools = [
                name for name, metrics in summary["tools"].items() 
                if metrics['avg_time'] > 5.0
            ]
            if slow_tools:
                report.append(f"  • Optimise slow tools: {', '.join(slow_tools)}")
                
            # Find error-prone tools
            error_tools = [
                name for name, metrics in summary["tools"].items()
                if metrics['success_rate'] < 0.9
            ]
            if error_tools:
                report.append(f"  • Improve reliability of: {', '.join(error_tools)}")
        
        if "system" in summary:
            # Check resource usage
            if summary["system"].get("cpu_usage", {}).get("average", 0) > 80:
                report.append("  • High CPU usage detected - consider parallel optimisation")
                
            if summary["system"].get("memory_usage", {}).get("average", 0) > 80:
                report.append("  • High memory usage detected - consider batch size reduction")
                
            if "gpu_usage" in summary["system"] and summary["system"]["gpu_usage"]["average"] < 30:
                report.append("  • Low GPU utilisation - check MACE parallelisation")
        
        return "\n".join(report)
    
    @staticmethod
    def generate_trend_analysis(historical_data: List[Dict[str, Any]]) -> str:
        """Analyse performance trends over multiple workflows"""
        if not historical_data:
            return "No historical data available for trend analysis."
            
        report = ["=== Performance Trend Analysis ===\n"]
        
        # Extract workflow durations
        durations = []
        success_rates = []
        tool_calls = []
        
        for data in historical_data:
            if "summary" in data and "workflow" in data["summary"]:
                wf = data["summary"]["workflow"]
                durations.append(wf.get("duration", 0))
                success_rates.append(wf.get("success_rate", 0))
                
                total_calls = sum(
                    tool_metrics.get("calls", 0) 
                    for tool_metrics in data["summary"].get("tools", {}).values()
                )
                tool_calls.append(total_calls)
        
        if durations:
            report.append(f"Workflow Performance Trends ({len(durations)} workflows):")
            report.append(f"  Average duration: {sum(durations)/len(durations):.2f}s")
            report.append(f"  Best duration: {min(durations):.2f}s")
            report.append(f"  Worst duration: {max(durations):.2f}s")
            
            # Trend direction
            if len(durations) >= 3:
                recent_avg = sum(durations[-3:]) / 3
                older_avg = sum(durations[:-3]) / len(durations[:-3]) if len(durations) > 3 else recent_avg
                
                if recent_avg < older_avg * 0.9:
                    report.append("  📈 Performance improving over time")
                elif recent_avg > older_avg * 1.1:
                    report.append("  📉 Performance degrading over time")
                else:
                    report.append("  ➡️ Performance stable")
            
            report.append("")
        
        if success_rates:
            avg_success = sum(success_rates) / len(success_rates)
            report.append(f"Reliability:")
            report.append(f"  Average success rate: {avg_success*100:.1f}%")
            report.append(f"  Best success rate: {max(success_rates)*100:.1f}%")
            report.append(f"  Worst success rate: {min(success_rates)*100:.1f}%")
            report.append("")
            
        if tool_calls:
            avg_calls = sum(tool_calls) / len(tool_calls)
            report.append(f"Tool Usage:")
            report.append(f"  Average tool calls per workflow: {avg_calls:.1f}")
            report.append(f"  Most tool-heavy workflow: {max(tool_calls)} calls")
            report.append(f"  Most efficient workflow: {min(tool_calls)} calls")
            
        return "\n".join(report)