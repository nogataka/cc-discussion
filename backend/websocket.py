"""
WebSocket Handler
=================

WebSocket endpoint for real-time discussion updates.
Supports both serial and parallel discussion orchestration.
"""

import asyncio
import json
import logging
from typing import Dict, List

from fastapi import WebSocket, WebSocketDisconnect

from .models.database import (
    DiscussionRoom,
    RoomStatus,
    get_session_maker,
)
from .services.parallel_orchestrator import (
    ParallelDiscussionOrchestrator,
    get_parallel_orchestrator,
    register_parallel_orchestrator,
    unregister_parallel_orchestrator,
)

logger = logging.getLogger(__name__)

# Active WebSocket connections per room
_connections: Dict[int, List[WebSocket]] = {}

# Type alias for orchestrator
Orchestrator = ParallelDiscussionOrchestrator


async def broadcast_to_room(room_id: int, message: dict):
    """Broadcast a message to all connected clients in a room."""
    if room_id not in _connections:
        return

    disconnected = []
    for ws in _connections[room_id]:
        try:
            await ws.send_json(message)
        except Exception:
            disconnected.append(ws)

    # Remove disconnected clients
    for ws in disconnected:
        if ws in _connections[room_id]:
            _connections[room_id].remove(ws)


async def room_websocket(websocket: WebSocket, room_id: int):
    """
    WebSocket endpoint for a discussion room.

    Handles:
    - Connection management
    - Starting discussions (with parallel preparation)
    - Streaming updates to clients
    - Moderator message injection
    - Background activity notifications
    """
    await websocket.accept()

    # Get database session
    SessionMaker = get_session_maker()
    db = SessionMaker()

    try:
        # Get room
        room = db.query(DiscussionRoom).filter(
            DiscussionRoom.id == room_id
        ).first()

        if not room:
            await websocket.send_json({
                "type": "error",
                "content": "Room not found"
            })
            await websocket.close()
            return

        # Register connection
        if room_id not in _connections:
            _connections[room_id] = []
        _connections[room_id].append(websocket)

        logger.info(f"WebSocket connected to room {room_id}")

        # Send initial state
        await websocket.send_json({
            "type": "room_state",
            "room_id": room_id,
            "status": room.status.value,
            "current_turn": room.current_turn,
            "max_turns": room.max_turns,
            "participants": [
                {
                    "id": p.id,
                    "name": p.name,
                    "role": p.role,
                    "color": p.color,
                    "is_speaking": p.is_speaking,
                }
                for p in room.participants
            ],
        })

        # Discussion task (started manually via 'start' message)
        discussion_task = None

        # Keep connection alive and handle client messages
        while True:
            try:
                data = await asyncio.wait_for(
                    websocket.receive_text(),
                    timeout=60.0
                )
                message = json.loads(data)

                if message.get("type") == "ping":
                    await websocket.send_json({"type": "pong"})

                elif message.get("type") == "start":
                    # Start discussion if not already running
                    if not get_parallel_orchestrator(room_id):
                        # Refresh room state
                        db.refresh(room)

                        # Handle COMPLETED status: reset to WAITING and extend turns
                        if room.status == RoomStatus.COMPLETED:
                            room.status = RoomStatus.WAITING
                            room.max_turns = room.current_turn + 20
                            db.commit()
                            db.refresh(room)

                        if room.status in (RoomStatus.WAITING, RoomStatus.PAUSED):
                            discussion_task = asyncio.create_task(
                                run_discussion_with_broadcast(room_id, db)
                            )
                            await websocket.send_json({
                                "type": "discussion_starting"
                            })
                    else:
                        await websocket.send_json({
                            "type": "info",
                            "content": "Discussion already running"
                        })

                elif message.get("type") == "pause":
                    orchestrator = get_parallel_orchestrator(room_id)
                    if orchestrator:
                        orchestrator.pause()
                        await broadcast_to_room(room_id, {
                            "type": "discussion_paused"
                        })

                elif message.get("type") == "stop":
                    orchestrator = get_parallel_orchestrator(room_id)
                    if orchestrator:
                        orchestrator.stop()

                elif message.get("type") == "moderate":
                    # Handle moderator message injection
                    content = message.get("content", "").strip()
                    if content:
                        from .models.database import DiscussionMessage
                        from .services.mention_parser import find_all_mentioned_participants

                        msg = DiscussionMessage(
                            room_id=room_id,
                            participant_id=None,
                            role="moderator",
                            content=content,
                            turn_number=room.current_turn,
                        )
                        db.add(msg)
                        db.commit()
                        db.refresh(msg)

                        # Check for @mentions and update orchestrator queue
                        mentioned_ids = []
                        orchestrator = get_parallel_orchestrator(room_id)
                        should_resume = False
                        if orchestrator and room.participants:
                            mentioned_ids = find_all_mentioned_participants(
                                content,
                                room.participants,
                                exclude_facilitator=True,
                            )
                            if mentioned_ids:
                                orchestrator._mentioned_speaker_queue = mentioned_ids
                                logger.info(
                                    f"Moderator mention detected: next speakers = {mentioned_ids}"
                                )

                            # Check if we were waiting for moderator input
                            if orchestrator._waiting_for_moderator:
                                orchestrator._waiting_for_moderator = False
                                orchestrator._paused = False
                                should_resume = True
                                logger.info("Moderator responded - resuming discussion")

                        await broadcast_to_room(room_id, {
                            "type": "moderator_message",
                            "message_id": msg.id,
                            "content": content,
                            "turn_number": msg.turn_number,
                            "mentioned_participants": mentioned_ids,
                        })

                        # Auto-resume discussion if it was waiting for moderator
                        if should_resume:
                            room.status = RoomStatus.WAITING
                            db.commit()
                            asyncio.create_task(run_discussion_with_broadcast(room_id))

            except asyncio.TimeoutError:
                # Send ping to keep connection alive
                try:
                    await websocket.send_json({"type": "ping"})
                except Exception:
                    break

            except WebSocketDisconnect:
                break

            except json.JSONDecodeError:
                await websocket.send_json({
                    "type": "error",
                    "content": "Invalid JSON"
                })

            except Exception as e:
                logger.error(f"WebSocket error: {e}")
                break

    except Exception as e:
        logger.error(f"WebSocket handler error: {e}")

    finally:
        # Remove connection
        if room_id in _connections:
            _connections[room_id] = [
                ws for ws in _connections[room_id] if ws != websocket
            ]
            if not _connections[room_id]:
                del _connections[room_id]

        db.close()
        logger.info(f"WebSocket disconnected from room {room_id}")


async def run_discussion_with_broadcast(room_id: int, _db=None):
    """
    Run a discussion with parallel preparation and broadcast updates.

    Uses ParallelDiscussionOrchestrator which allows participants to
    prepare in the background while maintaining turn-based order.

    Note: Creates its own database session to avoid session conflicts
    with the WebSocket handler's session.
    """
    logger.info(f"Starting discussion broadcast for room {room_id}")

    # Create a fresh session for the discussion to avoid session conflicts
    SessionMaker = get_session_maker()
    db = SessionMaker()

    try:
        # Get fresh room instance
        room = db.query(DiscussionRoom).filter(
            DiscussionRoom.id == room_id
        ).first()

        if not room:
            logger.error(f"Room {room_id} not found")
            await broadcast_to_room(room_id, {
                "type": "error",
                "content": "Room not found"
            })
            return

        logger.info(f"Found room: {room.name}, participants: {len(room.participants)}")

        if not room.participants:
            logger.error(f"Room {room_id} has no participants")
            await broadcast_to_room(room_id, {
                "type": "error",
                "content": "No participants in room"
            })
            return

        # Use parallel orchestrator for background preparation support
        orchestrator = ParallelDiscussionOrchestrator(room, db)
        register_parallel_orchestrator(room_id, orchestrator)

        try:
            logger.info("Initializing participants...")
            await orchestrator.initialize_participants()
            logger.info("Participants initialized, starting discussion...")

            async for event in orchestrator.run_discussion():
                logger.debug(f"Broadcasting event: {event.get('type')}")
                await broadcast_to_room(room_id, event)

            logger.info("Discussion completed normally")

        except Exception as e:
            logger.error(f"Discussion error: {e}", exc_info=True)
            await broadcast_to_room(room_id, {
                "type": "error",
                "content": str(e)
            })

        finally:
            await orchestrator.cleanup()
            unregister_parallel_orchestrator(room_id)

    except Exception as e:
        logger.error(f"Unexpected error in run_discussion_with_broadcast: {e}", exc_info=True)
        await broadcast_to_room(room_id, {
            "type": "error",
            "content": f"Unexpected error: {str(e)}"
        })

    finally:
        db.close()
        logger.info(f"Discussion broadcast ended for room {room_id}")
