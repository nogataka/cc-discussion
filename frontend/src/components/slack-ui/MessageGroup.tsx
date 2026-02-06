import { ParticipantAvatar } from '../ParticipantAvatar'

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

interface MessageGroupProps {
  participant: Participant
  messages: Message[]
  isStreaming?: boolean
  streamingContent?: string
}

function formatTime(dateString: string): string {
  const date = new Date(dateString)
  return date.toLocaleTimeString('ja-JP', {
    hour: '2-digit',
    minute: '2-digit',
  })
}

/**
 * Remove the "[Name]: " prefix from message content since
 * the participant name is already shown in the message header.
 */
function stripNamePrefix(content: string): string {
  // Trim leading whitespace/newlines first, then remove the prefix
  // Match patterns like "[Claude A]: " or "[名前]: " at the start
  return content.trim().replace(/^\[.+?\]:\s*/, '')
}

export function MessageGroup({
  participant,
  messages,
  isStreaming,
  streamingContent,
}: MessageGroupProps) {
  const firstMessage = messages[0]
  const displayTime = firstMessage?.created_at
    ? formatTime(firstMessage.created_at)
    : formatTime(new Date().toISOString())

  return (
    <div className="flex gap-3 py-2 px-4 hover:bg-muted/30 group transition-colors">
      {/* Avatar */}
      <div className="w-10 flex-shrink-0 pt-0.5">
        <ParticipantAvatar
          name={participant.name}
          color={participant.color}
          size={40}
        />
      </div>

      <div className="flex-1 min-w-0">
        {/* Header - Name, Role, Time */}
        <div className="flex items-baseline gap-2 mb-1">
          <span className="font-bold text-foreground">
            {participant.name}
          </span>
          {participant.role && (
            <span className="text-xs text-muted-foreground bg-muted px-1.5 py-0.5 rounded">
              {participant.role}
            </span>
          )}
          <span className="text-xs text-muted-foreground">
            {displayTime}
          </span>
        </div>

        {/* Messages */}
        <div className="space-y-1">
          {messages.map((msg, idx) => (
            <div key={msg.id} className="text-sm text-foreground leading-relaxed">
              {idx > 0 && (
                <span className="text-xs text-muted-foreground mr-2 opacity-0 group-hover:opacity-100 transition-opacity">
                  {formatTime(msg.created_at)}
                </span>
              )}
              <span className="whitespace-pre-wrap">{highlightMentions(stripNamePrefix(msg.content))}</span>
            </div>
          ))}

          {/* Streaming content */}
          {isStreaming && streamingContent && (
            <div className="text-sm text-foreground leading-relaxed">
              <span className="whitespace-pre-wrap">{highlightMentions(stripNamePrefix(streamingContent))}</span>
              <span className="inline-block w-2 h-4 bg-primary ml-0.5 animate-pulse" />
            </div>
          )}
        </div>
      </div>
    </div>
  )
}
