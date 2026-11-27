
import { describe, expect, it } from 'vitest'
import {
    getNormalizedPoint,
    getPolygonArea,
    isValidPolygon,
    normalizePoint,
} from '../../src/zones/zoneGeometry'
import type { Point2D } from '../../src/zones/zoneConfiguration'

describe('zone geometry', () => {
    describe('normalizePoint', () => {
        it('keeps coordinates inside the 0–100 range', () => {
            expect(normalizePoint({ x: 25, y: 75 })).toEqual({
                x: 25,
                y: 75,
            })
        })

        it('clamps coordinates outside the range', () => {
            expect(normalizePoint({ x: -10, y: 120 })).toEqual({
                x: 0,
                y: 100,
            })
        })
    })

    describe('getPolygonArea', () => {
        it('calculates the area of a square', () => {
            const points: Point2D[] = [
                { x: 10, y: 10 },
                { x: 30, y: 10 },
                { x: 30, y: 30 },
                { x: 10, y: 30 },
            ]

            expect(getPolygonArea(points)).toBe(400)
        })

        it('returns zero for fewer than three points', () => {
            expect(getPolygonArea([
                { x: 10, y: 10 },
                { x: 20, y: 20 },
            ])).toBe(0)
        })
    })

    describe('isValidPolygon', () => {
        it('accepts a valid triangle', () => {
            expect(isValidPolygon([
                { x: 10, y: 10 },
                { x: 80, y: 10 },
                { x: 40, y: 80 },
            ])).toBe(true)
        })

        it('rejects fewer than three points', () => {
            expect(isValidPolygon([
                { x: 10, y: 10 },
                { x: 80, y: 10 },
            ])).toBe(false)
        })

        it('rejects duplicate points that leave fewer than three unique points', () => {
            expect(isValidPolygon([
                { x: 10, y: 10 },
                { x: 80, y: 10 },
                { x: 10, y: 10 },
            ])).toBe(false)
        })

        it('rejects points outside the normalized range', () => {
            expect(isValidPolygon([
                { x: 10, y: 10 },
                { x: 110, y: 10 },
                { x: 40, y: 80 },
            ])).toBe(false)
        })

        it('rejects non-finite coordinates', () => {
            expect(isValidPolygon([
                { x: 10, y: 10 },
                { x: Number.NaN, y: 10 },
                { x: 40, y: 80 },
            ])).toBe(false)
        })

        it('rejects a zero-area polygon', () => {
            expect(isValidPolygon([
                { x: 10, y: 10 },
                { x: 40, y: 40 },
                { x: 70, y: 70 },
            ])).toBe(false)
        })
    })

    describe('getNormalizedPoint', () => {
        it('converts a screen position into normalized coordinates', () => {
            expect(getNormalizedPoint(150, 100, {
                left: 50,
                top: 50,
                width: 200,
                height: 100,
            })).toEqual({
                x: 50,
                y: 50,
            })
        })

        it('returns null for zero-sized bounds', () => {
            expect(getNormalizedPoint(100, 100, {
                left: 0,
                top: 0,
                width: 0,
                height: 100,
            })).toBeNull()
        })

        it('clamps pointer positions to the background bounds', () => {
            expect(getNormalizedPoint(300, -50, {
                left: 0,
                top: 0,
                width: 200,
                height: 100,
            })).toEqual({
                x: 100,
                y: 0,
            })
        })
    })
})
