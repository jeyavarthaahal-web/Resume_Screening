import { SendHorizonal } from 'lucide-react'
import { useState } from 'react'

export function ChatInput({ onSend, disabled = false }: { onSend: (value: string) => void; disabled?: boolean }) {
  const [value, setValue] = useState('')

  function submit() {
    const next = value.trim()
    if (!next || disabled) return
    onSend(next)
    setValue('')
  }

  return (
    <div className="career-chat-input-wrap">
      <textarea
        value={value}
        onChange={(event) => setValue(event.target.value)}
        onKeyDown={(event) => {
          if (event.key === 'Enter' && !event.shiftKey) {
            event.preventDefault()
            submit()
          }
        }}
        rows={1}
        placeholder="Ask about your resume, skill gaps, or interview prep..."
        disabled={disabled}
      />
      <button type="button" className="button button-dark" onClick={submit} disabled={!value.trim() || disabled}>
        <SendHorizonal size={16} /> Send
      </button>
    </div>
  )
}
