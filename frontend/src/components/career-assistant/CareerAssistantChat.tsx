import { LoaderCircle, Sparkles } from 'lucide-react'
import { useEffect, useRef, useState } from 'react'
import { ChatInput } from './ChatInput'
import { ChatMessage } from './ChatMessage'
import { sendAssistantMessage } from '../../services/careerAssistantService'

export type ChatMessageItem = {
  id: string
  role: 'user' | 'assistant'
  content: string
}

export function CareerAssistantChat() {
  const containerRef = useRef<HTMLDivElement | null>(null)
  const [messages, setMessages] = useState<ChatMessageItem[]>([
    {
      id: 'welcome-1',
      role: 'assistant',
      content: "Hi! I'm your TalentIQ Career Assistant.\n\nI can help you improve your resume, understand skill gaps, prepare for interviews, and plan your next career steps.\n\nWhat would you like to work on?",
    },
  ])
  const [loading, setLoading] = useState(false)
  const [error, setError] = useState<string | null>(null)

  useEffect(() => {
    containerRef.current?.scrollTo({ top: containerRef.current.scrollHeight, behavior: 'smooth' })
  }, [messages, loading])

  async function handleSend(message: string) {
    if (!message.trim()) return
    const userMessage = { id: crypto.randomUUID(), role: 'user' as const, content: message }
    setMessages((current) => [...current, userMessage])
    setLoading(true)
    setError(null)
    try {
      const result = await sendAssistantMessage({ message, session_type: 'chat' })
      setMessages((current) => [...current, { id: result.message_id, role: 'assistant', content: result.response }])
    } catch (sendError) {
      setError(sendError instanceof Error ? sendError.message : 'We could not send your message.')
    } finally {
      setLoading(false)
    }
  }

  return (
    <div className="career-chat-panel">
      <div className="career-chat-header">
        <div>
          <span className="resume-kicker">AI CHAT</span>
          <h3>Career coach</h3>
        </div>
        <div className="career-chat-status"><Sparkles size={14} /> Live guidance</div>
      </div>

      <div className="career-chat-messages" ref={containerRef}>
        {messages.length === 0 ? (
          <div className="career-empty-state">No messages yet.</div>
        ) : (
          messages.map((message) => <ChatMessage key={message.id} role={message.role} content={message.content} />)
        )}
        {loading && (
          <div className="career-chat-loading">
            <LoaderCircle size={16} className="career-spin" />
            Thinking…
          </div>
        )}
        {error && <div className="career-error-box">{error}</div>}
      </div>

      <ChatInput onSend={handleSend} disabled={loading} />
    </div>
  )
}
