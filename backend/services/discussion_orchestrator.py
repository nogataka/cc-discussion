"""
Discussion Orchestrator
=======================

Orchestrates multi-Claude discussions using subprocess-based agents.
Each participant agent runs in a separate process to avoid client reuse issues.
"""

import asyncio
import json
import logging
import os
import subprocess
import sys
import tempfile
from pathlib import Path
from typing import AsyncGenerator, Optional, List, Callable

from .history_reader import (
    load_session_history,
    format_context_for_injection,
    decode_project_id,
    get_original_path_from_dir,
)
from ..models.database import (
    DiscussionRoom,
    RoomParticipant,
    DiscussionMessage,
    RoomStatus,
)

logger = logging.getLogger(__name__)

# Path to the participant agent script
PARTICIPANT_AGENT_PATH = Path(__file__).parent / "participant_agent.py"


class ParticipantClient:
    """
    Manages a single Claude participant in the discussion.

    Uses subprocess-based execution to avoid client reuse issues.
    Each call to respond() spawns a fresh process with a new ClaudeSDKClient.
    """

    def __init__(
        self,
        participant: RoomParticipant,
        context_text: str,
        room_topic: str,
    ):
        self.participant = participant
        self.context_text = context_text
        self.room_topic = room_topic
        self.cwd: Optional[str] = None
        self._process: Optional[subprocess.Popen] = None

    def resolve_cwd(self) -> None:
        """Resolve the working directory from participant's project context."""
        if self.participant.context_project_dir:
            try:
                # Decode the Base64 project ID to get internal directory path
                internal_dir = Path(decode_project_id(self.participant.context_project_dir))
                # Get the actual project path from session files
                actual_path = get_original_path_from_dir(internal_dir)
                if actual_path and Path(actual_path).exists():
                    self.cwd = actual_path
                    logger.info(f"Resolved cwd for {self.participant.name}: {self.cwd}")
            except Exception as e:
                logger.warning(f"Failed to resolve cwd for {self.participant.name}: {e}")

    async def respond(
        self,
        conversation_history: str,
        mode: str = "speak",
        preparation_notes: str = "",
    ) -> AsyncGenerator[dict, None]:
        """
        Generate a response by spawning a subprocess.

        Args:
            conversation_history: Current conversation history
            mode: "speak" for generating response, "prepare" for preparation
            preparation_notes: Notes from preparation phase (if any)

        Yields:
            Dict with type and content (text chunks, tool use, completion, etc.)
        """
        # Create temporary file with context data
        data = {
            "room_topic": self.room_topic,
            "context_text": self.context_text,
            "conversation_history": conversation_history,
            "preparation_notes": preparation_notes,
        }

        # Write context to temp file
        fd, data_file = tempfile.mkstemp(suffix=".json", prefix="participant_")
        try:
            with os.fdopen(fd, "w", encoding="utf-8") as f:
                json.dump(data, f, ensure_ascii=False)

            # Build command
            cmd = [
                sys.executable, "-u",
                str(PARTICIPANT_AGENT_PATH),
                "--participant-id", str(self.participant.id),
                "--participant-name", self.participant.name,
                "--participant-role", self.participant.role or "",
                "--data-file", data_file,
                "--mode", mode,
            ]

            if self.cwd:
                cmd.extend(["--cwd", self.cwd])

            logger.info(f"Spawning participant agent: {self.participant.name} (mode={mode})")

            # Spawn subprocess
            env = os.environ.copy()
            env["PYTHONUNBUFFERED"] = "1"

            self._process = subprocess.Popen(
                cmd,
                stdout=subprocess.PIPE,
                stderr=subprocess.PIPE,
                text=True,
                encoding="utf-8",
                errors="replace",
                env=env,
                cwd=str(Path(__file__).parent.parent.parent),  # Project root
            )

            # Read stdout line by line (JSON Lines format)
            full_response = ""

            async def read_output():
                nonlocal full_response
                loop = asyncio.get_event_loop()

                while True:
                    # Read line in executor to not block event loop
                    line = await loop.run_in_executor(
                        None, self._process.stdout.readline
                    )

                    if not line:
                        break

                    line = line.strip()
                    if not line:
                        continue

                    try:
                        msg = json.loads(line)
                        yield msg

                        # Track full response
                        if msg.get("type") == "text":
                            full_response += msg.get("content", "")
                        elif msg.get("type") == "response_complete":
                            full_response = msg.get("full_content", full_response)

                    except json.JSONDecodeError:
                        logger.warning(f"Non-JSON output from agent: {line}")

            async for msg in read_output():
                yield msg

            # Wait for process to complete
            await asyncio.get_event_loop().run_in_executor(
                None, self._process.wait
            )

            # Check for errors
            if self._process.returncode != 0:
                stderr = self._process.stderr.read()
                logger.error(f"Agent process failed: {stderr}")
                if not full_response:
                    yield {
                        "type": "error",
                        "content": f"Agent process failed: {stderr[:500]}"
                    }

            # Ensure response_complete is yielded if not already
            # (in case the subprocess didn't output it)

        except Exception as e:
            logger.error(f"Error running participant agent: {e}")
            yield {"type": "error", "content": str(e)}

        finally:
            # Clean up temp file
            try:
                Path(data_file).unlink(missing_ok=True)
            except Exception:
                pass

            # Clean up process
            if self._process:
                try:
                    self._process.kill()
                except Exception:
                    pass
                self._process = None

    def stop(self):
        """Stop the running process if any."""
        if self._process:
            try:
                self._process.terminate()
                self._process.wait(timeout=5)
            except Exception:
                try:
                    self._process.kill()
                except Exception:
                    pass
            self._process = None


class DiscussionOrchestrator:
    """Orchestrates a multi-Claude discussion."""

    def __init__(
        self,
        room: DiscussionRoom,
        db_session,
        on_event: Optional[Callable] = None,
    ):
        self.room = room
        self.db = db_session
        self.participants: List[ParticipantClient] = []
        self.current_speaker_idx = 0
        self._running = False
        self._paused = False
        self.on_event = on_event

    async def initialize_participants(self):
        """Initialize all participant clients with their contexts."""
        for participant in self.room.participants:
            # Load context from ClaudeCode history if specified
            context_text = ""
            if participant.context_project_dir and participant.context_session_id:
                try:
                    messages = load_session_history(
                        participant.context_project_dir,
                        participant.context_session_id
                    )
                    context_text = format_context_for_injection(messages, max_chars=50000)
                    logger.info(
                        f"Loaded context for {participant.name}: "
                        f"{len(messages)} messages, {len(context_text)} chars"
                    )
                except Exception as e:
                    logger.warning(
                        f"Failed to load context for {participant.name}: {e}"
                    )
                    context_text = participant.context_summary or ""
            elif participant.context_summary:
                context_text = participant.context_summary

            client = ParticipantClient(
                participant=participant,
                context_text=context_text,
                room_topic=self.room.topic or "General discussion",
            )
            # Resolve working directory
            client.resolve_cwd()
            self.participants.append(client)

        logger.info(f"Initialized {len(self.participants)} participants")

    def _build_conversation_history(self) -> str:
        """Build conversation history string from all messages."""
        messages = self.db.query(DiscussionMessage).filter(
            DiscussionMessage.room_id == self.room.id
        ).order_by(DiscussionMessage.created_at).all()

        lines = []
        for msg in messages:
            if msg.role == "system":
                lines.append(f"[System]: {msg.content}\n")
            elif msg.role == "moderator":
                lines.append(f"[Moderator]: {msg.content}\n")
            else:
                # Find participant name
                participant = next(
                    (p for p in self.room.participants if p.id == msg.participant_id),
                    None
                )
                name = participant.name if participant else "Unknown"
                lines.append(f"[{name}]: {msg.content}\n")

        return "\n".join(lines)

    async def run_turn(self) -> AsyncGenerator[dict, None]:
        """Run a single turn of discussion."""
        if not self.participants:
            yield {"type": "error", "content": "No participants initialized"}
            return

        # Get current speaker
        speaker = self.participants[self.current_speaker_idx]
        participant = speaker.participant

        yield {
            "type": "turn_start",
            "participant_id": participant.id,
            "participant_name": participant.name,
            "turn_number": self.room.current_turn + 1,
        }

        # Mark as speaking
        participant.is_speaking = True
        self.db.commit()

        # Build history and get response
        history = self._build_conversation_history()
        full_content = ""

        async for chunk in speaker.respond(history):
            if chunk["type"] == "text":
                yield {
                    "type": "text",
                    "content": chunk["content"],
                    "participant_id": participant.id,
                }
            elif chunk["type"] == "tool_use":
                yield {
                    "type": "tool_use",
                    "tool": chunk.get("tool"),
                    "input": chunk.get("input"),
                    "participant_id": participant.id,
                }
            elif chunk["type"] == "response_complete":
                full_content = chunk["full_content"]
            elif chunk["type"] == "error":
                yield {
                    "type": "error",
                    "content": chunk["content"],
                    "participant_id": participant.id,
                }

        # Save message to database
        message = DiscussionMessage(
            room_id=self.room.id,
            participant_id=participant.id,
            role="participant",
            content=full_content,
            turn_number=self.room.current_turn + 1,
        )
        self.db.add(message)

        # Update state
        participant.is_speaking = False
        participant.message_count += 1
        self.room.current_turn += 1
        self.current_speaker_idx = (
            self.current_speaker_idx + 1
        ) % len(self.participants)
        self.db.commit()

        yield {
            "type": "turn_complete",
            "participant_id": participant.id,
            "message_id": message.id,
            "turn_number": self.room.current_turn,
        }

    async def run_discussion(self) -> AsyncGenerator[dict, None]:
        """Run the full discussion until max_turns or completion."""
        self._running = True
        self._paused = False
        self.room.status = RoomStatus.ACTIVE
        self.db.commit()

        yield {
            "type": "discussion_start",
            "room_id": self.room.id,
            "max_turns": self.room.max_turns,
        }

        while (
            self._running
            and not self._paused
            and self.room.current_turn < self.room.max_turns
        ):
            async for chunk in self.run_turn():
                yield chunk

            # Small delay between turns for readability
            await asyncio.sleep(1)

            # Refresh room state from database (for pause/stop from outside)
            self.db.refresh(self.room)
            if self.room.status == RoomStatus.PAUSED:
                self._paused = True
                yield {"type": "discussion_paused", "turn": self.room.current_turn}
                break

        if not self._paused:
            self.room.status = RoomStatus.COMPLETED
            self.db.commit()
            yield {
                "type": "discussion_complete",
                "total_turns": self.room.current_turn,
            }

    def pause(self):
        """Pause the discussion."""
        self._paused = True
        self.room.status = RoomStatus.PAUSED
        self.db.commit()

        # Stop any running participant process
        for p in self.participants:
            p.stop()

    def stop(self):
        """Stop the discussion."""
        self._running = False
        self.room.status = RoomStatus.COMPLETED
        self.db.commit()

        # Stop any running participant process
        for p in self.participants:
            p.stop()

    async def cleanup(self):
        """Clean up all participant clients."""
        for client in self.participants:
            client.stop()
        self.participants.clear()
        logger.info("Cleaned up all participant clients")


# Global registry of active orchestrators
_active_orchestrators: dict[int, DiscussionOrchestrator] = {}


def get_orchestrator(room_id: int) -> Optional[DiscussionOrchestrator]:
    """Get an active orchestrator by room ID."""
    return _active_orchestrators.get(room_id)


def register_orchestrator(room_id: int, orchestrator: DiscussionOrchestrator):
    """Register an active orchestrator."""
    _active_orchestrators[room_id] = orchestrator


def unregister_orchestrator(room_id: int):
    """Unregister an orchestrator."""
    if room_id in _active_orchestrators:
        del _active_orchestrators[room_id]


async def cleanup_all_orchestrators():
    """Clean up all active orchestrators."""
    for room_id, orchestrator in list(_active_orchestrators.items()):
        await orchestrator.cleanup()
    _active_orchestrators.clear()
