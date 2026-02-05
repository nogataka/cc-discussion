import { Loader2 } from 'lucide-react'

interface PreparationState {
  participantId: number
  participantName: string
  isComplete: boolean
  notesPreview?: string
}

interface BackgroundActivity {
  participantId: number
  participantName: string
  activity: string
  timestamp: string
}

interface StatusIndicatorProps {
  preparingParticipants: Map<number, PreparationState>
  backgroundActivities: BackgroundActivity[]
  speakingParticipantId?: number
}

export function StatusIndicator({
  preparingParticipants,
  backgroundActivities,
  speakingParticipantId,
}: StatusIndicatorProps) {
  // Get participants who are preparing (not the current speaker)
  const preparingList = Array.from(preparingParticipants.values()).filter(
    (p) => p.participantId !== speakingParticipantId && !p.isComplete
  )

  // Get the most recent background activity
  const recentActivity = backgroundActivities[backgroundActivities.length - 1]

  if (preparingList.length === 0 && !recentActivity) {
    return null
  }

  return (
    <div className="h-8 px-4 flex items-center gap-2 text-xs text-muted-foreground border-t bg-muted/20">
      {preparingList.length > 0 && (
        <div className="flex items-center gap-2">
          <Loader2 className="h-3 w-3 animate-spin text-primary" />
          <span>
            {preparingList.map((p) => p.participantName).join(', ')}
            {preparingList.length === 1 ? ' is ' : ' are '}
            preparing...
          </span>
        </div>
      )}

      {recentActivity && preparingList.length === 0 && (
        <div className="flex items-center gap-2 truncate">
          <div className="w-2 h-2 rounded-full bg-amber-400 animate-pulse" />
          <span className="truncate">
            {recentActivity.participantName}: {recentActivity.activity}
          </span>
        </div>
      )}
    </div>
  )
}
