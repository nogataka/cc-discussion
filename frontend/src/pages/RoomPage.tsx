import { useMemo, useState } from 'react'
import { useParams, useNavigate } from 'react-router-dom'
import { useQuery, useMutation, useQueryClient } from '@tanstack/react-query'
import { Loader2, Hash, Plus, Trash2, Users, ChevronDown } from 'lucide-react'
import { Button } from '@/components/ui/button'
import { useRoomWebSocket } from '@/hooks/useRoomWebSocket'
import { api } from '@/lib/api'
import {
  RoomHeader,
  MessageList,
  MessageInput,
  StatusIndicator,
} from '@/components/slack-ui'
import { ParticipantAvatar } from '@/components/ParticipantAvatar'
import { Badge } from '@/components/ui/badge'
import { CreateRoomModal } from '@/components/CreateRoomModal'

interface Participant {
  id: number
  name: string
  role: string | null
  color: string
  is_speaking: boolean
  message_count: number
  has_context: boolean
  project_name: string | null
  agent_type: string
}

interface Message {
  id: number
  participant_id: number | null
  role: string
  content: string
  turn_number: number
  created_at: string
}

export function RoomPage() {
  const { roomId } = useParams<{ roomId: string }>()
  const navigate = useNavigate()
  const queryClient = useQueryClient()
  const [showCreateModal, setShowCreateModal] = useState(false)

  const id = roomId ? parseInt(roomId) : null

  // Fetch all rooms for left sidebar
  const { data: rooms } = useQuery({
    queryKey: ['rooms'],
    queryFn: api.getRooms,
  })

  // Fetch current room details
  const { data: roomData, isLoading } = useQuery({
    queryKey: ['room', id],
    queryFn: () => api.getRoom(id!),
    enabled: !!id,
  })

  // Delete room mutation
  const deleteMutation = useMutation({
    mutationFn: api.deleteRoom,
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ['rooms'] })
      if (rooms && rooms.length > 1) {
        const nextRoom = rooms.find((r) => r.id !== id)
        if (nextRoom) navigate(`/room/${nextRoom.id}`)
      }
    },
  })

  // WebSocket connection
  const wsState = useRoomWebSocket(id)

  // Merge room data with WebSocket updates
  const rawParticipants: Participant[] = roomData?.participants || []
  const messages: Message[] = wsState.messages.length > 0
    ? wsState.messages
    : (roomData?.messages || [])

  // Calculate message counts from actual messages
  const messageCounts = useMemo(() => {
    const counts = new Map<number, number>()
    for (const msg of messages) {
      if (msg.participant_id !== null) {
        counts.set(msg.participant_id, (counts.get(msg.participant_id) || 0) + 1)
      }
    }
    return counts
  }, [messages])

  // Enrich participants with calculated message counts
  const participants = useMemo(() => {
    return rawParticipants.map((p) => ({
      ...p,
      message_count: messageCounts.get(p.id) || 0,
    }))
  }, [rawParticipants, messageCounts])

  const handleSendModeratorMessage = (content: string) => {
    wsState.sendMessage({ type: 'moderate', content })
  }

  const handleStart = () => wsState.sendMessage({ type: 'start' })
  const handlePause = () => wsState.sendMessage({ type: 'pause' })
  const handleStop = () => wsState.sendMessage({ type: 'stop' })

  const handleRoomCreated = (newRoomId: number) => {
    setShowCreateModal(false)
    queryClient.invalidateQueries({ queryKey: ['rooms'] })
    navigate(`/room/${newRoomId}`)
  }

  const status = wsState.status || roomData?.status || 'waiting'

  const headerParticipants = participants.map((p) => ({
    id: p.id,
    name: p.name,
    role: p.role || undefined,
    color: p.color,
    is_speaking: p.is_speaking || wsState.streamingContent?.participantId === p.id,
  }))

  const messageListParticipants = participants.map((p) => ({
    id: p.id,
    name: p.name,
    role: p.role || undefined,
    color: p.color,
  }))

  const speakingParticipantId = wsState.streamingContent?.participantId

  const getStatusColor = (roomStatus: string) => {
    switch (roomStatus) {
      case 'active': return 'bg-green-500'
      case 'paused': return 'bg-amber-500'
      case 'completed': return 'bg-blue-500'
      default: return 'bg-gray-400'
    }
  }

  return (
    <div className="h-[calc(100vh-73px)] flex overflow-hidden">
      {/* Left Sidebar - Rooms List */}
      <aside className="w-56 bg-slate-800 text-slate-200 flex flex-col flex-shrink-0">
        <div className="h-12 px-4 flex items-center justify-between border-b border-slate-700">
          <span className="font-bold text-white">Rooms</span>
        </div>

        <div className="p-2">
          <Button
            variant="ghost"
            size="sm"
            onClick={() => setShowCreateModal(true)}
            className="w-full justify-start gap-2 text-slate-300 hover:text-white hover:bg-slate-700"
          >
            <Plus className="w-4 h-4" />
            New Room
          </Button>
        </div>

        <div className="flex-1 overflow-y-auto px-2">
          <div className="text-xs font-semibold text-slate-400 px-2 py-2 flex items-center gap-1">
            <ChevronDown className="w-3 h-3" />
            Channels
          </div>
          <div className="space-y-0.5">
            {rooms?.map((room) => (
              <div
                key={room.id}
                onClick={() => navigate(`/room/${room.id}`)}
                className={`group flex items-center gap-2 px-2 py-1.5 rounded cursor-pointer ${
                  room.id === id
                    ? 'bg-blue-600 text-white'
                    : 'text-slate-300 hover:bg-slate-700'
                }`}
              >
                <Hash className="w-4 h-4 flex-shrink-0 opacity-70" />
                <span className="flex-1 truncate text-sm">{room.name}</span>
                <span className={`w-2 h-2 rounded-full flex-shrink-0 ${getStatusColor(room.status)}`} />
                {room.id === id && (
                  <button
                    onClick={(e) => {
                      e.stopPropagation()
                      if (confirm('Delete this room?')) {
                        deleteMutation.mutate(room.id)
                      }
                    }}
                    className="opacity-0 group-hover:opacity-100 p-0.5 hover:bg-slate-500 rounded"
                  >
                    <Trash2 className="w-3 h-3" />
                  </button>
                )}
              </div>
            ))}
          </div>
        </div>
      </aside>

      {/* Main Content */}
      <main className="flex-1 flex flex-col min-w-0 bg-white">
        {isLoading ? (
          <div className="flex-1 flex items-center justify-center">
            <Loader2 className="w-8 h-8 animate-spin text-primary" />
          </div>
        ) : !roomData ? (
          <div className="flex-1 flex items-center justify-center text-muted-foreground">
            <div className="text-center">
              <Hash className="w-12 h-12 mx-auto mb-4 opacity-50" />
              <p className="text-lg">Select a room to start</p>
            </div>
          </div>
        ) : (
          <>
            <RoomHeader
              name={roomData.name}
              topic={roomData.topic ?? undefined}
              status={status as 'waiting' | 'active' | 'paused' | 'completed'}
              currentTurn={wsState.currentTurn || roomData.current_turn}
              maxTurns={roomData.max_turns}
              participants={headerParticipants}
              isConnected={wsState.isConnected}
              onStart={handleStart}
              onPause={handlePause}
              onStop={handleStop}
            />
            <MessageList
              messages={messages}
              participants={messageListParticipants}
              streamingContent={wsState.streamingContent}
            />
            <StatusIndicator
              preparingParticipants={wsState.preparingParticipants}
              backgroundActivities={wsState.backgroundActivities}
              speakingParticipantId={speakingParticipantId}
            />
            <MessageInput
              onSend={handleSendModeratorMessage}
              placeholder="Send a moderator message..."
              disabled={!wsState.isConnected}
            />
          </>
        )}
      </main>

      {/* Right Sidebar - Participants */}
      {roomData && (
        <aside className="w-72 border-l bg-white flex flex-col flex-shrink-0">
          <div className="h-12 px-4 flex items-center border-b">
            <div className="flex items-center gap-2">
              <Users className="w-4 h-4 text-muted-foreground" />
              <span className="font-semibold text-sm">Participants</span>
              <Badge variant="secondary" className="text-xs">{participants.length}</Badge>
            </div>
          </div>

          <div className="flex-1 overflow-y-auto p-3">
            <div className="space-y-2">
              {participants.map((participant) => {
                const isActive =
                  participant.is_speaking ||
                  wsState.streamingContent?.participantId === participant.id
                const isPreparing = wsState.preparingParticipants.has(participant.id)

                return (
                  <div
                    key={participant.id}
                    className={`p-3 rounded-lg transition-all ${
                      isActive
                        ? 'bg-blue-50 ring-1 ring-blue-200'
                        : isPreparing
                        ? 'bg-amber-50 ring-1 ring-amber-200'
                        : 'hover:bg-gray-50'
                    }`}
                  >
                    <div className="flex items-center gap-3">
                      <div className="relative">
                        <ParticipantAvatar
                          name={participant.name}
                          color={participant.color}
                          size={36}
                          isActive={isActive}
                        />
                        {isPreparing && (
                          <div className="absolute -bottom-0.5 -right-0.5 w-3 h-3 rounded-full bg-amber-500 animate-pulse" />
                        )}
                        {isActive && (
                          <div className="absolute -bottom-0.5 -right-0.5 w-3 h-3 rounded-full bg-green-500 animate-pulse" />
                        )}
                      </div>
                      <div className="flex-1 min-w-0">
                        <div className="flex items-center gap-2">
                          <span className="font-medium truncate text-sm" style={{ color: participant.color }}>
                            {participant.name}
                          </span>
                          {isActive && (
                            <Loader2 className="w-3 h-3 animate-spin flex-shrink-0" style={{ color: participant.color }} />
                          )}
                        </div>
                        {participant.role && (
                          <p className="text-xs text-muted-foreground truncate">{participant.role}</p>
                        )}
                        {participant.project_name && (
                          <p className="text-xs text-blue-500 truncate">📁 {participant.project_name}</p>
                        )}
                      </div>
                    </div>

                    <div className="flex items-center justify-between mt-2 pt-2 border-t border-gray-100 text-xs text-muted-foreground">
                      <span>{participant.message_count} msgs</span>
                      <Badge
                        variant="outline"
                        className={`text-[10px] py-0 ${
                          participant.agent_type === 'codex'
                            ? 'border-green-500 text-green-600'
                            : 'border-purple-500 text-purple-600'
                        }`}
                      >
                        {participant.agent_type === 'codex' ? 'Codex' : 'Claude'}
                      </Badge>
                    </div>
                  </div>
                )
              })}
            </div>
          </div>
        </aside>
      )}

      <CreateRoomModal
        isOpen={showCreateModal}
        onClose={() => setShowCreateModal(false)}
        onRoomCreated={handleRoomCreated}
      />
    </div>
  )
}
