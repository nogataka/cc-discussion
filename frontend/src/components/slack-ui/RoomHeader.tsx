import { Hash, Users, Play, Pause, Square, Wifi, WifiOff } from 'lucide-react'
import { Button } from '../ui/button'
import { Badge } from '../ui/badge'
import { ParticipantAvatar } from '../ParticipantAvatar'

interface Participant {
  id: number
  name: string
  role?: string
  color: string
  is_speaking?: boolean
}

interface RoomHeaderProps {
  name: string
  topic?: string
  status: 'waiting' | 'active' | 'paused' | 'completed'
  currentTurn: number
  maxTurns: number
  participants: Participant[]
  isConnected: boolean
  onStart: () => void
  onPause: () => void
  onStop: () => void
}

function getStatusBadge(status: string) {
  switch (status) {
    case 'active':
      return <Badge variant="default" className="bg-green-500">Active</Badge>
    case 'paused':
      return <Badge variant="secondary" className="bg-amber-500 text-white">Paused</Badge>
    case 'completed':
      return <Badge variant="secondary">Completed</Badge>
    default:
      return <Badge variant="outline">Waiting</Badge>
  }
}

export function RoomHeader({
  name,
  topic,
  status,
  currentTurn,
  maxTurns,
  participants,
  isConnected,
  onStart,
  onPause,
  onStop,
}: RoomHeaderProps) {
  return (
    <div className="h-14 px-4 flex items-center justify-between border-b bg-card">
      {/* Left: Room info */}
      <div className="flex items-center gap-3 min-w-0">
        <div className="flex items-center gap-2">
          <Hash className="h-5 w-5 text-muted-foreground" />
          <h1 className="font-bold text-lg truncate">{name}</h1>
        </div>

        {topic && (
          <span className="text-sm text-muted-foreground truncate max-w-[300px] hidden md:inline">
            {topic}
          </span>
        )}

        {getStatusBadge(status)}

        <span className="text-sm text-muted-foreground">
          Turn {currentTurn}/{maxTurns}
        </span>
      </div>

      {/* Right: Participants and controls */}
      <div className="flex items-center gap-4">
        {/* Participant avatars */}
        <div className="flex items-center gap-1">
          <Users className="h-4 w-4 text-muted-foreground mr-1" />
          <div className="flex -space-x-2">
            {participants.slice(0, 5).map((p) => (
              <div
                key={p.id}
                className={`rounded-full border-2 border-background ${
                  p.is_speaking ? 'ring-2 ring-primary ring-offset-1' : ''
                }`}
                title={p.name}
              >
                <ParticipantAvatar name={p.name} color={p.color} size={28} />
              </div>
            ))}
            {participants.length > 5 && (
              <div className="w-7 h-7 rounded-full bg-muted flex items-center justify-center text-xs font-medium border-2 border-background">
                +{participants.length - 5}
              </div>
            )}
          </div>
        </div>

        {/* Connection status */}
        <div className="flex items-center gap-1">
          {isConnected ? (
            <Wifi className="h-4 w-4 text-green-500" />
          ) : (
            <WifiOff className="h-4 w-4 text-red-500" />
          )}
        </div>

        {/* Control buttons */}
        <div className="flex items-center gap-2">
          {(status === 'waiting' || status === 'paused') && (
            <Button size="sm" onClick={onStart} className="gap-1">
              <Play className="h-4 w-4" />
              {status === 'paused' ? 'Resume' : 'Start'}
            </Button>
          )}

          {status === 'active' && (
            <>
              <Button
                size="sm"
                variant="outline"
                onClick={() => {
                  console.log('Pause button clicked!')
                  onPause()
                }}
                className="gap-1"
              >
                <Pause className="h-4 w-4" />
                Pause
              </Button>
              <Button
                size="sm"
                variant="destructive"
                onClick={() => {
                  console.log('Stop button clicked!')
                  onStop()
                }}
                className="gap-1"
              >
                <Square className="h-4 w-4" />
                Stop
              </Button>
            </>
          )}
        </div>
      </div>
    </div>
  )
}
