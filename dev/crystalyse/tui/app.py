"""Main Textual application for Crystalyse TUI.

Provides a rich terminal interface for interactive materials discovery.
"""

from __future__ import annotations

import asyncio
from datetime import datetime
from typing import TYPE_CHECKING

try:
    from textual.app import App, ComposeResult
    from textual.binding import Binding
    from textual.containers import Container, Horizontal, ScrollableContainer
    from textual.widgets import Button, Footer, Header, Input, Label, Markdown, Static

    TEXTUAL_AVAILABLE = True
except ImportError:
    TEXTUAL_AVAILABLE = False

if TYPE_CHECKING:
    pass


if TEXTUAL_AVAILABLE:

    class MessageWidget(Static):
        """Widget displaying a single message."""

        DEFAULT_CSS = """
        MessageWidget {
            padding: 1 2;
            margin: 0 0 1 0;
        }

        MessageWidget.user {
            background: $primary-darken-2;
            border-left: thick $primary;
        }

        MessageWidget.assistant {
            background: $surface;
            border-left: thick $secondary;
        }

        MessageWidget.system {
            background: $warning-darken-3;
            border-left: thick $warning;
            color: $warning;
        }

        MessageWidget .message-header {
            text-style: bold;
            margin-bottom: 1;
        }

        MessageWidget .message-content {
            margin-left: 2;
        }
        """

        def __init__(
            self,
            role: str,
            content: str,
            timestamp: datetime | None = None,
            **kwargs,
        ) -> None:
            super().__init__(**kwargs)
            self.role = role
            self.content = content
            self.timestamp = timestamp or datetime.now()
            self.add_class(role.lower())

        def compose(self) -> ComposeResult:
            role_display = self.role.capitalize()
            if self.role == "assistant":
                role_display = "CrystaLyse"
            elif self.role == "user":
                role_display = "You"

            time_str = self.timestamp.strftime("%H:%M")
            yield Label(f"{role_display} [{time_str}]", classes="message-header")
            yield Markdown(self.content, classes="message-content")

    class ChatDisplay(ScrollableContainer):
        """Scrollable container for chat messages."""

        DEFAULT_CSS = """
        ChatDisplay {
            height: 1fr;
            border: solid $primary-darken-2;
            padding: 1;
        }
        """

        def add_message(self, role: str, content: str) -> MessageWidget:
            """Add a new message to the display."""
            widget = MessageWidget(role, content)
            self.mount(widget)
            self.scroll_end(animate=False)
            return widget

        def update_last_message(self, content: str) -> None:
            """Update the content of the last message (for streaming)."""
            children = list(self.children)
            if children:
                last = children[-1]
                if isinstance(last, MessageWidget):
                    # Update the markdown content
                    md = last.query_one(Markdown)
                    md.update(content)
                    self.scroll_end(animate=False)

    class StatusBar(Horizontal):
        """Status bar showing model and session info."""

        DEFAULT_CSS = """
        StatusBar {
            dock: bottom;
            height: 1;
            background: $primary-darken-3;
            padding: 0 1;
        }

        StatusBar Label {
            margin-right: 2;
        }

        StatusBar .mode-rigorous {
            color: $warning;
        }

        StatusBar .mode-creative {
            color: $success;
        }
        """

        def __init__(
            self,
            model: str = "gpt-5-mini",
            mode: str = "creative",
            session_id: str | None = None,
            **kwargs,
        ) -> None:
            super().__init__(**kwargs)
            self.model_name = model
            self.mode_name = mode
            self.session = session_id

        def compose(self) -> ComposeResult:
            mode_class = f"mode-{self.mode_name}"
            yield Label(f"Model: {self.model_name}")
            yield Label(f"Mode: {self.mode_name.upper()}", classes=mode_class)
            if self.session:
                yield Label(f"Session: {self.session[:8]}...")
            yield Label("| Ctrl+C: Cancel | Ctrl+Q: Quit")

    class InputArea(Horizontal):
        """Input area with text field and send button."""

        DEFAULT_CSS = """
        InputArea {
            dock: bottom;
            height: 3;
            padding: 0 1;
        }

        InputArea Input {
            width: 1fr;
        }

        InputArea Button {
            width: 10;
            margin-left: 1;
        }
        """

        def compose(self) -> ComposeResult:
            yield Input(placeholder="Ask CrystaLyse about materials...", id="query-input")
            yield Button("Send", variant="primary", id="send-btn")

    class CrystalyseApp(App):
        """Main Crystalyse TUI application."""

        TITLE = "CrystaLyse"
        SUB_TITLE = "Intelligent Materials Discovery"

        CSS = """
        Screen {
            layout: grid;
            grid-size: 1;
            grid-rows: 1fr auto auto;
        }

        #main-container {
            height: 100%;
        }
        """

        BINDINGS = [
            Binding("ctrl+q", "quit", "Quit"),
            Binding("ctrl+c", "cancel", "Cancel"),
            Binding("ctrl+l", "clear", "Clear"),
            Binding("escape", "focus_input", "Focus Input"),
        ]

        def __init__(
            self,
            rigorous: bool = False,
            session_id: str | None = None,
            **kwargs,
        ) -> None:
            super().__init__(**kwargs)
            self.rigorous = rigorous
            self.session_id = session_id
            self.model = "gpt-5.2" if rigorous else "gpt-5-mini"
            self.mode = "rigorous" if rigorous else "creative"
            self._agent = None
            self._current_task: asyncio.Task | None = None

        def compose(self) -> ComposeResult:
            yield Header()
            yield Container(
                ChatDisplay(id="chat-display"),
                id="main-container",
            )
            yield InputArea()
            yield StatusBar(
                model=self.model,
                mode=self.mode,
                session_id=self.session_id,
            )
            yield Footer()

        def on_mount(self) -> None:
            """Called when app is mounted."""
            # Focus the input
            self.query_one("#query-input", Input).focus()

            # Add welcome message
            chat = self.query_one("#chat-display", ChatDisplay)
            chat.add_message(
                "system",
                f"Welcome to CrystaLyse! Running in **{self.mode}** mode with `{self.model}`.\n\n"
                "Ask me about materials discovery, composition validation, or structure prediction.",
            )

        async def on_button_pressed(self, event: Button.Pressed) -> None:
            """Handle button press."""
            if event.button.id == "send-btn":
                await self._send_message()

        async def on_input_submitted(self, event: Input.Submitted) -> None:
            """Handle input submission (Enter key)."""
            if event.input.id == "query-input":
                await self._send_message()

        async def _send_message(self) -> None:
            """Send the current input as a message."""
            input_widget = self.query_one("#query-input", Input)
            query = input_widget.value.strip()

            if not query:
                return

            # Clear input
            input_widget.value = ""

            # Add user message
            chat = self.query_one("#chat-display", ChatDisplay)
            chat.add_message("user", query)

            # Add thinking indicator
            chat.add_message("assistant", "_Thinking..._")

            # Process query
            self._current_task = asyncio.create_task(self._process_query(query))

        async def _process_query(self, query: str) -> None:
            """Process a query through the agent."""
            chat = self.query_one("#chat-display", ChatDisplay)

            try:
                # Lazy load agent
                if self._agent is None:
                    chat.update_last_message("_Loading agent..._")
                    try:
                        from ..agents import MaterialsAgent

                        self._agent = MaterialsAgent(rigorous=self.rigorous)
                    except ImportError as e:
                        chat.update_last_message(
                            f"**Error**: Could not load agent: {e}\n\n"
                            "Make sure all dependencies are installed."
                        )
                        return

                # Run query
                chat.update_last_message("_Processing..._")
                result = await self._agent.query(
                    query,
                    session_id=self.session_id,
                )

                if result.get("status") == "completed":
                    response = result.get("response", "No response generated.")
                    chat.update_last_message(response)
                else:
                    error = result.get("error", "Unknown error")
                    chat.update_last_message(f"**Error**: {error}")

            except asyncio.CancelledError:
                chat.update_last_message("_Query cancelled._")
            except Exception as e:
                chat.update_last_message(f"**Error**: {e}")
            finally:
                self._current_task = None

        def action_cancel(self) -> None:
            """Cancel current operation."""
            if self._current_task and not self._current_task.done():
                self._current_task.cancel()
                self.notify("Cancelling...")

        def action_clear(self) -> None:
            """Clear the chat display."""
            chat = self.query_one("#chat-display", ChatDisplay)
            chat.remove_children()
            chat.add_message(
                "system",
                "Chat cleared. Ready for new queries.",
            )

        def action_focus_input(self) -> None:
            """Focus the input field."""
            self.query_one("#query-input", Input).focus()

else:
    # Fallback when textual not available
    class CrystalyseApp:  # type: ignore
        """Stub class when textual is not available."""

        def __init__(self, **kwargs) -> None:
            raise ImportError("TUI requires textual. Install with: pip install crystalyse[tui]")

        def run(self) -> None:
            pass
