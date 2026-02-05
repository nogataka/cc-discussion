import { useState } from 'react'
import { useNavigate } from 'react-router-dom'
import { useQuery, useMutation, useQueryClient } from '@tanstack/react-query'
import { Plus, Users, Clock, MessageSquare, Trash2, ChevronRight } from 'lucide-react'
import { Button } from '@/components/ui/button'
import { Card, CardContent, CardHeader, CardTitle } from '@/components/ui/card'
import { CreateRoomModal } from '@/components/CreateRoomModal'
import { api } from '@/lib/api'

export function HomePage() {
  const navigate = useNavigate()
  const queryClient = useQueryClient()
  const [showCreateModal, setShowCreateModal] = useState(false)

  // Fetch rooms
  const { data: rooms, isLoading } = useQuery({
    queryKey: ['rooms'],
    queryFn: api.getRooms,
  })

  // Delete room mutation
  const deleteMutation = useMutation({
    mutationFn: api.deleteRoom,
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ['rooms'] })
    },
  })

  const handleRoomCreated = (roomId: number) => {
    setShowCreateModal(false)
    navigate(`/room/${roomId}`)
  }

  const getStatusColor = (status: string) => {
    switch (status) {
      case 'waiting':
        return 'bg-yellow-500'
      case 'active':
        return 'bg-green-500'
      case 'paused':
        return 'bg-orange-500'
      case 'completed':
        return 'bg-blue-500'
      default:
        return 'bg-gray-500'
    }
  }

  return (
    <main className="max-w-7xl mx-auto px-4 py-8">
      {/* Hero Section */}
      <div className="text-center mb-12">
        <h2 className="text-4xl font-bold mb-4">
          Multi-Claude Discussions
        </h2>
        <p className="text-xl text-muted-foreground max-w-2xl mx-auto mb-8">
          Create discussion rooms where multiple Claude instances with different contexts
          can collaborate to solve problems together.
        </p>
        <Button
          size="lg"
          onClick={() => setShowCreateModal(true)}
          className="gap-2"
        >
          <Plus className="w-5 h-5" />
          Create New Room
        </Button>
      </div>

      {/* Rooms List */}
      <div className="space-y-6">
        <h3 className="text-2xl font-bold">Discussion Rooms</h3>

        {isLoading ? (
          <div className="text-center py-12 text-muted-foreground">
            Loading rooms...
          </div>
        ) : !rooms || rooms.length === 0 ? (
          <Card className="text-center py-12">
            <CardContent>
              <MessageSquare className="w-12 h-12 mx-auto mb-4 text-muted-foreground" />
              <p className="text-lg text-muted-foreground mb-4">
                No discussion rooms yet
              </p>
              <Button onClick={() => setShowCreateModal(true)}>
                Create Your First Room
              </Button>
            </CardContent>
          </Card>
        ) : (
          <div className="grid gap-4 md:grid-cols-2 lg:grid-cols-3">
            {rooms.map((room) => (
              <Card
                key={room.id}
                className="hover:shadow-lg transition-shadow cursor-pointer group"
                onClick={() => navigate(`/room/${room.id}`)}
              >
                <CardHeader className="pb-2">
                  <div className="flex items-start justify-between">
                    <CardTitle className="text-lg">{room.name}</CardTitle>
                    <div className="flex items-center gap-2">
                      <span
                        className={`w-2 h-2 rounded-full ${getStatusColor(room.status)}`}
                        title={room.status}
                      />
                      <span className="text-xs text-muted-foreground capitalize">
                        {room.status}
                      </span>
                    </div>
                  </div>
                </CardHeader>
                <CardContent>
                  {room.topic && (
                    <p className="text-sm text-muted-foreground mb-4 line-clamp-2">
                      {room.topic}
                    </p>
                  )}

                  <div className="flex items-center justify-between text-sm text-muted-foreground">
                    <div className="flex items-center gap-4">
                      <span className="flex items-center gap-1">
                        <Users className="w-4 h-4" />
                        {room.participant_count}
                      </span>
                      <span className="flex items-center gap-1">
                        <MessageSquare className="w-4 h-4" />
                        {room.current_turn}/{room.max_turns}
                      </span>
                    </div>

                    <div className="flex items-center gap-2">
                      <Button
                        variant="ghost"
                        size="sm"
                        onClick={(e) => {
                          e.stopPropagation()
                          if (confirm('Delete this room?')) {
                            deleteMutation.mutate(room.id)
                          }
                        }}
                        className="opacity-0 group-hover:opacity-100 transition-opacity"
                      >
                        <Trash2 className="w-4 h-4 text-destructive" />
                      </Button>
                      <ChevronRight className="w-4 h-4" />
                    </div>
                  </div>

                  <div className="mt-2 text-xs text-muted-foreground flex items-center gap-1">
                    <Clock className="w-3 h-3" />
                    {new Date(room.created_at).toLocaleDateString()}
                  </div>
                </CardContent>
              </Card>
            ))}
          </div>
        )}
      </div>

      {/* Create Room Modal */}
      <CreateRoomModal
        isOpen={showCreateModal}
        onClose={() => setShowCreateModal(false)}
        onRoomCreated={handleRoomCreated}
      />
    </main>
  )
}
