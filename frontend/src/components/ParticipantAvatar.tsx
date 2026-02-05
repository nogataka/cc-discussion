/**
 * Participant Avatar Component
 * Generates unique robot SVG avatars for Claude participants
 */

interface ParticipantAvatarProps {
  name: string
  color: string
  size?: number
  isActive?: boolean
}

// Robot avatar patterns for Claude participants
const robotPatterns = [
  // Robot A - Classic robot head with antenna
  (color: string) => (
    <>
      <rect x="5" y="6" width="14" height="14" rx="2" fill={color} opacity="0.2" />
      <rect x="7" y="8" width="4" height="3" rx="1" fill={color} />
      <rect x="13" y="8" width="4" height="3" rx="1" fill={color} />
      <rect x="9" y="14" width="6" height="2" rx="1" fill={color} />
      <line x1="12" y1="2" x2="12" y2="6" stroke={color} strokeWidth="2" strokeLinecap="round" />
      <circle cx="12" cy="2" r="1.5" fill={color} />
    </>
  ),
  // Robot B - Rounded robot with visor eyes
  (color: string) => (
    <>
      <circle cx="12" cy="12" r="9" fill={color} opacity="0.2" />
      <rect x="6" y="9" width="12" height="4" rx="2" fill={color} opacity="0.5" />
      <circle cx="9" cy="11" r="1.5" fill={color} />
      <circle cx="15" cy="11" r="1.5" fill={color} />
      <rect x="9" y="16" width="6" height="1.5" rx="0.75" fill={color} />
      <rect x="10" y="3" width="4" height="3" rx="1" fill={color} opacity="0.3" />
      <circle cx="12" cy="2" r="1" fill={color} />
    </>
  ),
  // Robot C - Square bot with gear pattern
  (color: string) => (
    <>
      <rect x="5" y="5" width="14" height="14" rx="1" fill={color} opacity="0.2" />
      <circle cx="9" cy="10" r="2" fill="white" stroke={color} strokeWidth="1.5" />
      <circle cx="15" cy="10" r="2" fill="white" stroke={color} strokeWidth="1.5" />
      <circle cx="9" cy="10" r="0.8" fill={color} />
      <circle cx="15" cy="10" r="0.8" fill={color} />
      <path d="M8 15 L10 14 L12 15 L14 14 L16 15" stroke={color} strokeWidth="1.5" fill="none" strokeLinecap="round" />
      <rect x="4" y="9" width="2" height="4" rx="1" fill={color} opacity="0.4" />
      <rect x="18" y="9" width="2" height="4" rx="1" fill={color} opacity="0.4" />
    </>
  ),
  // Robot D - Cute compact robot
  (color: string) => (
    <>
      <rect x="6" y="7" width="12" height="12" rx="3" fill={color} opacity="0.2" />
      <rect x="8" y="10" width="3" height="2" rx="0.5" fill={color} />
      <rect x="13" y="10" width="3" height="2" rx="0.5" fill={color} />
      <circle cx="12" cy="15" r="1.5" fill={color} opacity="0.5" />
      <line x1="9" y1="4" x2="9" y2="7" stroke={color} strokeWidth="1.5" strokeLinecap="round" />
      <line x1="15" y1="4" x2="15" y2="7" stroke={color} strokeWidth="1.5" strokeLinecap="round" />
      <circle cx="9" cy="3" r="1" fill={color} />
      <circle cx="15" cy="3" r="1" fill={color} />
    </>
  ),
  // Robot E - Monitor-head robot
  (color: string) => (
    <>
      <rect x="4" y="5" width="16" height="12" rx="2" fill={color} opacity="0.2" />
      <rect x="6" y="7" width="12" height="8" rx="1" fill={color} opacity="0.15" stroke={color} strokeWidth="1" />
      <circle cx="9" cy="11" r="1.5" fill={color} />
      <circle cx="15" cy="11" r="1.5" fill={color} />
      <path d="M10 14 Q12 15.5 14 14" stroke={color} strokeWidth="1.5" fill="none" strokeLinecap="round" />
      <rect x="10" y="17" width="4" height="2" fill={color} opacity="0.3" />
      <rect x="8" y="19" width="8" height="2" rx="1" fill={color} opacity="0.2" />
    </>
  ),
  // Robot F - Spherical helper bot
  (color: string) => (
    <>
      <circle cx="12" cy="12" r="9" fill={color} opacity="0.2" />
      <ellipse cx="12" cy="10" rx="6" ry="3" fill={color} opacity="0.3" />
      <circle cx="9" cy="10" r="1.5" fill="white" />
      <circle cx="15" cy="10" r="1.5" fill="white" />
      <circle cx="9" cy="10" r="0.7" fill={color} />
      <circle cx="15" cy="10" r="0.7" fill={color} />
      <ellipse cx="12" cy="15" rx="2" ry="1" fill={color} opacity="0.4" />
      <circle cx="12" cy="3" r="1.5" fill={color} />
      <line x1="12" y1="3" x2="12" y2="5" stroke={color} strokeWidth="1" />
    </>
  ),
]

// Get a consistent pattern based on name
function getPatternIndex(name: string): number {
  let hash = 0
  for (let i = 0; i < name.length; i++) {
    hash = ((hash << 5) - hash) + name.charCodeAt(i)
    hash = hash & hash
  }
  return Math.abs(hash) % robotPatterns.length
}

export function ParticipantAvatar({ name, color, size = 40, isActive = false }: ParticipantAvatarProps) {
  const patternIndex = getPatternIndex(name)
  const Pattern = robotPatterns[patternIndex]

  return (
    <div
      className={`relative flex-shrink-0 rounded-full transition-all duration-300 ${
        isActive ? 'ring-2 ring-offset-2 shadow-lg scale-110' : ''
      }`}
      style={{
        width: size,
        height: size,
        // @ts-expect-error - Tailwind CSS ring color via CSS custom property
        '--tw-ring-color': isActive ? color : undefined,
      }}
    >
      <svg
        width={size}
        height={size}
        viewBox="0 0 24 24"
        className="rounded-full"
        style={{ backgroundColor: `${color}10` }}
      >
        {Pattern(color)}
      </svg>
      {isActive && (
        <span
          className="absolute -bottom-1 -right-1 w-3 h-3 rounded-full border-2 border-white animate-pulse"
          style={{ backgroundColor: color }}
        />
      )}
    </div>
  )
}
