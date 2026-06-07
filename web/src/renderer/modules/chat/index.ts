/** 聊天模块导出 */

// 组件
export { ChatContent } from './components/chat-panel'
export { MessageBubble } from './components/message-bubble'
export { MessageList, SimpleMessageList } from './components/message-list'
export { MessageInput } from './components/message-input'
export { ThinkingIndicator } from './components/thinking-indicator'
export { FeedbackButtons } from './components/feedback-buttons'
export { ReasoningDepthSwitch } from './components/reasoning-depth'
export { QuickAnswerBadge } from './components/quick-answer-badge'

// Hooks
export { useChat } from './hooks/use-chat'
export { useAutoScroll } from './hooks/use-auto-scroll'

// Services
export { chat, chatStream, submitFeedback } from './services/chat-api'

// Types
export type {
  ChatMessage,
  Conversation,
  MessageRole,
  ReasoningDepth,
  FeedbackType,
  FeedbackReason,
  FeedbackData,
  IntentRoute,
  MessageMetadata,
  ChatRequest,
  ChatResponse,
  StreamToken,
  FeedbackRequest,
  FeedbackResponse,
  WSEventType,
  WSEvent,
} from './types/chat'
