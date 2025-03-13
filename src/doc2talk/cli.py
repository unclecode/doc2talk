"""
DocTalk CLI - Terminal interface for the doc2talk library
"""

import argparse
import asyncio

from rich.console import Console
from rich.live import Live
from rich.markdown import Markdown
from rich.table import Table

from .core import ChatEngine, ChatSession, SessionManager

# --- UI Constants ---
HAIR_SPACE = "\u200a"  # Thinnest space
THIN_SPACE = "\u2009"  # A bit thicker
SIX_PER_EM_SPACE = "\u2006"  # Slightly thicker


class ChatCLI:
    def __init__(self):
        self.console = Console()
        # Track terminal width and listen for changes
        self.width = self.console.width
        self.console.set_window_title("DocTalk - Code Chat")
        self.console.show_cursor(False)

    def draw_box(self, title, color="cyan"):
        """Draw a complete box using terminal width"""
        width = self.console.width - 2
        # Use dim style and ╌ (U+256C) for a dimmer line
        self.console.print(
            f"[dim]╌[/dim] [{color}]{title}[/{color}] [dim]"
            + "╌" * (width - len(title) - 3)
            + "[/dim]"
        )
        return width

    async def display_streaming_response(
        self, session: ChatSession, engine: ChatEngine, question: str
    ) -> str:
        """Display response with live streaming using Rich"""
        # Get first a decision on context
        decision = await engine.get_context_decision(session, question)
        await engine.update_context(session, question, decision)

        # Now stream the response
        with Live(Markdown(""), refresh_per_second=10) as live:
            full_response = []
            async for chunk in engine.generate_response_stream(session, question):
                full_response.append(chunk)
                # Update the live display with latest markdown
                live.update(Markdown("".join(full_response)))

        # Display context status
        status = session.context_manager.get_status()
        self.console.print(
            f"[dim][{status['context_count']} Contexts, "
            f"{status['token_count']:,} tokens, "
            f"{status['action']}][/dim]",
            style="dim cyan",
        )

        return "".join(full_response)

    async def list_sessions_cmd(self):
        """List all saved sessions in a table"""
        table = Table(show_header=True)
        table.add_column("Session ID")
        table.add_column("Created")
        table.add_column("Messages")

        for session in SessionManager.list_sessions():
            table.add_row(
                session["id"],
                session["created"].split("T")[0]
                if "T" in session.get("created", "")
                else "",
                str(session["message_count"]),
            )

        self.console.print(table)

    async def delete_session_cmd(self, session_id: str):
        """Delete a specific session"""
        if SessionManager.delete_session(session_id):
            self.console.print(f"[green]Session {session_id} deleted.[/green]")
        else:
            self.console.print(f"[red]Session {session_id} not found.[/red]")

    async def chat_session(self, engine: ChatEngine, session: ChatSession):
        """Run an interactive chat session"""
        # Display session ID information in a header
        self.console.print(f"[dim]Session ID: {session.session_id} (use with -c to continue this session)[/dim]")
        
        if session.is_new:
            greeting = "Hello! I'm DocTalk, your code documentation assistant. How can I help you today?"  # noqa: E501
            session.add_message("assistant", greeting)
            self.draw_box("DocTalk", "cyan")
            self.console.print(f"{greeting}")
            self.console.print(HAIR_SPACE)
            SessionManager.save(session)

        while True:
            try:
                self.draw_box("You", "yellow")
                self.console.show_cursor(True)
                user_input = input().strip()
                self.console.show_cursor(False)

                if not user_input:
                    continue
                if user_input.lower() == "/exit":
                    break

                self.console.print(HAIR_SPACE)
                session.add_message("user", user_input)

                # Draw AI response box
                self.draw_box("DocTalk")

                # Display streaming response
                response = await self.display_streaming_response(
                    session, engine, user_input
                )

                # Save the message
                session.add_message("assistant", response)
                SessionManager.save(session)

            except KeyboardInterrupt:
                self.console.print(
                    "\n[red]Session saved. Use -c to continue later.[/red]"
                )
                break

    async def run(self):
        """Parse arguments and run the CLI"""
        parser = argparse.ArgumentParser(
            description="DocTalk - Code Documentation Chat Interface"
        )
        # Session management
        parser.add_argument(
            "--continue", "-c", metavar="ID", help="Continue existing session"
        )
        parser.add_argument(
            "--list", "-l", action="store_true", help="List all saved sessions"
        )
        parser.add_argument(
            "--delete", "-d", metavar="ID", help="Delete a specific session"
        )

        # Repository configuration
        parser.add_argument(
            "--code",
            metavar="PATH",
            help="Path to code source (local directory or GitHub URL)",
        )
        parser.add_argument(
            "--docs",
            metavar="PATH",
            help="Path to documentation source (local directory or GitHub URL)",
        )
        parser.add_argument(
            "--exclude",
            metavar="PATTERN",
            action="append",
            help="Glob patterns to exclude (can be used multiple times)",
        )
        parser.add_argument(
            "--cache-id", metavar="ID", help="Custom identifier for the cache file"
        )

        args = parser.parse_args()

        if args.list:
            await self.list_sessions_cmd()
            return

        if args.delete:
            await self.delete_session_cmd(args.delete)
            return

        # Create or load session
        if args.__dict__["continue"]:
            try:
                session = SessionManager.load(args.__dict__["continue"])
                self.console.print(f"[green]Continuing session: {args.__dict__['continue']}[/green]")
            except Exception as e:
                self.console.print(f"[red]Error loading session: {str(e)}[/red]")
                return
        else:
            session = ChatSession()
            self.console.print(f"[green]New session created: {session.session_id}[/green]")

        # Initialize ChatEngine with command line arguments
        engine = ChatEngine(
            code_source=args.code,
            docs_source=args.docs,
            exclude_patterns=args.exclude,
            cache_id=args.cache_id,
        )

        # Start chat session
        await self.chat_session(engine, session)


async def main():
    """Entry point for the CLI"""
    await ChatCLI().run()


if __name__ == "__main__":
    asyncio.run(main())
