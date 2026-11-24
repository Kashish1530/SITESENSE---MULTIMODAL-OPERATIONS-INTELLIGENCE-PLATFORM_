import type { MockChatEvent } from './types'

const wait = (milliseconds: number) =>
    new Promise<void>(resolve => setTimeout(resolve, milliseconds))

const DEMO_CITATIONS = [
    {
        id: 'citation-1',
        title: 'Workplace Safety Policy',
        source: 'Demo Knowledge Base · Section 4',
        excerpt:
            'Work areas must be kept clear, accessible and free from avoidable hazards.',
    },
    {
        id: 'citation-2',
        title: 'Inspection Procedures',
        source: 'Demo Operations Manual · Section 2',
        excerpt:
            'Record observations with supporting evidence and assign corrective actions where required.',
    },
]

export async function* streamMockResponse(
    question: string,
    hasAttachments: boolean,
    attachmentTypes?: string[],
): AsyncGenerator<MockChatEvent> {
    yield {
        type: 'tool',
        label: 'Searching the demo knowledge base',
    }

    await wait(700)

    yield {
        type: 'tool',
        label: 'Preparing a simulated response',
    }

    await wait(500)

    let response: string
    if (hasAttachments) {
        const typesStr = attachmentTypes && attachmentTypes.length > 0
            ? attachmentTypes.join(', ')
            : 'photo, video, PDF, or Excel spreadsheet'
        response = `I received your attachment(s) (${typesStr}) in this preview. The SiteSense Multimodal Assistant supports images, video recordings, PDF documentation, and Excel spreadsheets (.xlsx, .xls, .csv). In a live inspection environment, these files are uploaded directly to MinIO and grounded against operational compliance policies and detection models.`
    } else {
        response = `This is a simulated response to: "${question}".\n\nFor a workplace inspection, record the observation clearly, include the relevant location, attach supporting evidence and assign a corrective action when necessary.\n\nPlease verify any operational decision against your organization's actual policies. This preview does not access live SiteSense data.`
    }

    const words = response.split(/(\s+)/)

    for (const word of words) {
        yield {
            type: 'token',
            text: word,
        }

        await wait(35)
    }

    yield {
        type: 'citations',
        citations: DEMO_CITATIONS,
    }

    yield { type: 'done' }
}