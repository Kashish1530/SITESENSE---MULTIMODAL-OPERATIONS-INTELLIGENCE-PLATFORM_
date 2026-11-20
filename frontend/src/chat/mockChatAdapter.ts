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
    hasImages: boolean,
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

    const response = hasImages
        ? 'I received your image attachment in this preview. Image analysis is not connected yet, so I cannot identify objects or verify conditions in the photograph. I can still help explain the inspection process or suggest what evidence an inspector should record.'
        : `This is a simulated response to: "${question}".\n\nFor a workplace inspection, record the observation clearly, include the relevant location, attach supporting evidence and assign a corrective action when necessary.\n\nPlease verify any operational decision against your organization's actual policies. This preview does not access live SiteSense data.`

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