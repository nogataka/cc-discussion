import { Hash, Plus, MessageSquare } from 'lucide-react'
import { useNavigate } from 'react-router-dom'
import { Button } from '../ui/button'

interface Room {
  id: number
  name: string
  status: string
  current_turn: number
  max_turns: number
}

interface ChannelSidebarProps {
  rooms: Room[]
  currentRoomId?: number
  onCreateRoom: () => void
}

function getStatusColor(status: string): string {
  switch (status) {
    case 'active':
      return 'bg-green-500'
    case 'paused':
      return 'bg-amber-500'
    case 'completed':
      return 'bg-muted-foreground'
    default:
      return 'bg-muted-foreground/50'
  }
}

export function ChannelSidebar({
  rooms,
  currentRoomId,
  onCreateRoom,
}: ChannelSidebarProps) {
  const navigate = useNavigate()

  return (
    <div className="w-60 bg-card border-r flex flex-col h-full">
      {/* Header */}
      <div className="h-14 px-4 flex items-center border-b">
        <div className="flex items-center gap-2">
          <MessageSquare className="h-5 w-5 text-primary" />
          <span className="font-bold text-lg">Discussions</span>
        </div>
      </div>

      {/* Rooms List */}
      <div className="flex-1 overflow-y-auto py-2">
        <div className="px-3 mb-2">
          <span className="text-xs font-semibold text-muted-foreground uppercase tracking-wider">
            Rooms
          </span>
        </div>

        <div className="space-y-0.5 px-2">
          {rooms.map((room) => (
            <button
              key={room.id}
              onClick={() => navigate(`/rooms/${room.id}`)}
              className={`w-full flex items-center gap-2 px-2 py-1.5 rounded-md text-sm transition-colors ${
                currentRoomId === room.id
                  ? 'bg-primary/10 text-primary font-medium'
                  : 'text-foreground hover:bg-muted'
              }`}
            >
              <Hash className="h-4 w-4 flex-shrink-0 text-muted-foreground" />
              <span className="truncate flex-1 text-left">{room.name}</span>
              <div
                className={`w-2 h-2 rounded-full flex-shrink-0 ${getStatusColor(room.status)}`}
                title={room.status}
              />
            </button>
          ))}

          {rooms.length === 0 && (
            <div className="px-2 py-4 text-sm text-muted-foreground text-center">
              No rooms yet
            </div>
          )}
        </div>
      </div>

      {/* Create Room Button */}
      <div className="p-3 border-t">
        <Button
          variant="outline"
          size="sm"
          className="w-full justify-start gap-2"
          onClick={onCreateRoom}
        >
          <Plus className="h-4 w-4" />
          Create Room
        </Button>
      </div>
    </div>
  )
}
