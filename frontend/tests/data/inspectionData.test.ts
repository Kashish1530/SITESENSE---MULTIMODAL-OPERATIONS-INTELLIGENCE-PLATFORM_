
import { describe, expect, it } from 'vitest'

import {
    INSPECTION_TEMPLATES,
    INSPECTIONS,
    INSPECTION_FINDINGS,
    CORRECTIVE_ACTIONS,
    INSPECTION_EVIDENCE,
} from '../../src/data/inspectionData'

import {
    DEMO_SITES,
    DEMO_USERS,
} from '../../src/data/users'

// Runtime record access also lets these tests detect fields
// that may be missing from the declared TypeScript interfaces.
type DataRecord = Record<string, unknown>

const records = (items: readonly unknown[]): DataRecord[] =>
    items as DataRecord[]

const ids = (items: readonly unknown[]): unknown[] =>
    records(items).map(item => item.id)

const findById = (items: readonly unknown[], id: unknown) =>
    records(items).find(item => item.id === id)

const hasId = (items: readonly unknown[], id: unknown) =>
    id !== undefined &&
    id !== null &&
    findById(items, id) !== undefined

describe('Inspection seed data integrity', () => {
    describe('Unique identifiers', () => {
        const collections = [
            ['sites', DEMO_SITES],
            ['users', DEMO_USERS],
            ['templates', INSPECTION_TEMPLATES],
            ['inspections', INSPECTIONS],
            ['findings', INSPECTION_FINDINGS],
            ['corrective actions', CORRECTIVE_ACTIONS],
            ['evidence', INSPECTION_EVIDENCE],
        ] as const

        it.each(collections)(
            'requires unique, non-empty IDs for %s',
            (_name, collection) => {
                const collectionIds = ids(collection)

                expect(collectionIds.every(
                    id => typeof id === 'string' && id.length > 0,
                )).toBe(true)

                expect(new Set(collectionIds).size).toBe(collection.length)
            },
        )
    })

    describe('Sites and users', () => {
        it('references existing sites from every inspection', () => {
            for (const inspection of records(INSPECTIONS)) {
                expect(hasId(DEMO_SITES, inspection.siteId)).toBe(true)
            }
        })

        it('references existing assigned users and assigners', () => {
            for (const inspection of records(INSPECTIONS)) {
                expect(hasId(DEMO_USERS, inspection.assignedToUserId)).toBe(true)
                expect(hasId(DEMO_USERS, inspection.assignedByUserId)).toBe(true)
            }
        })

        it('references existing reviewers when a reviewer is assigned', () => {
            for (const inspection of records(INSPECTIONS)) {
                if (inspection.reviewerUserId) {
                    expect(hasId(DEMO_USERS, inspection.reviewerUserId)).toBe(true)
                }
            }
        })

        it('references existing supervisors and managers in the user hierarchy', () => {
            for (const user of records(DEMO_USERS)) {
                if (user.supervisorId) {
                    expect(hasId(DEMO_USERS, user.supervisorId)).toBe(true)
                }

                if (user.managerId) {
                    expect(hasId(DEMO_USERS, user.managerId)).toBe(true)
                }
            }
        })
    })

    describe('Inspection templates', () => {
        it('references existing template creators', () => {
            for (const template of records(INSPECTION_TEMPLATES)) {
                expect(hasId(DEMO_USERS, template.createdByUserId)).toBe(true)
            }
        })

        it('has unique question IDs across all templates', () => {
            const questionIds = records(INSPECTION_TEMPLATES)
                .flatMap(template =>
                    records(template.checklist as unknown[]).map(
                        question => question.id,
                    ),
                )

            expect(questionIds.every(
                id => typeof id === 'string' && id.length > 0,
            )).toBe(true)

            expect(new Set(questionIds).size).toBe(questionIds.length)
        })

        it('references existing templates from inspections', () => {
            for (const inspection of records(INSPECTIONS)) {
                if (inspection.templateId) {
                    expect(
                        hasId(INSPECTION_TEMPLATES, inspection.templateId),
                    ).toBe(true)
                }
            }
        })
    })

    describe('Checklist answers', () => {
        it('references questions belonging to each inspection template', () => {
            for (const inspection of records(INSPECTIONS)) {
                if (!inspection.templateId) continue

                const template = findById(
                    INSPECTION_TEMPLATES,
                    inspection.templateId,
                )

                expect(template).toBeDefined()

                const questionIds = records(
                    template!.checklist as unknown[],
                ).map(question => question.id)

                for (const answer of records(inspection.answers as unknown[])) {
                    expect(questionIds).toContain(answer.questionId)
                }
            }
        })

        it('references existing evidence from checklist answers', () => {
            for (const inspection of records(INSPECTIONS)) {
                for (const answer of records(inspection.answers as unknown[])) {
                    for (const evidenceId of answer.evidenceIds as unknown[]) {
                        const evidence = findById(
                            INSPECTION_EVIDENCE,
                            evidenceId,
                        )

                        expect(evidence).toBeDefined()
                        expect(evidence?.inspectionId).toBe(inspection.id)
                    }
                }
            }
        })
    })

    describe('Findings', () => {
        it('references existing inspections', () => {
            for (const finding of records(INSPECTION_FINDINGS)) {
                expect(hasId(INSPECTIONS, finding.inspectionId)).toBe(true)
            }
        })

        it('references existing reporters when a reporter is specified', () => {
            for (const finding of records(INSPECTION_FINDINGS)) {
                const reporterId = finding.reportedByUserId

                if (reporterId) {
                    expect(hasId(DEMO_USERS, reporterId)).toBe(true)
                }
            }
        })

        it('references valid checklist questions when specified', () => {
            for (const finding of records(INSPECTION_FINDINGS)) {
                if (!finding.questionId) continue

                const inspection = findById(
                    INSPECTIONS,
                    finding.inspectionId,
                )

                const template = findById(
                    INSPECTION_TEMPLATES,
                    inspection?.templateId,
                )

                const questionIds = records(
                    (template?.checklist ?? []) as unknown[],
                ).map(question => question.id)

                expect(questionIds).toContain(finding.questionId)
            }
        })

        it('is linked from its corresponding inspection', () => {
            for (const finding of records(INSPECTION_FINDINGS)) {
                const inspection = findById(
                    INSPECTIONS,
                    finding.inspectionId,
                )

                expect(
                    inspection?.findingIds as unknown[],
                ).toContain(finding.id)
            }
        })
    })

    describe('Corrective actions', () => {
        it('references existing findings and inspections', () => {
            for (const action of records(CORRECTIVE_ACTIONS)) {
                expect(hasId(INSPECTION_FINDINGS, action.findingId)).toBe(true)
                expect(hasId(INSPECTIONS, action.inspectionId)).toBe(true)
            }
        })

        it('matches the inspection associated with its finding', () => {
            for (const action of records(CORRECTIVE_ACTIONS)) {
                const finding = findById(
                    INSPECTION_FINDINGS,
                    action.findingId,
                )

                expect(finding?.inspectionId).toBe(action.inspectionId)
            }
        })

        it('references existing assignees and assigners', () => {
            for (const action of records(CORRECTIVE_ACTIONS)) {
                expect(hasId(DEMO_USERS, action.assignedToUserId)).toBe(true)
                expect(hasId(DEMO_USERS, action.assignedByUserId)).toBe(true)
            }
        })

        it('is linked from its corresponding finding when specified', () => {
            for (const finding of records(INSPECTION_FINDINGS)) {
                const actionId = finding.correctiveActionId

                if (actionId) {
                    const action = findById(CORRECTIVE_ACTIONS, actionId)

                    expect(action).toBeDefined()
                    expect(action?.findingId).toBe(finding.id)
                }
            }
        })

        it('references existing evidence from corrective actions', () => {
            for (const action of records(CORRECTIVE_ACTIONS)) {
                for (const evidenceId of action.evidenceIds as unknown[]) {
                    expect(hasId(INSPECTION_EVIDENCE, evidenceId)).toBe(true)
                }
            }
        })
    })

    describe('Evidence', () => {
        it('references existing inspections and uploaders', () => {
            for (const evidence of records(INSPECTION_EVIDENCE)) {
                expect(hasId(INSPECTIONS, evidence.inspectionId)).toBe(true)
                expect(hasId(DEMO_USERS, evidence.uploadedByUserId)).toBe(true)
            }
        })

        it('references existing findings when a finding is specified', () => {
            for (const evidence of records(INSPECTION_EVIDENCE)) {
                if (evidence.findingId) {
                    const finding = findById(
                        INSPECTION_FINDINGS,
                        evidence.findingId,
                    )

                    expect(finding).toBeDefined()
                    expect(finding?.inspectionId).toBe(evidence.inspectionId)
                }
            }
        })

        it('is linked from its corresponding inspection', () => {
            for (const evidence of records(INSPECTION_EVIDENCE)) {
                const inspection = findById(
                    INSPECTIONS,
                    evidence.inspectionId,
                )

                expect(
                    inspection?.evidenceIds as unknown[],
                ).toContain(evidence.id)
            }
        })

        it('references valid checklist questions when specified', () => {
            for (const evidence of records(INSPECTION_EVIDENCE)) {
                if (!evidence.questionId) continue

                const inspection = findById(
                    INSPECTIONS,
                    evidence.inspectionId,
                )

                const template = findById(
                    INSPECTION_TEMPLATES,
                    inspection?.templateId,
                )

                const questionIds = records(
                    (template?.checklist ?? []) as unknown[],
                ).map(question => question.id)

                expect(questionIds).toContain(evidence.questionId)
            }
        })
    })

    describe('Observations', () => {
        it('references existing reporters and evidence', () => {
            for (const inspection of records(INSPECTIONS)) {
                for (const observation of records(
                    inspection.observations as unknown[],
                )) {
                    expect(
                        hasId(DEMO_USERS, observation.reportedByUserId),
                    ).toBe(true)

                    for (const evidenceId of observation.evidenceIds as unknown[]) {
                        const evidence = findById(
                            INSPECTION_EVIDENCE,
                            evidenceId,
                        )

                        expect(evidence).toBeDefined()
                        expect(evidence?.inspectionId).toBe(inspection.id)
                    }
                }
            }
        })
    })
})
