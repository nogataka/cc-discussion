"""
Participant Agent
=================

Subprocess-based participant agent for discussions.
Each invocation creates a fresh ClaudeSDKClient, generates one response, and exits.

This solves the client reuse problem where max_turns=1 causes empty responses
on subsequent queries to the same client.

Usage:
    python -m backend.services.participant_agent \
        --participant-id 1 \
        --participant-name "Claude A" \
        --participant-role "Tech Lead" \
        --data-file /tmp/context.json \
        --mode speak

Output (JSON Lines to stdout):
    {"type": "text", "content": "..."}
    {"type": "tool_use", "tool": "Read", "input": "..."}
    {"type": "response_complete", "full_content": "..."}
"""

import argparse
import asyncio
import json
import logging
import sys
from pathlib import Path
from typing import Optional

# Lazy import for ClaudeSDK - check availability at runtime
ClaudeSDKClient = None
ClaudeAgentOptions = None

def _ensure_claude_sdk():
    """Ensure ClaudeSDK is available, exit with error if not."""
    global ClaudeSDKClient, ClaudeAgentOptions
    if ClaudeSDKClient is None:
        try:
            from claude_agent_sdk import ClaudeSDKClient as _Client, ClaudeAgentOptions as _Options
            ClaudeSDKClient = _Client
            ClaudeAgentOptions = _Options
        except ImportError:
            print(json.dumps({
                "type": "error",
                "content": "ClaudeCode SDK is not installed. Please run: pip install claude-agent-sdk"
            }), flush=True)
            sys.exit(1)

# Import meeting prompts - handle both module and standalone execution
try:
    from .meeting_prompts import (
        get_meeting_type_prompt,
        get_language_instruction,
        FACILITATOR_SYSTEM_PROMPT,
        PARTICIPANT_NOMINATION_INSTRUCTION,
    )
    from .settings import get_tool_permission_mode, ToolPermissionMode
except ImportError:
    # Running as standalone script - use direct import
    import sys
    from pathlib import Path
    sys.path.insert(0, str(Path(__file__).parent))
    from meeting_prompts import (
        get_meeting_type_prompt,
        get_language_instruction,
        FACILITATOR_SYSTEM_PROMPT,
        PARTICIPANT_NOMINATION_INSTRUCTION,
    )
    from settings import get_tool_permission_mode, ToolPermissionMode

# Configure logging to stderr (stdout is reserved for JSON output)
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s - %(name)s - %(levelname)s - %(message)s",
    stream=sys.stderr,
)
logger = logging.getLogger(__name__)

# Read-only tools allowed for discussion participants
READ_ONLY_TOOLS = [
    "Read",      # Read files
    "Grep",      # Search file contents
    "Glob",      # Find files by pattern
    "WebFetch",  # Fetch web content (read-only)
    "WebSearch", # Search the web (read-only)
]


def build_system_prompt(
    name: str,
    role: str,
    context: str,
    topic: str,
    mode: str = "speak",
    meeting_type: Optional[str] = None,
    custom_meeting_description: str = "",
    language: str = "ja",
    is_facilitator: bool = False,
) -> str:
    """Build the system prompt for this participant."""
    role_desc = role or "discussion participant"

    # Get meeting type prompt and language instruction
    # meeting_type is already a string, pass it directly
    meeting_type_prompt = ""
    if meeting_type:
        meeting_type_prompt = get_meeting_type_prompt(meeting_type, custom_meeting_description)

    language_instruction = get_language_instruction(language)

    # Facilitator closing prompt
    if is_facilitator and mode == "speak":
        return f"""You are {name}, the facilitator of this multi-Claude discussion room.

{language_instruction}

{FACILITATOR_SYSTEM_PROMPT}

{meeting_type_prompt}

## Discussion Topic
{topic}

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

    if mode == "prepare":
        # Preparation mode: gather information but don't speak yet
        prompt = f"""You are {name}, a {role_desc} preparing for a multi-Claude discussion.

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
        # Speaking mode: generate a discussion response
        prompt = f"""You are {name}, a {role_desc} in a multi-Claude discussion room.

{language_instruction}

## CRITICAL: READ-ONLY DISCUSSION MODE
This is a DISCUSSION-ONLY environment.

**Allowed Actions:**
- Read files to understand code structure
- Search code using Grep and Glob
- Fetch web content for reference
- Discuss, analyze, and share insights

**STRICTLY FORBIDDEN:**
- Writing, editing, or modifying any files
- Executing any bash commands
- Implementing any features or fixes
- Making any changes to the codebase

Your role is to discuss, analyze, share insights, and exchange ideas with other participants.
You may read files to support your discussion points, but you must NEVER modify anything.
If asked to implement or modify anything, politely decline and redirect to discussing the approach instead.

{meeting_type_prompt}

## Discussion Topic
{topic}

## Your Background Context
The following is conversation history from your previous work that is relevant to this discussion:

{context if context else "(No prior context provided)"}

## IMPORTANT: Before Responding
When you are nominated to speak, follow this process:

1. **Review the conversation**: Understand what has been discussed and what question/point was directed at you
2. **Check relevant files**: If the discussion involves code, use Read/Grep/Glob to examine the relevant files in your working directory before forming your opinion
3. **Formulate your response**: Based on your understanding of both the conversation AND the actual code

Do NOT respond immediately with generic observations. Take time to read the relevant code first.

## Discussion Guidelines
1. Build on what others have said - reference their points by name
2. Share insights from your background context when relevant
3. Be concise but thorough - aim for 2-4 paragraphs per response
4. If you disagree, explain your reasoning respectfully
5. Ask clarifying questions when needed
6. When the discussion seems complete, suggest concrete next steps or conclusions
7. Focus on analysis, architecture discussions, code review feedback, and sharing knowledge
8. Do NOT offer to implement anything - only discuss approaches and trade-offs
9. **Ground your discussion in actual code** - cite specific files and line numbers when relevant

{PARTICIPANT_NOMINATION_INSTRUCTION}

## Response Format
- Start your response with [{name}]:
- Write in a conversational but professional tone
- Focus on substance over pleasantries
- Reference specific files/code when making technical points
"""
    return prompt


def emit_json(data: dict) -> None:
    """Emit a JSON line to stdout."""
    print(json.dumps(data, ensure_ascii=False), flush=True)


async def run_participant_agent(
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
    Run the participant agent to generate one response.

    Args:
        participant_id: Database ID of the participant
        participant_name: Display name of the participant
        participant_role: Role description
        room_topic: Discussion topic
        context_text: Background context from ClaudeCode history
        conversation_history: Current conversation history
        cwd: Working directory for file operations
        mode: "speak" for generating response, "prepare" for preparation
        preparation_notes: Notes from preparation phase (if any)
        meeting_type: Type of meeting (from MeetingType enum)
        custom_meeting_description: Custom description for "other" meeting type
        language: Language for the discussion (ja or en)
        is_facilitator: Whether this participant is the facilitator
    """
    # Ensure SDK is available
    _ensure_claude_sdk()

    logger.info(f"Starting participant agent: {participant_name} (mode={mode}, lang={language}, facilitator={is_facilitator})")

    system_prompt = build_system_prompt(
        name=participant_name,
        role=participant_role,
        context=context_text,
        topic=room_topic,
        mode=mode,
        meeting_type=meeting_type,
        custom_meeting_description=custom_meeting_description,
        language=language,
        is_facilitator=is_facilitator,
    )

    # Build the prompt based on mode
    if mode == "prepare":
        prompt = f"""## Discussion Topic
{room_topic}

## Current Discussion (for context)
{conversation_history if conversation_history else "(Discussion not started yet)"}

Please analyze the codebase and prepare notes for your upcoming contribution to this discussion.
"""
    else:
        prompt = f"""## Current Discussion
{conversation_history}

"""
        if preparation_notes:
            prompt += f"""## Your Preparation Notes
{preparation_notes}

"""
        prompt += f"""Please provide your response to continue the discussion. Remember to start with [{participant_name}]:"""

    # Check tool permission mode
    permission_mode = get_tool_permission_mode()
    if permission_mode == ToolPermissionMode.SYSTEM_DEFAULT:
        allowed_tools = None  # Allow all tools
        logger.info(f"Using system default mode - all tools allowed")
    else:
        allowed_tools = READ_ONLY_TOOLS
        logger.info(f"Using read-only mode - tools: {READ_ONLY_TOOLS}")

    try:
        async with ClaudeSDKClient(
            options=ClaudeAgentOptions(
                model="claude-sonnet-4-20250514",
                system_prompt=system_prompt,
                max_turns=10,  # Allow multiple tool uses within one response
                allowed_tools=allowed_tools,
                permission_mode="bypassPermissions",
                cwd=cwd,
            )
        ) as client:
            await client.query(prompt)

            full_response = ""
            async for msg in client.receive_response():
                msg_type = type(msg).__name__

                if msg_type == "AssistantMessage" and hasattr(msg, "content"):
                    for block in msg.content:
                        block_type = type(block).__name__

                        if block_type == "TextBlock" and hasattr(block, "text"):
                            text = block.text
                            full_response += text
                            emit_json({"type": "text", "content": text})

                        elif block_type == "ToolUseBlock" and hasattr(block, "name"):
                            tool_name = block.name
                            tool_input = getattr(block, "input", {})
                            emit_json({
                                "type": "tool_use",
                                "tool": tool_name,
                                "input": str(tool_input)[:200],  # Truncate for display
                            })

                elif msg_type == "UserMessage" and hasattr(msg, "content"):
                    # Tool results
                    for block in msg.content:
                        block_type = type(block).__name__
                        if block_type == "ToolResultBlock":
                            is_error = getattr(block, "is_error", False)
                            if is_error:
                                emit_json({"type": "tool_error", "error": "Tool execution failed"})

            # Emit completion
            emit_json({
                "type": "response_complete",
                "full_content": full_response,
                "mode": mode,
            })

    except Exception as e:
        logger.error(f"Error in participant agent: {e}")
        emit_json({
            "type": "error",
            "content": str(e),
        })
        sys.exit(1)


def main():
    parser = argparse.ArgumentParser(description="Participant agent for discussions")
    parser.add_argument("--participant-id", type=int, required=True, help="Participant database ID")
    parser.add_argument("--participant-name", required=True, help="Participant display name")
    parser.add_argument("--participant-role", default="", help="Participant role")
    parser.add_argument("--data-file", required=True, help="JSON file with context data")
    parser.add_argument("--cwd", default=None, help="Working directory for file operations")
    parser.add_argument("--mode", choices=["speak", "prepare"], default="speak", help="Agent mode")
    parser.add_argument("--meeting-type", default=None, help="Meeting type (from MeetingType enum)")
    parser.add_argument("--language", default="ja", help="Language for discussion (ja or en)")
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
    asyncio.run(run_participant_agent(
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
