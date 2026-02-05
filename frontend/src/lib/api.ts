/**
 * API Client for Claude Discussion Room
 */

const API_BASE = '/api'

// ============================================
// History API Types (ClaudeCode projects/sessions)
// ============================================

export interface Project {
  id: string
  name: string
  path: string
  last_modified_at: string
}

export interface Session {
  id: string
  jsonl_file_path: string
  last_modified_at: string
  message_count: number
  first_user_message: string | null
}

export interface ToolCall {
  id: string | null
  name: string | null
  input: Record<string, unknown>
}

export interface ToolResult {
  tool_use_id: string | null
  content: unknown
  is_error: boolean
}

export interface Conversation {
  type: 'user' | 'assistant' | 'system' | 'summary'
  uuid: string
  timestamp: string
  content: string | { text: string; raw: unknown[] }
  is_sidechain: boolean
  parent_uuid: string | null
  tool_calls: ToolCall[]
  tool_results: ToolResult[]
}

export interface SessionDetail {
  id: string
  jsonl_file_path: string
  conversations: Conversation[]
}

// ============================================
// Codex History Types
// ============================================

export interface CodexProject {
  id: string
  name: string
  path: string
  last_modified_at: string
  session_count: number
}

export interface CodexSession {
  id: string
  session_uuid: string
  jsonl_file_path: string
  first_user_message: string | null
  message_count: number
  last_modified_at: string
}

// ============================================
// Room API Types (Discussion rooms)
// ============================================

export type MeetingType =
  | 'progress_check'
  | 'spec_alignment'
  | 'technical_review'
  | 'issue_resolution'
  | 'review'
  | 'planning'
  | 'release_ops'
  | 'retrospective'
  | 'other'

export const MEETING_TYPES = [
  { value: 'progress_check', label: '進捗・状況確認' },
  { value: 'spec_alignment', label: '要件・仕様の認識合わせ' },
  { value: 'technical_review', label: '技術検討・設計判断' },
  { value: 'issue_resolution', label: '課題・不具合対応' },
  { value: 'review', label: 'レビュー' },
  { value: 'planning', label: '計画・タスク整理' },
  { value: 'release_ops', label: 'リリース・運用判断' },
  { value: 'retrospective', label: '改善・振り返り' },
  { value: 'other', label: 'その他' },
] as const

export type AgentType = 'claude' | 'codex'

export interface Room {
  id: number
  name: string
  topic: string | null
  status: 'waiting' | 'active' | 'paused' | 'completed'
  current_turn: number
  max_turns: number
  meeting_type: MeetingType
  custom_meeting_description: string | null
  language: string
  participant_count: number
  created_at: string
}

export interface Participant {
  id: number
  name: string
  role: string | null
  color: string
  has_context: boolean
  is_speaking: boolean
  message_count: number
  is_facilitator: boolean
  agent_type: AgentType
  project_name: string | null
}

export interface RoomMessage {
  id: number
  participant_id: number | null
  role: 'system' | 'participant' | 'moderator'
  content: string
  turn_number: number
  created_at: string
}

export interface RoomDetail extends Omit<Room, 'participant_count'> {
  participants: Participant[]
  messages: RoomMessage[]
}

export interface CreateRoomRequest {
  name: string
  topic?: string
  max_turns?: number
  meeting_type?: MeetingType
  custom_meeting_description?: string
  language?: string
  participants: Array<{
    name: string
    role?: string
    color?: string
    context_project_dir?: string
    context_session_id?: string
    is_facilitator?: boolean
    agent_type?: AgentType
  }>
}

// ============================================
// API Client
// ============================================

export class ApiError extends Error {
  constructor(
    message: string,
    public status: number,
    public endpoint: string
  ) {
    super(message)
    this.name = 'ApiError'
  }
}

async function fetchApi<T>(
  endpoint: string,
  options?: RequestInit
): Promise<T> {
  const url = `${API_BASE}${endpoint}`

  try {
    const response = await fetch(url, {
      headers: {
        'Content-Type': 'application/json',
        ...options?.headers,
      },
      ...options,
    })

    // Check for redirect (indicates trailing slash mismatch)
    if (response.redirected) {
      console.warn(`API redirect detected: ${url} -> ${response.url}`)
    }

    if (!response.ok) {
      const error = await response.json().catch(() => ({ detail: 'Request failed' }))
      throw new ApiError(
        error.detail || `Request failed with status ${response.status}`,
        response.status,
        endpoint
      )
    }

    const data = await response.json()

    // Validate response is not HTML (common redirect issue)
    if (typeof data === 'string' && data.includes('<!DOCTYPE')) {
      throw new ApiError(
        'Received HTML instead of JSON - possible redirect issue',
        500,
        endpoint
      )
    }

    return data
  } catch (error) {
    if (error instanceof ApiError) {
      throw error
    }
    // Network error or other fetch failure
    throw new ApiError(
      error instanceof Error ? error.message : 'Network error',
      0,
      endpoint
    )
  }
}

// Validate that API response is an array
function ensureArray<T>(data: unknown, endpoint: string): T[] {
  if (Array.isArray(data)) {
    return data
  }
  throw new ApiError(
    `Expected array but got ${typeof data}`,
    500,
    endpoint
  )
}

export const api = {
  // History endpoints - ClaudeCode projects/sessions
  getProjects: async () => {
    const endpoint = '/history/projects'
    const data = await fetchApi<Project[]>(endpoint)
    return ensureArray<Project>(data, endpoint)
  },

  getSessions: async (projectId: string) => {
    const endpoint = `/history/projects/${projectId}/sessions`
    const data = await fetchApi<Session[]>(endpoint)
    return ensureArray<Session>(data, endpoint)
  },

  getSessionDetail: (sessionId: string) =>
    fetchApi<SessionDetail>(`/history/sessions/${sessionId}`),

  // Room endpoints - Discussion rooms
  getRooms: async () => {
    const endpoint = '/rooms'
    const data = await fetchApi<Room[]>(endpoint)
    return ensureArray<Room>(data, endpoint)
  },

  getRoom: (roomId: number) => fetchApi<RoomDetail>(`/rooms/${roomId}`),

  createRoom: (data: CreateRoomRequest) =>
    fetchApi<Room>('/rooms', {
      method: 'POST',
      body: JSON.stringify(data),
    }),

  deleteRoom: (roomId: number) =>
    fetchApi<{ status: string }>(`/rooms/${roomId}`, {
      method: 'DELETE',
    }),

  startRoom: (roomId: number) =>
    fetchApi<{ status: string; websocket_url: string }>(`/rooms/${roomId}/start`, {
      method: 'POST',
    }),

  pauseRoom: (roomId: number) =>
    fetchApi<{ status: string }>(`/rooms/${roomId}/pause`, {
      method: 'POST',
    }),

  sendModeratorMessage: (roomId: number, content: string) =>
    fetchApi<RoomMessage>(`/rooms/${roomId}/moderate`, {
      method: 'POST',
      body: JSON.stringify({ content }),
    }),

  // Codex History endpoints
  getCodexProjects: async () => {
    const endpoint = '/history/codex/projects'
    const data = await fetchApi<CodexProject[]>(endpoint)
    return ensureArray<CodexProject>(data, endpoint)
  },

  getCodexSessions: async (projectId: string) => {
    const endpoint = `/history/codex/projects/${projectId}/sessions`
    const data = await fetchApi<CodexSession[]>(endpoint)
    return ensureArray<CodexSession>(data, endpoint)
  },

  // Config endpoints
  getAvailableAgents: async (): Promise<AgentType[]> => {
    const data = await fetchApi<{ available_agents: AgentType[] }>('/config/available-agents')
    return data.available_agents || []
  },
}
