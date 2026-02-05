"""
Codex Participant Agent
=======================

Codex SDK を使用した Codex エージェント。
サブプロセスとして実行し、JSON Lines 形式で出力。

Required:
    pip install codex-sdk-py

Usage:
    python -m backend.services.codex_agent \
        --participant-id 1 \
        --participant-name "Codex A" \
        --participant-role "Code Expert" \
        --data-file /tmp/context.json \
        --mode speak

Output (JSON Lines to stdout):
    {"type": "text", "content": "..."}
    {"type": "response_complete", "full_content": "..."}
"""

import argparse
import asyncio
import json
import logging
import sys
from pathlib import Path
from typing import Optional

# Codex SDK
try:
    from codex_sdk import Codex, SandboxMode, ApprovalMode
except ImportError:
    print(json.dumps({
        "type": "error",
        "content": "Codex SDK is not installed. Please run: pip install codex-sdk-py"
    }), flush=True)
    sys.exit(1)

# Configure logging to stderr (stdout is reserved for JSON output)
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s - %(name)s - %(levelname)s - %(message)s",
    stream=sys.stderr,
)
logger = logging.getLogger(__name__)


def emit_json(data: dict) -> None:
    """Emit a JSON line to stdout."""
    print(json.dumps(data, ensure_ascii=False), flush=True)


def build_prompt(
    name: str,
    role: str,
    topic: str,
    context: str,
    conversation_history: str,
    meeting_type_prompt: str,
    language: str = "ja",
    is_facilitator: bool = False,
    mode: str = "speak",
    preparation_notes: str = "",
) -> str:
    """Build the prompt for Codex participant."""
    role_desc = role or "discussion participant"

    language_instruction = (
        "あなたは日本語で議論に参加します。全ての発言は日本語で行ってください。"
        if language == "ja"
        else "You participate in the discussion in English. All your responses should be in English."
    )

    if is_facilitator:
        base_prompt = f"""You are {name}, the facilitator of this multi-Claude discussion room.

{language_instruction}

## READ-ONLY MODE
This is a discussion-only environment. DO NOT modify any files.

## Discussion Topic
{topic}

{meeting_type_prompt}

## Your Task
You are generating the CLOSING message for this discussion.
Please summarize:
1. The key discussion points
2. Decisions made (if any)
3. Next actions or open items

## Response Format
- Start with [{name}]:
- Be concise but comprehensive
- Thank the participants at the end
"""
    elif mode == "prepare":
        base_prompt = f"""You are {name}, a {role_desc} preparing for a multi-Claude discussion.

{language_instruction}

## PREPARATION MODE
You are preparing to contribute to a discussion. Your task is to:
1. Read relevant files to understand the codebase
2. Search for information that will be useful for the discussion
3. Take notes on key findings

**DO NOT** generate a discussion response yet. Instead, output a summary of your findings
that will help you when it's your turn to speak.

{meeting_type_prompt}

## Discussion Topic
{topic}

## Your Background Context
{context if context else "(No prior context provided)"}

## Output Format
Summarize your findings in 2-3 paragraphs that will help you contribute to the discussion.
Focus on technical details, code patterns, and insights relevant to the topic.
"""
    else:
        base_prompt = f"""You are {name}, a {role_desc} in a multi-Claude discussion room.

{language_instruction}

## READ-ONLY MODE
This is a DISCUSSION-ONLY environment. DO NOT modify any files.

{meeting_type_prompt}

## Discussion Topic
{topic}

## Your Background Context
{context if context else "(No prior context provided)"}

## Discussion Guidelines
1. Reference other participants by name
2. Be concise (2-4 paragraphs)
3. Start with [{name}]:
4. Focus on analysis, architecture discussions, code review feedback, and sharing knowledge
5. Do NOT offer to implement anything - only discuss approaches and trade-offs
"""

    # Add conversation history and final instruction
    if mode == "prepare":
        return f"""{base_prompt}

## Current Discussion (for context)
{conversation_history if conversation_history else "(Discussion not started yet)"}

Please analyze and prepare notes for your upcoming contribution to this discussion.
"""
    else:
        prompt = f"""{base_prompt}

## Current Discussion
{conversation_history}

"""
        if preparation_notes:
            prompt += f"""## Your Preparation Notes
{preparation_notes}

"""
        prompt += f"""Please provide your response to continue the discussion. Remember to start with [{name}]:"""
        return prompt


async def run_codex_agent(
    participant_id: int,
    participant_name: str,
    participant_role: str,
    room_topic: str,
    context_text: str,
    conversation_history: str,
    cwd: Optional[str] = None,
    mode: str = "speak",
    preparation_notes: str = "",
    meeting_type: Optional[str] = None,
    custom_meeting_description: str = "",
    language: str = "ja",
    is_facilitator: bool = False,
) -> None:
    """
    Run the Codex agent to generate one response.

    Uses Codex SDK (codex-sdk-py package).
    """
    logger.info(f"Starting Codex agent: {participant_name} (mode={mode}, lang={language})")

    # Build meeting type prompt
    meeting_type_prompt = ""
    if meeting_type:
        # Import meeting_prompts - handle both module and standalone execution
        try:
            from .meeting_prompts import get_meeting_type_prompt
        except ImportError:
            sys.path.insert(0, str(Path(__file__).parent))
            from meeting_prompts import get_meeting_type_prompt

        meeting_type_prompt = get_meeting_type_prompt(meeting_type, custom_meeting_description)

    prompt = build_prompt(
        name=participant_name,
        role=participant_role,
        topic=room_topic,
        context=context_text,
        conversation_history=conversation_history,
        meeting_type_prompt=meeting_type_prompt,
        language=language,
        is_facilitator=is_facilitator,
        mode=mode,
        preparation_notes=preparation_notes,
    )

    try:
        # Create Codex client
        codex = Codex()

        # Start thread with read-only sandbox mode
        thread_options = {
            "sandbox_mode": SandboxMode.READ_ONLY,
            "approval_policy": ApprovalMode.NEVER,
            "skip_git_repo_check": True,  # Always skip for discussion mode
        }

        # Set working directory if provided
        if cwd:
            thread_options["working_directory"] = cwd

        thread = codex.start_thread(thread_options)

        # Run with streaming to get intermediate events
        streamed = await thread.run_streamed(prompt)

        full_response = ""
        async for event in streamed.events:
            event_type = event.get("type")
            # Emit debug info as JSON to stdout (so orchestrator can see it)
            emit_json({"type": "debug", "event_type": event_type, "event_data": json.dumps(event, default=str)[:500]})

            if event_type == "item.completed":
                item = event.get("item", {})
                item_type = item.get("type")

                if item_type == "agent_message":
                    # agent_message has direct "text" field
                    text = item.get("text", "")
                    if text:
                        full_response += text
                        emit_json({"type": "text", "content": text})

                elif item_type == "reasoning":
                    # reasoning items have "text" field too, but we skip them for now
                    pass

                elif item_type == "command_execution":
                    # Tool use - show what command was executed
                    command = item.get("command", "")
                    emit_json({
                        "type": "tool_use",
                        "tool": "command",
                        "input": command[:200],
                    })

                elif item_type == "file_change":
                    # File read/write
                    file_path = item.get("file_path", "")
                    action = item.get("action", "read")
                    emit_json({
                        "type": "tool_use",
                        "tool": f"file_{action}",
                        "input": file_path[:200],
                    })

            elif event_type == "turn.completed":
                # Turn completed - extract final response if not already captured
                turn_response = event.get("final_response", "")
                if turn_response and not full_response:
                    full_response = turn_response
                    emit_json({"type": "text", "content": turn_response})
                logger.info(f"Turn completed, full_response length: {len(full_response)}")

            elif event_type == "turn.failed":
                error = event.get("error", "Unknown error")
                logger.error(f"Turn failed: {error}")
                emit_json({"type": "error", "content": str(error)})

        # If still no response, try to get from streamed.turn
        if not full_response and hasattr(streamed, 'turn') and streamed.turn:
            full_response = getattr(streamed.turn, 'final_response', '') or ''
            if full_response:
                emit_json({"type": "text", "content": full_response})

        # Emit completion
        emit_json({
            "type": "response_complete",
            "full_content": full_response,
            "mode": mode,
        })

    except Exception as e:
        logger.error(f"Error in Codex agent: {e}")
        emit_json({"type": "error", "content": str(e)})
        sys.exit(1)


def main():
    parser = argparse.ArgumentParser(description="Codex agent for discussions")
    parser.add_argument("--participant-id", type=int, required=True, help="Participant database ID")
    parser.add_argument("--participant-name", required=True, help="Participant display name")
    parser.add_argument("--participant-role", default="", help="Participant role")
    parser.add_argument("--data-file", required=True, help="JSON file with context data")
    parser.add_argument("--cwd", default=None, help="Working directory for file operations")
    parser.add_argument("--mode", choices=["speak", "prepare"], default="speak", help="Agent mode")
    parser.add_argument("--meeting-type", default=None, help="Meeting type")
    parser.add_argument("--language", default="ja", help="Language for discussion")
    parser.add_argument("--is-facilitator", action="store_true", help="Whether this is a facilitator")

    args = parser.parse_args()

    # Load context data from file
    try:
        with open(args.data_file, "r", encoding="utf-8") as f:
            data = json.load(f)
    except Exception as e:
        emit_json({"type": "error", "content": f"Failed to load data file: {e}"})
        sys.exit(1)

    # Run the agent
    asyncio.run(run_codex_agent(
        participant_id=args.participant_id,
        participant_name=args.participant_name,
        participant_role=args.participant_role,
        room_topic=data.get("room_topic", ""),
        context_text=data.get("context_text", ""),
        conversation_history=data.get("conversation_history", ""),
        cwd=args.cwd,
        mode=args.mode,
        preparation_notes=data.get("preparation_notes", ""),
        meeting_type=args.meeting_type or data.get("meeting_type"),
        custom_meeting_description=data.get("custom_meeting_description", ""),
        language=args.language or data.get("language", "ja"),
        is_facilitator=args.is_facilitator or data.get("is_facilitator", False),
    ))


if __name__ == "__main__":
    main()
