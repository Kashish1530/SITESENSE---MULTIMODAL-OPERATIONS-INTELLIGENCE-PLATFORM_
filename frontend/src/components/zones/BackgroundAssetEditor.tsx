
import { useEffect, useRef, useState } from 'react'
import type { ChangeEvent } from 'react'
import {
    Camera,
    ImagePlus,
    Video,
} from 'lucide-react'

import type { BackgroundAsset } from '../../zones/zoneConfiguration'

type Props = {
    currentBackground: BackgroundAsset | null
    disabled: boolean
    onApply: (background: BackgroundAsset) => boolean
    showPreview?: boolean
}

const MAX_FILE_SIZE = 25 * 1024 * 1024

const IMAGE_TYPES = ['image/jpeg', 'image/png', 'image/webp']
const VIDEO_TYPES = ['video/mp4', 'video/webm']

function readFileAsDataUrl(file: File): Promise<string> {
    return new Promise((resolve, reject) => {
        const reader = new FileReader()

        reader.onload = () => {
            if (typeof reader.result === 'string') {
                resolve(reader.result)
            } else {
                reject(new Error('The selected file could not be read.'))
            }
        }

        reader.onerror = () => reject(
            new Error('The selected file could not be read.'),
        )

        reader.readAsDataURL(file)
    })
}

export default function BackgroundAssetEditor({
    currentBackground,
    disabled,
    onApply,
    showPreview = true,
}: Props) {
    const videoRef = useRef<HTMLVideoElement>(null)

    const [videoFile, setVideoFile] = useState<File | null>(null)
    const [videoUrl, setVideoUrl] = useState('')
    const [videoReady, setVideoReady] = useState(false)
    const [videoDuration, setVideoDuration] = useState(0)
    const [error, setError] = useState('')
    const [message, setMessage] = useState('')

    useEffect(() => {
        return () => {
            if (videoUrl) URL.revokeObjectURL(videoUrl)
        }
    }, [videoUrl])

    const handleFileChange = async (
        event: ChangeEvent<HTMLInputElement>,
    ) => {
        const file = event.target.files?.[0]
        event.target.value = ''

        if (!file) return

        setError('')
        setMessage('')
        setVideoReady(false)
        setVideoFile(null)
        setVideoUrl('')

        if (file.size > MAX_FILE_SIZE) {
            setError('File size must not exceed 25 MB.')
            return
        }

        if (IMAGE_TYPES.includes(file.type)) {
            try {
                const dataUrl = await readFileAsDataUrl(file)

                const applied = onApply({
                    id: `BACKGROUND-${Date.now()}`,
                    name: file.name,
                    type: 'image',
                    mimeType: file.type,
                    url: dataUrl,
                })

                setMessage(
                    applied
                        ? 'Image added to the working copy. Save the configuration to keep this change.'
                        : 'Image was not applied. The existing configuration is unchanged.',
                )
            } catch {
                setError('Unable to read this image. Please try another file.')
            }

            return
        }

        if (VIDEO_TYPES.includes(file.type)) {
            const url = URL.createObjectURL(file)

            setVideoFile(file)
            setVideoUrl(url)
            setMessage('Choose a frame from the video, then capture it as the background.')
            return
        }

        setError('Unsupported file. Choose JPEG, PNG, WebP, MP4 or WebM.')
    }

    const captureVideoFrame = () => {
        const video = videoRef.current

        if (!video || !videoReady || !video.videoWidth || !video.videoHeight) {
            setError('The video is not ready. Please wait for it to load.')
            return
        }

        try {
            const canvas = document.createElement('canvas')
            canvas.width = video.videoWidth
            canvas.height = video.videoHeight

            const context = canvas.getContext('2d')

            if (!context) {
                setError('Frame capture is unavailable in this browser.')
                return
            }

            context.drawImage(video, 0, 0, canvas.width, canvas.height)

            const frameDataUrl = canvas.toDataURL('image/png')

            const applied = onApply({
                id: `BACKGROUND-${Date.now()}`,
                name: `${videoFile?.name ?? 'Video'} - captured frame`,
                type: 'image',
                mimeType: 'image/png',
                url: frameDataUrl,
                capturedAt: new Date().toISOString(),
                durationSeconds: videoDuration,
            })

            setMessage(
                applied
                    ? 'Video frame added to the working copy. Save the configuration to keep this change.'
                    : 'Frame was not applied. The existing configuration is unchanged.',
            )
            setError('')
        } catch {
            setError('Unable to capture this video frame. Try another frame or video.')
        }
    }

    return (
        <div className="mt-3 space-y-4">
            {showPreview && currentBackground && (
                <div className="space-y-2">
                    <p className="text-xs font-medium text-slate-600">
                        Current working-copy background
                    </p>

                    <div className="overflow-hidden rounded-lg border border-slate-200 bg-slate-50">
                        <img
                            src={currentBackground.url}
                            alt={currentBackground.name}
                            className="block max-h-72 w-full object-contain"
                        />
                    </div>

                    <p className="text-xs text-slate-500">
                        {currentBackground.name}
                        {currentBackground.capturedAt
                            ? ' · Captured from video'
                            : ''}
                    </p>
                </div>
            )}

            {!currentBackground && (
                <p className="text-sm text-slate-500">
                    No background image configured yet.
                </p>
            )}

            {disabled ? (
                <p className="text-xs text-slate-500">
                    Background replacement is available to Admin users only while editing.
                </p>
            ) : (
                <>
                    <label className="inline-flex cursor-pointer items-center gap-2 rounded-lg border border-slate-300 px-3 py-2 text-sm font-medium text-slate-700 hover:bg-slate-50">
                        <ImagePlus className="h-4 w-4" />
                        Choose image or video
                        <input
                            type="file"
                            accept="image/jpeg,image/png,image/webp,video/mp4,video/webm"
                            onChange={handleFileChange}
                            className="sr-only"
                        />
                    </label>

                    {videoUrl && (
                        <div className="space-y-3 rounded-lg border border-slate-200 p-3">
                            <div className="flex items-center gap-2 text-sm font-medium text-slate-700">
                                <Video className="h-4 w-4" />
                                Video frame selection
                            </div>

                            <video
                                ref={videoRef}
                                src={videoUrl}
                                controls
                                playsInline
                                onLoadedData={() => {
                                    setVideoReady(true)
                                    setVideoDuration(
                                        videoRef.current?.duration ?? 0,
                                    )
                                }}
                                onError={() => {
                                    setVideoReady(false)
                                    setError('This video could not be loaded.')
                                }}
                                className="block max-h-72 w-full bg-black object-contain"
                            />

                            <p className="text-xs text-slate-500">
                                Pause the video at the frame you want, then capture it.
                                Original proportions are preserved.
                            </p>

                            <button
                                type="button"
                                onClick={captureVideoFrame}
                                disabled={!videoReady}
                                className="inline-flex items-center gap-2 rounded-lg bg-indigo-600 px-4 py-2 text-sm font-medium text-white hover:bg-indigo-700 disabled:cursor-not-allowed disabled:opacity-50"
                            >
                                <Camera className="h-4 w-4" />
                                Capture current frame
                            </button>
                        </div>
                    )}
                </>
            )}

            {message && (
                <p role="status" className="text-xs text-emerald-700">
                    {message}
                </p>
            )}

            {error && (
                <p role="alert" className="text-xs text-red-700">
                    {error}
                </p>
            )}

            <p className="text-xs text-slate-400">
                Demo only: files are held in browser memory and are not uploaded to a server.
                Maximum file size: 25 MB.
            </p>
        </div>
    )
}
