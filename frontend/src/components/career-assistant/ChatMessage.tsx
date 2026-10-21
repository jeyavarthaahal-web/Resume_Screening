import { Bot, User } from 'lucide-react'

export function ChatMessage({ role, content }: { role: 'user' | 'assistant'; content: string }) {
  const isUser = role === 'user'

  return (
    <div className={isUser ? 'career-chat-message user' : 'career-chat-message assistant'}>
      <div className="career-chat-avatar">{isUser ? <User size={15} /> : <Bot size={15} />}</div>
      <div className="career-chat-bubble">
        {content}
      </div>
    </div>
  )
}
