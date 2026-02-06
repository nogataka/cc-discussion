import { useEffect, useRef } from 'react'
import { MessageGroup } from './MessageGroup'
import { MessageSquare, User } from 'lucide-react'

/**
 * Parse and highlight @mentions in message content.
 * Returns an array of React elements with mentions styled in blue.
 */
function highlightMentions(content: string): React.ReactNode {
  // Match @name patterns (including @ALL, @END, @モデレーター, @moderator, @[name with spaces], @name_with_underscore, @Name X)
  // Added support for space + single letter suffix (e.g., @エージェント B)
  const mentionPattern = /@(?:\[[^\]]+\]|ALL\b|END\b|モデレーター\b|moderator\b|[\w\u3040-\u309F\u30A0-\u30FF\u4E00-\u9FFF][\w\u3040-\u309F\u30A0-\u30FF\u4E00-\u9FFF\-_]*(?: [A-Za-z0-9])?)/gi

  const parts: React.ReactNode[] = []
  let lastIndex = 0
  let match: RegExpExecArray | null

  while ((match = mentionPattern.exec(content)) !== null) {
    // Add text before the mention
    if (match.index > lastIndex) {
      parts.push(content.slice(lastIndex, match.index))
    }

    // Add the mention with blue styling
    parts.push(
      <span key={match.index} className="text-blue-600 font-medium">
        {match[0]}
      </span>
    )

    lastIndex = match.index + match[0].length
  }

  // Add remaining text
  if (lastIndex < content.length) {
    parts.push(content.slice(lastIndex))
  }

  return parts.length > 0 ? parts : content
}

interface Message {
  id: number
  participant_id: number | null
  role: string
  content: string
  turn_number: number
  created_at: string
}

interface Participant {
  id: number
  name: string
  role?: string
  color: string
}

interface StreamingContent {
  participantId: number
  content: string
}

interface MessageListProps {
  messages: Message[]
  participants: Participant[]
  streamingContent: StreamingContent | null
}

interface MessageGroupData {
  participant: Participant
  messages: Message[]
}

// Group consecutive messages from the same participant
function groupMessages(
  messages: Message[],
  participants: Participant[]
): MessageGroupData[] {
  const groups: MessageGroupData[] = []

  for (const msg of messages) {
    if (msg.role !== 'participant' || msg.participant_id === null) {
      // Moderator or system messages are not grouped
      continue
    }

    const participant = participants.find((p) => p.id === msg.participant_id)
    if (!participant) continue

    const lastGroup = groups[groups.length - 1]

    if (lastGroup && lastGroup.participant.id === msg.participant_id) {
      // Add to existing group
      lastGroup.messages.push(msg)
    } else {
      // Start new group
      groups.push({
        participant,
        messages: [msg],
      })
    }
  }

  return groups
}

export function MessageList({
  messages,
  participants,
  streamingContent,
}: MessageListProps) {
  const scrollRef = useRef<HTMLDivElement>(null)
  const bottomRef = useRef<HTMLDivElement>(null)

  // Auto-scroll to bottom when new messages arrive
  useEffect(() => {
    bottomRef.current?.scrollIntoView({ behavior: 'smooth' })
  }, [messages, streamingContent])

  const messageGroups = groupMessages(messages, participants)

  // Find streaming participant
  const streamingParticipant = streamingContent
    ? participants.find((p) => p.id === streamingContent.participantId)
    : null

  // Check if streaming is for a new group
  const lastGroup = messageGroups[messageGroups.length - 1]
  const isStreamingNewGroup =
    streamingParticipant &&
    (!lastGroup || lastGroup.participant.id !== streamingParticipant.id)

  if (messages.length === 0 && !streamingContent) {
    return (
      <div className="flex-1 flex items-center justify-center text-muted-foreground">
        <div className="text-center">
          <MessageSquare className="h-12 w-12 mx-auto mb-4 opacity-50" />
          <p className="text-lg font-medium">No messages yet</p>
          <p className="text-sm">Start the discussion to begin</p>
        </div>
      </div>
    )
  }

  return (
    <div ref={scrollRef} className="flex-1 overflow-y-auto">
      <div className="py-4">
        {/* Render message groups with moderator messages interspersed */}
        {messages.map((msg, idx) => {
          if (msg.role === 'moderator') {
            // Render moderator message like participant messages but with amber background
            const msgTime = new Date(msg.created_at).toLocaleTimeString('ja-JP', {
              hour: '2-digit',
              minute: '2-digit',
            })
            return (
              <div
                key={`mod-${msg.id}`}
                className="flex gap-3 py-2 px-4 bg-amber-50 hover:bg-amber-100/70 transition-colors"
              >
                {/* Avatar */}
                <div className="w-10 flex-shrink-0 pt-0.5">
                  <div className="w-10 h-10 rounded-full bg-amber-100 border-2 border-amber-300 flex items-center justify-center">
                    <User className="w-5 h-5 text-amber-600" />
                  </div>
                </div>

                <div className="flex-1 min-w-0">
                  {/* Header - Name, Role, Time */}
                  <div className="flex items-baseline gap-2 mb-1">
                    <span className="font-bold text-amber-700">
                      モデレーター
                    </span>
                    <span className="text-xs text-muted-foreground bg-amber-200/50 px-1.5 py-0.5 rounded">
                      Human
                    </span>
                    <span className="text-xs text-muted-foreground">
                      {msgTime}
                    </span>
                  </div>

                  {/* Message content */}
                  <div className="text-sm text-foreground leading-relaxed">
                    <span className="whitespace-pre-wrap">{highlightMentions(msg.content)}</span>
                  </div>
                </div>
              </div>
            )
          }

          if (msg.role === 'system') {
            return (
              <div
                key={`sys-${msg.id}`}
                className="flex justify-center py-2 px-4"
              >
                <div className="bg-muted text-muted-foreground px-4 py-2 rounded-full text-sm">
                  {msg.content}
                </div>
              </div>
            )
          }

          // For participant messages, check if this is the first in a group
          const prevMsg = messages[idx - 1]
          const isFirstInGroup =
            !prevMsg ||
            prevMsg.role !== 'participant' ||
            prevMsg.participant_id !== msg.participant_id

          if (!isFirstInGroup) {
            return null // Will be rendered as part of the group
          }

          // Collect all consecutive messages from this participant
          const groupMessages: Message[] = [msg]
          for (let i = idx + 1; i < messages.length; i++) {
            const nextMsg = messages[i]
            if (
              nextMsg.role === 'participant' &&
              nextMsg.participant_id === msg.participant_id
            ) {
              groupMessages.push(nextMsg)
            } else {
              break
            }
          }

          const participant = participants.find((p) => p.id === msg.participant_id)
          if (!participant) return null

          // Check if this group is currently streaming
          const isStreamingGroup =
            streamingContent?.participantId === participant.id

          return (
            <MessageGroup
              key={`group-${msg.id}`}
              participant={participant}
              messages={groupMessages}
              isStreaming={isStreamingGroup && !isStreamingNewGroup}
              streamingContent={
                isStreamingGroup && !isStreamingNewGroup
                  ? streamingContent.content
                  : undefined
              }
            />
          )
        })}

        {/* Render streaming content as new group if needed */}
        {isStreamingNewGroup && streamingParticipant && streamingContent && (
          <MessageGroup
            participant={streamingParticipant}
            messages={[]}
            isStreaming={true}
            streamingContent={streamingContent.content}
          />
        )}

        <div ref={bottomRef} />
      </div>
    </div>
  )
}
