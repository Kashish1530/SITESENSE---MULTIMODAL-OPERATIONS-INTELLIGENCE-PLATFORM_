export type ChatRole = 'user' | 'assistant'

export type AttachmentType = 'image' | 'video' | 'pdf' | 'excel' | 'doc'

export type ChatAttachment = {
    id: string
    name: string
    previewUrl: string
    type?: AttachmentType
    file?: File
    size?: number
    storagePath?: string
}

export type ChatCitation = {
    id: string
    title: string
    source: string
    excerpt: string
}

export type ChatMessage = {
    id: string
    role: ChatRole
    content: string
    createdAt: string
    attachments?: ChatAttachment[]
    citations?: ChatCitation[]
}

export type MockChatEvent =
    | { type: 'tool'; label: string }
    | { type: 'token'; text: string }
    | { type: 'citations'; citations: ChatCitation[] }
    | { type: 'done' }