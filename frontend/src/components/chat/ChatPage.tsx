import { useEffect, useRef, useState } from 'react'
import {
    BookOpen,
    Bot,
    Camera,
    CheckCircle2,
    FileSpreadsheet,
    FileText,
    Film,
    LoaderCircle,
    MessageSquare,
    Paperclip,
    Plus,
    Send,
    ShieldCheck,
    Sparkles,
    User,
    X,
} from 'lucide-react'

import {
    createChatSessionApi,
    sendChatMessageApi,
    uploadChatAttachmentApi,
    getStoredAccessToken,
    loginApi,
} from '../../api/client'
import type {
    AttachmentType,
    ChatAttachment,
    ChatCitation,
    ChatMessage,
} from '../../chat/types'

function createId() {
    return globalThis.crypto?.randomUUID?.() ??
        `${Date.now()}-${Math.random()}`
}

function detectFileType(file: File): AttachmentType {
    const ext = file.name.slice(file.name.lastIndexOf('.')).toLowerCase()
    if (file.type.startsWith('image/') || /\.(jpe?g|png|webp|bmp|tiff)$/i.test(ext)) {
        return 'image'
    }
    if (file.type.startsWith('video/') || /\.(mp4|mov|avi|webm|mkv)$/i.test(ext)) {
        return 'video'
    }
    if (file.type === 'application/pdf' || ext === '.pdf') {
        return 'pdf'
    }
    if (
        /\.(xlsx|xls|csv)$/i.test(ext) ||
        file.type.includes('spreadsheet') ||
        file.type.includes('excel') ||
        file.type === 'text/csv'
    ) {
        return 'excel'
    }
    return 'doc'
}

function parseCitationInfo(rawTitle: string, rawSource: string, rawExcerpt: string) {
    const combined = `${rawTitle} ${rawSource}`
    const codeMatch = combined.match(/\b(WHP-\d{3}|SHB-\d{2}|Clause\s+[A-Z0-9.]+)\b/i)
    const code = codeMatch ? codeMatch[1].toUpperCase() : 'WHP'

    const pageMatch = rawSource.match(/p(?:age|\.)\s*(\d+)/i) || rawTitle.match(/p(?:age|\.)\s*(\d+)/i)
    const pageStr = pageMatch ? `Page ${pageMatch[1]}` : 'General Standard'

    let clean = rawSource.replace(/\.pdf$/i, '').replace(/·.*$/, '').trim()
    clean = clean.replace(/^[A-Z0-9_-]+[_\s-]+/, '')
    clean = clean.replace(/_/g, ' ')
    if (!clean || clean.length < 3) {
        clean = rawTitle.replace(/^Policy Reference:\s*/i, '').replace(/_/g, ' ')
    }

    return {
        code,
        cleanTitle: clean.length > 55 ? `${clean.slice(0, 52)}...` : clean,
        pageStr,
        excerpt: rawExcerpt
    }
}

function renderInlineFormatting(text: string) {
    if (!text) return null

    // Strip stray bullet asterisks at start or orphan asterisks inside sentences
    const cleanText = text
        .replace(/^\s*([*\-•])\s+/, '')
        .replace(/\s+\*\s+/g, ' — ')

    const tokens = cleanText.split(/(\*\*[^*]+\*\*|\[[A-Z0-9\s,\-.]+\]|\b\d+(?:\.\d+)?\s*(?:m(?:eters?)?|ft|feet|%|cm)\b)/g)

    return tokens.map((token, idx) => {
        if (!token) return null

        // Bold text: **content**
        if (token.startsWith('**') && token.endsWith('**') && token.length >= 4) {
            return (
                <strong key={idx} className="font-bold text-slate-950">
                    {token.slice(2, -2).replace(/\*/g, '')}
                </strong>
            )
        }

        // Citation badge: [WHP-004, Page 2]
        if (token.startsWith('[') && token.endsWith(']') && token.length <= 40) {
            return (
                <span
                    key={idx}
                    className="inline-flex items-center gap-1 px-2 py-0.5 mx-1 rounded-md text-[11px] font-bold bg-blue-100 text-blue-900 border border-blue-300 shadow-2xs"
                >
                    <BookOpen size={10} className="text-blue-700" />
                    {token.slice(1, -1)}
                </span>
            )
        }

        // Metric measurements: e.g. 1.2m, 2.1m, 4ft, 7ft
        if (/^\d+(?:\.\d+)?\s*(?:m(?:eters?)?|ft|feet|%|cm)$/i.test(token.trim())) {
            return (
                <span
                    key={idx}
                    className="inline-flex items-center px-1.5 py-0.5 mx-0.5 rounded text-xs font-extrabold bg-emerald-100 text-emerald-950 border border-emerald-300 shadow-2xs"
                >
                    {token.trim()}
                </span>
            )
        }

        // Clean out any leftover stray asterisks so they never render as raw code symbols
        const prose = token.replace(/\*/g, '')
        return prose
    })
}

function FormattedMessage({ content }: { content: string }) {
    if (!content) return null

    // Remove any demo count noise and normalize malformed headers or inline bullet points
    let text = content
        .replace(/^\s*\d+\s+demo source references.*$/gim, '')
        .trim()

    // 1. Normalize headings even if asterisks are malformed, inline, or unspaced
    const sectionKeywords = [
        'EXECUTIVE SUMMARY',
        'EVIDENCE ANALYSIS',
        'POLICY CITATIONS?',
        'POLICY CITATIONS',
        'RECOMMENDATIONS?',
        'RECOMMENDATION',
        'FINAL DETERMINATION',
        'DETECTION SUMMARY',
        'POLICY VIOLATIONS?',
    ]
    for (const kw of sectionKeywords) {
        const re = new RegExp(`(?:^|\\n|\\.\\s+)(?:\\*{1,3}|#{1,4}\\s*)?(${kw})(?:\\*{1,3}|:)?(?:\\s*[*•\\-]\\s*|\\s{2,}|\\s*\\n|\\s*$)`, 'gi')
        text = text.replace(re, (_, match) => `\n\n### ${match.trim()}\n\n* `)
    }

    // 2. Ensure bullet points (* or • or -) start on clean new lines
    text = text.replace(/\s+([*\-•])\s+/g, '\n\n* ')

    // 3. Ensure table rows are spaced
    text = text.replace(/(\|[^\n]+\|)\s*(###|\*\*)/g, '$1\n\n$2')
    text = text.replace(/(###[^\n]+)\s*(\|)/g, '$1\n\n$2')

    const rawParagraphs = text.split(/\n\s*\n/)

    return (
        <div className="space-y-4 text-sm leading-relaxed text-slate-800">
            {rawParagraphs.map((para, pIdx) => {
                const trimmed = para.trim()
                if (!trimmed) return null

                // Case 1: Executive Heading (### Title, ## Title, or **Header**)
                // Must be a genuine short heading (< 70 chars, no sentence periods, no markdown links)
                const isHeading =
                    (trimmed.startsWith('###') || trimmed.startsWith('##'))
                        ? !trimmed.includes('\n') && trimmed.length < 70 && !trimmed.includes('. ')
                        : (trimmed.startsWith('**') && trimmed.endsWith('**') && !trimmed.slice(2, -2).includes('\n') && trimmed.length < 70 && !trimmed.includes('. '))

                if (isHeading) {
                    const cleanTitle = trimmed
                        .replace(/^#+\s*/, '')
                        .replace(/^\*\*|\*\*$/g, '')
                        .replace(/\*/g, '')
                        .trim()
                    const isCitationSection = /citation|policy|clause/i.test(cleanTitle)

                    return (
                        <div key={pIdx} className="pt-2 pb-1 first:pt-0">
                            <div className="flex items-center gap-2.5">
                                <span className={`flex h-5 w-5 shrink-0 items-center justify-center rounded-md ${isCitationSection ? 'bg-amber-100 text-amber-800' : 'bg-blue-600 text-white'}`}>
                                    {isCitationSection ? <BookOpen size={12} /> : <ShieldCheck size={13} />}
                                </span>
                                <h3 className="text-sm font-bold uppercase tracking-wider text-slate-900">
                                    {cleanTitle}
                                </h3>
                            </div>
                            <div className={`mt-1.5 h-0.5 w-full rounded-full ${isCitationSection ? 'bg-amber-200' : 'bg-blue-200'}`} />
                        </div>
                    )
                }

                // Split paragraph into lines to detect lists or citations
                const lines = trimmed.split('\n')

                // Case 2: Numbered compliance steps (e.g. 1. **Title**: ... 2. ...)
                const isNumberedList = lines.some(l => /^\s*\d+\.\s+/.test(l))
                if (isNumberedList) {
                    return (
                        <div key={pIdx} className="space-y-2.5">
                            {lines.map((line, lIdx) => {
                                const clean = line.trim()
                                if (!clean) return null

                                const numMatch = clean.match(/^(\d+)\.\s+(.*)$/)
                                if (numMatch) {
                                    const [, num, rest] = numMatch
                                    const keyMatch = rest.match(/^\*\*([^*]+)\*\*:?(.*)$/)
                                    if (keyMatch) {
                                        const [, key, val] = keyMatch
                                        return (
                                            <div
                                                key={lIdx}
                                                className="flex items-start gap-3 rounded-xl border border-slate-200/90 bg-slate-50/70 p-3 shadow-2xs hover:bg-slate-50 transition"
                                            >
                                                <span className="flex h-5 w-5 shrink-0 items-center justify-center rounded-full bg-blue-600 text-[11px] font-bold text-white mt-0.5">
                                                    {num}
                                                </span>
                                                <div className="min-w-0 flex-1">
                                                    <span className="font-bold text-slate-950 text-xs uppercase tracking-wide bg-blue-100 text-blue-900 px-2 py-0.5 rounded mr-2">
                                                        {key.trim()}
                                                    </span>
                                                    <span className="text-slate-800 text-xs sm:text-sm leading-relaxed">
                                                        {renderInlineFormatting(val.trim())}
                                                    </span>
                                                </div>
                                            </div>
                                        )
                                    }

                                    return (
                                        <div
                                            key={lIdx}
                                            className="flex items-start gap-3 rounded-xl border border-slate-200/90 bg-slate-50/70 p-3 shadow-2xs"
                                        >
                                            <span className="flex h-5 w-5 shrink-0 items-center justify-center rounded-full bg-blue-600 text-[11px] font-bold text-white mt-0.5">
                                                {num}
                                            </span>
                                            <div className="min-w-0 flex-1 text-slate-800 text-xs sm:text-sm leading-relaxed">
                                                {renderInlineFormatting(rest)}
                                            </div>
                                        </div>
                                    )
                                }

                                const subBullet = clean.replace(/^\s*([*\-•]|\d+\.)\s+/, '')
                                return (
                                    <div key={lIdx} className="ml-8 flex items-start gap-2 text-xs text-slate-600">
                                        <span className="mt-1.5 h-1.5 w-1.5 shrink-0 rounded-full bg-blue-400" />
                                        <span>{renderInlineFormatting(subBullet)}</span>
                                    </div>
                                )
                            })}
                        </div>
                    )
                }

                // Case 3: Paragraph contains bullet items (e.g. policy citations or rules)
                const bulletLines = lines.filter(l => /^\s*([*\-•])\s+/.test(l))
                const introLines = lines.filter(l => !/^\s*([*\-•])\s+/.test(l) && l.trim() !== '')

                if (bulletLines.length > 0) {
                    return (
                        <div key={pIdx} className="space-y-3">
                            {introLines.length > 0 && (
                                <p className="text-slate-700 text-xs sm:text-sm font-medium leading-relaxed">
                                    {renderInlineFormatting(introLines.join(' '))}
                                </p>
                            )}
                            <div className="grid grid-cols-1 gap-2.5">
                                {bulletLines.map((line, bIdx) => {
                                    const clean = line.replace(/^\s*([*\-•])\s+/, '').trim()
                                    if (!clean) return null

                                    const keyMatch = clean.match(/^\*\*([^*]+)\*\*:?(.*)$/)
                                    if (keyMatch) {
                                        const [, key, rest] = keyMatch
                                        const isPolicyCode = /WHP|SHB|Clause/i.test(key)
                                        return (
                                            <div
                                                key={bIdx}
                                                className={`flex items-start gap-3 rounded-xl border p-3.5 shadow-2xs transition ${
                                                    isPolicyCode
                                                        ? 'border-amber-200/90 bg-amber-50/40 hover:bg-amber-50/70'
                                                        : 'border-slate-200/90 bg-slate-50/70 hover:bg-slate-50'
                                                }`}
                                            >
                                                <span className={`mt-0.5 flex h-4 w-4 shrink-0 items-center justify-center rounded-full ${isPolicyCode ? 'bg-amber-500 text-white' : 'bg-blue-600 text-white'}`}>
                                                    {isPolicyCode ? <BookOpen size={9} /> : <CheckCircle2 size={10} />}
                                                </span>
                                                <div className="min-w-0 flex-1">
                                                    <span className={`inline-block font-bold text-xs uppercase tracking-wide px-2 py-0.5 rounded mr-2 ${
                                                        isPolicyCode
                                                            ? 'bg-amber-100 text-amber-900 border border-amber-300'
                                                            : 'bg-blue-100 text-blue-900 border border-blue-200'
                                                    }`}>
                                                        {key.trim()}
                                                    </span>
                                                    <span className="text-slate-800 text-xs sm:text-sm leading-relaxed">
                                                        {renderInlineFormatting(rest.trim())}
                                                    </span>
                                                </div>
                                            </div>
                                        )
                                    }

                                    return (
                                        <div key={bIdx} className="flex items-start gap-2.5 pl-1 text-slate-700 text-xs sm:text-sm">
                                            <span className="mt-1.5 h-1.5 w-1.5 shrink-0 rounded-full bg-blue-500" />
                                            <span className="flex-1">{renderInlineFormatting(clean)}</span>
                                        </div>
                                    )
                                })}
                            </div>
                        </div>
                    )
                }

                // Case 4: Markdown Table
                const isTable = lines.length >= 2 && lines.filter(l => l.trim().startsWith('|') && l.trim().endsWith('|')).length >= 2
                if (isTable) {
                    const tableLines = lines.filter(l => l.trim().startsWith('|') && l.trim().endsWith('|'))
                    const headerLine = tableLines[0]
                    const dataLines = tableLines.slice(1).filter(l => !/^[|\s\-:]+$/.test(l))

                    const parseCells = (row: string) => row.split('|').slice(1, -1).map(c => c.trim())
                    const headers = parseCells(headerLine)

                    return (
                        <div key={pIdx} className="overflow-x-auto rounded-xl border border-slate-200 bg-white shadow-2xs my-2">
                            <table className="w-full text-left text-xs sm:text-sm">
                                <thead className="bg-slate-100 text-slate-800 uppercase tracking-wider font-semibold text-[11px] border-b border-slate-200">
                                    <tr>
                                        {headers.map((h, hIdx) => (
                                            <th key={hIdx} className="px-3.5 py-2.5">
                                                {h}
                                            </th>
                                        ))}
                                    </tr>
                                </thead>
                                <tbody className="divide-y divide-slate-100">
                                    {dataLines.map((row, rIdx) => {
                                        const cells = parseCells(row)
                                        return (
                                            <tr key={rIdx} className="hover:bg-slate-50/60 transition">
                                                {cells.map((cell, cIdx) => {
                                                    const isPass = /yes|compliant|pass/i.test(cell)
                                                    const isFail = /no|violation|fail/i.test(cell)
                                                    return (
                                                        <td key={cIdx} className="px-3.5 py-2.5 text-slate-700">
                                                            {isPass ? (
                                                                <span className="inline-flex items-center gap-1 px-2 py-0.5 rounded-md text-xs font-bold bg-emerald-100 text-emerald-800 border border-emerald-300">
                                                                    <CheckCircle2 size={11} className="text-emerald-600" />
                                                                    {cell.replace(/\*\*/g, '')}
                                                                </span>
                                                            ) : isFail ? (
                                                                <span className="inline-flex items-center gap-1 px-2 py-0.5 rounded-md text-xs font-bold bg-rose-100 text-rose-800 border border-rose-300">
                                                                    <X size={11} className="text-rose-600" />
                                                                    {cell.replace(/\*\*/g, '')}
                                                                </span>
                                                            ) : (
                                                                renderInlineFormatting(cell)
                                                            )}
                                                        </td>
                                                    )
                                                })}
                                            </tr>
                                        )
                                    })}
                                </tbody>
                            </table>
                        </div>
                    )
                }

                // Case 5: Executive takeaway / concluding summary
                const isSummary =
                    trimmed.toLowerCase().startsWith('these clauses') ||
                    trimmed.toLowerCase().startsWith('conclusion:') ||
                    trimmed.toLowerCase().startsWith('summary:') ||
                    trimmed.toLowerCase().startsWith('note:') ||
                    trimmed.toLowerCase().startsWith('key compliance')

                if (isSummary) {
                    return (
                        <div
                            key={pIdx}
                            className="rounded-xl border border-blue-200 bg-gradient-to-r from-blue-50/80 to-indigo-50/60 p-3.5 shadow-2xs"
                        >
                            <div className="flex items-center gap-2 mb-1.5">
                                <CheckCircle2 size={14} className="text-blue-600 shrink-0" />
                                <span className="text-[11px] font-bold uppercase tracking-wider text-blue-900">
                                    Operational Compliance Takeaway
                                </span>
                            </div>
                            <p className="text-xs sm:text-sm font-medium leading-relaxed text-slate-900">
                                {renderInlineFormatting(trimmed)}
                            </p>
                        </div>
                    )
                }

                // Case 5: Standard paragraph
                return (
                    <p key={pIdx} className="text-slate-800 text-xs sm:text-sm leading-relaxed">
                        {renderInlineFormatting(trimmed)}
                    </p>
                )
            })}
        </div>
    )
}

function ChatPage() {
    const [messages, setMessages] = useState<ChatMessage[]>([
        {
            id: createId(),
            role: 'assistant',
            content:
                'Hello! I am your SiteSense Operations Agent. You can ask compliance questions, query warehouse policies, or attach photos, videos, PDFs, and Excel spreadsheets for automated multimodal auditing.',
            createdAt: new Date().toISOString(),
        },
    ])

    const [isLiveConnected, setIsLiveConnected] = useState(true)
    const [input, setInput] = useState('')
    const [attachments, setAttachments] = useState<ChatAttachment[]>([])
    const [activity, setActivity] = useState<string[]>([])
    const [citations, setCitations] = useState<ChatCitation[]>([])
    const [selectedCitation, setSelectedCitation] =
        useState<ChatCitation | null>(null)
    const [isStreaming, setIsStreaming] = useState(false)
    const [attachmentError, setAttachmentError] = useState('')

    const fileInputRef = useRef<HTMLInputElement>(null)
    const cameraInputRef = useRef<HTMLInputElement>(null)
    const bottomRef = useRef<HTMLDivElement>(null)
    const objectUrls = useRef(new Set<string>())
    const backendSessionId = useRef<string | null>(null)

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

    function addFiles(fileList: FileList | null) {
        if (!fileList) return

        setAttachmentError('')

        const files = Array.from(fileList)

        const validFiles = files.filter(file => {
            const ext = file.name.slice(file.name.lastIndexOf('.')).toLowerCase()
            const isAllowed =
                file.type.startsWith('image/') ||
                file.type.startsWith('video/') ||
                file.type === 'application/pdf' ||
                file.type.includes('spreadsheet') ||
                file.type.includes('excel') ||
                file.type === 'text/csv' ||
                /\.(jpe?g|png|webp|bmp|tiff|mp4|mov|avi|webm|mkv|pdf|xlsx|xls|csv)$/i.test(ext)

            if (!isAllowed) {
                setAttachmentError(
                    'Unsupported file format. Please upload photos, videos, PDFs, or Excel sheets (.xlsx, .xls, .csv).'
                )
                return false
            }

            if (file.size > 50 * 1024 * 1024) {
                setAttachmentError('Each file must be 50 MB or smaller.')
                return false
            }

            return true
        })

        const remainingSlots = 4 - attachments.length
        const selectedFiles = validFiles.slice(0, remainingSlots)

        if (validFiles.length > remainingSlots) {
            setAttachmentError('You can attach up to 4 files per message.')
        }

        const newAttachments = selectedFiles.map(file => {
            const previewUrl = URL.createObjectURL(file)
            objectUrls.current.add(previewUrl)
            const type = detectFileType(file)

            return {
                id: createId(),
                name: file.name,
                previewUrl,
                type,
                file,
                size: file.size,
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
            let handledByLiveBackend = false
            let token = getStoredAccessToken()

            // If no token exists, automatically acquire session token from live backend
            if (!token) {
                try {
                    const authRes = await loginApi('admin@sitesense.io', 'SiteSense@2026')
                    token = authRes.token
                } catch {
                    // Backend might be offline
                }
            }

            if (token) {
                try {
                    if (!backendSessionId.current) {
                        setActivity(['Initializing intelligence session...'])
                        const session = await createChatSessionApi('Operations Assistant')
                        backendSessionId.current = session.id
                    }

                    setActivity([
                        'Dispatching query to multimodal intelligence engine...',
                        'Evaluating operational rules & grounding policies...',
                    ])

                    const uploadedAttachmentMetadata: Array<{
                        id?: string
                        name: string
                        type: string
                        size?: number
                        preview_url?: string
                        storage_path?: string
                    }> = []

                    for (const att of sentAttachments) {
                        if (att.file) {
                            try {
                                const uploaded = await uploadChatAttachmentApi(
                                    att.file,
                                    backendSessionId.current || undefined
                                )
                                uploadedAttachmentMetadata.push({
                                    id: uploaded.id,
                                    name: uploaded.name,
                                    type: uploaded.type,
                                    size: uploaded.size,
                                    preview_url: uploaded.download_url,
                                    storage_path: uploaded.path,
                                })
                            } catch {
                                uploadedAttachmentMetadata.push({
                                    name: att.name,
                                    type: att.type || 'doc',
                                    size: att.size,
                                })
                            }
                        } else {
                            uploadedAttachmentMetadata.push({
                                name: att.name,
                                type: att.type || 'doc',
                                size: att.size,
                            })
                        }
                    }

                    const result = await sendChatMessageApi(
                        backendSessionId.current,
                        question || 'Review attached media files',
                        undefined,
                        uploadedAttachmentMetadata,
                    )

                    if (result?.assistant_message) {
                        const rawCitations = result.citations || result.assistant_message.citations || []
                        const seenKeys = new Set<string>()
                        const mappedCitations: ChatCitation[] = []

                        for (const c of rawCitations) {
                            const key = `${c.source_file || ''}-${c.page || ''}-${c.clause || ''}`
                            if (!seenKeys.has(key)) {
                                seenKeys.add(key)
                                mappedCitations.push({
                                    id: `cite-${mappedCitations.length}`,
                                    title: c.clause || c.title || 'Policy Standard',
                                    source: c.source_file ? `${c.source_file}${c.page ? ` · Page ${c.page}` : ''}` : 'Warehouse Safety Policy',
                                    excerpt: c.excerpt || '',
                                })
                            }
                        }

                        setCitations(mappedCitations)
                        setMessages(previous =>
                            previous.map(message =>
                                message.id === assistantId
                                    ? {
                                        ...message,
                                        content: result.assistant_message.content,
                                        citations: mappedCitations,
                                    }
                                    : message,
                            ),
                        )
                        setIsLiveConnected(true)
                        setActivity([
                            `Query routed to: ${result.route || 'policy'}`,
                            `Grounded against ${mappedCitations.length} policy clause(s)`,
                            'ReAct reasoning & citation synthesis complete',
                        ])
                        handledByLiveBackend = true
                    }
                } catch (apiErr) {
                    console.warn('Live chat API call fallback:', apiErr)
                }
            }

            if (!handledByLiveBackend) {
                setMessages(previous =>
                    previous.map(message =>
                        message.id === assistantId
                            ? {
                                ...message,
                                content: 'Unable to reach the live SiteSense Intelligence backend. Please ensure the backend server and PostgreSQL database are running.',
                            }
                            : message,
                    ),
                )
            }
        } catch {
            setMessages(previous =>
                previous.map(message =>
                    message.id === assistantId
                        ? {
                            ...message,
                            content:
                                'The request could not be processed. Please check your backend connection and try again.',
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

        backendSessionId.current = null

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

            {isLiveConnected ? (
                <div className="rounded-xl border border-emerald-200 bg-emerald-50 px-4 py-3 text-sm text-emerald-900 flex items-center justify-between">
                    <div>
                        <strong>Live Agent Connected:</strong> Powered by SiteSense ReAct Engine & Hybrid Retrieval (pgvector Dense + BM25 + Cross-Encoder).
                    </div>
                    <span className="inline-flex items-center gap-1.5 rounded-full bg-emerald-100 px-2.5 py-0.5 text-xs font-semibold text-emerald-800">
                        <span className="h-1.5 w-1.5 rounded-full bg-emerald-600 animate-pulse"></span>
                        Active
                    </span>
                </div>
            ) : (
                <div className="rounded-xl border border-amber-200 bg-amber-50 px-4 py-3 text-sm text-amber-900">
                    <strong>Preview mode:</strong> Responses, tool activity and
                    citations are simulated. Images stay in your browser and are
                    not uploaded or analysed by an AI service.
                </div>
            )}

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
                            Operations Intelligence
                        </div>
                        <p className="mt-2 text-xs leading-5 text-slate-500">
                            Live grounded policy reasoning with verified citations & computer vision evidence.
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
                                    {isLiveConnected ? 'Live Operations Agent' : 'Demo conversation'}
                                </p>
                            </div>
                        </div>

                        {isLiveConnected ? (
                            <span className="rounded-full bg-emerald-50 border border-emerald-200 px-3 py-1 text-xs font-semibold text-emerald-700 flex items-center gap-1.5">
                                <span className="h-1.5 w-1.5 rounded-full bg-emerald-500 animate-pulse"></span>
                                Live ReAct Agent
                            </span>
                        ) : (
                            <span className="rounded-full bg-amber-50 px-3 py-1 text-xs font-semibold text-amber-700">
                                Simulation
                            </span>
                        )}
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
                                    className={`min-w-0 max-w-[88%] rounded-2xl px-5 py-4 ${message.role === 'assistant'
                                        ? 'bg-white border border-slate-200/90 text-slate-800 shadow-xs'
                                        : 'bg-blue-600 text-white shadow-xs'
                                        }`}
                                >
                                    {message.content && (
                                        message.role === 'assistant' ? (
                                            <FormattedMessage content={message.content} />
                                        ) : (
                                            <p className="whitespace-pre-wrap text-sm leading-relaxed">
                                                {message.content}
                                            </p>
                                        )
                                    )}

                                    {message.attachments &&
                                        message.attachments.length > 0 && (
                                            <div className="mt-3 grid grid-cols-2 gap-2 sm:grid-cols-3">
                                                {message.attachments.map(
                                                    attachment => (
                                                        <div
                                                            key={attachment.id}
                                                            className="overflow-hidden rounded-lg border border-white/30 bg-black/20"
                                                        >
                                                            {attachment.type === 'video' ? (
                                                                <div className="relative flex h-28 w-full items-center justify-center bg-slate-900">
                                                                    <video
                                                                        src={attachment.previewUrl}
                                                                        controls
                                                                        className="h-full w-full object-cover"
                                                                    />
                                                                </div>
                                                            ) : attachment.type === 'pdf' ? (
                                                                <div className="flex h-28 w-full flex-col items-center justify-center bg-red-950/40 p-2 text-center">
                                                                    <FileText size={32} className="text-red-400" />
                                                                    <span className="mt-1 text-[11px] font-bold uppercase text-red-300">
                                                                        PDF Document
                                                                    </span>
                                                                </div>
                                                            ) : attachment.type === 'excel' ? (
                                                                <div className="flex h-28 w-full flex-col items-center justify-center bg-emerald-950/40 p-2 text-center">
                                                                    <FileSpreadsheet size={32} className="text-emerald-400" />
                                                                    <span className="mt-1 text-[11px] font-bold uppercase text-emerald-300">
                                                                        Excel Sheet
                                                                    </span>
                                                                </div>
                                                            ) : (
                                                                <img
                                                                    src={attachment.previewUrl}
                                                                    alt={attachment.name}
                                                                    className="h-28 w-full object-cover"
                                                                />
                                                            )}
                                                            <p className="truncate bg-black/40 px-2 py-1 text-xs text-white" title={attachment.name}>
                                                                {attachment.name}
                                                            </p>
                                                        </div>
                                                    ),
                                                )}
                                            </div>
                                        )}

                                    {message.citations && message.citations.length > 0 && (
                                        <div className="mt-4 pt-3.5 border-t border-slate-200">
                                            <div className="flex items-center justify-between mb-2">
                                                <div className="flex items-center gap-1.5 text-xs font-bold uppercase tracking-wider text-slate-500">
                                                    <FileText size={13} className="text-blue-600" />
                                                    Grounded Knowledge Citations ({message.citations.length})
                                                </div>
                                                <span className="text-[10px] font-semibold text-emerald-700 bg-emerald-50 border border-emerald-200 px-2 py-0.5 rounded-full">
                                                    Verified Policy
                                                </span>
                                            </div>
                                            <div className="flex flex-wrap gap-2">
                                                {message.citations.map((c) => {
                                                    const info = parseCitationInfo(c.title, c.source, c.excerpt)
                                                    return (
                                                        <button
                                                            key={c.id}
                                                            type="button"
                                                            onClick={() => setSelectedCitation(c)}
                                                            className="group inline-flex items-center gap-2 rounded-xl border border-blue-200 bg-slate-50/70 hover:bg-blue-50 px-3 py-1.5 text-xs text-slate-800 shadow-xs hover:border-blue-300 transition cursor-pointer text-left"
                                                            title="Click to view policy excerpt in side panel"
                                                        >
                                                            <span className="rounded-md bg-blue-600 px-1.5 py-0.5 text-[10px] font-bold text-white tracking-wide">
                                                                {info.code}
                                                            </span>
                                                            <span className="font-semibold text-slate-800 group-hover:text-blue-900">
                                                                {info.cleanTitle}
                                                            </span>
                                                            <span className="text-[11px] font-semibold text-blue-600">
                                                                · {info.pageStr}
                                                            </span>
                                                        </button>
                                                    )
                                                })}
                                            </div>
                                        </div>
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
                                        className="relative h-20 w-24 overflow-hidden rounded-xl border border-slate-200 bg-slate-100 shadow-sm"
                                    >
                                        {attachment.type === 'video' ? (
                                            <div className="relative flex h-full w-full items-center justify-center bg-slate-900">
                                                <video
                                                    src={attachment.previewUrl}
                                                    className="h-full w-full object-cover opacity-75"
                                                    muted
                                                />
                                                <span className="absolute bottom-1 left-1 flex items-center gap-0.5 rounded bg-black/75 px-1 py-0.5 text-[9px] font-semibold text-white">
                                                    <Film size={10} /> Video
                                                </span>
                                            </div>
                                        ) : attachment.type === 'pdf' ? (
                                            <div className="flex h-full w-full flex-col items-center justify-center bg-red-50 p-1 text-center">
                                                <FileText size={22} className="text-red-500" />
                                                <span className="text-[9px] font-bold uppercase text-red-600">PDF</span>
                                                <p className="w-full truncate text-[9px] text-slate-700">{attachment.name}</p>
                                            </div>
                                        ) : attachment.type === 'excel' ? (
                                            <div className="flex h-full w-full flex-col items-center justify-center bg-emerald-50 p-1 text-center">
                                                <FileSpreadsheet size={22} className="text-emerald-600" />
                                                <span className="text-[9px] font-bold uppercase text-emerald-700">Excel</span>
                                                <p className="w-full truncate text-[9px] text-slate-700">{attachment.name}</p>
                                            </div>
                                        ) : (
                                            <img
                                                src={attachment.previewUrl}
                                                alt={attachment.name}
                                                className="h-full w-full object-cover"
                                            />
                                        )}
                                        <button
                                            type="button"
                                            onClick={() =>
                                                removeAttachment(attachment.id)
                                            }
                                            aria-label={`Remove ${attachment.name}`}
                                            className="absolute right-1 top-1 rounded-full bg-slate-900/80 p-1 text-white hover:bg-slate-900 transition"
                                        >
                                            <X size={12} />
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
                                    ref={fileInputRef}
                                    type="file"
                                    accept="image/*,video/*,application/pdf,.xlsx,.xls,.csv,application/vnd.openxmlformats-officedocument.spreadsheetml.sheet,application/vnd.ms-excel,text/csv"
                                    multiple
                                    className="hidden"
                                    aria-label="Choose chat files (photo, video, PDF, Excel)"
                                    onChange={event => {
                                        addFiles(event.target.files)
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
                                        addFiles(event.target.files)
                                        event.currentTarget.value = ''
                                    }}
                                />

                                <button
                                    type="button"
                                    onClick={() => fileInputRef.current?.click()}
                                    disabled={isStreaming || attachments.length >= 4}
                                    className="inline-flex items-center gap-2 rounded-lg border border-slate-200 bg-white px-3 py-2 text-xs font-semibold text-slate-700 shadow-sm transition hover:bg-slate-50 disabled:opacity-50"
                                    title="Attach photos, videos, PDFs, or Excel spreadsheets at a time"
                                >
                                    <Paperclip size={16} className="text-blue-600" />
                                    Add Media / File (Photo, Video, PDF, Excel)
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
                            Attach up to 4 files at a time (photos, videos, PDFs, Excel sheets) · Up to 50 MB each
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

                    <section className="rounded-2xl border border-slate-200 bg-white p-4 shadow-xs">
                        <div className="flex items-center justify-between">
                            <div className="flex items-center gap-2">
                                <FileText size={17} className="text-blue-600" />
                                <h3 className="text-sm font-semibold text-slate-900">
                                    Source Citations
                                </h3>
                            </div>
                            {citations.length > 0 && (
                                <span className="rounded-full bg-blue-100 text-blue-800 px-2.5 py-0.5 text-[11px] font-bold">
                                    {citations.length}
                                </span>
                            )}
                        </div>

                        {citations.length === 0 ? (
                            <p className="mt-4 text-xs leading-5 text-slate-400">
                                Grounded policy references will appear here after a query is processed.
                            </p>
                        ) : (
                            <div className="mt-4 space-y-3">
                                {citations.map(citation => {
                                    const info = parseCitationInfo(citation.title, citation.source, citation.excerpt)
                                    const isSelected = selectedCitation?.id === citation.id
                                    return (
                                        <div
                                            key={citation.id}
                                            onClick={() => setSelectedCitation(citation)}
                                            className={`w-full rounded-xl border p-3.5 text-left transition cursor-pointer shadow-xs ${
                                                isSelected
                                                    ? 'border-blue-500 bg-blue-50/80 ring-2 ring-blue-100'
                                                    : 'border-slate-200 bg-white hover:border-blue-300 hover:bg-slate-50/90'
                                            }`}
                                        >
                                            <div className="flex items-center justify-between gap-1.5 mb-1.5">
                                                <span className="rounded-md bg-blue-100 text-blue-900 text-[10px] font-bold px-2 py-0.5 uppercase tracking-wide">
                                                    {info.code}
                                                </span>
                                                <span className="text-[11px] font-semibold text-slate-500">
                                                    {info.pageStr}
                                                </span>
                                            </div>
                                            <h4 className="text-xs font-bold text-slate-900 leading-snug">
                                                {info.cleanTitle}
                                            </h4>
                                            {info.excerpt && (
                                                <div className="mt-2 text-[11px] leading-relaxed text-slate-600 bg-slate-50 rounded-lg p-2.5 border border-slate-100">
                                                    <p className="line-clamp-3 italic text-slate-700">
                                                        "{info.excerpt}"
                                                    </p>
                                                </div>
                                            )}
                                        </div>
                                    )
                                })}
                            </div>
                        )}
                    </section>

                    {selectedCitation && (
                        <section className="rounded-2xl border border-blue-300 bg-blue-50/70 p-4 shadow-sm">
                            <div className="flex items-start justify-between gap-2">
                                <div>
                                    <span className="text-[10px] font-bold uppercase tracking-wider text-emerald-700 bg-emerald-100 border border-emerald-200 px-2 py-0.5 rounded-full">
                                        Verified Policy Clause
                                    </span>
                                    <h3 className="mt-2 text-sm font-bold text-blue-950">
                                        {selectedCitation.title}
                                    </h3>
                                </div>
                                <button
                                    type="button"
                                    aria-label="Close citation details"
                                    onClick={() => setSelectedCitation(null)}
                                    className="rounded-lg p-1 text-slate-500 hover:bg-blue-100 hover:text-slate-700 cursor-pointer"
                                >
                                    <X size={16} />
                                </button>
                            </div>

                            <p className="mt-2 text-xs font-semibold text-blue-800">
                                {selectedCitation.source}
                            </p>
                            <div className="mt-3 text-xs leading-relaxed text-slate-800 bg-white p-3 rounded-xl border border-blue-200/80 shadow-xs">
                                <p className="italic">
                                    "{selectedCitation.excerpt}"
                                </p>
                            </div>
                            <p className="mt-2.5 text-[10px] font-bold uppercase tracking-wider text-blue-700 text-right">
                                Neon DB Knowledge Base Grounded
                            </p>
                        </section>
                    )}
                </aside>
            </div>
        </div>
    )
}

export default ChatPage