import { useState, useRef, useEffect, KeyboardEvent } from 'react'
import { Send, AtSign } from 'lucide-react'
import { Button } from '../ui/button'
import { Textarea } from '../ui/textarea'

interface Participant {
  id: number
  name: string
  color?: string
}

interface MentionOption {
  id: string | number
  name: string
  color?: string
}

interface MessageInputProps {
  onSend: (content: string) => void
  placeholder?: string
  disabled?: boolean
  participants?: Participant[]
}

export function MessageInput({
  onSend,
  placeholder = 'Send a moderator message...',
  disabled = false,
  participants = [],
}: MessageInputProps) {
  const [content, setContent] = useState('')
  const [isComposing, setIsComposing] = useState(false)
  const [showMentionPicker, setShowMentionPicker] = useState(false)
  const [mentionFilter, setMentionFilter] = useState('')
  const [selectedIndex, setSelectedIndex] = useState(0)
  const [mentionStartPos, setMentionStartPos] = useState<number | null>(null)
  const textareaRef = useRef<HTMLTextAreaElement>(null)
  const pickerRef = useRef<HTMLDivElement>(null)

  // Build mention options: ALL + participants
  const mentionOptions: MentionOption[] = [
    { id: 'ALL', name: '全員', color: '#f59e0b' },
    ...participants.map((p) => ({ id: p.id, name: p.name, color: p.color })),
  ]

  // Filter options based on input
  const filteredOptions = mentionOptions.filter((opt) =>
    opt.name.toLowerCase().includes(mentionFilter.toLowerCase())
  )

  // Reset selected index when filter changes
  useEffect(() => {
    setSelectedIndex(0)
  }, [mentionFilter])

  // Close picker when clicking outside
  useEffect(() => {
    const handleClickOutside = (e: MouseEvent) => {
      if (pickerRef.current && !pickerRef.current.contains(e.target as Node)) {
        setShowMentionPicker(false)
      }
    }
    document.addEventListener('mousedown', handleClickOutside)
    return () => document.removeEventListener('mousedown', handleClickOutside)
  }, [])

  const handleSend = () => {
    const trimmed = content.trim()
    if (trimmed && !disabled) {
      onSend(trimmed)
      setContent('')
      setShowMentionPicker(false)
      // Reset textarea height
      if (textareaRef.current) {
        textareaRef.current.style.height = 'auto'
      }
    }
  }

  const insertMention = (option: MentionOption) => {
    if (mentionStartPos === null) return

    const before = content.slice(0, mentionStartPos)
    const after = content.slice(textareaRef.current?.selectionStart || mentionStartPos)

    // Use @name for participants, @ALL for all
    const mention = option.id === 'ALL' ? '@ALL' : `@${option.name}`
    const newContent = before + mention + ' ' + after

    setContent(newContent)
    setShowMentionPicker(false)
    setMentionFilter('')
    setMentionStartPos(null)

    // Focus back to textarea
    setTimeout(() => {
      if (textareaRef.current) {
        const newPos = before.length + mention.length + 1
        textareaRef.current.focus()
        textareaRef.current.setSelectionRange(newPos, newPos)
      }
    }, 0)
  }

  const handleKeyDown = (e: KeyboardEvent<HTMLTextAreaElement>) => {
    // Handle mention picker navigation
    if (showMentionPicker && filteredOptions.length > 0) {
      if (e.key === 'ArrowDown') {
        e.preventDefault()
        setSelectedIndex((prev) => (prev + 1) % filteredOptions.length)
        return
      }
      if (e.key === 'ArrowUp') {
        e.preventDefault()
        setSelectedIndex((prev) => (prev - 1 + filteredOptions.length) % filteredOptions.length)
        return
      }
      if (e.key === 'Enter' || e.key === 'Tab') {
        e.preventDefault()
        insertMention(filteredOptions[selectedIndex])
        return
      }
      if (e.key === 'Escape') {
        e.preventDefault()
        setShowMentionPicker(false)
        return
      }
    }

    // Send on Enter (without Shift), but not during IME composition
    if (e.key === 'Enter' && !e.shiftKey && !isComposing && !showMentionPicker) {
      e.preventDefault()
      handleSend()
    }
  }

  const handleChange = (e: React.ChangeEvent<HTMLTextAreaElement>) => {
    const newValue = e.target.value
    const cursorPos = e.target.selectionStart

    setContent(newValue)

    // Detect @ trigger for mention picker
    if (cursorPos > 0) {
      const charBefore = newValue[cursorPos - 1]
      const charBeforeThat = cursorPos > 1 ? newValue[cursorPos - 2] : ' '

      // Show picker when @ is typed after a space or at start
      if (charBefore === '@' && (charBeforeThat === ' ' || charBeforeThat === '\n' || cursorPos === 1)) {
        setShowMentionPicker(true)
        setMentionStartPos(cursorPos - 1)
        setMentionFilter('')
        return
      }
    }

    // Update filter if picker is showing
    if (showMentionPicker && mentionStartPos !== null) {
      const textAfterAt = newValue.slice(mentionStartPos + 1, cursorPos)

      // Close picker if space or newline is entered
      if (textAfterAt.includes(' ') || textAfterAt.includes('\n')) {
        setShowMentionPicker(false)
        setMentionStartPos(null)
        return
      }

      setMentionFilter(textAfterAt)
    }
  }

  const handleInput = () => {
    // Auto-resize textarea
    if (textareaRef.current) {
      textareaRef.current.style.height = 'auto'
      textareaRef.current.style.height = `${Math.min(textareaRef.current.scrollHeight, 200)}px`
    }
  }

  return (
    <div className="p-4 border-t bg-card relative">
      {/* Mention Picker Dropdown */}
      {showMentionPicker && filteredOptions.length > 0 && (
        <div
          ref={pickerRef}
          className="absolute bottom-full left-4 mb-2 w-64 bg-popover border rounded-lg shadow-lg overflow-hidden z-50"
        >
          <div className="p-2 border-b bg-muted/50">
            <div className="flex items-center gap-2 text-sm text-muted-foreground">
              <AtSign className="w-4 h-4" />
              <span>メンションを選択</span>
            </div>
          </div>
          <div className="max-h-48 overflow-y-auto">
            {filteredOptions.map((option, index) => (
              <button
                key={option.id}
                onClick={() => insertMention(option)}
                className={`w-full px-3 py-2 text-left flex items-center gap-2 hover:bg-muted transition-colors ${
                  index === selectedIndex ? 'bg-muted' : ''
                }`}
              >
                <div
                  className="w-6 h-6 rounded-full flex items-center justify-center text-xs font-bold text-white"
                  style={{ backgroundColor: option.color || '#6b7280' }}
                >
                  {option.id === 'ALL' ? '全' : option.name[0]}
                </div>
                <span className="font-medium">{option.name}</span>
                {option.id === 'ALL' && (
                  <span className="text-xs text-muted-foreground ml-auto">@ALL</span>
                )}
              </button>
            ))}
          </div>
        </div>
      )}

      <div className="flex items-end gap-2 bg-muted/50 rounded-lg p-2">
        <Textarea
          ref={textareaRef}
          value={content}
          onChange={handleChange}
          onKeyDown={handleKeyDown}
          onInput={handleInput}
          onCompositionStart={() => setIsComposing(true)}
          onCompositionEnd={() => setIsComposing(false)}
          placeholder={placeholder}
          disabled={disabled}
          className="min-h-[40px] max-h-[200px] resize-none border-0 bg-transparent focus-visible:ring-0 focus-visible:ring-offset-0"
          rows={1}
        />
        <Button
          size="icon"
          onClick={handleSend}
          disabled={!content.trim() || disabled}
          className="flex-shrink-0"
        >
          <Send className="h-4 w-4" />
        </Button>
      </div>
      <p className="text-xs text-muted-foreground mt-1 px-1">
        Press Enter to send, Shift+Enter for new line, @ to mention
      </p>
    </div>
  )
}
