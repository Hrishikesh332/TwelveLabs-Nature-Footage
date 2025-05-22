"use client"

import { useState, useEffect, useRef } from "react"
import { useParams, useRouter } from "next/navigation"
import Image from "next/image"
import Link from "next/link"
import {
  ArrowLeft,
  ArrowRight,
  Play,
  Pause,
  AlertCircle,
  ChevronLeft,
  ChevronRight,
  ThumbsUp,
  Github,
  Globe,
  Layers,
  PuzzleIcon as PuzzlePiece,
  Loader2,
} from "lucide-react"
import type { VideoResult, Clip } from "@/types/search"
import { getFullVideoUrl } from "@/config/api-config"
import VideoMetadata from "@/components/video-metadata"

interface SimilarVideo {
  video_id: string
  filename: string
  thumbnail_url?: string
  video_url: string
  similarity_score?: number
  similarity_percentage?: number
  embedding_type?: string
  scope?: string
}

// Add this helper function to format similarity scores
const formatSimilarityScore = (score: number | undefined): string => {
  if (score === undefined || score === null) return "N/A"
  // If score is already a percentage (e.g., 93.1)
  if (score > 1) return score.toFixed(1) + "%"
  // If score is a decimal (e.g., 0.931)
  return (score * 100).toFixed(1) + "%"
}

export default function VideoDetailPage() {
  const params = useParams()
  const router = useRouter()
  const videoId = params.id as string
  const [videoData, setVideoData] = useState<VideoResult | null>(null)
  const [isLoading, setIsLoading] = useState(true)
  const [error, setError] = useState<string | null>(null)
  const [selectedClip, setSelectedClip] = useState<Clip | null>(null)
  const [isPlaying, setIsPlaying] = useState(false)
  const videoRef = useRef<HTMLVideoElement | null>(null)
  const [allVideos, setAllVideos] = useState<VideoResult[]>([])
  const [currentVideoIndex, setCurrentVideoIndex] = useState<number>(-1)
  const [lastSearchQuery, setLastSearchQuery] = useState<string>("")

  const [similarVideos, setSimilarVideos] = useState<SimilarVideo[]>([])
  const [isLoadingSimilar, setIsLoadingSimilar] = useState(false)
  const [similarError, setSimilarError] = useState<string | null>(null)
  const [similarErrorDetails, setSimilarErrorDetails] = useState<string | null>(null)

  // Track which videos are playing
  const [playingSimilarVideoId, setPlayingSimilarVideoId] = useState<string | null>(null)
  const [hoveredSimilarVideoId, setHoveredSimilarVideoId] = useState<string | null>(null)
  const [videoErrors, setVideoErrors] = useState<{ [videoId: string]: string }>({})
  const [videoLoaded, setVideoLoaded] = useState<{ [videoId: string]: boolean }>({})

  // Add a ref to track play requests to prevent race conditions
  const playRequestsRef = useRef<{ [videoId: string]: boolean }>({})

  const similarVideoRefs = useRef<{ [videoId: string]: HTMLVideoElement | null }>({})

  const [isClipSwitching, setIsClipSwitching] = useState(false)
  const [videoSourceLoaded, setVideoSourceLoaded] = useState(false)
  const videoSourceRef = useRef<string | null>(null)
  const clipSwitchTimeoutRef = useRef<NodeJS.Timeout | null>(null)

  // Fetch video data
  useEffect(() => {
    const fetchVideoData = async () => {
      if (!videoId) return

      setIsLoading(true)
      setError(null)
      setVideoSourceLoaded(false)
      videoSourceRef.current = null

      try {
        // Get the last search query for the "Back to Search" button
        const storedQuery = sessionStorage.getItem("lastSearchQuery")
        if (storedQuery) {
          setLastSearchQuery(storedQuery)
        }

        const storedResults = sessionStorage.getItem("searchResults")
        if (storedResults) {
          const parsedResults = JSON.parse(storedResults)
          setAllVideos(parsedResults)

          // Find the current video and its index
          const videoIndex = parsedResults.findIndex((v: VideoResult) => v.video_id === videoId)
          setCurrentVideoIndex(videoIndex)

          if (videoIndex !== -1) {
            const video = parsedResults[videoIndex]

            const cachedVideo = sessionStorage.getItem(`video_${videoId}`)
            if (cachedVideo) {
              try {
                const parsedVideo = JSON.parse(cachedVideo)
                setVideoData(parsedVideo)

                // Select the highest scoring clip by default
                if (parsedVideo.clips && parsedVideo.clips.length > 0) {
                  const bestClip = parsedVideo.clips.reduce(
                    (best, current) => (current.score > best.score ? current : best),
                    parsedVideo.clips[0],
                  )
                  setSelectedClip(bestClip)
                }

                setIsLoading(false)
                console.log("Using cached video data for:", videoId)
                return
              } catch (err) {
                console.error("Error parsing cached video:", err)
                // Continue with normal fetch if cache parsing fails
              }
            }

            setVideoData(video)
            // Cache this specific video
            sessionStorage.setItem(`video_${videoId}`, JSON.stringify(video))

            // Select the highest scoring clip by default
            if (video.clips && video.clips.length > 0) {
              const bestClip = video.clips.reduce(
                (best, current) => (current.score > best.score ? current : best),
                video.clips[0],
              )
              setSelectedClip(bestClip)
            }
          } else {
            setError("Video not found. It may have been removed or is no longer available.")
          }
        } else {
          setError("Video data not found. Please go back to search and try again.")
        }
      } catch (err) {
        console.error("Error fetching video data:", err)
        setError("Failed to load video details. Please try again.")
      } finally {
        // After setting videoData and before the final setIsLoading(false)
        const cachedSimilarVideos = sessionStorage.getItem(`similar_videos_${videoId}`)
        if (cachedSimilarVideos) {
          try {
            const parsedSimilarVideos = JSON.parse(cachedSimilarVideos)
            setSimilarVideos(parsedSimilarVideos)
            console.log("Automatically loaded cached similar videos for:", videoId)
          } catch (err) {
            console.error("Error parsing cached similar videos:", err)
          }
        }
        setIsLoading(false)
      }
    }

    fetchVideoData()

    // Reset similar videos when video changes
    setSimilarVideos([])
    setSimilarError(null)
    setSimilarErrorDetails(null)
    setVideoErrors({})
    setPlayingSimilarVideoId(null)
    setHoveredSimilarVideoId(null)
    setVideoLoaded({})
    playRequestsRef.current = {}

    similarVideoRefs.current = {}


    if (clipSwitchTimeoutRef.current) {
      clearTimeout(clipSwitchTimeoutRef.current)
      clipSwitchTimeoutRef.current = null
    }

    return () => {
      if (clipSwitchTimeoutRef.current) {
        clearTimeout(clipSwitchTimeoutRef.current)
        clipSwitchTimeoutRef.current = null
      }
    }
  }, [videoId])

  const fetchSimilarVideos = async () => {
    if (!videoId) return

    setIsLoadingSimilar(true)
    setSimilarError(null)
    setSimilarErrorDetails(null)
    setVideoErrors({})
    setVideoLoaded({})
    playRequestsRef.current = {}

    try {
      const cachedSimilarVideos = sessionStorage.getItem(`similar_videos_${videoId}`)
      if (cachedSimilarVideos) {
        try {
          const parsedSimilarVideos = JSON.parse(cachedSimilarVideos)
          setSimilarVideos(parsedSimilarVideos)
          setIsLoadingSimilar(false)
          console.log("Using cached similar videos for:", videoId)
          return
        } catch (err) {
          console.error("Error parsing cached similar videos:", err)
        }
      }

      console.log(`Fetching similar videos for video ID: ${videoId}`)

      const response = await fetch(`/api/similar-videos/${videoId}`)
      console.log(`Similar videos API response status: ${response.status}`)

      if (!response.ok) {
        let errorMessage = `Failed to fetch similar videos: ${response.status}`
        let errorDetails = ""

        try {
          const errorData = await response.json()
          console.error("Error response data:", errorData)
          errorMessage = errorData.error || errorMessage
          errorDetails = errorData.details || ""
        } catch (e) {
          try {
            errorDetails = await response.text()
            console.error("Error response text:", errorDetails)
          } catch (e2) {
            errorDetails = "Could not parse error response"
          }
        }

        throw new Error(errorMessage, { cause: errorDetails })
      }

      const data = await response.json()
      console.log("Similar videos API response:", data)

      if (data.success && data.similar_videos) {
        const processedVideos = data.similar_videos.map((video: SimilarVideo) => {
          const videoUrl = video.video_url || ""

          console.log(`Original video URL for ${video.filename || video.video_id}:`, videoUrl)
          const fullVideoUrl = getFullVideoUrl(videoUrl)
          console.log(`Processed video URL for ${video.filename || video.video_id}:`, fullVideoUrl)

          return {
            ...video,
            video_url: fullVideoUrl,
            source: data.source || "unknown",
          }
        })

        console.log("Processed similar videos:", processedVideos)
        setSimilarVideos(processedVideos)
        // Cache the similar videos
        sessionStorage.setItem(`similar_videos_${videoId}`, JSON.stringify(processedVideos))
      } else {
        throw new Error("Invalid response format from similar videos API")
      }
    } catch (err) {
      console.error("Error fetching similar videos:", err)
      setSimilarError(err instanceof Error ? err.message : "Failed to load similar videos. Please try again.")
      setSimilarErrorDetails(err instanceof Error && err.cause ? String(err.cause) : null)
    } finally {
      setIsLoadingSimilar(false)
    }
  }


  const playSimilarVideo = (videoId: string) => {
    if (playingSimilarVideoId === videoId) return
    playRequestsRef.current[videoId] = true

    if (playingSimilarVideoId && similarVideoRefs.current[playingSimilarVideoId]) {
      similarVideoRefs.current[playingSimilarVideoId]?.pause()
    }

    setPlayingSimilarVideoId(videoId)

    // Find the video data
    const videoData = similarVideos.find((v) => v.video_id === videoId)
    if (!videoData) {
      console.error(`No video data found for ID: ${videoId}`)
      return
    }

    // Play the new video with a small delay to avoid race conditions
    setTimeout(() => {
      if (!playRequestsRef.current[videoId]) {
        console.log(`Play request for ${videoId} was cancelled`)
        return
      }

      const videoElement = similarVideoRefs.current[videoId]
      if (videoElement) {
        // Make sure the video has a source
        if (!videoElement.src) {
          console.log(`Setting video source for ${videoId}: ${videoData.video_url}`)
          videoElement.src = videoData.video_url
          videoElement.load()
        }

        videoElement.currentTime = 0
        videoElement.play().catch((err) => {
          console.error(`Error playing similar video ${videoId}:`, err)

          // Only show errors that aren't related to interrupted play requests
          if (!err.message.includes("interrupted") && !err.message.includes("aborted")) {
            setVideoErrors((prev) => ({ ...prev, [videoId]: `Failed to play: ${err.message}` }))
          }
        })
      }
    }, 100) 
  }

  const stopSimilarVideo = (videoId: string) => {
    // Cancel any pending play requests for this video
    playRequestsRef.current[videoId] = false

    if (playingSimilarVideoId === videoId) {
      const videoElement = similarVideoRefs.current[videoId]
      if (videoElement) {
        videoElement.pause()
      }
      setPlayingSimilarVideoId(null)
    }
  }

  useEffect(() => {
    if (!videoData) return

    const setupVideo = async () => {
      try {
        const videoElement = videoRef.current
        if (!videoElement) return

        // Get the full video URL
        const fullVideoUrl = getFullVideoUrl(videoData.video_url)

        // Only set up the video source once per video
        if (videoSourceRef.current !== fullVideoUrl) {
          console.log(`Setting up main video with URL: ${fullVideoUrl}`)

          setVideoSourceLoaded(false)
          setIsPlaying(false)

          // Set the video source
          videoElement.src = fullVideoUrl
          videoSourceRef.current = fullVideoUrl
          videoElement.load()

          // Add event listeners for the video element
          const handleLoadedData = () => {
            console.log("Video source loaded successfully")
            setVideoSourceLoaded(true)

            // If we have a selected clip, set the start time
            if (selectedClip) {
              videoElement.currentTime = selectedClip.start
            }
          }

          const handleError = (e: any) => {
            console.error("Video error:", e)
            console.error("Video error details:", e.target.error)
            setError(`Error loading video: ${e.target.error?.message || "Unknown error"}`)
            setVideoSourceLoaded(false)
          }

          videoElement.addEventListener("loadeddata", handleLoadedData)
          videoElement.addEventListener("error", handleError)

          return () => {
            videoElement.removeEventListener("loadeddata", handleLoadedData)
            videoElement.removeEventListener("error", handleError)
          }
        } else if (selectedClip && videoSourceLoaded) {
          // If the video source is already loaded and we're just switching clips
          videoElement.currentTime = selectedClip.start
        }
      } catch (error) {
        console.error("Error setting up video:", error)
        setError("An unexpected error occurred while setting up the video.")
      }
    }

    setupVideo()
  }, [videoData])

  // Separate effect for handling clip changes
  useEffect(() => {
    if (!videoRef.current || !selectedClip || !videoSourceLoaded) return

    console.log(`Switching to clip: ${selectedClip.start} - ${selectedClip.end}`)
    setIsClipSwitching(true)

    const videoElement = videoRef.current

    // Set the current time to the clip start
    videoElement.currentTime = selectedClip.start

    const handleTimeUpdate = () => {
      if (selectedClip && videoElement.currentTime >= selectedClip.end) {
        videoElement.pause()
        setIsPlaying(false)
      }
    }

    videoElement.addEventListener("timeupdate", handleTimeUpdate)

    // Set a timeout to hide the switching indicator
    clipSwitchTimeoutRef.current = setTimeout(() => {
      setIsClipSwitching(false)
    }, 500)

    if (isPlaying) {
      videoElement.play().catch((err) => {
        console.error("Error playing video after clip switch:", err)
        setIsPlaying(false)
      })
    }

    return () => {
      videoElement.removeEventListener("timeupdate", handleTimeUpdate)
      if (clipSwitchTimeoutRef.current) {
        clearTimeout(clipSwitchTimeoutRef.current)
        clipSwitchTimeoutRef.current = null
      }
    }
  }, [selectedClip, videoSourceLoaded])

  const togglePlayPause = () => {
    if (!videoRef.current || !videoSourceLoaded) return

    if (isPlaying) {
      videoRef.current.pause()
      setIsPlaying(false)
    } else {
      if (selectedClip && videoRef.current.currentTime >= selectedClip.end) {
        videoRef.current.currentTime = selectedClip.start
      }

      videoRef.current
        .play()
        .then(() => {
          setIsPlaying(true)
        })
        .catch((err) => {
          console.error("Error playing video:", err)
          setError("Failed to play video. Please try again.")
          setIsPlaying(false)
        })
    }
  }

  // Format time (seconds) to MM:SS format
  const formatTime = (seconds: number): string => {
    const mins = Math.floor(seconds / 60)
    const secs = Math.floor(seconds % 60)
    return `${mins.toString().padStart(2, "0")}:${secs.toString().padStart(2, "0")}`
  }

  // Format clip duration
  const formatDuration = (start: number, end: number): string => {
    const duration = end - start
    return formatTime(duration)
  }

  // Format confidence
  const formatConfidence = (confidence: string): string => {
    return confidence.charAt(0).toUpperCase() + confidence.slice(1).toLowerCase()
  }

  // Get the highest score from clips if video score is null
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

  // Format score to 2 decimal places
  const formatScore = (score: number | null | undefined): string => {
    if (score === undefined || score === null) return "N/A"
    return score.toFixed(2)
  }

  // Select a clip
  const handleSelectClip = (clip: Clip) => {
    setSelectedClip(clip)
  }

  // Navigate to previous video
  const goToPreviousVideo = () => {
    if (currentVideoIndex > 0) {
      const previousVideo = allVideos[currentVideoIndex - 1]
      router.push(`/detail/${previousVideo.video_id}`)
    }
  }

  // Navigate to next video
  const goToNextVideo = () => {
    if (currentVideoIndex < allVideos.length - 1) {
      const nextVideo = allVideos[currentVideoIndex + 1]
      router.push(`/detail/${nextVideo.video_id}`)
    }
  }

  // Navigate back to search results
  const goBackToSearch = () => {
    // Navigate directly to the search page with the last query
    if (lastSearchQuery) {
      router.push(`/search?q=${encodeURIComponent(lastSearchQuery)}`)
    } else {
      // If no query is stored, just go to the search page
      router.push("/search")
    }
  }

  // Handle clicking on a similar video
  const handleSimilarVideoClick = (videoId: string) => {
    // If we have similar videos for the current video, make sure they're cached
    if (similarVideos.length > 0 && videoData) {
      try {
        // Store the current similar videos in cache before navigating
        sessionStorage.setItem(`similar_videos_${videoData.video_id}`, JSON.stringify(similarVideos))
      } catch (err) {
        console.error("Error caching similar videos:", err)
      }
    }

    console.log(`Navigating to video detail: ${videoId}`)

    // Navigate to the new video detail page
    router.push(`/detail/${videoId}`)
  }

  // Check if navigation is possible
  const hasPreviousVideo = currentVideoIndex > 0
  const hasNextVideo = currentVideoIndex < allVideos.length - 1 && currentVideoIndex !== -1

  if (isLoading) {
    return (
      <div className="min-h-screen flex flex-col items-center justify-center bg-white">
        <div className="relative w-24 h-24">
          <div className="absolute inset-0 rounded-full border-t-4 border-b-4 border-brand-teal-500 animate-spin"></div>
          <div className="absolute inset-2 rounded-full border-r-4 border-l-4 border-brand-green-500 animate-spin animation-delay-150"></div>
          <div className="absolute inset-4 rounded-full border-t-4 border-b-4 border-brand-teal-300 animate-spin animation-delay-300"></div>
          <div className="absolute inset-6 rounded-full border-r-4 border-l-4 border-brand-green-300 animate-spin animation-delay-450"></div>
        </div>
        <p className="mt-6 text-lg text-brand-teal-600 font-medium">Loading video details...</p>
      </div>
    )
  }

  if (error && !videoData) {
    return (
      <div className="min-h-screen flex flex-col items-center justify-center bg-white p-4">
        <div className="text-center max-w-md">
          <AlertCircle className="h-16 w-16 text-red-500 mx-auto mb-4" />
          <h1 className="text-2xl font-bold text-gray-800 mb-2">Error Loading Video</h1>
          <p className="text-gray-600 mb-6">{error}</p>
          <button
            onClick={goBackToSearch}
            className="px-4 py-2 bg-brand-teal-500 text-white rounded-md hover:bg-brand-teal-600 transition-colors"
          >
            Go Back to Search
          </button>
        </div>
      </div>
    )
  }

  if (!videoData) {
    return (
      <div className="min-h-screen flex flex-col items-center justify-center bg-white p-4">
        <div className="text-center max-w-md">
          <h1 className="text-2xl font-bold text-gray-800 mb-2">Video Not Found</h1>
          <p className="text-gray-600 mb-6">The requested video could not be found.</p>
          <button
            onClick={goBackToSearch}
            className="px-4 py-2 bg-brand-teal-500 text-white rounded-md hover:bg-brand-teal-600 transition-colors"
          >
            Go Back to Search
          </button>
        </div>
      </div>
    )
  }

  // Get the video score (either from video.score or highest clip score)
  const videoScore = getVideoScore(videoData)

  return (
    <div className="min-h-screen flex flex-col bg-white">
      <header className="backdrop-blur-md bg-white/90 sticky top-0 z-50 border-b border-gray-100">
        <div className="container mx-auto px-4 py-3 flex items-center justify-between">
          <div className="flex items-center gap-8">
            <Link href="/" className="flex items-center">
              <Image src="/logo.jpg" alt="Nature Footage" width={50} height={50} className="mr-2 rounded-full" />
              <span className="text-xl font-bold text-brand-teal-600">
                Nature<span className="text-brand-green-600">Footage</span>
              </span>
            </Link>
          </div>

          <nav className="hidden md:flex items-center gap-6">
            <Link href="/#browse" className="text-gray-700 hover:text-brand-teal transition-colors">
              Browse
            </Link>
            <Link
              href="https://www.naturefootage.com/overview"
              target="_blank"
              rel="noopener noreferrer"
              className="text-gray-700 hover:text-brand-teal transition-colors"
            >
              Contribute
            </Link>
            <Link
              href="https://www.naturefootage.com/free-research#"
              target="_blank"
              rel="noopener noreferrer"
              className="text-gray-700 hover:text-brand-teal transition-colors"
            >
              Services
            </Link>
            <Link href="/blog" className="text-gray-700 hover:text-brand-teal transition-colors">
              Blog
            </Link>
            <Link
              href="https://github.com/Hrishikesh332/TwelveLabs-Nature-Footage"
              target="_blank"
              rel="noopener noreferrer"
              className="text-brand-teal-600 hover:text-brand-teal-700 transition-colors"
            >
              <Github className="h-6 w-6" />
            </Link>
          </nav>

          <button
            onClick={goBackToSearch}
            className="flex items-center text-gray-700 hover:text-brand-teal-600 transition-colors"
          >
            <ArrowLeft className="h-5 w-5 mr-1" />
            Back to Search
          </button>
        </div>
      </header>

      <main className="flex-grow container mx-auto px-4 py-8">
        <div className="mb-6">
          <h1 className="text-3xl font-bold mb-2">
            {videoData.filename || `Video ${videoData.video_id.substring(0, 8)}`}
          </h1>
          <div className="flex items-center gap-2">
            <span className="inline-flex items-center justify-center px-2 py-1 rounded-full bg-brand-teal-500 text-white text-xs font-medium">
              RF
            </span>
            <span className="inline-flex items-center justify-center px-2 py-1 rounded-full bg-brand-green-500 text-white text-xs font-medium">
              $
            </span>
            <span className="text-gray-600">Score: {formatScore(videoScore)}</span>
          </div>
          <div className="flex items-center mt-2">
            <span className="text-sm text-gray-500">
              Video {currentVideoIndex + 1} of {allVideos.length}
            </span>
          </div>
        </div>

        <div className="grid grid-cols-1 lg:grid-cols-3 gap-8">
          {/* Left column - Video player and similar videos */}
          <div className="lg:col-span-2 space-y-8">
            {/* Video player */}
            <div>
              <div className="relative aspect-video bg-black rounded-lg overflow-hidden">
                {/* Video element */}
                <video
                  ref={videoRef}
                  className="w-full h-full object-contain"
                  playsInline
                  controls={false}
                  onPlay={() => setIsPlaying(true)}
                  onPause={() => setIsPlaying(false)}
                  onEnded={() => setIsPlaying(false)}
                />

                {/* Loading overlay - show when video source is not loaded or clip is switching */}
                {(!videoSourceLoaded || isClipSwitching) && (
                  <div className="absolute inset-0 flex items-center justify-center bg-black/50 z-40">
                    <div className="flex flex-col items-center">
                      <Loader2 className="h-10 w-10 text-white animate-spin mb-2" />
                      <p className="text-white text-sm">
                        {!videoSourceLoaded ? "Loading video..." : "Switching clip..."}
                      </p>
                    </div>
                  </div>
                )}

                {/* Error message that doesn't block the UI */}
                {error && (
                  <div className="absolute top-4 left-4 right-4 bg-red-500/80 text-white px-4 py-2 rounded-md z-50">
                    <p className="text-sm font-medium">{error}</p>
                    <button
                      onClick={() => setError(null)}
                      className="absolute top-2 right-2 text-white"
                      aria-label="Dismiss error"
                    >
                      ×
                    </button>
                  </div>
                )}

                {/* Navigation arrows */}
                {hasPreviousVideo && (
                  <button
                    onClick={goToPreviousVideo}
                    className="absolute left-4 top-1/2 transform -translate-y-1/2 bg-black/50 hover:bg-black/70 text-white p-3 rounded-full transition-colors z-30"
                    aria-label="Previous video"
                  >
                    <ChevronLeft className="h-6 w-6" />
                  </button>
                )}

                {hasNextVideo && (
                  <button
                    onClick={goToNextVideo}
                    className="absolute right-4 top-1/2 transform -translate-y-1/2 bg-black/50 hover:bg-black/70 text-white p-3 rounded-full transition-colors z-30"
                    aria-label="Next video"
                  >
                    <ChevronRight className="h-6 w-6" />
                  </button>
                )}

                {/* Play/Pause overlay - only show when video is loaded and not switching clips */}
                {videoSourceLoaded && !isClipSwitching && (
                  <div
                    className="absolute inset-0 flex items-center justify-center bg-black/20 cursor-pointer z-20"
                    onClick={togglePlayPause}
                  >
                    <button
                      className="p-4 bg-black/40 rounded-full hover:bg-black/60 transition-colors"
                      aria-label={isPlaying ? "Pause video" : "Play video"}
                    >
                      {isPlaying ? (
                        <Pause className="h-10 w-10 text-white" />
                      ) : (
                        <Play className="h-10 w-10 text-white" />
                      )}
                    </button>
                  </div>
                )}

                {/* Clip time indicator */}
                {selectedClip && videoSourceLoaded && (
                  <div className="absolute bottom-4 left-4 right-4 bg-black/60 text-white px-3 py-1 rounded-md text-sm z-30">
                    <div className="flex justify-between">
                      <span>
                        Clip: {formatTime(selectedClip.start)} - {formatTime(selectedClip.end)}
                      </span>
                      <span>Duration: {formatDuration(selectedClip.start, selectedClip.end)}</span>
                    </div>
                  </div>
                )}
              </div>

              {/* Video navigation controls below the player */}
              <div className="flex justify-between mt-4">
                <button
                  onClick={goToPreviousVideo}
                  disabled={!hasPreviousVideo}
                  className={`flex items-center px-4 py-2 rounded-md ${
                    hasPreviousVideo
                      ? "bg-gray-100 hover:bg-gray-200 text-gray-700"
                      : "bg-gray-100 text-gray-400 cursor-not-allowed"
                  }`}
                >
                  <ArrowLeft className="h-4 w-4 mr-2" />
                  Previous Video
                </button>

                {/* Recommend Similar button */}
                <button
                  onClick={fetchSimilarVideos}
                  disabled={isLoadingSimilar}
                  className={`flex items-center px-4 py-2 rounded-md bg-brand-teal-500 hover:bg-brand-teal-600 text-white transition-colors ${
                    isLoadingSimilar ? "opacity-70 cursor-wait" : ""
                  }`}
                >
                  {isLoadingSimilar ? (
                    <span className="flex items-center">
                      <svg
                        className="animate-spin -ml-1 mr-2 h-4 w-4 text-white"
                        xmlns="http://www.w3.org/2000/svg"
                        fill="none"
                        viewBox="0 0 24 24"
                      >
                        <circle
                          className="opacity-25"
                          cx="12"
                          cy="12"
                          r="10"
                          stroke="currentColor"
                          strokeWidth="4"
                        ></circle>
                        <path
                          className="opacity-75"
                          fill="currentColor"
                          d="M4 12a8 8 0 018-8V0C5.373 0 0 5.373 0 12h4zm2 5.291A7.962 7.962 0 014 12H0c0 3.042 1.135 5.824 3 7.938l3-2.647z"
                        ></path>
                      </svg>
                      Loading...
                    </span>
                  ) : (
                    <>
                      <ThumbsUp className="h-4 w-4 mr-2" />
                      Recommend Similar
                    </>
                  )}
                </button>

                <button
                  onClick={goToNextVideo}
                  disabled={!hasNextVideo}
                  className={`flex items-center px-4 py-2 rounded-md ${
                    hasNextVideo
                      ? "bg-gray-100 hover:bg-gray-200 text-gray-700"
                      : "bg-gray-100 text-gray-400 cursor-not-allowed"
                  }`}
                >
                  Next Video
                  <ArrowRight className="h-4 w-4 ml-2" />
                </button>
              </div>
            </div>

            {/* Similar Videos Section - Only in left column */}
            {similarVideos.length > 0 && (
              <div className="mt-8">
                <div className="flex justify-between items-center mb-4">
                  <h2 className="text-xl font-bold">Similar Videos</h2>
                  {similarVideos[0]?.source && (
                    <span className="text-xs px-2 py-1 bg-gray-100 rounded-full text-gray-600">
                      Source: {similarVideos[0].source}
                    </span>
                  )}
                </div>

                <div className="grid grid-cols-1 sm:grid-cols-2 gap-4">
                  {similarVideos.map((video) => {
                    // Get the video URL directly from the processed data
                    const videoUrl = video.video_url
                    const isHovered = hoveredSimilarVideoId === video.video_id
                    const isPlaying = playingSimilarVideoId === video.video_id
                    const hasError = !!videoErrors[video.video_id]
                    const isLoaded = !!videoLoaded[video.video_id]

                    console.log(`Rendering similar video: ${video.video_id}`)
                    console.log(`Video URL: ${videoUrl}`)
                    console.log(`Has error: ${hasError}, Is hovered: ${isHovered}, Is playing: ${isPlaying}`)

                    return (
                      <div
                        key={video.video_id}
                        className="relative overflow-hidden rounded-lg border border-gray-200 hover:shadow-lg transition-all duration-300"
                        onClick={() => handleSimilarVideoClick(video.video_id)}
                        onMouseEnter={() => {
                          setHoveredSimilarVideoId(video.video_id)
                          playSimilarVideo(video.video_id)
                        }}
                        onMouseLeave={() => {
                          setHoveredSimilarVideoId(null)
                          stopSimilarVideo(video.video_id)
                        }}
                      >
                        {/* Video container with fixed aspect ratio */}
                        <div className="relative aspect-video cursor-pointer">
                          {}
                          <video
                            ref={(el) => (similarVideoRefs.current[video.video_id] = el)}
                            src={videoUrl} 
                            className="absolute inset-0 w-full h-full object-cover"
                            playsInline
                            muted
                            loop
                            onClick={(e) => e.stopPropagation()}
                            onEnded={() => setPlayingSimilarVideoId(null)}
                            onError={(e) => {
                              console.error(`Error loading similar video ${video.video_id}:`, e)
                              console.error(`Video URL that failed: ${videoUrl}`)
                              console.error(`Error details:`, e.currentTarget.error)
                              setVideoErrors((prev) => ({
                                ...prev,
                                [video.video_id]: `Error: ${e.currentTarget.error?.message || "Unknown error"}`,
                              }))
                            }}
                            onLoadedData={() => {
                              console.log(`Similar video loaded successfully: ${video.video_id}`)
                              setVideoLoaded((prev) => ({ ...prev, [video.video_id]: true }))
                            }}
                          />

                          {/* Dark gradient overlay for better text readability */}
                          <div className="absolute inset-0 bg-gradient-to-t from-black/70 via-transparent to-black/30 z-20"></div>

                          {/* Top right metadata - Similarity Score */}
                          <div className="absolute top-2 right-2 z-30">
                            <span className="text-xs px-2 py-0.5 rounded-md bg-brand-teal-500 text-white font-medium">
                              {video.similarity_percentage
                                ? `${video.similarity_percentage.toFixed(1)}%`
                                : video.similarity_score
                                  ? `${(video.similarity_score * 100).toFixed(1)}%`
                                  : "Similar"}
                            </span>
                          </div>

                          {/* Bottom metadata - Filename */}
                          <div className="absolute bottom-0 left-0 right-0 p-2 z-30">
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
                              </div>
                            </div>
                          </div>

                          {/* Play/Pause button overlay - only show when hovered */}
                          {isHovered && !hasError && (
                            <div className="absolute inset-0 flex items-center justify-center bg-black/20 transition-opacity duration-200 z-40">
                              <button
                                onClick={(e) => {
                                  e.stopPropagation()
                                  handleSimilarVideoClick(video.video_id)
                                }}
                                className="p-3 bg-black/40 rounded-full hover:bg-black/60 transition-colors"
                                aria-label="View video details"
                              >
                                <Play className="h-8 w-8 text-white" />
                              </button>
                            </div>
                          )}

                          {/* Error message overlay - only show for non interruption errors */}
                          {hasError && !videoErrors[video.video_id].includes("interrupted") && (
                            <div className="absolute inset-0 flex items-center justify-center bg-black/70 z-50">
                              <div className="text-center p-4">
                                <AlertCircle className="h-8 w-8 text-red-500 mx-auto mb-2" />
                                <p className="text-white text-sm">
                                  {videoErrors[video.video_id] || "An error occurred"}
                                </p>
                                <button
                                  onClick={(e) => {
                                    e.stopPropagation()
                                    setVideoErrors((prev) => {
                                      const newErrors = { ...prev }
                                      delete newErrors[video.video_id]
                                      return newErrors
                                    })
                                    setPlayingSimilarVideoId(null)
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
              </div>
            )}

            {similarError && (
              <div className="mt-4 p-4 bg-red-50 border border-red-200 rounded-lg">
                <div className="flex items-start">
                  <AlertCircle className="h-5 w-5 text-red-500 mt-0.5 mr-2" />
                  <div>
                    <h3 className="font-medium text-red-800">Error loading similar videos</h3>
                    <p className="text-red-700 text-sm mt-1">{similarError}</p>

                    {similarErrorDetails && (
                      <div className="mt-2 p-2 bg-red-100 rounded text-xs font-mono text-red-800 max-h-32 overflow-auto">
                        {similarErrorDetails}
                      </div>
                    )}

                    <div className="mt-3">
                      <button
                        onClick={fetchSimilarVideos}
                        className="px-3 py-1 bg-red-100 hover:bg-red-200 text-red-800 text-sm rounded transition-colors"
                      >
                        Try Again
                      </button>
                    </div>
                  </div>
                </div>
              </div>
            )}

            {/* Loading state for similar videos */}
            {isLoadingSimilar && similarVideos.length === 0 && !similarError && (
              <div className="mt-8 p-6 flex flex-col items-center justify-center">
                <div className="relative w-12 h-12">
                  <div className="absolute inset-0 rounded-full border-t-4 border-b-4 border-brand-teal-500 animate-spin"></div>
                  <div className="absolute inset-2 rounded-full border-r-4 border-l-4 border-brand-green-500 animate-spin animation-delay-150"></div>
                </div>
                <p className="mt-4 text-brand-teal-600 text-sm">Loading similar videos...</p>
              </div>
            )}
          </div>

          {/* Right column - Clips section and Metadata */}
          <div className="lg:col-span-1">
            {/* Clips section */}
            <div className="bg-gray-50 rounded-lg p-4">
              <h2 className="text-xl font-semibold mb-4">Clips</h2>

              {videoData.clips && videoData.clips.length > 0 ? (
                <div className="space-y-4">
                  {videoData.clips.map((clip, index) => (
                    <div
                      key={index}
                      className={`p-3 rounded-lg cursor-pointer transition-colors ${
                        selectedClip === clip
                          ? "bg-brand-teal-100 border border-brand-teal-300"
                          : "bg-white border border-gray-200 hover:bg-gray-50"
                      }`}
                      onClick={() => handleSelectClip(clip)}
                    >
                      <div className="flex items-start gap-3">
                        <div className="relative w-24 h-16 flex-shrink-0 rounded overflow-hidden">
                          <Image
                            src={clip.thumbnail_url || "/placeholder.svg?height=64&width=96&query=nature"}
                            alt={`Clip thumbnail`}
                            fill
                            className="object-cover"
                            unoptimized
                          />
                        </div>
                        <div className="flex-grow">
                          <div className="flex flex-col">
                            <div className="flex justify-between">
                              <span className="font-medium">Clip Duration</span>
                              <span>{formatDuration(clip.start, clip.end)}</span>
                            </div>
                            <div className="flex justify-between">
                              <span className="font-medium">Confidence</span>
                              <span>{formatConfidence(clip.confidence)}</span>
                            </div>
                            <div className="flex justify-between">
                              <span className="font-medium">Score</span>
                              <span>{formatScore(clip.score)}</span>
                            </div>
                          </div>
                        </div>
                      </div>
                    </div>
                  ))}
                </div>
              ) : (
                <p className="text-gray-500">No clips available for this video.</p>
              )}
            </div>

            {/* Video Metadata Section */}
            {videoId && <VideoMetadata videoId={videoId} />}
          </div>
        </div>
      </main>

      <footer className="bg-white py-8 border-t border-gray-100">
        <div className="container mx-auto px-4">
          <div className="grid grid-cols-1 md:grid-cols-3 gap-8">
            <div>
              <div className="flex items-center mb-4">
                <Image src="/logo.jpg" alt="Nature Footage" width={60} height={60} className="mr-3 rounded-full" />
                <div>
                  <h3 className="text-xl font-bold text-brand-teal-600">
                    Nature<span className="text-brand-green-600">Footage</span>
                  </h3>
                  <p className="text-sm text-gray-500">Premium nature footage</p>
                </div>
              </div>
              <p className="text-gray-600 mt-2">High-quality video assets for your creative projects.</p>
            </div>

            <div>
              <h3 className="font-medium text-brand-teal-700 mb-4">Categories</h3>
              <ul className="space-y-2">
                <li>
                  <Link href="#" className="text-gray-600 hover:text-brand-teal transition-colors">
                    Pro Access
                  </Link>
                </li>
                <li>
                  <Link href="#" className="text-gray-600 hover:text-brand-teal transition-colors">
                    Bestsellers
                  </Link>
                </li>
                <li>
                  <Link href="#" className="text-gray-600 hover:text-brand-teal transition-colors">
                    4K to 8K Ultra HD
                  </Link>
                </li>
              </ul>
            </div>

            <div>
              <h3 className="font-medium text-brand-teal-700 mb-4">Legal</h3>
              <ul className="space-y-2">
                <li>
                  <Link href="#" className="text-gray-600 hover:text-brand-teal transition-colors">
                    Terms of Service
                  </Link>
                </li>
                <li>
                  <Link href="#" className="text-gray-600 hover:text-brand-teal transition-colors">
                    Privacy Policy
                  </Link>
                </li>
                <li>
                  <Link href="#" className="text-gray-600 hover:text-brand-teal transition-colors">
                    License Information
                  </Link>
                </li>
              </ul>
            </div>
          </div>

          <div className="mt-8 pt-6 border-t flex flex-col md:flex-row justify-between items-center">
            <p className="text-gray-500 text-sm">© 2025 NatureFootage, Inc. All Rights Reserved</p>
            <div className="flex space-x-6 mt-4 md:mt-0">
              <Link
                href="https://github.com/Hrishikesh332/TwelveLabs-Nature-Footage"
                target="_blank"
                rel="noopener noreferrer"
                aria-label="GitHub"
                className="text-gray-400 hover:text-brand-teal-500 transition-colors"
              >
                <Github className="h-5 w-5" />
              </Link>
              <Link
                href="https://www.naturefootage.com"
                target="_blank"
                rel="noopener noreferrer"
                aria-label="Website"
                className="text-gray-400 hover:text-brand-teal-500 transition-colors"
              >
                <Globe className="h-5 w-5" />
              </Link>
              <Link
                href="https://www.naturefootage.com/features"
                target="_blank"
                rel="noopener noreferrer"
                aria-label="Features"
                className="text-gray-400 hover:text-brand-teal-500 transition-colors"
              >
                <Layers className="h-5 w-5" />
              </Link>
              <Link
                href="https://www.naturefootage.com/integrations"
                target="_blank"
                rel="noopener noreferrer"
                aria-label="Integrations"
                className="text-gray-400 hover:text-brand-teal-500 transition-colors"
              >
                <PuzzlePiece className="h-5 w-5" />
              </Link>
            </div>
          </div>
        </div>
      </footer>
    </div>
  )
}
