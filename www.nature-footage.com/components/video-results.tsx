"use client"

import { useState, useRef, useEffect } from "react"
import Image from "next/image"
import { Play, AlertCircle } from "lucide-react"
import { useRouter } from "next/navigation"
import type { VideoResult, Clip } from "@/types/search"

import { getFullVideoUrl } from "@/config/api-config"

interface VideoResultsProps {
  results: VideoResult[]
}

export default function VideoResults({ results }: VideoResultsProps) {
  const router = useRouter()
  const [containerIds] = useState(() =>
    results.map((_, index) => `video-container-${index}-${Math.random().toString(36).substring(2, 9)}`),
  )

  const [playingContainer, setPlayingContainer] = useState<string | null>(null)
  const [hoveredContainer, setHoveredContainer] = useState<string | null>(null)
  // Store video element references
  const videoRefs = useRef<{ [containerId: string]: HTMLVideoElement | null }>({})
  // Track playback errors
  const [playbackError, setPlaybackError] = useState<{ containerId: string; message: string } | null>(null)

  useEffect(() => {
    return () => {
      // Pause all videos
      Object.values(videoRefs.current).forEach((video) => {
        if (video) {
          video.pause()
          video.src = ""
          video.load()
        }
      })
    }
  }, [])

  // Handle video playback when playingContainer changes
  useEffect(() => {
    if (!playingContainer) return

    const videoElement = videoRefs.current[playingContainer]
    if (!videoElement) return

    // Find the index of the container to get the corresponding video data
    const containerIndex = containerIds.findIndex((id) => id === playingContainer)
    if (containerIndex === -1) return

    const videoData = results[containerIndex]
    if (!videoData || !videoData.video_url) return

    console.log(`Setting up video playback for container ${playingContainer} with URL ${videoData.video_url}`)

    const setupVideo = async () => {
      try {
        const videoElement = videoRefs.current[playingContainer]
        if (!videoElement) return

        const containerIndex = containerIds.findIndex((id) => id === playingContainer)
        if (containerIndex === -1) return

        const videoData = results[containerIndex]
        if (!videoData || !videoData.video_url) return

        console.log(`Setting up video playback for container ${playingContainer} with URL ${videoData.video_url}`)

        // Get the full video URL by prefixing with backend URL
        const fullVideoUrl = getFullVideoUrl(videoData.video_url)

        // Set the video source directly
        videoElement.src = fullVideoUrl
        videoElement.load()
        videoElement.play().catch((error) => {
          console.error("Play error:", error)
          setPlaybackError({
            containerId: playingContainer,
            message: "Failed to play video. Please try again.",
          })
        })
      } catch (error) {
        console.error(`Error setting up video for container ${playingContainer}:`, error)
        setPlaybackError({
          containerId: playingContainer,
          message: "An unexpected error occurred while setting up the video.",
        })
      }
    }

    setupVideo()

    // Cleanup function
    return () => {
      if (videoElement) {
        videoElement.pause()
      }
    }
  }, [playingContainer, results, containerIds])


  const handleVideoClick = (containerId: string, videoId: string) => {
    // Navigate to detail page with the video ID
    router.push(`/detail/${videoId}`)
  }

  const isVideoPlaying = (containerId: string) => {
    const videoElement = videoRefs.current[containerId]
    return playingContainer === containerId && videoElement && !videoElement.paused
  }

  const handleMouseEnter = (containerId: string) => {
    setHoveredContainer(containerId)
  }

  const handleMouseLeave = (containerId: string) => {
    setHoveredContainer(null)
  }

  const formatConfidence = (confidence: string | undefined): string => {
    if (!confidence) return "N/A"

    const normalizedConfidence = confidence.trim().toLowerCase()
    if (normalizedConfidence === "low" || normalizedConfidence === "medium" || normalizedConfidence === "high") {
      return confidence.charAt(0).toUpperCase() + confidence.slice(1).toLowerCase()
    }

    return confidence
  }

  const getVideoScore = (video: VideoResult): number | null => {
    if (video.score !== undefined && video.score !== null) {
      return video.score
    }

    if (video.clips && video.clips.length > 0) {
      const highestClipScore = Math.max(
        ...video.clips.map((clip) => (clip.score !== undefined && clip.score !== null ? clip.score : 0)),
      )
      return highestClipScore > 0 ? highestClipScore : null
    }

    return null
  }

  const formatScore = (score: number | undefined | null): string => {
    if (score === undefined || score === null) return "N/A"
    return score.toFixed(2)
  }

  const getBestClip = (video: VideoResult): Clip | null => {
    if (!video.clips || video.clips.length === 0) return null
    return video.clips.reduce((best, current) => (current.score > best.score ? current : best), video.clips[0])
  }

  if (!results || results.length === 0) {
    return (
      <div className="text-center py-10">
        <p className="text-gray-500">No videos found. Try a different search term.</p>
      </div>
    )
  }

  return (
    <div className="grid grid-cols-1 md:grid-cols-3 gap-6">
      {results.map((video, index) => {
        const containerId = containerIds[index]
        const isPlaying = isVideoPlaying(containerId)
        const isHovered = hoveredContainer === containerId
        const hasError = playbackError && playbackError.containerId === containerId
        const bestClip = getBestClip(video)
        const videoScore = getVideoScore(video)

        return (
          <div
            key={containerId}
            className={`relative overflow-hidden rounded-lg border border-gray-200 
              ${playingContainer === containerId ? "ring-2 ring-brand-teal-500" : ""} 
              hover:shadow-lg transition-all duration-300`}
            onMouseEnter={() => handleMouseEnter(containerId)}
            onMouseLeave={() => handleMouseLeave(containerId)}
          >
            {/* Video container with fixed aspect ratio */}
            <div
              className="relative aspect-video cursor-pointer"
              onClick={() => handleVideoClick(containerId, video.video_id)}
            >
              {/* Show video when playing, otherwise show thumbnail */}
              {playingContainer === containerId ? (
                <video
                  ref={(el) => (videoRefs.current[containerId] = el)}
                  className="absolute inset-0 w-full h-full object-cover"
                  playsInline
                  onClick={(e) => e.stopPropagation()}
                  onEnded={() => setPlayingContainer(null)}
                  onError={() => {
                    setPlaybackError({
                      containerId,
                      message: "Error loading video. The video might be unavailable or in an unsupported format.",
                    })
                  }}
                />
              ) : (
                <Image
                  src={video.thumbnail_url || "/placeholder.svg?height=200&width=400&query=nature"}
                  alt={`Nature footage ${video.filename || video.video_id}`}
                  fill
                  className="object-cover"
                  unoptimized 
                />
              )}

              {/* Dark gradient overlay for text */}
              <div className="absolute inset-0 bg-gradient-to-t from-black/70 via-transparent to-black/30"></div>

              {/* Top right metadata - Confidence and Score */}
              <div className="absolute top-2 right-2 flex flex-col gap-1">
                <span className="text-xs px-2 py-0.5 rounded-md bg-green-600 text-white font-medium">
                  Confidence: {formatConfidence(bestClip?.confidence)}
                </span>
                <span className="text-xs px-2 py-0.5 rounded-md bg-purple-600 text-white font-medium">
                  Score: {formatScore(videoScore)}
                </span>
              </div>

              {/* Filename and RF tag */}
              <div className="absolute bottom-0 left-0 right-0 p-2">
                <div className="flex justify-between items-center">
                  <span className="text-sm font-medium text-white drop-shadow-md">
                    {video.filename
                      ? video.filename.split(".")[0]
                      : `Video ${video.video_id?.substring(0, 8) || "Unknown"}`}
                  </span>
                  <div className="flex gap-1">
                    <span className="text-xs px-2 py-0.5 rounded-full bg-brand-teal-500 text-white font-medium">
                      RF
                    </span>
                    <span className="text-xs px-2 py-0.5 rounded-full bg-brand-green-500 text-white font-medium">
                      $
                    </span>
                  </div>
                </div>
              </div>

              {/* Clips count badge on Search Result */}
              {video.clips && video.clips.length > 0 && (
                <div className="absolute top-2 left-2">
                  <span className="text-xs px-2 py-0.5 rounded-md bg-black/50 text-white font-medium">
                    {video.clips.length} clip{video.clips.length !== 1 ? "s" : ""}
                  </span>
                </div>
              )}

              {/* Play/Pause button overlay */}
              {isHovered && !hasError && (
                <div className="absolute inset-0 flex items-center justify-center bg-black/20 transition-opacity duration-200">
                  <button
                    onClick={(e) => {
                      e.stopPropagation()
                      handleVideoClick(containerId, video.video_id)
                    }}
                    className="p-3 bg-black/40 rounded-full hover:bg-black/60 transition-colors"
                    aria-label="View video details"
                  >
                    <Play className="h-8 w-8 text-white" />
                  </button>
                </div>
              )}

              {/* Error message overlay */}
              {hasError && (
                <div className="absolute inset-0 flex items-center justify-center bg-black/70 z-20">
                  <div className="text-center p-4">
                    <AlertCircle className="h-8 w-8 text-red-500 mx-auto mb-2" />
                    <p className="text-white text-sm">{playbackError?.message || "An error occurred"}</p>
                    <button
                      onClick={() => {
                        setPlaybackError(null)
                        setPlayingContainer(null)
                      }}
                      className="mt-3 px-3 py-1 bg-white/20 hover:bg-white/30 rounded text-white text-xs"
                    >
                      Dismiss
                    </button>
                  </div>
                </div>
              )}
            </div>
          </div>
        )
      })}
    </div>
  )
}
