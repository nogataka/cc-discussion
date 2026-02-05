import { useEffect, useRef, useState, useCallback } from 'react'

interface Message {
  id: number
  participant_id: number | null
  role: string
  content: string
  turn_number: number
  created_at: string
}

interface StreamingContent {
  participantId: number
  content: string
}

interface BackgroundActivity {
  participantId: number
  participantName: string
  activity: string
  timestamp: string
}

interface PreparationState {
  participantId: number
  participantName: string
  isComplete: boolean
  notesPreview?: string
}

interface RoomWebSocketState {
  messages: Message[]
  status: 'waiting' | 'active' | 'paused' | 'completed'
  currentTurn: number
  maxTurns: number
  isConnected: boolean
  streamingContent: StreamingContent | null
  // New parallel preparation state
  preparingParticipants: Map<number, PreparationState>
  backgroundActivities: BackgroundActivity[]
}

interface WebSocketMessage {
  type: string
  content?: string
}

export function useRoomWebSocket(roomId: number | null) {
  const [state, setState] = useState<RoomWebSocketState>({
    messages: [],
    status: 'waiting',
    currentTurn: 0,
    maxTurns: 20,
    isConnected: false,
    streamingContent: null,
    preparingParticipants: new Map(),
    backgroundActivities: [],
  })

  const wsRef = useRef<WebSocket | null>(null)
  const reconnectTimeoutRef = useRef<number | null>(null)
  const messageIdCounter = useRef(1000)

  const connect = useCallback(() => {
    if (!roomId) return

    const protocol = window.location.protocol === 'https:' ? 'wss:' : 'ws:'
    const wsUrl = `${protocol}//${window.location.host}/ws/rooms/${roomId}`

    const ws = new WebSocket(wsUrl)
    wsRef.current = ws

    ws.onopen = () => {
      console.log('WebSocket connected')
      setState(prev => ({ ...prev, isConnected: true }))
    }

    ws.onmessage = (event) => {
      try {
        const message = JSON.parse(event.data)

        switch (message.type) {
          case 'room_state':
            setState(prev => ({
              ...prev,
              status: message.status,
              currentTurn: message.current_turn,
              maxTurns: message.max_turns,
            }))
            break

          case 'discussion_start':
            setState(prev => ({
              ...prev,
              status: 'active',
            }))
            break

          case 'discussion_starting':
            // Discussion is being initialized
            console.log('Discussion starting...')
            break

          case 'turn_start':
            setState(prev => ({
              ...prev,
              streamingContent: {
                participantId: message.participant_id,
                content: '',
              },
            }))
            break

          case 'text':
            setState(prev => ({
              ...prev,
              streamingContent: prev.streamingContent
                ? {
                    ...prev.streamingContent,
                    content: prev.streamingContent.content + message.content,
                  }
                : null,
            }))
            break

          case 'tool_use':
            // Tool use during speaking - could show in UI
            console.log(`[Tool: ${message.tool}] ${message.input}`)
            break

          case 'turn_complete':
            setState(prev => {
              const newMessage: Message = {
                id: message.message_id || messageIdCounter.current++,
                participant_id: message.participant_id,
                role: 'participant',
                content: prev.streamingContent?.content || '',
                turn_number: message.turn_number,
                created_at: new Date().toISOString(),
              }

              return {
                ...prev,
                currentTurn: message.turn_number,
                streamingContent: null,
                messages: [...prev.messages, newMessage],
              }
            })
            break

          case 'moderator_message':
            setState(prev => {
              const newMessage: Message = {
                id: message.message_id || messageIdCounter.current++,
                participant_id: null,
                role: 'moderator',
                content: message.content,
                turn_number: message.turn_number,
                created_at: new Date().toISOString(),
              }
              return {
                ...prev,
                messages: [...prev.messages, newMessage],
              }
            })
            break

          // New parallel preparation events
          case 'preparation_start':
            setState(prev => {
              const newMap = new Map(prev.preparingParticipants)
              newMap.set(message.participant_id, {
                participantId: message.participant_id,
                participantName: message.participant_name,
                isComplete: false,
              })
              return {
                ...prev,
                preparingParticipants: newMap,
              }
            })
            break

          case 'preparation_complete':
            setState(prev => {
              const newMap = new Map(prev.preparingParticipants)
              const existing = newMap.get(message.participant_id)
              if (existing) {
                newMap.set(message.participant_id, {
                  ...existing,
                  isComplete: true,
                  notesPreview: message.notes_preview,
                })
              }
              return {
                ...prev,
                preparingParticipants: newMap,
              }
            })
            break

          case 'background_activity':
            setState(prev => {
              const newActivity: BackgroundActivity = {
                participantId: message.participant_id,
                participantName: message.participant_name,
                activity: message.activity,
                timestamp: new Date().toISOString(),
              }
              // Keep only last 10 activities
              const activities = [...prev.backgroundActivities, newActivity].slice(-10)
              return {
                ...prev,
                backgroundActivities: activities,
              }
            })
            break

          case 'discussion_paused':
            setState(prev => ({
              ...prev,
              status: 'paused',
            }))
            break

          case 'discussion_complete':
            setState(prev => ({
              ...prev,
              status: 'completed',
              currentTurn: message.total_turns,
              preparingParticipants: new Map(),
              backgroundActivities: [],
            }))
            break

          case 'error':
            console.error('WebSocket error:', message.content)
            break

          case 'info':
            console.log('WebSocket info:', message.content)
            break

          case 'ping':
            // Server ping - respond with pong
            if (wsRef.current?.readyState === WebSocket.OPEN) {
              wsRef.current.send(JSON.stringify({ type: 'pong' }))
            }
            break

          case 'pong':
            // Heartbeat response
            break

          default:
            console.log('Unknown message type:', message.type)
        }
      } catch (error) {
        console.error('Error parsing WebSocket message:', error)
      }
    }

    ws.onclose = () => {
      console.log('WebSocket disconnected')
      setState(prev => ({ ...prev, isConnected: false }))

      // Attempt to reconnect after 3 seconds
      reconnectTimeoutRef.current = window.setTimeout(connect, 3000)
    }

    ws.onerror = (error) => {
      console.error('WebSocket error:', error)
    }
  }, [roomId])

  // Send message to WebSocket
  const sendMessage = useCallback((message: WebSocketMessage) => {
    console.log('sendMessage called:', message, 'readyState:', wsRef.current?.readyState)
    if (wsRef.current?.readyState === WebSocket.OPEN) {
      console.log('Sending message:', message)
      wsRef.current.send(JSON.stringify(message))
    } else {
      console.warn('WebSocket not open, message not sent:', message)
    }
  }, [])

  useEffect(() => {
    if (!roomId) return

    connect()

    // Ping interval to keep connection alive
    const pingInterval = setInterval(() => {
      if (wsRef.current?.readyState === WebSocket.OPEN) {
        wsRef.current.send(JSON.stringify({ type: 'ping' }))
      }
    }, 30000)

    return () => {
      clearInterval(pingInterval)
      if (reconnectTimeoutRef.current) {
        clearTimeout(reconnectTimeoutRef.current)
      }
      wsRef.current?.close()
    }
  }, [roomId, connect])

  return {
    ...state,
    sendMessage,
  }
}
