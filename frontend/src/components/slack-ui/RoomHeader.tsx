import { useState, useRef, useEffect } from 'react'
import { Hash, Users, Play, Pause, Square, Wifi, WifiOff, Trash2, Pencil, Check, X } from 'lucide-react'
import { Button } from '../ui/button'
import { Badge } from '../ui/badge'
import { ParticipantAvatar } from '../ParticipantAvatar'
import { Input } from '../ui/input'

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
  onDelete?: () => void
  onRename?: (newName: string) => void
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
  onDelete,
  onRename,
}: RoomHeaderProps) {
  const [isEditing, setIsEditing] = useState(false)
  const [editValue, setEditValue] = useState(name)
  const inputRef = useRef<HTMLInputElement>(null)

  // Focus input when editing starts
  useEffect(() => {
    if (isEditing && inputRef.current) {
      inputRef.current.focus()
      inputRef.current.select()
    }
  }, [isEditing])

  // Update editValue when name prop changes
  useEffect(() => {
    setEditValue(name)
  }, [name])

  const handleStartEdit = () => {
    if (status !== 'active' && onRename) {
      setIsEditing(true)
      setEditValue(name)
    }
  }

  const handleSave = () => {
    const trimmedValue = editValue.trim()
    if (trimmedValue && trimmedValue !== name && onRename) {
      onRename(trimmedValue)
    }
    setIsEditing(false)
  }

  const handleCancel = () => {
    setEditValue(name)
    setIsEditing(false)
  }

  const handleKeyDown = (e: React.KeyboardEvent) => {
    if (e.key === 'Enter') {
      handleSave()
    } else if (e.key === 'Escape') {
      handleCancel()
    }
  }

  return (
    <div className="h-14 px-4 flex items-center justify-between border-b bg-card">
      {/* Left: Room info */}
      <div className="flex items-center gap-3 min-w-0">
        <div className="flex items-center gap-2">
          <Hash className="h-5 w-5 text-muted-foreground" />
          {isEditing ? (
            <div className="flex items-center gap-1">
              <Input
                ref={inputRef}
                value={editValue}
                onChange={(e) => setEditValue(e.target.value)}
                onKeyDown={handleKeyDown}
                onBlur={handleSave}
                className="h-7 w-48 text-lg font-bold"
              />
              <Button
                size="sm"
                variant="ghost"
                onClick={handleSave}
                className="h-7 w-7 p-0 text-green-600 hover:text-green-700 hover:bg-green-50"
              >
                <Check className="h-4 w-4" />
              </Button>
              <Button
                size="sm"
                variant="ghost"
                onClick={handleCancel}
                className="h-7 w-7 p-0 text-red-600 hover:text-red-700 hover:bg-red-50"
              >
                <X className="h-4 w-4" />
              </Button>
            </div>
          ) : (
            <div
              className={`flex items-center gap-1 group ${
                status !== 'active' && onRename ? 'cursor-pointer hover:bg-muted/50 rounded px-1 -mx-1' : ''
              }`}
              onClick={handleStartEdit}
              title={status !== 'active' && onRename ? 'クリックして名前を変更' : undefined}
            >
              <h1 className="font-bold text-lg truncate">{name}</h1>
              {status !== 'active' && onRename && (
                <Pencil className="h-3 w-3 text-muted-foreground opacity-0 group-hover:opacity-100 transition-opacity" />
              )}
            </div>
          )}
        </div>

        {topic && !isEditing && (
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
          {(status === 'waiting' || status === 'paused' || status === 'completed') && (
            <Button size="sm" onClick={onStart} className="gap-1">
              <Play className="h-4 w-4" />
              {status === 'waiting' ? 'Start' : 'Resume'}
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

          {/* Delete button - only show when not active */}
          {onDelete && status !== 'active' && (
            <Button
              size="sm"
              variant="ghost"
              onClick={onDelete}
              className="text-muted-foreground hover:text-destructive hover:bg-destructive/10"
              title="ルームを削除"
            >
              <Trash2 className="h-4 w-4" />
            </Button>
          )}
        </div>
      </div>
    </div>
  )
}
