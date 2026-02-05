import { useState, useRef, KeyboardEvent } from 'react'
import { Send } from 'lucide-react'
import { Button } from '../ui/button'
import { Textarea } from '../ui/textarea'

interface MessageInputProps {
  onSend: (content: string) => void
  placeholder?: string
  disabled?: boolean
}

export function MessageInput({
  onSend,
  placeholder = 'Send a moderator message...',
  disabled = false,
}: MessageInputProps) {
  const [content, setContent] = useState('')
  const [isComposing, setIsComposing] = useState(false)
  const textareaRef = useRef<HTMLTextAreaElement>(null)

  const handleSend = () => {
    const trimmed = content.trim()
    if (trimmed && !disabled) {
      onSend(trimmed)
      setContent('')
      // Reset textarea height
      if (textareaRef.current) {
        textareaRef.current.style.height = 'auto'
      }
    }
  }

  const handleKeyDown = (e: KeyboardEvent<HTMLTextAreaElement>) => {
    // Send on Enter (without Shift), but not during IME composition
    if (e.key === 'Enter' && !e.shiftKey && !isComposing) {
      e.preventDefault()
      handleSend()
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
    <div className="p-4 border-t bg-card">
      <div className="flex items-end gap-2 bg-muted/50 rounded-lg p-2">
        <Textarea
          ref={textareaRef}
          value={content}
          onChange={(e) => setContent(e.target.value)}
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
        Press Enter to send, Shift+Enter for new line
      </p>
    </div>
  )
}
