import { ParticipantAvatar } from '../ParticipantAvatar'

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
              <span className="whitespace-pre-wrap">{stripNamePrefix(msg.content)}</span>
            </div>
          ))}

          {/* Streaming content */}
          {isStreaming && streamingContent && (
            <div className="text-sm text-foreground leading-relaxed">
              <span className="whitespace-pre-wrap">{stripNamePrefix(streamingContent)}</span>
              <span className="inline-block w-2 h-4 bg-primary ml-0.5 animate-pulse" />
            </div>
          )}
        </div>
      </div>
    </div>
  )
}
