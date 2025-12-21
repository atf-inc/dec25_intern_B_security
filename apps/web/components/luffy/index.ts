// Barrel export for all Luffy chatbot components
// This makes imports cleaner: import { LuffyChatbot, ChatHeader } from "@/components/luffy"

export { LuffyChatbot } from "../luffy-chatbot"
export { ChatHeader, CompactHeader } from "../luffy-header"
export { ChatInput, SuggestedPrompts, defaultPrompts } from "../luffy-input"
export {
    MessageBubble,
    MessageTimestamp,
    TypingIndicator,
    ErrorMessage,
    MessageGroup,
    type Message
} from "../luffy-message"
export {
    QuickActionChips,
    Chip,
    defaultQuickActions,
    extendedQuickActions,
    type QuickActionChip
} from "../luffy-quick-actions"
