"""
Parallel Discussion Orchestrator
================================

Enhanced orchestrator that allows participants to prepare in the background
while maintaining turn-based discussion order.

Architecture:
- Current speaker: Active process generating response
- Next speaker(s): Background processes preparing (reading files, searching, etc.)
- Preparation results are cached and used when it's their turn to speak
"""

import asyncio
import json
import logging
import os
import subprocess
import sys
import tempfile
import threading
from pathlib import Path
from typing import AsyncGenerator, Optional, List, Callable, Dict

from .history_reader import (
    load_session_history,
    format_context_for_injection,
    decode_project_id,
    get_original_path_from_dir,
)
from .codex_history_reader import _decode_path as decode_codex_path
from .meeting_prompts import get_facilitator_opening
from ..models.database import (
    DiscussionRoom,
    RoomParticipant,
    DiscussionMessage,
    RoomStatus,
    MeetingType,
)

logger = logging.getLogger(__name__)

# Path to the agent scripts
PARTICIPANT_AGENT_PATH = Path(__file__).parent / "participant_agent.py"
CODEX_AGENT_PATH = Path(__file__).parent / "codex_agent.py"

# How many participants ahead to prepare
PREPARATION_LOOKAHEAD = 2


class ParticipantAgent:
    """
    Manages a single Claude participant with background preparation support.

    Supports two modes:
    - prepare: Background preparation (reading files, gathering info)
    - speak: Generate actual discussion response
    """

    def __init__(
        self,
        participant: RoomParticipant,
        context_text: str,
        room_topic: str,
        meeting_type: Optional[str] = None,
        custom_meeting_description: str = "",
        language: str = "ja",
    ):
        self.participant = participant
        self.context_text = context_text
        self.room_topic = room_topic
        self.meeting_type = meeting_type
        self.custom_meeting_description = custom_meeting_description
        self.language = language
        self.cwd: Optional[str] = None
        self.is_facilitator = participant.is_facilitator or False
        self.agent_type = participant.agent_type.value if participant.agent_type else "claude"

        # Process management
        self._speak_process: Optional[subprocess.Popen] = None
        self._prepare_process: Optional[subprocess.Popen] = None

        # Preparation state
        self.preparation_notes: str = ""
        self.is_preparing: bool = False
        self.preparation_complete: bool = False

        # Thread safety
        self._lock = threading.Lock()

    def resolve_cwd(self) -> None:
        """Resolve the working directory from participant's project context."""
        if self.participant.context_project_dir:
            try:
                if self.agent_type == "codex":
                    # Codex projects: context_project_dir is base64-encoded path
                    actual_path = decode_codex_path(self.participant.context_project_dir)
                    if actual_path and Path(actual_path).exists():
                        self.cwd = actual_path
                        logger.info(f"Resolved cwd for {self.participant.name} (Codex): {self.cwd}")
                else:
                    # Claude Code projects: use internal directory structure
                    internal_dir = Path(decode_project_id(self.participant.context_project_dir))
                    actual_path = get_original_path_from_dir(internal_dir)
                    if actual_path and Path(actual_path).exists():
                        self.cwd = actual_path
                        logger.info(f"Resolved cwd for {self.participant.name} (Claude): {self.cwd}")
            except Exception as e:
                logger.warning(f"Failed to resolve cwd for {self.participant.name}: {e}")

    def _create_data_file(
        self,
        conversation_history: str,
        preparation_notes: str = "",
    ) -> str:
        """Create temporary file with context data."""
        data = {
            "room_topic": self.room_topic,
            "context_text": self.context_text,
            "conversation_history": conversation_history,
            "preparation_notes": preparation_notes,
            "meeting_type": self.meeting_type,
            "custom_meeting_description": self.custom_meeting_description,
            "language": self.language,
        }

        fd, data_file = tempfile.mkstemp(suffix=".json", prefix="participant_")
        with os.fdopen(fd, "w", encoding="utf-8") as f:
            json.dump(data, f, ensure_ascii=False)
        return data_file

    def _build_command(self, data_file: str, mode: str) -> List[str]:
        """Build the subprocess command."""
        # Choose agent script based on agent_type
        agent_script = CODEX_AGENT_PATH if self.agent_type == "codex" else PARTICIPANT_AGENT_PATH

        cmd = [
            sys.executable, "-u",
            str(agent_script),
            "--participant-id", str(self.participant.id),
            "--participant-name", self.participant.name,
            "--participant-role", self.participant.role or "",
            "--data-file", data_file,
            "--mode", mode,
            "--language", self.language,
        ]
        if self.cwd:
            cmd.extend(["--cwd", self.cwd])
        if self.meeting_type:
            cmd.extend(["--meeting-type", self.meeting_type])
        if self.is_facilitator:
            cmd.append("--is-facilitator")
        return cmd

    def start_preparation(
        self,
        conversation_history: str,
        on_activity: Optional[Callable[[str], None]] = None,
        on_complete: Optional[Callable[[str], None]] = None,
    ) -> None:
        """
        Start background preparation process.

        Args:
            conversation_history: Current conversation for context
            on_activity: Callback for activity updates (tool use, etc.)
            on_complete: Callback when preparation completes
        """
        with self._lock:
            if self.is_preparing or self.preparation_complete:
                return

            self.is_preparing = True
            self.preparation_notes = ""

        data_file = self._create_data_file(conversation_history)
        cmd = self._build_command(data_file, "prepare")

        logger.info(f"Starting preparation for {self.participant.name}")

        env = os.environ.copy()
        env["PYTHONUNBUFFERED"] = "1"

        self._prepare_process = subprocess.Popen(
            cmd,
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
            text=True,
            encoding="utf-8",
            errors="replace",
            env=env,
            cwd=str(Path(__file__).parent.parent.parent),
        )

        # Start reader thread
        # Store local reference to avoid race condition with stop_preparation()
        proc = self._prepare_process

        def read_preparation_output():
            try:
                notes = ""
                if proc and proc.stdout:
                    for line in proc.stdout:
                        line = line.strip()
                        if not line:
                            continue

                        try:
                            msg = json.loads(line)

                            if msg.get("type") == "tool_use":
                                if on_activity:
                                    on_activity(f"Using {msg.get('tool')}: {msg.get('input', '')[:50]}...")

                            elif msg.get("type") == "text":
                                notes += msg.get("content", "")

                            elif msg.get("type") == "response_complete":
                                notes = msg.get("full_content", notes)

                        except json.JSONDecodeError:
                            pass

                if proc:
                    proc.wait()

                with self._lock:
                    self.preparation_notes = notes
                    self.is_preparing = False
                    self.preparation_complete = True

                if on_complete:
                    on_complete(notes[:200] + "..." if len(notes) > 200 else notes)

                logger.info(f"Preparation complete for {self.participant.name}: {len(notes)} chars")

            except Exception as e:
                logger.error(f"Error in preparation for {self.participant.name}: {e}")
                with self._lock:
                    self.is_preparing = False

            finally:
                # Clean up data file
                try:
                    Path(data_file).unlink(missing_ok=True)
                except Exception:
                    pass

        thread = threading.Thread(target=read_preparation_output, daemon=True)
        thread.start()

    async def speak(
        self,
        conversation_history: str,
    ) -> AsyncGenerator[dict, None]:
        """
        Generate a speaking response.

        Uses preparation notes if available.
        """
        with self._lock:
            prep_notes = self.preparation_notes
            # Reset preparation state for next turn
            self.preparation_notes = ""
            self.preparation_complete = False

        data_file = self._create_data_file(conversation_history, prep_notes)
        cmd = self._build_command(data_file, "speak")

        logger.info(f"Starting speech for {self.participant.name} (prep_notes: {len(prep_notes)} chars)")

        env = os.environ.copy()
        env["PYTHONUNBUFFERED"] = "1"

        logger.info(f"speak: Spawning subprocess for {self.participant.name}")
        logger.info(f"speak: Command: {' '.join(cmd)}")

        self._speak_process = subprocess.Popen(
            cmd,
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
            text=True,
            encoding="utf-8",
            errors="replace",
            env=env,
            cwd=str(Path(__file__).parent.parent.parent),
        )

        logger.info(f"speak: Process started, PID={self._speak_process.pid}")

        try:
            loop = asyncio.get_event_loop()
            full_response = ""

            while True:
                logger.debug(f"speak: Waiting for output line...")
                line = await loop.run_in_executor(
                    None, self._speak_process.stdout.readline
                )

                if not line:
                    logger.info(f"speak: No more output, breaking loop")
                    break

                line = line.strip()
                if not line:
                    continue

                logger.debug(f"speak: Got line: {line[:100]}...")

                try:
                    msg = json.loads(line)
                    msg_type = msg.get("type")
                    logger.info(f"speak: Received message type: {msg_type}")

                    # Log debug messages from Codex agent
                    if msg_type == "debug":
                        logger.info(f"speak: DEBUG from agent: {msg.get('event_type')} - {msg.get('event_data', '')[:300]}")
                        continue  # Don't yield debug messages

                    yield msg

                    if msg_type == "text":
                        full_response += msg.get("content", "")
                    elif msg_type == "response_complete":
                        full_response = msg.get("full_content", full_response)

                except json.JSONDecodeError:
                    logger.warning(f"Non-JSON output: {line}")

            # Store local reference to avoid race condition with stop_speech()
            proc = self._speak_process
            if proc:
                await loop.run_in_executor(None, proc.wait)

                if proc.returncode != 0:
                    stderr = proc.stderr.read() if proc.stderr else ""
                    logger.error(f"Speech process failed: {stderr}")
                    if not full_response:
                        yield {"type": "error", "content": f"Process failed: {stderr[:500]}"}

        except Exception as e:
            logger.error(f"Error in speech for {self.participant.name}: {e}")
            yield {"type": "error", "content": str(e)}

        finally:
            try:
                Path(data_file).unlink(missing_ok=True)
            except Exception:
                pass

            proc = self._speak_process
            if proc:
                try:
                    proc.kill()
                except Exception:
                    pass
                self._speak_process = None

    def stop_preparation(self):
        """Stop the preparation process if running."""
        proc = self._prepare_process
        self._prepare_process = None
        if proc:
            try:
                proc.terminate()
                proc.wait(timeout=2)
            except Exception:
                try:
                    proc.kill()
                except Exception:
                    pass

        with self._lock:
            self.is_preparing = False

    def stop_speech(self):
        """Stop the speech process if running."""
        proc = self._speak_process
        self._speak_process = None
        if proc:
            try:
                proc.terminate()
                proc.wait(timeout=2)
            except Exception:
                try:
                    proc.kill()
                except Exception:
                    pass

    def stop_all(self):
        """Stop all processes."""
        self.stop_preparation()
        self.stop_speech()

    def generate_facilitator_opening(
        self,
        participants: List["ParticipantAgent"],
        first_speaker_name: str,
    ) -> str:
        """Generate the facilitator opening message."""
        if not self.is_facilitator:
            return ""

        meeting_type_enum = None
        if self.meeting_type:
            try:
                meeting_type_enum = MeetingType(self.meeting_type)
            except ValueError:
                meeting_type_enum = MeetingType.TECHNICAL_REVIEW
        else:
            meeting_type_enum = MeetingType.TECHNICAL_REVIEW

        participant_names = [p.participant.name for p in participants if not p.is_facilitator]

        return get_facilitator_opening(
            meeting_type=meeting_type_enum,
            topic=self.room_topic,
            participants=participant_names,
            first_speaker=first_speaker_name,
            custom_description=self.custom_meeting_description,
        )


class ParallelDiscussionOrchestrator:
    """
    Orchestrates a multi-Claude discussion with parallel preparation.

    While one participant is speaking, the next participant(s) can prepare
    in the background by reading files, searching code, etc.
    """

    def __init__(
        self,
        room: DiscussionRoom,
        db_session,
        on_event: Optional[Callable] = None,
    ):
        self.room = room
        self.db = db_session
        self.participants: List[ParticipantAgent] = []
        self.regular_participants: List[ParticipantAgent] = []  # Non-facilitator participants
        self.facilitator: Optional[ParticipantAgent] = None
        self.current_speaker_idx = 0
        self._running = False
        self._paused = False
        self.on_event = on_event

        # Event queue for background activity
        self._event_queue: asyncio.Queue = asyncio.Queue()

    async def initialize_participants(self):
        """Initialize all participant agents with their contexts."""
        # Get room-level settings
        meeting_type = self.room.meeting_type.value if self.room.meeting_type else None
        custom_meeting_description = self.room.custom_meeting_description or ""
        language = self.room.language or "ja"

        for participant in self.room.participants:
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
                    logger.warning(f"Failed to load context for {participant.name}: {e}")
                    context_text = participant.context_summary or ""
            elif participant.context_summary:
                context_text = participant.context_summary

            agent = ParticipantAgent(
                participant=participant,
                context_text=context_text,
                room_topic=self.room.topic or "General discussion",
                meeting_type=meeting_type,
                custom_meeting_description=custom_meeting_description,
                language=language,
            )
            agent.resolve_cwd()

            # Set default cwd to project root if not resolved
            project_root = str(Path(__file__).parent.parent.parent)
            if not agent.cwd:
                agent.cwd = project_root

            # Track facilitator separately
            if agent.is_facilitator:
                self.facilitator = agent
            else:
                self.regular_participants.append(agent)

            self.participants.append(agent)

        logger.info(
            f"Initialized {len(self.participants)} participants "
            f"(lang={language}, type={meeting_type}, facilitator={self.facilitator is not None})"
        )

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
                participant = next(
                    (p for p in self.room.participants if p.id == msg.participant_id),
                    None
                )
                name = participant.name if participant else "Unknown"
                lines.append(f"[{name}]: {msg.content}\n")

        return "\n".join(lines)

    def _get_next_speakers(self, count: int = PREPARATION_LOOKAHEAD) -> List[int]:
        """Get indices of next regular speakers to prepare."""
        if not self.regular_participants:
            return []

        indices = []
        for i in range(1, count + 1):
            idx = (self.current_speaker_idx + i) % len(self.regular_participants)
            if idx != self.current_speaker_idx:
                indices.append(idx)
        return indices

    def _start_preparations(self, history: str):
        """Start preparation for upcoming regular speakers."""
        for idx in self._get_next_speakers():
            agent = self.regular_participants[idx]

            if not agent.is_preparing and not agent.preparation_complete:
                def on_activity(activity: str, agent=agent):
                    # Queue activity event for broadcast
                    try:
                        self._event_queue.put_nowait({
                            "type": "background_activity",
                            "participant_id": agent.participant.id,
                            "participant_name": agent.participant.name,
                            "activity": activity,
                        })
                    except asyncio.QueueFull:
                        pass

                def on_complete(notes_preview: str, agent=agent):
                    try:
                        self._event_queue.put_nowait({
                            "type": "preparation_complete",
                            "participant_id": agent.participant.id,
                            "participant_name": agent.participant.name,
                            "notes_preview": notes_preview,
                        })
                    except asyncio.QueueFull:
                        pass

                agent.start_preparation(
                    history,
                    on_activity=on_activity,
                    on_complete=on_complete,
                )

                # Queue preparation start event
                try:
                    self._event_queue.put_nowait({
                        "type": "preparation_start",
                        "participant_id": agent.participant.id,
                        "participant_name": agent.participant.name,
                    })
                except asyncio.QueueFull:
                    pass

    async def _drain_event_queue(self) -> AsyncGenerator[dict, None]:
        """Drain and yield events from the background event queue."""
        while True:
            try:
                event = self._event_queue.get_nowait()
                yield event
            except asyncio.QueueEmpty:
                break

    async def run_turn(self) -> AsyncGenerator[dict, None]:
        """Run a single turn of discussion with parallel preparation."""
        logger.info(f"run_turn: starting turn {self.room.current_turn + 1}")

        if not self.regular_participants:
            logger.error("run_turn: no regular participants initialized")
            yield {"type": "error", "content": "No participants initialized"}
            return

        # Get current speaker (from regular participants, not facilitator)
        speaker = self.regular_participants[self.current_speaker_idx]
        participant = speaker.participant
        logger.info(f"run_turn: speaker is {participant.name} (idx={self.current_speaker_idx})")

        yield {
            "type": "turn_start",
            "participant_id": participant.id,
            "participant_name": participant.name,
            "turn_number": self.room.current_turn + 1,
        }

        # Mark as speaking
        participant.is_speaking = True
        self.db.commit()

        # Build history
        history = self._build_conversation_history()
        logger.info(f"run_turn: built history ({len(history)} chars)")

        # Start preparations for next speakers
        self._start_preparations(history)

        # Yield any queued background events
        async for event in self._drain_event_queue():
            yield event

        # Generate speech
        logger.info(f"run_turn: calling speaker.speak()")
        full_content = ""
        async for chunk in speaker.speak(history):
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

            # Also yield any background events that came in
            async for event in self._drain_event_queue():
                yield event

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
        ) % len(self.regular_participants)
        self.db.commit()

        yield {
            "type": "turn_complete",
            "participant_id": participant.id,
            "message_id": message.id,
            "turn_number": self.room.current_turn,
        }

    async def run_facilitator_opening(self) -> AsyncGenerator[dict, None]:
        """Generate facilitator opening message."""
        if not self.facilitator:
            return

        participant = self.facilitator.participant

        yield {
            "type": "turn_start",
            "participant_id": participant.id,
            "participant_name": participant.name,
            "turn_number": 0,
            "is_facilitator": True,
        }

        # Mark as speaking
        participant.is_speaking = True
        self.db.commit()

        # Get first regular speaker name
        first_speaker_name = (
            self.regular_participants[0].participant.name
            if self.regular_participants
            else "参加者"
        )

        # Generate opening message
        opening_message = self.facilitator.generate_facilitator_opening(
            participants=self.participants,
            first_speaker_name=first_speaker_name,
        )

        if opening_message:
            # Yield the message as text chunks
            yield {
                "type": "text",
                "content": opening_message,
                "participant_id": participant.id,
            }

            # Save to database
            message = DiscussionMessage(
                room_id=self.room.id,
                participant_id=participant.id,
                role="participant",
                content=opening_message,
                turn_number=0,
            )
            self.db.add(message)

            participant.is_speaking = False
            participant.message_count += 1
            self.db.commit()

            yield {
                "type": "turn_complete",
                "participant_id": participant.id,
                "message_id": message.id,
                "turn_number": 0,
                "is_facilitator": True,
            }

    async def run_facilitator_closing(self) -> AsyncGenerator[dict, None]:
        """Generate facilitator closing message."""
        if not self.facilitator:
            return

        participant = self.facilitator.participant

        yield {
            "type": "turn_start",
            "participant_id": participant.id,
            "participant_name": participant.name,
            "turn_number": self.room.current_turn + 1,
            "is_facilitator": True,
            "is_closing": True,
        }

        # Mark as speaking
        participant.is_speaking = True
        self.db.commit()

        # Build conversation history for closing summary
        history = self._build_conversation_history()

        # Generate closing using the agent (so it can summarize the discussion)
        full_content = ""
        async for chunk in self.facilitator.speak(history):
            if chunk["type"] == "text":
                yield {
                    "type": "text",
                    "content": chunk["content"],
                    "participant_id": participant.id,
                }
            elif chunk["type"] == "response_complete":
                full_content = chunk["full_content"]

        # Save to database
        message = DiscussionMessage(
            room_id=self.room.id,
            participant_id=participant.id,
            role="participant",
            content=full_content,
            turn_number=self.room.current_turn + 1,
        )
        self.db.add(message)

        participant.is_speaking = False
        participant.message_count += 1
        self.room.current_turn += 1
        self.db.commit()

        yield {
            "type": "turn_complete",
            "participant_id": participant.id,
            "message_id": message.id,
            "turn_number": self.room.current_turn,
            "is_facilitator": True,
            "is_closing": True,
        }

    async def run_discussion(self) -> AsyncGenerator[dict, None]:
        """Run the full discussion with parallel preparation."""
        self._running = True
        self._paused = False
        self.room.status = RoomStatus.ACTIVE
        self.db.commit()

        yield {
            "type": "discussion_start",
            "room_id": self.room.id,
            "max_turns": self.room.max_turns,
            "has_facilitator": self.facilitator is not None,
        }

        # Facilitator opening (if present)
        if self.facilitator:
            async for chunk in self.run_facilitator_opening():
                yield chunk
            await asyncio.sleep(1)

        while (
            self._running
            and not self._paused
            and self.room.current_turn < self.room.max_turns
        ):
            async for chunk in self.run_turn():
                yield chunk

            # Small delay between turns
            await asyncio.sleep(1)

            # Refresh room state
            self.db.refresh(self.room)
            if self.room.status == RoomStatus.PAUSED:
                self._paused = True
                yield {"type": "discussion_paused", "turn": self.room.current_turn}
                break

        # Facilitator closing (if present and not paused)
        if not self._paused and self.facilitator:
            async for chunk in self.run_facilitator_closing():
                yield chunk

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

        for p in self.participants:
            p.stop_all()

    def stop(self):
        """Stop the discussion."""
        self._running = False
        self.room.status = RoomStatus.COMPLETED
        self.db.commit()

        for p in self.participants:
            p.stop_all()

    async def cleanup(self):
        """Clean up all participant agents."""
        for agent in self.participants:
            agent.stop_all()
        self.participants.clear()
        logger.info("Cleaned up all participant agents")


# Global registry of active orchestrators
_active_parallel_orchestrators: Dict[int, ParallelDiscussionOrchestrator] = {}


def get_parallel_orchestrator(room_id: int) -> Optional[ParallelDiscussionOrchestrator]:
    """Get an active parallel orchestrator by room ID."""
    return _active_parallel_orchestrators.get(room_id)


def register_parallel_orchestrator(room_id: int, orchestrator: ParallelDiscussionOrchestrator):
    """Register an active parallel orchestrator."""
    _active_parallel_orchestrators[room_id] = orchestrator


def unregister_parallel_orchestrator(room_id: int):
    """Unregister a parallel orchestrator."""
    if room_id in _active_parallel_orchestrators:
        del _active_parallel_orchestrators[room_id]


async def cleanup_all_parallel_orchestrators():
    """Clean up all active parallel orchestrators."""
    for room_id, orchestrator in list(_active_parallel_orchestrators.items()):
        await orchestrator.cleanup()
    _active_parallel_orchestrators.clear()
