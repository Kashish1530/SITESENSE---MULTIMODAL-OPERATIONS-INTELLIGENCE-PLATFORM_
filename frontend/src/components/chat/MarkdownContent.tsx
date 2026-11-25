import React from 'react'

function renderInline(text: string): React.ReactNode[] {
    const parts = text.split(/(\*\*[^*]+\*\*|`[^`]+`)/g)
    return parts.map((part, index) => {
        if (part.startsWith('**') && part.endsWith('**')) {
            return (
                <strong key={index} className="font-semibold text-slate-900">
                    {part.slice(2, -2)}
                </strong>
            )
        }
        if (part.startsWith('`') && part.endsWith('`')) {
            return (
                <code
                    key={index}
                    className="px-1.5 py-0.5 rounded bg-slate-200/80 font-mono text-xs text-blue-700 font-medium"
                >
                    {part.slice(1, -1)}
                </code>
            )
        }
        return part
    })
}

export function MarkdownContent({ content }: { content: string }) {
    if (!content) return null

    const lines = content.split('\n')
    const blocks: React.ReactNode[] = []
    let currentTableRows: string[] = []

    function flushTable(key: number) {
        if (currentTableRows.length === 0) return
        const headerRow = currentTableRows[0]
        const dataRows = currentTableRows
            .slice(1)
            .filter(r => !r.match(/^\s*\|?\s*[-:]+[-| :]*\|?\s*$/))

        const parseCells = (row: string) => {
            return row
                .split('|')
                .map(c => c.trim())
                .filter(
                    (c, idx, arr) =>
                        (idx > 0 && idx < arr.length - 1) ||
                        (idx === 0 && c !== '') ||
                        (idx === arr.length - 1 && c !== ''),
                )
        }

        const headers = parseCells(headerRow)

        blocks.push(
            <div
                key={`table-${key}`}
                className="my-3 overflow-x-auto rounded-xl border border-slate-200 bg-white shadow-xs"
            >
                <table className="w-full text-left text-xs border-collapse">
                    <thead className="bg-slate-100/80 border-b border-slate-200">
                        <tr>
                            {headers.map((h, i) => (
                                <th
                                    key={i}
                                    className="px-3.5 py-2.5 font-semibold text-slate-800 tracking-wide text-[11px]"
                                >
                                    {renderInline(h)}
                                </th>
                            ))}
                        </tr>
                    </thead>
                    <tbody className="divide-y divide-slate-100">
                        {dataRows.map((rowStr, rIdx) => {
                            const cells = parseCells(rowStr)
                            return (
                                <tr
                                    key={rIdx}
                                    className={
                                        rIdx % 2 === 0
                                            ? 'bg-white hover:bg-slate-50/50'
                                            : 'bg-slate-50/40 hover:bg-slate-50'
                                    }
                                >
                                    {cells.map((cell, cIdx) => (
                                        <td
                                            key={cIdx}
                                            className="px-3.5 py-2.5 text-slate-700 align-top leading-relaxed"
                                        >
                                            {renderInline(cell)}
                                        </td>
                                    ))}
                                </tr>
                            )
                        })}
                    </tbody>
                </table>
            </div>,
        )
        currentTableRows = []
    }

    lines.forEach((line, lineIndex) => {
        const trimmed = line.trim()

        if (trimmed.startsWith('|') && trimmed.endsWith('|')) {
            currentTableRows.push(trimmed)
            return
        } else if (currentTableRows.length > 0) {
            flushTable(lineIndex)
        }

        if (trimmed.startsWith('### ')) {
            blocks.push(
                <h4
                    key={lineIndex}
                    className="mt-3 mb-1 text-sm font-bold text-slate-900"
                >
                    {renderInline(trimmed.replace(/^###\s+/, ''))}
                </h4>,
            )
        } else if (trimmed.startsWith('## ')) {
            blocks.push(
                <h3
                    key={lineIndex}
                    className="mt-4 mb-1 text-base font-bold text-slate-900"
                >
                    {renderInline(trimmed.replace(/^##\s+/, ''))}
                </h3>,
            )
        } else if (trimmed.startsWith('- ') || trimmed.startsWith('* ')) {
            blocks.push(
                <div
                    key={lineIndex}
                    className="flex items-start gap-2 text-sm text-slate-700 my-0.5 ml-1"
                >
                    <span className="text-blue-500 font-bold">•</span>
                    <span>{renderInline(trimmed.replace(/^[-*]\s+/, ''))}</span>
                </div>,
            )
        } else if (trimmed.startsWith('Tools invoked:')) {
            blocks.push(
                <div
                    key={lineIndex}
                    className="mt-2 text-[11px] font-mono text-slate-500 bg-slate-100 px-2 py-1 rounded inline-block border border-slate-200"
                >
                    {trimmed}
                </div>,
            )
        } else if (trimmed) {
            blocks.push(
                <p
                    key={lineIndex}
                    className="text-sm leading-6 text-slate-700 my-1"
                >
                    {renderInline(trimmed)}
                </p>,
            )
        }
    })

    if (currentTableRows.length > 0) {
        flushTable(lines.length)
    }

    return <div className="space-y-1">{blocks}</div>
}
