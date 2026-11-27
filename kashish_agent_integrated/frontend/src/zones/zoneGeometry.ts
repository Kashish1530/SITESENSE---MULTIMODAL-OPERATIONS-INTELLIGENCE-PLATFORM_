
import type { Point2D } from './zoneConfiguration'

const MIN_POLYGON_POINTS = 3
const MAX_POLYGON_POINTS = 100

/**
 * Keeps coordinates inside the normalized 0–100 background space.
 */
export function normalizePoint(point: Point2D): Point2D {
    return {
        x: Math.min(100, Math.max(0, point.x)),
        y: Math.min(100, Math.max(0, point.y)),
    }
}

/**
 * Checks whether a polygon has enough valid, finite points.
 */
export function isValidPolygon(points: Point2D[]): boolean {
    if (
        points.length < MIN_POLYGON_POINTS ||
        points.length > MAX_POLYGON_POINTS
    ) {
        return false
    }

    if (points.some(point =>
        !Number.isFinite(point.x) ||
        !Number.isFinite(point.y) ||
        point.x < 0 ||
        point.x > 100 ||
        point.y < 0 ||
        point.y > 100
    )) {
        return false
    }

    const uniquePoints = new Set(
        points.map(point => `${point.x},${point.y}`),
    )

    if (uniquePoints.size < MIN_POLYGON_POINTS) return false

    return Math.abs(getPolygonArea(points)) > 0.01
}

/**
 * Calculates polygon area using the shoelace formula.
 */
export function getPolygonArea(points: Point2D[]): number {
    if (points.length < 3) return 0

    let area = 0

    for (let index = 0; index < points.length; index += 1) {
        const current = points[index]
        const next = points[(index + 1) % points.length]

        area += current.x * next.y
        area -= next.x * current.y
    }

    return Math.abs(area) / 2
}

/**
 * Converts a pointer position into normalized background coordinates.
 */
export function getNormalizedPoint(
    clientX: number,
    clientY: number,
    bounds: Pick<DOMRect, 'left' | 'top' | 'width' | 'height'>,
): Point2D | null {
    if (bounds.width <= 0 || bounds.height <= 0) return null

    return normalizePoint({
        x: ((clientX - bounds.left) / bounds.width) * 100,
        y: ((clientY - bounds.top) / bounds.height) * 100,
    })
}
