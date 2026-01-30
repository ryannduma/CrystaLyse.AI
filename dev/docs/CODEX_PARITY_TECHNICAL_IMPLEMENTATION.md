# Codex Parity: Technical Implementation Report

**Date**: 2026-01-30
**Commit**: 405c050
**Branch**: feature/skills-v2-architecture

## Overview

This document details the technical implementation of features achieving parity with the Codex CLI architecture. The implementation adds sandboxing, orchestration integration, context compaction, and a TUI foundation.

**Summary**:
- 3,628 lines added across 38 files
- 85 new tests
- 4 new packages/modules created
- ~5,800 lines of legacy code archived

---

## 1. Sandboxing Package

### Purpose

Platform-specific sandboxing for shell command execution, preventing unintended file system modifications while allowing legitimate workspace operations.

### Architecture

```
crystalyse/sandbox/
├── __init__.py         # 115 lines - SandboxBackend ABC, get_backend()
├── policy.py           # 175 lines - SandboxPolicy, WritableRoot, SandboxLevel
├── seatbelt.py         # 290 lines - macOS sandbox-exec backend
├── landlock.py         # 290 lines - Linux Landlock + seccomp backend
└── detection.py        # 85 lines  - Denial detection heuristics
```

**Total**: ~955 lines

### Design Philosophy

The design follows Codex's approach: **policy as data, platform-specific backends**.

1. **Declarative Policies**: Users specify what they want (workspace access), not how to achieve it
2. **Platform Abstraction**: Same API works on macOS and Linux with different enforcement mechanisms
3. **Protected Paths**: `.git/` and `.crystalyse/` remain read-only even within writable roots
4. **Helpful Errors**: Denial detection provides human-readable explanations when commands fail

### Key Components

#### SandboxLevel Enum

```python
class SandboxLevel(Enum):
    NONE = "none"           # No sandbox (dangerous)
    READ_ONLY = "read_only" # Full disk read, no write
    WORKSPACE = "workspace" # Write in cwd + /tmp only
```

#### WritableRoot Dataclass

```python
@dataclass(frozen=True)
class WritableRoot:
    root: Path
    read_only_subpaths: tuple[Path, ...] = field(default_factory=tuple)

    @classmethod
    def from_path(cls, path: Path) -> WritableRoot:
        """Auto-detect .git and .crystalyse as read-only subpaths."""
        protected = []
        if (path / ".git").exists():
            protected.append(path / ".git")
        if (path / ".crystalyse").exists():
            protected.append(path / ".crystalyse")
        return cls(root=path, read_only_subpaths=tuple(protected))
```

#### SandboxBackend ABC

```python
class SandboxBackend(ABC):
    @property
    @abstractmethod
    def sandbox_type(self) -> str:
        """Return sandbox type identifier."""

    @abstractmethod
    async def execute(
        self,
        command: list[str],
        *,
        cwd: Path,
        policy: SandboxPolicy,
        timeout: float = 60.0,
        env: dict[str, str] | None = None,
    ) -> SandboxResult:
        """Execute command under sandbox restrictions."""
```

### macOS Seatbelt Implementation

The Seatbelt backend generates SBPL (Seatbelt Profile Language) dynamically:

```python
SEATBELT_BASE_POLICY = """
(version 1)
(deny default)

;; Allow reading from everywhere
(allow file-read*)

;; Allow writing to specified directories only
(allow file-write*
    (subpath (param "CWD"))
    (subpath (param "TMP"))
    (subpath "/dev/null")
    (subpath "/dev/zero")
    (subpath "/dev/random")
    (subpath "/dev/urandom"))

;; Protect git and crystalyse directories
(deny file-write*
    (subpath (param "GIT_DIR"))
    (subpath (param "CRYSTALYSE_DIR")))

;; Allow process operations
(allow process-fork)
(allow process-exec)
...
"""
```

Execution wraps commands with `sandbox-exec`:

```python
sandbox_cmd = [
    "sandbox-exec",
    "-p", policy_content,
    "-D", f"CWD={cwd}",
    "-D", f"TMP={tmpdir}",
    "-D", f"GIT_DIR={git_dir}",
    "-D", f"CRYSTALYSE_DIR={crystalyse_dir}",
    "bash", "-c", " ".join(command),
]
```

### Linux Landlock Implementation

The Landlock backend uses ctypes to invoke syscalls directly:

```python
# Landlock ABI V5 constants
LANDLOCK_ACCESS_FS_READ_FILE = 1 << 2
LANDLOCK_ACCESS_FS_WRITE_FILE = 1 << 5
LANDLOCK_ACCESS_FS_REMOVE_FILE = 1 << 7
# ... etc

# Inline Python script applied in subprocess
LANDLOCK_SETUP_SCRIPT = '''
import os
import ctypes
...
# Create ruleset, add rules, restrict self
'''
```

For network blocking, seccomp filters are applied:

```python
SECCOMP_NETWORK_SCRIPT = '''
# Block socket creation for network families
# Allow AF_UNIX for IPC
'''
```

### Denial Detection

When commands fail, the detection module determines if it was sandbox-related:

```python
SANDBOX_DENIED_KEYWORDS = (
    "operation not permitted",
    "permission denied",
    "read-only file system",
    "sandbox",
    "landlock",
    "seccomp",
)

def is_sandbox_denied(sandbox_type: str, output: CommandOutput) -> bool:
    if sandbox_type == "none":
        return False
    if output.exit_code == 0:
        return False

    # Check keywords
    combined = (output.stdout + output.stderr).lower()
    for keyword in SANDBOX_DENIED_KEYWORDS:
        if keyword in combined:
            return True

    # Check SIGSYS (seccomp violation) on Linux
    if sandbox_type == "linux-landlock" and output.exit_code == 159:
        return True

    return False
```

### Integration with shell.py

Added `run_sandboxed_command()` to `crystalyse/tools/shell.py`:

```python
async def run_sandboxed_command(
    command: str,
    working_directory: str | None = None,
    timeout: int = DEFAULT_TIMEOUT,
    network_access: bool = True,
    additional_writable_roots: list[str] | None = None,
) -> dict[str, Any]:
    """Execute a command under platform-specific sandbox restrictions."""
    backend = get_backend()
    policy = SandboxPolicy.workspace(
        cwd=cwd,
        additional_roots=[Path(p) for p in (additional_writable_roots or [])],
        network_access=network_access,
    )
    result = await backend.execute(
        ["bash", "-c", command],
        cwd=cwd,
        policy=policy,
        timeout=float(timeout),
    )
    return {
        "success": result.success,
        "stdout": result.stdout,
        "stderr": result.stderr,
        "return_code": result.exit_code,
        "sandbox_type": result.sandbox_type,
        "sandbox_denied": result.sandbox_denied,
        "denial_reason": result.denial_reason,
    }
```

### Tests

```
tests/unit/sandbox/
├── __init__.py
├── test_policy.py      # 20 tests - policy dataclasses
└── test_detection.py   # 22 tests - denial detection
```

All 42 sandbox tests pass.

---

## 2. Orchestration Integration

### Purpose

Prepare infrastructure for migrating away from SDK-managed tool execution to custom orchestration with parallel/serial tool classification.

### Architecture

```
crystalyse/agents/
├── tool_classification.py  # 100 lines - tool classification
└── tool_executor.py        # 150 lines - executor infrastructure
```

**Total**: ~250 lines

### Design Philosophy

The orchestration package (implemented previously) provides primitives. This integration:

1. **Classifies Tools**: Read-only tools run in parallel, mutation tools run serially
2. **Provides Migration Path**: `AgentToolExecutor` can replace SDK tool handling when ready
3. **Maintains Compatibility**: Current SDK integration unchanged

### Tool Classification

```python
PARALLEL_TOOLS = frozenset([
    # Read-only operations - safe to run concurrently
    "query_optimade",
    "web_search",
    "read_file",
    "read_artifact",
    "list_artifacts",
    "search_materials",
    "get_structure",
    "validate_composition",
])

SERIAL_TOOLS = frozenset([
    # Mutation operations - must run serially
    "run_shell_command",
    "execute_python",
    "write_file",
    "write_artifact",
    "predict_structure",
    "calculate_energy",
    "relax_structure",
])

def classify_tool(tool_name: str) -> bool:
    """Return True if tool supports parallel execution."""
    if tool_name in PARALLEL_TOOLS:
        return True
    if tool_name in SERIAL_TOOLS:
        return False
    # Unknown tools default to serial (safer)
    return False
```

### ToolSpec and ToolCall

```python
@dataclass
class ToolSpec:
    name: str
    handler: Callable[..., Any]
    supports_parallel: bool = True
    description: str = ""

@dataclass
class ToolCall:
    id: str
    name: str
    input: dict[str, Any]
```

### AgentToolExecutor

```python
class AgentToolExecutor:
    """Execute tools with orchestration support."""

    def __init__(
        self,
        tools: list[ToolSpec],
        timeout: int = 300,
    ):
        self.tools = {t.name: t for t in tools}
        self.timeout = timeout
        self.lock = AsyncRwLock()
        self._metrics: list[ToolMetrics] = []

    async def execute(
        self,
        call: ToolCall,
        token: CancellationToken | None = None,
    ) -> ToolResult:
        """Execute a single tool call with appropriate locking."""
        spec = self.tools.get(call.name)
        if not spec:
            return ToolResult(
                call_id=call.id,
                output=f"Unknown tool: {call.name}",
                error=True,
            )

        # Use read lock for parallel, write lock for serial
        if spec.supports_parallel:
            async with self.lock.read():
                return await self._execute_with_metrics(spec, call, token)
        else:
            async with self.lock.write():
                return await self._execute_with_metrics(spec, call, token)
```

### Tests

```
tests/unit/agents/
└── test_tool_classification.py  # 19 tests
```

---

## 3. Context Compaction

### Purpose

Automatically summarise old conversation messages when approaching token limits, preserving recent context while reducing overall size.

### Architecture

```
crystalyse/memory/
└── compaction.py  # 270 lines
```

### Design Philosophy

1. **Preserve Recent Context**: Keep last N messages verbatim
2. **Summarise History**: Compress older messages into a summary
3. **Extract Key Points**: Identify findings, errors, user requests
4. **Configurable Thresholds**: Trigger compaction at configurable token percentage

### Key Components

#### CompactionConfig

```python
@dataclass
class CompactionConfig:
    max_tokens: int = 100_000
    threshold: float = 0.8       # Compact at 80% capacity
    keep_recent: int = 10        # Keep last 10 messages
    summary_max_tokens: int = 2000
```

#### Message Dataclass

```python
@dataclass
class Message:
    role: str  # "user", "assistant", "system", "tool"
    content: str
    name: str | None = None
    metadata: dict[str, Any] = field(default_factory=dict)

    def to_dict(self) -> dict[str, Any]:
        d = {"role": self.role, "content": self.content}
        if self.name:
            d["name"] = self.name
        return d
```

#### ContextManager

```python
class ContextManager:
    def __init__(self, config: CompactionConfig | None = None):
        self.config = config or CompactionConfig()
        self.compaction_count = 0

    def needs_compaction(self, messages: list[Message]) -> bool:
        total = sum(estimate_tokens(m.content) for m in messages)
        threshold = self.config.max_tokens * self.config.threshold
        return total > threshold

    async def compact_if_needed(
        self, messages: list[Message]
    ) -> CompactionResult:
        if not self.needs_compaction(messages):
            return CompactionResult(
                messages=messages,
                summary=None,
                original_count=len(messages),
                final_count=len(messages),
                compacted=False,
            )
        return await self.compact(messages)

    async def compact(self, messages: list[Message]) -> CompactionResult:
        if len(messages) <= self.config.keep_recent:
            return CompactionResult(messages=messages, compacted=False, ...)

        # Split into old and recent
        old_messages = messages[:-self.config.keep_recent]
        recent_messages = messages[-self.config.keep_recent:]

        # Generate summary
        summary = self._extract_key_points(old_messages)

        # Create summary message
        summary_message = Message(
            role="system",
            content=f"[Previous Context Summary]\n{summary}",
        )

        self.compaction_count += 1
        return CompactionResult(
            messages=[summary_message] + recent_messages,
            summary=summary,
            original_count=len(messages),
            final_count=len(recent_messages) + 1,
            compacted=True,
        )
```

#### Key Point Extraction

```python
def _extract_key_points(self, messages: list[Message]) -> str:
    """Extract key points from messages without LLM."""
    points = []

    for msg in messages:
        content = msg.content.lower()

        # Extract findings
        if msg.role == "assistant":
            finding_patterns = ["found", "discovered", "calculated", "predicted"]
            for pattern in finding_patterns:
                if pattern in content:
                    points.append(f"Finding: {msg.content[:200]}")
                    break

        # Extract user requests
        if msg.role == "user":
            request_patterns = ["find", "search", "calculate", "predict", "analyse"]
            for pattern in request_patterns:
                if pattern in content:
                    points.append(f"User request: {msg.content[:150]}")
                    break

        # Extract errors
        if "error" in content or "failed" in content:
            points.append(f"Issue: {msg.content[:150]}")

    if not points:
        return f"Conversation history: {len(messages)} messages exchanged."

    return "\n".join(points[:20])  # Limit to 20 key points
```

### Tests

```
tests/unit/memory/
└── test_compaction.py  # 24 tests
```

---

## 4. TUI Foundation

### Purpose

Provide a rich terminal user interface using Textual framework as an optional feature.

### Architecture

```
crystalyse/tui/
├── __init__.py  # 30 lines - entry point
└── app.py       # 180 lines - Textual app
```

**Total**: ~210 lines

### Design Philosophy

1. **Optional Dependency**: TUI only loads if `textual` is installed
2. **Composable Widgets**: Separate concerns into focused widgets
3. **Keyboard-Driven**: Standard shortcuts (Ctrl+C, Ctrl+D)
4. **Streaming Support**: Display partial responses as they arrive

### Components

#### CrystalyseApp

```python
class CrystalyseApp(App):
    CSS = """
    Screen {
        layout: grid;
        grid-size: 1 3;
        grid-rows: 1fr 3 auto;
    }

    #chat-display {
        height: 100%;
        scrollbar-gutter: stable;
    }

    #status-bar {
        height: 3;
        dock: top;
        background: $surface;
        padding: 0 1;
    }

    #input-area {
        height: auto;
        min-height: 3;
        max-height: 10;
        dock: bottom;
    }
    """

    BINDINGS = [
        Binding("ctrl+c", "cancel", "Cancel"),
        Binding("ctrl+d", "quit", "Quit"),
        Binding("ctrl+l", "clear", "Clear"),
    ]

    def __init__(self, rigorous: bool = False, session_id: str | None = None):
        super().__init__()
        self.rigorous = rigorous
        self.session_id = session_id or str(uuid.uuid4())[:8]
        self.agent: MaterialsAgent | None = None

    def compose(self) -> ComposeResult:
        yield StatusBar(self.rigorous, self.session_id)
        yield ChatDisplay(id="chat-display")
        yield InputArea(id="input-area")

    async def on_input_area_submitted(self, event: InputArea.Submitted) -> None:
        # Handle user input, run agent, display response
        ...
```

#### Widgets

```python
class StatusBar(Static):
    """Status bar showing mode, model, and session."""

class ChatDisplay(ScrollableContainer):
    """Scrollable chat history display."""

class MessageWidget(Static):
    """Individual message display with role styling."""

class InputArea(TextArea):
    """Multi-line input with Ctrl+Enter submission."""
```

### CLI Integration

Added to `crystalyse/cli.py`:

```python
@app.command()
def tui(
    rigorous: bool = typer.Option(
        False, "--rigorous", "-r", help="Use rigorous mode"
    ),
    session_id: str | None = typer.Option(
        None, "--session", "-s", help="Resume session"
    ),
):
    """Launch the TUI interface."""
    try:
        from crystalyse.tui import run_tui
    except ImportError:
        console.print(
            "[red]TUI requires textual. Install with: "
            "pip install 'crystalyse[tui]'[/red]"
        )
        raise typer.Exit(1)

    run_tui(rigorous=rigorous, session_id=session_id)
```

### Optional Dependency

Added to `pyproject.toml`:

```toml
[project.optional-dependencies]
tui = ["textual>=0.47.0"]
```

---

## 5. Legacy UI Cleanup

### Archived Files

Moved 12 files (~5,800 lines) to `archive/ui-legacy/`:

| File | Lines | Purpose |
|------|-------|---------|
| `chat_ui.py` | 1,200 | Old ChatExperience system |
| `enhanced_clarification.py` | 1,500 | Duplicate of clarification.py |
| `dynamic_mode_adapter.py` | 400 | V1 mode detection |
| `user_preference_memory.py` | 300 | Duplicate preference system |
| `ascii_art.py` | 150 | Unused ASCII banners |
| `slash_commands.py` | 250 | Unused command system |
| `trace_handler.py` | 400 | Old tracing |
| `enhanced_trace_handler.py` | 500 | Never imported |
| `enhanced_trace_handler_v2.py` | 500 | Never imported |
| `enhanced_result_formatter.py` | 350 | Unused formatting |
| `provenance_bridge.py` | 200 | Unused bridge |
| `progress.py` | 150 | Duplicate progress |

### Retained

Only `clarification.py` retained - actively used by `cli.py`.

### Audit Process

1. Traced all imports from entry points
2. Identified `clarification.py` as only used module
3. Verified no runtime dependencies on archived files
4. Ran full test suite (234 tests passing)

---

## Test Coverage

### New Tests by Module

| Module | Tests | Coverage |
|--------|-------|----------|
| sandbox/test_policy.py | 20 | Policy dataclasses |
| sandbox/test_detection.py | 22 | Denial heuristics |
| agents/test_tool_classification.py | 19 | Classification logic |
| memory/test_compaction.py | 24 | Compaction logic |
| **Total** | **85** | |

### Test Execution

```bash
$ pytest tests/unit/ -v -m "not slow and not requires_gpu and not requires_api"
================================ 234 passed ================================
```

---

## Implementation Principles Applied

### From CLAUDE.md

1. **Single Responsibility**: Each file does one thing (policy.py, detection.py, etc.)
2. **Tests Alongside**: Created tests as each module was implemented
3. **Explicit Exports**: All `__init__.py` files have explicit exports
4. **Dataclasses**: Used for all data containers (ToolSpec, Message, etc.)
5. **Async Context Managers**: Resource cleanup patterns applied
6. **Error Classes**: Custom errors with context (ToolTimeoutError, etc.)

### From Codex Reference

1. **Policy as Data**: SandboxPolicy is declarative, backends interpret it
2. **Platform Abstraction**: Same API, different enforcement
3. **Protected Paths**: Auto-detect .git, .crystalyse
4. **Denial Detection**: Human-readable sandbox failure explanations

---

## Future Work

### Immediate

1. **Wire TUI to Agent**: Connect InputArea → MaterialsAgent → ChatDisplay
2. **Sandboxed Tool Calls**: Use run_sandboxed_command() for shell.py by default
3. **Context Compaction Integration**: Add to MaterialsAgent conversation loop

### Medium-term

1. **SDK Migration**: Replace SDK tool handling with AgentToolExecutor
2. **TUI Enhancements**: Tool progress widgets, artifact display
3. **Session Persistence**: Integrate compaction with session storage

### Long-term

1. **Workers**: Subagent spawning for parallel research
2. **Full Orchestration**: ParallelToolExecutor managing all tool execution

---

## File Summary

### Created (28 files)

```
crystalyse/sandbox/__init__.py
crystalyse/sandbox/policy.py
crystalyse/sandbox/seatbelt.py
crystalyse/sandbox/landlock.py
crystalyse/sandbox/detection.py
crystalyse/agents/tool_classification.py
crystalyse/agents/tool_executor.py
crystalyse/memory/compaction.py
crystalyse/tui/__init__.py
crystalyse/tui/app.py
tests/unit/sandbox/__init__.py
tests/unit/sandbox/test_policy.py
tests/unit/sandbox/test_detection.py
tests/unit/agents/test_tool_classification.py
tests/unit/memory/test_compaction.py
archive/ui-legacy/README.md
archive/ui-legacy/*.py (12 files)
```

### Modified (10 files)

```
crystalyse/agents/__init__.py
crystalyse/cli.py
crystalyse/memory/__init__.py
crystalyse/tools/shell.py
pyproject.toml
tests/conftest.py
tests/unit/config/test_preferences.py
tests/unit/tools/test_tool_caching.py
crystalyse/tools/mace/energy.py
```

### Line Counts

| Category | Lines |
|----------|-------|
| Sandbox package | ~955 |
| Orchestration integration | ~250 |
| Compaction | ~270 |
| TUI | ~210 |
| Tests | ~900 |
| **Total new** | **~2,585** |
| Legacy archived | ~5,800 |
