import { useState, useMemo } from 'react'
import { useMutation, useQuery, useQueryClient } from '@tanstack/react-query'
import { Plus, Trash2, History, Loader2, ChevronDown, ChevronRight, ChevronLeft, MessageSquare, Calendar } from 'lucide-react'
import {
  Dialog,
  DialogContent,
  DialogHeader,
  DialogTitle,
} from '@/components/ui/dialog'
import { Button } from '@/components/ui/button'
import { Input } from '@/components/ui/input'
import { Label } from '@/components/ui/label'
import { Textarea } from '@/components/ui/textarea'
import { Card, CardContent } from '@/components/ui/card'
import { Checkbox } from '@/components/ui/checkbox'
import {
  api,
  type CreateRoomRequest,
  type Project,
  type Session,
  type MeetingType,
  type AgentType,
  MEETING_TYPES,
} from '@/lib/api'

interface ParticipantForm {
  id: string  // Unique ID for React key
  name: string
  role: string
  color: string
  context_project_dir?: string
  context_session_id?: string
  selectedProjectName?: string
  selectedSessionPrompt?: string
  is_facilitator?: boolean
  agent_type?: AgentType
}

// Generate unique ID
const generateId = () => Math.random().toString(36).substring(2, 9)

const COLORS = [
  '#6366f1', // Indigo
  '#22c55e', // Green
  '#f59e0b', // Amber
  '#ec4899', // Pink
  '#8b5cf6', // Violet
  '#06b6d4', // Cyan
]

interface CreateRoomModalProps {
  isOpen: boolean
  onClose: () => void
  onRoomCreated: (roomId: number) => void
}

export function CreateRoomModal({
  isOpen,
  onClose,
  onRoomCreated,
}: CreateRoomModalProps) {
  const queryClient = useQueryClient()

  const [roomName, setRoomName] = useState('')
  const [topic, setTopic] = useState('')
  const [maxTurns, setMaxTurns] = useState(20)
  const [meetingType, setMeetingType] = useState<MeetingType>('technical_review')
  const [customMeetingDescription, setCustomMeetingDescription] = useState('')
  const [language, setLanguage] = useState<'ja' | 'en'>('ja')
  const [participants, setParticipants] = useState<ParticipantForm[]>([
    { id: generateId(), name: 'Claude A', role: '', color: COLORS[0], agent_type: 'claude' },
    { id: generateId(), name: 'Claude B', role: '', color: COLORS[1], agent_type: 'claude' },
  ])
  const [expandedParticipant, setExpandedParticipant] = useState<number | null>(null)
  const [selectedProject, setSelectedProject] = useState<string | null>(null)
  const [hideEmptySessions, setHideEmptySessions] = useState(true)

  // Get current expanded participant's agent type
  const expandedAgentType = expandedParticipant !== null
    ? participants[expandedParticipant]?.agent_type || 'claude'
    : 'claude'

  // Fetch ClaudeCode projects
  const { data: projects } = useQuery({
    queryKey: ['claudeProjects'],
    queryFn: api.getProjects,
    enabled: isOpen && expandedAgentType === 'claude',
  })

  // Fetch Codex projects
  const { data: codexProjects } = useQuery({
    queryKey: ['codexProjects'],
    queryFn: api.getCodexProjects,
    enabled: isOpen && expandedAgentType === 'codex',
  })

  // Fetch sessions for selected ClaudeCode project
  const { data: sessions, isLoading: sessionsLoading } = useQuery({
    queryKey: ['claudeSessions', selectedProject],
    queryFn: () => api.getSessions(selectedProject!),
    enabled: !!selectedProject && expandedAgentType === 'claude',
  })

  // Fetch sessions for selected Codex project
  const { data: codexSessions, isLoading: codexSessionsLoading } = useQuery({
    queryKey: ['codexSessions', selectedProject],
    queryFn: () => api.getCodexSessions(selectedProject!),
    enabled: !!selectedProject && expandedAgentType === 'codex',
  })

  // Sort ClaudeCode projects by last modified (most recent first)
  const sortedProjects = useMemo(() => {
    if (!projects) return []
    return [...projects].sort((a, b) =>
      new Date(b.last_modified_at).getTime() - new Date(a.last_modified_at).getTime()
    )
  }, [projects])

  // Sort Codex projects by last modified (most recent first)
  const sortedCodexProjects = useMemo(() => {
    if (!codexProjects) return []
    return [...codexProjects].sort((a, b) =>
      new Date(b.last_modified_at).getTime() - new Date(a.last_modified_at).getTime()
    )
  }, [codexProjects])

  // Filter ClaudeCode sessions
  const filteredSessions = useMemo(() => {
    if (!sessions) return []
    let result = [...sessions].sort((a, b) =>
      new Date(b.last_modified_at).getTime() - new Date(a.last_modified_at).getTime()
    )
    if (hideEmptySessions) {
      result = result.filter(s => s.first_user_message !== null)
    }
    return result
  }, [sessions, hideEmptySessions])

  // Filter Codex sessions
  const filteredCodexSessions = useMemo(() => {
    if (!codexSessions) return []
    let result = [...codexSessions].sort((a, b) =>
      new Date(b.last_modified_at).getTime() - new Date(a.last_modified_at).getTime()
    )
    if (hideEmptySessions) {
      result = result.filter(s => s.first_user_message !== null)
    }
    return result
  }, [codexSessions, hideEmptySessions])

  // Create room mutation
  const createMutation = useMutation({
    mutationFn: api.createRoom,
    onSuccess: (room) => {
      queryClient.invalidateQueries({ queryKey: ['rooms'] })
      onRoomCreated(room.id)
      resetForm()
    },
  })

  const resetForm = () => {
    setRoomName('')
    setTopic('')
    setMaxTurns(20)
    setMeetingType('technical_review')
    setCustomMeetingDescription('')
    setLanguage('ja')
    setParticipants([
      { id: generateId(), name: 'Claude A', role: '', color: COLORS[0], agent_type: 'claude' },
      { id: generateId(), name: 'Claude B', role: '', color: COLORS[1], agent_type: 'claude' },
    ])
    setExpandedParticipant(null)
    setSelectedProject(null)
    setHideEmptySessions(true)
  }

  const handleAddParticipant = () => {
    if (participants.length >= 3) return
    setParticipants(prev => [
      ...prev,
      {
        id: generateId(),
        name: `Claude ${String.fromCharCode(65 + prev.length)}`,
        role: '',
        color: COLORS[prev.length % COLORS.length],
        agent_type: 'claude',
      },
    ])
  }

  const handleAddFacilitator = () => {
    // Check if facilitator already exists
    const hasFacilitator = participants.some(p => p.is_facilitator)
    if (hasFacilitator || participants.length >= 3) return
    setParticipants(prev => [
      {
        id: generateId(),
        name: 'Facilitator',
        role: 'ファシリテーター',
        color: '#9333ea',  // Purple
        is_facilitator: true,
        agent_type: 'claude',
      },
      ...prev,
    ])
  }

  const handleRemoveParticipant = (index: number) => {
    setParticipants(prev => {
      if (prev.length <= 2) return prev
      return prev.filter((_, i) => i !== index)
    })
  }

  const handleUpdateParticipant = (
    index: number,
    field: keyof ParticipantForm,
    value: string
  ) => {
    setParticipants(prev => {
      const updated = [...prev]
      updated[index] = { ...updated[index], [field]: value }
      return updated
    })
  }

  const handleSelectSession = (
    participantIndex: number,
    project: Project,
    session: Session
  ) => {
    setParticipants(prev => {
      const updated = [...prev]
      updated[participantIndex] = {
        ...updated[participantIndex],
        context_project_dir: project.id,
        context_session_id: session.id,
        selectedProjectName: project.name,
        selectedSessionPrompt: session.first_user_message || '(No prompt)',
      }
      return updated
    })
    setExpandedParticipant(null)
    setSelectedProject(null)
  }

  const handleClearContext = (participantIndex: number) => {
    setParticipants(prev => {
      const updated = [...prev]
      updated[participantIndex] = {
        ...updated[participantIndex],
        context_project_dir: undefined,
        context_session_id: undefined,
        selectedProjectName: undefined,
        selectedSessionPrompt: undefined,
      }
      return updated
    })
  }

  const handleSubmit = () => {
    if (!roomName.trim() || participants.length < 2) return

    const request: CreateRoomRequest = {
      name: roomName.trim(),
      topic: topic.trim() || undefined,
      max_turns: maxTurns,
      meeting_type: meetingType,
      custom_meeting_description: meetingType === 'other' ? customMeetingDescription : undefined,
      language: language,
      participants: participants.map((p) => ({
        name: p.name,
        role: p.role || undefined,
        color: p.color,
        context_project_dir: p.context_project_dir,
        context_session_id: p.context_session_id,
        is_facilitator: p.is_facilitator,
        agent_type: p.agent_type,
      })),
    }

    createMutation.mutate(request)
  }

  return (
    <Dialog open={isOpen} onOpenChange={(open) => !open && onClose()}>
      <DialogContent className="w-[90vw] max-w-4xl max-h-[90vh] overflow-y-auto">
        <DialogHeader>
          <DialogTitle>Create Discussion Room</DialogTitle>
        </DialogHeader>

        <div className="space-y-6 py-4">
          {/* Room Details */}
          <div className="space-y-4">
            <div>
              <Label htmlFor="roomName">Room Name *</Label>
              <Input
                id="roomName"
                value={roomName}
                onChange={(e) => setRoomName(e.target.value)}
                placeholder="e.g., Architecture Review"
              />
            </div>

            <div>
              <Label htmlFor="topic">Discussion Topic</Label>
              <Textarea
                id="topic"
                value={topic}
                onChange={(e) => setTopic(e.target.value)}
                placeholder="What should the Claudes discuss?"
                rows={3}
              />
            </div>

            <div>
              <Label htmlFor="maxTurns">Max Turns</Label>
              <Input
                id="maxTurns"
                type="number"
                min={1}
                max={100}
                value={maxTurns}
                onChange={(e) => setMaxTurns(parseInt(e.target.value) || 20)}
              />
            </div>

            {/* Meeting Type Selection */}
            <div>
              <Label>会議タイプ</Label>
              <div className="grid grid-cols-2 md:grid-cols-3 gap-2 mt-2">
                {MEETING_TYPES.map((mt) => (
                  <label
                    key={mt.value}
                    className={`flex items-center gap-2 p-2 rounded-md border cursor-pointer transition-colors ${
                      meetingType === mt.value
                        ? 'border-primary bg-primary/10'
                        : 'border-border hover:bg-muted'
                    }`}
                  >
                    <input
                      type="radio"
                      name="meetingType"
                      value={mt.value}
                      checked={meetingType === mt.value}
                      onChange={(e) => setMeetingType(e.target.value as MeetingType)}
                      className="sr-only"
                    />
                    <span className="text-sm">{mt.label}</span>
                  </label>
                ))}
              </div>
              {meetingType === 'other' && (
                <Textarea
                  className="mt-2"
                  value={customMeetingDescription}
                  onChange={(e) => setCustomMeetingDescription(e.target.value)}
                  placeholder="会議の目的や議論内容を入力してください..."
                  rows={3}
                />
              )}
            </div>

            {/* Language Selection */}
            <div>
              <Label>言語</Label>
              <div className="flex gap-4 mt-2">
                <label className={`flex items-center gap-2 p-2 px-4 rounded-md border cursor-pointer transition-colors ${
                  language === 'ja' ? 'border-primary bg-primary/10' : 'border-border hover:bg-muted'
                }`}>
                  <input
                    type="radio"
                    name="language"
                    value="ja"
                    checked={language === 'ja'}
                    onChange={() => setLanguage('ja')}
                    className="sr-only"
                  />
                  <span className="text-sm">日本語</span>
                </label>
                <label className={`flex items-center gap-2 p-2 px-4 rounded-md border cursor-pointer transition-colors ${
                  language === 'en' ? 'border-primary bg-primary/10' : 'border-border hover:bg-muted'
                }`}>
                  <input
                    type="radio"
                    name="language"
                    value="en"
                    checked={language === 'en'}
                    onChange={() => setLanguage('en')}
                    className="sr-only"
                  />
                  <span className="text-sm">English</span>
                </label>
              </div>
            </div>
          </div>

          {/* Participants */}
          <div>
            <div className="flex items-center justify-between mb-4">
              <Label>参加者 ({participants.length}/3)</Label>
              <div className="flex gap-2">
                {!participants.some(p => p.is_facilitator) && participants.length < 3 && (
                  <Button
                    variant="outline"
                    size="sm"
                    onClick={handleAddFacilitator}
                  >
                    <Plus className="w-4 h-4 mr-1" />
                    ファシリテーター追加
                  </Button>
                )}
                {participants.length < 3 && (
                  <Button
                    variant="outline"
                    size="sm"
                    onClick={handleAddParticipant}
                  >
                    <Plus className="w-4 h-4 mr-1" />
                    参加者追加
                  </Button>
                )}
              </div>
            </div>

            <div className="space-y-4">
              {participants.map((participant, index) => (
                <Card key={participant.id}>
                  <CardContent className="p-4">
                    <div className="flex items-start gap-4">
                      {/* Color indicator */}
                      <div
                        className="w-4 h-4 rounded-full mt-2 flex-shrink-0"
                        style={{ backgroundColor: participant.color }}
                      />

                      <div className="flex-1 space-y-3">
                        {/* Facilitator badge */}
                        {participant.is_facilitator && (
                          <div className="inline-flex items-center gap-1 px-2 py-1 bg-purple-100 text-purple-700 rounded-md text-xs font-medium">
                            ファシリテーター
                          </div>
                        )}

                        <div className="flex gap-4">
                          <div className="flex-1">
                            <Label>名前</Label>
                            <Input
                              value={participant.name}
                              onChange={(e) =>
                                handleUpdateParticipant(index, 'name', e.target.value)
                              }
                              placeholder="参加者名"
                            />
                          </div>
                          <div className="flex-1">
                            <Label>役割</Label>
                            <Input
                              value={participant.role}
                              onChange={(e) =>
                                handleUpdateParticipant(index, 'role', e.target.value)
                              }
                              placeholder="例: アーキテクト"
                            />
                          </div>
                        </div>

                        {/* Agent Type Selection */}
                        <div>
                          <Label>エージェントタイプ</Label>
                          <div className="flex gap-2 mt-1">
                            <label className={`flex items-center gap-2 p-2 px-3 rounded-md border cursor-pointer transition-colors text-sm ${
                              participant.agent_type === 'claude' ? 'border-primary bg-primary/10' : 'border-border hover:bg-muted'
                            }`}>
                              <input
                                type="radio"
                                name={`agent-type-${participant.id}`}
                                value="claude"
                                checked={participant.agent_type === 'claude'}
                                onChange={() => {
                                  setParticipants(prev => {
                                    const updated = [...prev]
                                    updated[index] = { ...updated[index], agent_type: 'claude' }
                                    return updated
                                  })
                                }}
                                className="sr-only"
                              />
                              Claude
                            </label>
                            <label className={`flex items-center gap-2 p-2 px-3 rounded-md border cursor-pointer transition-colors text-sm ${
                              participant.agent_type === 'codex' ? 'border-primary bg-primary/10' : 'border-border hover:bg-muted'
                            }`}>
                              <input
                                type="radio"
                                name={`agent-type-${participant.id}`}
                                value="codex"
                                checked={participant.agent_type === 'codex'}
                                onChange={() => {
                                  setParticipants(prev => {
                                    const updated = [...prev]
                                    updated[index] = { ...updated[index], agent_type: 'codex' }
                                    return updated
                                  })
                                }}
                                className="sr-only"
                              />
                              Codex
                            </label>
                          </div>
                        </div>

                        {/* Context Selection */}
                        <div>
                          <Label className="flex items-center gap-1">
                            <History className="w-4 h-4" />
                            {participant.agent_type === 'codex' ? 'Codex Context' : 'ClaudeCode Context'}
                          </Label>

                          {participant.context_session_id ? (
                            <div className="mt-2 p-2 bg-muted rounded-md">
                              <div className="flex items-center justify-between">
                                <div className="text-sm">
                                  <span className="font-medium">
                                    {participant.selectedProjectName}
                                  </span>
                                  <p className="text-muted-foreground line-clamp-1">
                                    {participant.selectedSessionPrompt}
                                  </p>
                                </div>
                                <Button
                                  variant="ghost"
                                  size="sm"
                                  onClick={() => handleClearContext(index)}
                                >
                                  <Trash2 className="w-4 h-4" />
                                </Button>
                              </div>
                            </div>
                          ) : (
                            <Button
                              variant="outline"
                              size="sm"
                              className="mt-2"
                              onClick={() => {
                                setExpandedParticipant(
                                  expandedParticipant === index ? null : index
                                )
                                setSelectedProject(null)
                              }}
                            >
                              {expandedParticipant === index ? (
                                <ChevronDown className="w-4 h-4 mr-1" />
                              ) : (
                                <ChevronRight className="w-4 h-4 mr-1" />
                              )}
                              Select Context
                            </Button>
                          )}

                          {/* Context Browser */}
                          {expandedParticipant === index && (
                            <div className="mt-2 border rounded-md p-3 max-h-80 overflow-y-auto bg-muted/30">
                              {!selectedProject ? (
                                // Project list - show based on agent type
                                <div className="space-y-2">
                                  <p className="text-sm font-medium text-muted-foreground mb-3">
                                    プロジェクトを選択:
                                  </p>
                                  {participant.agent_type === 'codex' ? (
                                    // Codex projects
                                    <>
                                      {sortedCodexProjects.map((project) => (
                                        <button
                                          key={project.id}
                                          className="w-full text-left p-3 hover:bg-muted rounded-lg text-sm border bg-background transition-colors"
                                          onClick={() => setSelectedProject(project.id)}
                                        >
                                          <div className="flex items-center gap-2">
                                            <History className="w-4 h-4 text-muted-foreground flex-shrink-0" />
                                            <span className="font-medium truncate">{project.name}</span>
                                          </div>
                                          <div className="text-muted-foreground text-xs truncate mt-1 ml-6">
                                            {project.path}
                                          </div>
                                          <div className="flex items-center gap-3 text-xs text-muted-foreground mt-1 ml-6">
                                            <span className="flex items-center gap-1">
                                              <Calendar className="w-3 h-3" />
                                              {new Date(project.last_modified_at).toLocaleDateString()}
                                            </span>
                                            <span>{project.session_count} sessions</span>
                                          </div>
                                        </button>
                                      ))}
                                      {sortedCodexProjects.length === 0 && (
                                        <p className="text-sm text-muted-foreground text-center py-4">
                                          Codexプロジェクトが見つかりません
                                        </p>
                                      )}
                                    </>
                                  ) : (
                                    // ClaudeCode projects
                                    <>
                                      {sortedProjects.map((project) => (
                                        <button
                                          key={project.id}
                                          className="w-full text-left p-3 hover:bg-muted rounded-lg text-sm border bg-background transition-colors"
                                          onClick={() => setSelectedProject(project.id)}
                                        >
                                          <div className="flex items-center gap-2">
                                            <History className="w-4 h-4 text-muted-foreground flex-shrink-0" />
                                            <span className="font-medium truncate">{project.name}</span>
                                          </div>
                                          <div className="text-muted-foreground text-xs truncate mt-1 ml-6">
                                            {project.path}
                                          </div>
                                          <div className="flex items-center gap-1 text-xs text-muted-foreground mt-1 ml-6">
                                            <Calendar className="w-3 h-3" />
                                            {new Date(project.last_modified_at).toLocaleDateString()}
                                          </div>
                                        </button>
                                      ))}
                                      {sortedProjects.length === 0 && (
                                        <p className="text-sm text-muted-foreground text-center py-4">
                                          ClaudeCodeプロジェクトが見つかりません
                                        </p>
                                      )}
                                    </>
                                  )}
                                </div>
                              ) : (
                                // Session list - show based on agent type
                                <div className="space-y-2">
                                  <div className="flex items-center justify-between mb-3">
                                    <button
                                      className="text-sm text-primary hover:underline flex items-center gap-1"
                                      onClick={() => setSelectedProject(null)}
                                    >
                                      <ChevronLeft className="w-4 h-4" />
                                      プロジェクト一覧へ
                                    </button>
                                    <label className="flex items-center gap-2 text-xs text-muted-foreground cursor-pointer">
                                      <Checkbox
                                        checked={hideEmptySessions}
                                        onCheckedChange={(checked) => setHideEmptySessions(checked === true)}
                                      />
                                      空のセッションを非表示
                                    </label>
                                  </div>

                                  {participant.agent_type === 'codex' ? (
                                    // Codex sessions
                                    <>
                                      {codexSessionsLoading ? (
                                        <div className="flex items-center justify-center py-8">
                                          <Loader2 className="w-5 h-5 animate-spin text-muted-foreground" />
                                        </div>
                                      ) : filteredCodexSessions.length === 0 ? (
                                        <p className="text-sm text-muted-foreground text-center py-4">
                                          {hideEmptySessions ? 'メッセージのあるセッションがありません' : 'セッションが見つかりません'}
                                        </p>
                                      ) : (
                                        filteredCodexSessions.map((session) => {
                                          const project = sortedCodexProjects.find(
                                            (p) => p.id === selectedProject
                                          )
                                          return (
                                            <button
                                              key={session.id}
                                              className="w-full text-left p-3 hover:bg-muted rounded-lg text-sm border bg-background transition-colors"
                                              onClick={() => {
                                                if (project) {
                                                  setParticipants(prev => {
                                                    const updated = [...prev]
                                                    updated[index] = {
                                                      ...updated[index],
                                                      context_project_dir: project.id,
                                                      context_session_id: session.id,
                                                      selectedProjectName: project.name,
                                                      selectedSessionPrompt: session.first_user_message || '(No prompt)',
                                                    }
                                                    return updated
                                                  })
                                                  setExpandedParticipant(null)
                                                  setSelectedProject(null)
                                                }
                                              }}
                                            >
                                              <div className="flex items-start gap-2">
                                                <MessageSquare className="w-4 h-4 text-muted-foreground flex-shrink-0 mt-0.5" />
                                                <div className="flex-1 min-w-0">
                                                  <div className="line-clamp-2 font-medium">
                                                    {session.first_user_message || '(No prompt)'}
                                                  </div>
                                                  <div className="flex items-center gap-3 text-xs text-muted-foreground mt-2">
                                                    <span className="flex items-center gap-1">
                                                      <MessageSquare className="w-3 h-3" />
                                                      {session.message_count} messages
                                                    </span>
                                                    <span className="flex items-center gap-1">
                                                      <Calendar className="w-3 h-3" />
                                                      {new Date(session.last_modified_at).toLocaleDateString()}
                                                    </span>
                                                  </div>
                                                </div>
                                              </div>
                                            </button>
                                          )
                                        })
                                      )}
                                    </>
                                  ) : (
                                    // ClaudeCode sessions
                                    <>
                                      {sessionsLoading ? (
                                        <div className="flex items-center justify-center py-8">
                                          <Loader2 className="w-5 h-5 animate-spin text-muted-foreground" />
                                        </div>
                                      ) : filteredSessions.length === 0 ? (
                                        <p className="text-sm text-muted-foreground text-center py-4">
                                          {hideEmptySessions ? 'メッセージのあるセッションがありません' : 'セッションが見つかりません'}
                                        </p>
                                      ) : (
                                        filteredSessions.map((session) => {
                                          const project = sortedProjects.find(
                                            (p) => p.id === selectedProject
                                          )
                                          return (
                                            <button
                                              key={session.id}
                                              className="w-full text-left p-3 hover:bg-muted rounded-lg text-sm border bg-background transition-colors"
                                              onClick={() =>
                                                project &&
                                                handleSelectSession(index, project, session)
                                              }
                                            >
                                              <div className="flex items-start gap-2">
                                                <MessageSquare className="w-4 h-4 text-muted-foreground flex-shrink-0 mt-0.5" />
                                                <div className="flex-1 min-w-0">
                                                  <div className="line-clamp-2 font-medium">
                                                    {session.first_user_message || '(No prompt)'}
                                                  </div>
                                                  <div className="flex items-center gap-3 text-xs text-muted-foreground mt-2">
                                                    <span className="flex items-center gap-1">
                                                      <MessageSquare className="w-3 h-3" />
                                                      {session.message_count} messages
                                                    </span>
                                                    <span className="flex items-center gap-1">
                                                      <Calendar className="w-3 h-3" />
                                                      {new Date(session.last_modified_at).toLocaleDateString()}
                                                    </span>
                                                  </div>
                                                </div>
                                              </div>
                                            </button>
                                          )
                                        })
                                      )}
                                    </>
                                  )}
                                </div>
                              )}
                            </div>
                          )}
                        </div>
                      </div>

                      {/* Remove button */}
                      {participants.length > 2 && (
                        <Button
                          variant="ghost"
                          size="sm"
                          onClick={() => handleRemoveParticipant(index)}
                        >
                          <Trash2 className="w-4 h-4" />
                        </Button>
                      )}
                    </div>
                  </CardContent>
                </Card>
              ))}
            </div>
          </div>

          {/* Actions */}
          <div className="flex justify-end gap-2">
            <Button variant="outline" onClick={onClose}>
              Cancel
            </Button>
            <Button
              onClick={handleSubmit}
              disabled={
                !roomName.trim() ||
                participants.length < 2 ||
                createMutation.isPending
              }
            >
              {createMutation.isPending ? (
                <>
                  <Loader2 className="w-4 h-4 mr-2 animate-spin" />
                  Creating...
                </>
              ) : (
                'Create Room'
              )}
            </Button>
          </div>

          {createMutation.isError && (
            <p className="text-sm text-destructive text-center">
              {createMutation.error.message}
            </p>
          )}
        </div>
      </DialogContent>
    </Dialog>
  )
}
