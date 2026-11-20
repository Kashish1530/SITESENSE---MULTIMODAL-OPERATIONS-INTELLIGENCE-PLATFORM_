import { useEffect, useRef, useState } from 'react'
import {
    Bot,
    Camera,
    FileText,
    ImagePlus,
    LoaderCircle,
    MessageSquare,
    Plus,
    Send,
    Sparkles,
    User,
    X,
} from 'lucide-react'

import { streamMockResponse } from '../../chat/mockChatAdapter'
import type {
    ChatAttachment,
    ChatCitation,
    ChatMessage,
} from '../../chat/types'

function createId() {
    return globalThis.crypto?.randomUUID?.() ??
        `${Date.now()}-${Math.random()}`
}

function ChatPage() {
    const [messages, setMessages] = useState<ChatMessage[]>([
        {
            id: createId(),
            role: 'assistant',
            content:
                'Hello! I am your SiteSense Intelligence Assistant preview. You can ask a question or attach a photo to explore the interface. AI analysis is simulated in this demo.',
            createdAt: new Date().toISOString(),
        },
    ])

    const [input, setInput] = useState('')
    const [attachments, setAttachments] = useState<ChatAttachment[]>([])
    const [activity, setActivity] = useState<string[]>([])
    const [citations, setCitations] = useState<ChatCitation[]>([])
    const [selectedCitation, setSelectedCitation] =
        useState<ChatCitation | null>(null)
    const [isStreaming, setIsStreaming] = useState(false)
    const [attachmentError, setAttachmentError] = useState('')

    const imageInputRef = useRef<HTMLInputElement>(null)
    const cameraInputRef = useRef<HTMLInputElement>(null)
    const bottomRef = useRef<HTMLDivElement>(null)
    const objectUrls = useRef(new Set<string>())

    useEffect(() => {
        bottomRef.current?.scrollIntoView({ behavior: 'smooth' })
    }, [messages])

    useEffect(() => {
        const urls = objectUrls.current

        return () => {
            urls.forEach(url => URL.revokeObjectURL(url))
            urls.clear()
        }
    }, [])

    function addImages(fileList: FileList | null) {
        if (!fileList) return

        setAttachmentError('')

        const files = Array.from(fileList)

        const validFiles = files.filter(file => {
            if (!file.type.startsWith('image/')) {
                setAttachmentError('Only image files are supported.')
                return false
            }

            if (file.size > 10 * 1024 * 1024) {
                setAttachmentError('Each image must be 10 MB or smaller.')
                return false
            }

            return true
        })

        const remainingSlots = 4 - attachments.length
        const selectedFiles = validFiles.slice(0, remainingSlots)

        if (validFiles.length > remainingSlots) {
            setAttachmentError('You can attach up to 4 images per message.')
        }

        const newAttachments = selectedFiles.map(file => {
            const previewUrl = URL.createObjectURL(file)
            objectUrls.current.add(previewUrl)

            return {
                id: createId(),
                name: file.name,
                previewUrl,
            }
        })

        setAttachments(previous => [...previous, ...newAttachments])
    }

    function removeAttachment(id: string) {
        setAttachments(previous => {
            const removed = previous.find(item => item.id === id)

            if (removed) {
                URL.revokeObjectURL(removed.previewUrl)
                objectUrls.current.delete(removed.previewUrl)
            }

            return previous.filter(item => item.id !== id)
        })
    }

    async function sendMessage() {
        const question = input.trim()

        if ((!question && attachments.length === 0) || isStreaming) {
            return
        }

        const sentAttachments = [...attachments]
        const hasImages = sentAttachments.length > 0

        const userMessage: ChatMessage = {
            id: createId(),
            role: 'user',
            content: question,
            createdAt: new Date().toISOString(),
            attachments: sentAttachments,
        }

        const assistantId = createId()

        const assistantMessage: ChatMessage = {
            id: assistantId,
            role: 'assistant',
            content: '',
            createdAt: new Date().toISOString(),
        }

        setMessages(previous => [
            ...previous,
            userMessage,
            assistantMessage,
        ])

        setInput('')
        setAttachments([])
        setAttachmentError('')
        setActivity([])
        setCitations([])
        setSelectedCitation(null)
        setIsStreaming(true)

        try {
            for await (const event of streamMockResponse(
                question || 'Please review the attached image.',
                hasImages,
            )) {
                if (event.type === 'tool') {
                    setActivity(previous => [
                        ...previous,
                        event.label,
                    ])
                }

                if (event.type === 'token') {
                    setMessages(previous =>
                        previous.map(message =>
                            message.id === assistantId
                                ? {
                                    ...message,
                                    content: message.content + event.text,
                                }
                                : message,
                        ),
                    )
                }

                if (event.type === 'citations') {
                    setCitations(event.citations)

                    setMessages(previous =>
                        previous.map(message =>
                            message.id === assistantId
                                ? {
                                    ...message,
                                    citations: event.citations,
                                }
                                : message,
                        ),
                    )
                }
            }
        } catch {
            setMessages(previous =>
                previous.map(message =>
                    message.id === assistantId
                        ? {
                            ...message,
                            content:
                                'The simulated response failed. Please try again.',
                        }
                        : message,
                ),
            )
        } finally {
            setIsStreaming(false)
        }
    }

    function startNewChat() {
        if (isStreaming) return

        setMessages([
            {
                id: createId(),
                role: 'assistant',
                content:
                    'New conversation started. What would you like help with?',
                createdAt: new Date().toISOString(),
            },
        ])

        setActivity([])
        setCitations([])
        setSelectedCitation(null)
        setInput('')
        setAttachments([])
        setAttachmentError('')
    }

    return (
        <div className="space-y-5">
            <div>
                <p className="text-sm font-medium text-blue-600">
                    SiteSense Workspace
                </p>
                <h1 className="mt-1 text-2xl font-bold text-slate-900">
                    Intelligence Chat
                </h1>
                <p className="mt-2 text-sm text-slate-500">
                    Ask questions and explore inspection evidence with the
                    Intelligence Assistant.
                </p>
            </div>

            <div className="rounded-xl border border-amber-200 bg-amber-50 px-4 py-3 text-sm text-amber-900">
                <strong>Preview mode:</strong> Responses, tool activity and
                citations are simulated. Images stay in your browser and are
                not uploaded or analysed by an AI service.
            </div>

            <div className="grid min-h-[650px] grid-cols-1 gap-4 xl:grid-cols-[210px_minmax(0,1fr)_260px]">
                {/* Conversation sidebar */}
                <aside className="rounded-2xl border border-slate-200 bg-white p-4">
                    <button
                        type="button"
                        onClick={startNewChat}
                        disabled={isStreaming}
                        className="flex w-full items-center justify-center gap-2 rounded-xl bg-blue-600 px-3 py-3 text-sm font-semibold text-white transition hover:bg-blue-700 disabled:opacity-50"
                    >
                        <Plus size={17} />
                        New conversation
                    </button>

                    <div className="mt-6">
                        <p className="mb-3 text-xs font-semibold uppercase tracking-wider text-slate-400">
                            Workspace
                        </p>

                        <div className="flex items-center gap-2 rounded-lg bg-blue-50 px-3 py-3 text-sm font-medium text-blue-700">
                            <MessageSquare size={17} />
                            Current conversation
                        </div>
                    </div>

                    <div className="mt-8 rounded-xl bg-slate-50 p-3">
                        <div className="flex items-center gap-2 text-sm font-semibold text-slate-700">
                            <Sparkles size={16} className="text-blue-500" />
                            Assistant preview
                        </div>
                        <p className="mt-2 text-xs leading-5 text-slate-500">
                            Explore the chat experience using simulated
                            responses.
                        </p>
                    </div>
                </aside>

                {/* Main chat */}
                <section className="flex min-h-[650px] min-w-0 flex-col overflow-hidden rounded-2xl border border-slate-200 bg-white shadow-sm">
                    <div className="flex items-center justify-between border-b border-slate-100 px-5 py-4">
                        <div className="flex items-center gap-3">
                            <div className="flex h-10 w-10 items-center justify-center rounded-xl bg-blue-50 text-blue-600">
                                <Bot size={22} />
                            </div>
                            <div>
                                <h2 className="text-sm font-semibold text-slate-900">
                                    SiteSense Assistant
                                </h2>
                                <p className="text-xs text-slate-500">
                                    Demo conversation
                                </p>
                            </div>
                        </div>

                        <span className="rounded-full bg-amber-50 px-3 py-1 text-xs font-semibold text-amber-700">
                            Simulation
                        </span>
                    </div>

                    <div className="flex-1 space-y-6 overflow-y-auto p-4 sm:p-6">
                        {messages.map(message => (
                            <div
                                key={message.id}
                                className={`flex gap-3 ${message.role === 'user'
                                    ? 'flex-row-reverse'
                                    : ''
                                    }`}
                            >
                                <div
                                    className={`flex h-9 w-9 shrink-0 items-center justify-center rounded-xl ${message.role === 'assistant'
                                        ? 'bg-blue-50 text-blue-600'
                                        : 'bg-slate-100 text-slate-600'
                                        }`}
                                >
                                    {message.role === 'assistant'
                                        ? <Bot size={18} />
                                        : <User size={18} />}
                                </div>

                                <div
                                    className={`min-w-0 max-w-[85%] rounded-2xl px-4 py-3 ${message.role === 'assistant'
                                        ? 'bg-slate-50 text-slate-800'
                                        : 'bg-blue-600 text-white'
                                        }`}
                                >
                                    {message.content && (
                                        <p className="whitespace-pre-wrap text-sm leading-7">
                                            {message.content}
                                        </p>
                                    )}

                                    {message.attachments &&
                                        message.attachments.length > 0 && (
                                            <div className="mt-3 grid grid-cols-2 gap-2 sm:grid-cols-3">
                                                {message.attachments.map(
                                                    attachment => (
                                                        <div
                                                            key={attachment.id}
                                                            className="overflow-hidden rounded-lg border border-white/30"
                                                        >
                                                            <img
                                                                src={attachment.previewUrl}
                                                                alt={attachment.name}
                                                                className="h-28 w-full object-cover"
                                                            />
                                                            <p className="truncate bg-black/10 px-2 py-1 text-xs">
                                                                {attachment.name}
                                                            </p>
                                                        </div>
                                                    ),
                                                )}
                                            </div>
                                        )}

                                    {message.citations &&
                                        message.citations.length > 0 && (
                                            <p className="mt-3 text-xs text-slate-500">
                                                {message.citations.length} demo
                                                source references provided
                                            </p>
                                        )}
                                </div>
                            </div>
                        ))}

                        {isStreaming && (
                            <div className="flex items-center gap-2 text-sm text-blue-600">
                                <LoaderCircle
                                    size={17}
                                    className="animate-spin"
                                />
                                Assistant is generating a simulated response…
                            </div>
                        )}

                        <div ref={bottomRef} />
                    </div>

                    {/* Composer */}
                    <div className="border-t border-slate-100 p-4 sm:p-5">
                        {attachments.length > 0 && (
                            <div className="mb-3 flex flex-wrap gap-3">
                                {attachments.map(attachment => (
                                    <div
                                        key={attachment.id}
                                        className="relative h-20 w-20 overflow-hidden rounded-xl border border-slate-200"
                                    >
                                        <img
                                            src={attachment.previewUrl}
                                            alt={attachment.name}
                                            className="h-full w-full object-cover"
                                        />
                                        <button
                                            type="button"
                                            onClick={() =>
                                                removeAttachment(attachment.id)
                                            }
                                            aria-label={`Remove ${attachment.name}`}
                                            className="absolute right-1 top-1 rounded-full bg-slate-900/80 p-1 text-white hover:bg-slate-900"
                                        >
                                            <X size={13} />
                                        </button>
                                    </div>
                                ))}
                            </div>
                        )}

                        {attachmentError && (
                            <p role="alert" className="mb-2 text-xs text-red-600">
                                {attachmentError}
                            </p>
                        )}

                        <textarea
                            value={input}
                            onChange={event => setInput(event.target.value)}
                            onKeyDown={event => {
                                if (
                                    event.key === 'Enter' &&
                                    !event.shiftKey
                                ) {
                                    event.preventDefault()
                                    void sendMessage()
                                }
                            }}
                            placeholder="Ask about an inspection, safety issue or procedure…"
                            rows={3}
                            disabled={isStreaming}
                            className="w-full resize-none rounded-xl border border-slate-200 bg-slate-50 px-4 py-3 text-sm text-slate-800 outline-none transition placeholder:text-slate-400 focus:border-blue-400 focus:ring-2 focus:ring-blue-100 disabled:opacity-60"
                        />

                        <div className="mt-3 flex flex-wrap items-center justify-between gap-3">
                            <div className="flex flex-wrap gap-2">
                                <input
                                    ref={imageInputRef}
                                    type="file"
                                    accept="image/*"
                                    multiple
                                    className="hidden"
                                    aria-label="Choose chat photos"
                                    onChange={event => {
                                        addImages(event.target.files)
                                        event.currentTarget.value = ''
                                    }}
                                />

                                <input
                                    ref={cameraInputRef}
                                    type="file"
                                    accept="image/*"
                                    capture="environment"
                                    className="hidden"
                                    aria-label="Capture chat photo"
                                    onChange={event => {
                                        addImages(event.target.files)
                                        event.currentTarget.value = ''
                                    }}
                                />

                                <button
                                    type="button"
                                    onClick={() => imageInputRef.current?.click()}
                                    disabled={isStreaming || attachments.length >= 4}
                                    className="inline-flex items-center gap-2 rounded-lg border border-slate-200 px-3 py-2 text-xs font-semibold text-slate-600 transition hover:bg-slate-50 disabled:opacity-50"
                                >
                                    <ImagePlus size={16} />
                                    Add Photo
                                </button>

                                <button
                                    type="button"
                                    onClick={() => cameraInputRef.current?.click()}
                                    disabled={isStreaming || attachments.length >= 4}
                                    className="inline-flex items-center gap-2 rounded-lg border border-slate-200 px-3 py-2 text-xs font-semibold text-slate-600 transition hover:bg-slate-50 disabled:opacity-50"
                                >
                                    <Camera size={16} />
                                    Camera
                                </button>
                            </div>

                            <button
                                type="button"
                                onClick={() => void sendMessage()}
                                disabled={
                                    isStreaming ||
                                    (!input.trim() && attachments.length === 0)
                                }
                                className="inline-flex items-center gap-2 rounded-xl bg-blue-600 px-5 py-2.5 text-sm font-semibold text-white transition hover:bg-blue-700 disabled:cursor-not-allowed disabled:opacity-50"
                            >
                                <Send size={16} />
                                Send
                            </button>
                        </div>

                        <p className="mt-3 text-center text-[11px] text-slate-400">
                            Up to 4 images · 10 MB each · Images remain in this
                            browser preview
                        </p>
                    </div>
                </section>

                {/* Context panel */}
                <aside className="space-y-4">
                    <section className="rounded-2xl border border-slate-200 bg-white p-4">
                        <div className="flex items-center gap-2">
                            <Sparkles size={17} className="text-blue-600" />
                            <h3 className="text-sm font-semibold text-slate-800">
                                Tool activity
                            </h3>
                        </div>

                        {activity.length === 0 ? (
                            <p className="mt-4 text-xs leading-5 text-slate-400">
                                Tool activity will appear here when you send a
                                message.
                            </p>
                        ) : (
                            <div className="mt-4 space-y-3">
                                {activity.map((item, index) => (
                                    <div
                                        key={`${item}-${index}`}
                                        className="flex gap-2 text-xs leading-5 text-slate-600"
                                    >
                                        <span className="mt-1 h-2 w-2 shrink-0 rounded-full bg-green-500" />
                                        {item}
                                    </div>
                                ))}
                            </div>
                        )}
                    </section>

                    <section className="rounded-2xl border border-slate-200 bg-white p-4">
                        <div className="flex items-center gap-2">
                            <FileText size={17} className="text-blue-600" />
                            <h3 className="text-sm font-semibold text-slate-800">
                                Source citations
                            </h3>
                        </div>

                        {citations.length === 0 ? (
                            <p className="mt-4 text-xs leading-5 text-slate-400">
                                Demo source references will appear here after a
                                response.
                            </p>
                        ) : (
                            <div className="mt-4 space-y-3">
                                {citations.map(citation => (
                                    <button
                                        key={citation.id}
                                        type="button"
                                        onClick={() =>
                                            setSelectedCitation(citation)
                                        }
                                        className="w-full rounded-xl border border-slate-100 p-3 text-left transition hover:border-blue-200 hover:bg-blue-50"
                                    >
                                        <p className="text-xs font-semibold text-slate-800">
                                            {citation.title}
                                        </p>
                                        <p className="mt-1 text-[11px] text-slate-500">
                                            {citation.source}
                                        </p>
                                    </button>
                                ))}
                            </div>
                        )}
                    </section>

                    {selectedCitation && (
                        <section className="rounded-2xl border border-blue-200 bg-blue-50 p-4">
                            <div className="flex items-start justify-between gap-2">
                                <h3 className="text-sm font-semibold text-blue-900">
                                    {selectedCitation.title}
                                </h3>
                                <button
                                    type="button"
                                    aria-label="Close citation details"
                                    onClick={() => setSelectedCitation(null)}
                                    className="rounded p-1 text-blue-700 hover:bg-blue-100"
                                >
                                    <X size={15} />
                                </button>
                            </div>

                            <p className="mt-2 text-xs text-blue-700">
                                {selectedCitation.source}
                            </p>
                            <p className="mt-3 text-xs leading-5 text-blue-900">
                                {selectedCitation.excerpt}
                            </p>
                            <p className="mt-3 text-[10px] font-semibold uppercase tracking-wide text-blue-600">
                                Demonstration reference only
                            </p>
                        </section>
                    )}
                </aside>
            </div>
        </div>
    )
}

export default ChatPage