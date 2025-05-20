"use client"

import type React from "react"
import { useEffect, useRef, useState } from "react"
import { Play } from "lucide-react"

// This component will accept video URLs as props
interface VideoGridProps {
  videoUrls?: string[]
}

interface VideoCardProps {
  videoSrc: string
  code: string
  tags: string[]
  style?: React.CSSProperties
}

function VideoCard({ videoSrc, code, tags, style = {} }: VideoCardProps) {
  const [isHovered, setIsHovered] = useState(false)
  const [isLoaded, setIsLoaded] = useState(false)
  const videoRef = useRef<HTMLVideoElement>(null)

  useEffect(() => {
    // Ensure video loads and plays
    if (videoRef.current) {
      videoRef.current.load()

      // Event listeners to track loading and errors
      const handleLoaded = () => {
        console.log(`Video loaded: ${videoSrc}`)
        setIsLoaded(true)
      }

      const handleError = (e: any) => {
        console.error(`Error loading video: ${videoSrc}`, e)
      }

      videoRef.current.addEventListener("loadeddata", handleLoaded)
      videoRef.current.addEventListener("error", handleError)

      videoRef.current.play().catch((err) => {
        console.warn(`Autoplay prevented for ${videoSrc}:`, err)
      })

      return () => {
        if (videoRef.current) {
          videoRef.current.removeEventListener("loadeddata", handleLoaded)
          videoRef.current.removeEventListener("error", handleError)
        }
      }
    }
  }, [videoSrc])

  return (
    <div
      className="relative w-full h-[180px] overflow-hidden group transition-all duration-300"
      style={{
        ...style,
        transitionProperty: "opacity, transform",
      }}
      onMouseEnter={() => setIsHovered(true)}
      onMouseLeave={() => setIsHovered(false)}
    >
      {!isLoaded && (
        <div className="absolute inset-0 flex items-center justify-center bg-gray-200 z-5">
          <div className="w-8 h-8 border-4 border-brand-teal-500 border-t-transparent rounded-full animate-spin"></div>
        </div>
      )}

      <video
        ref={videoRef}
        src={videoSrc}
        autoPlay
        loop
        muted
        playsInline
        className={`absolute inset-0 w-full h-full object-cover transition-transform duration-500 group-hover:scale-110 z-10 ${isLoaded ? "opacity-100" : "opacity-0"}`}
        onCanPlay={() => setIsLoaded(true)}
      />

      {}
      <div className="absolute inset-0 bg-gradient-to-b from-black/20 via-transparent to-black/20 z-20"></div>

      <div className="absolute bottom-0 left-0 right-0 p-3 flex justify-between items-center z-30">
        <span className="text-sm text-white font-medium drop-shadow-md">{code}</span>
        <div className="flex gap-1">
          {tags.map((tag, index) => (
            <span
              key={index}
              className={`text-xs px-2 py-0.5 rounded-full font-medium ${
                tag === "RF" ? "bg-brand-teal-500 text-white" : "bg-brand-green-500 text-white"
              }`}
            >
              {tag}
            </span>
          ))}
        </div>
      </div>

      {isHovered && (
        <div className="absolute inset-0 bg-black/40 flex items-center justify-center gap-6 opacity-0 group-hover:opacity-100 transition-opacity duration-300 z-40">
          <button
            className="p-3 bg-white rounded-full hover:bg-gray-100 transition-colors transform hover:scale-110"
            aria-label="Play video"
          >
            <Play className="h-5 w-5 text-black" />
          </button>
        </div>
      )}
    </div>
  )
}

export default function VideoGrid({ videoUrls = [] }: VideoGridProps) {
  // S3 video URLs provided
  const defaultVideoUrls = [
    "https://test-001-fashion.s3.eu-north-1.amazonaws.com/nature-footage-demo/CBE200624_0124.mp4",
    "https://test-001-fashion.s3.eu-north-1.amazonaws.com/nature-footage-demo/CBE200626_0094.mp4",
    "https://test-001-fashion.s3.eu-north-1.amazonaws.com/nature-footage-demo/CBE200627_0216.mp4",
    "https://test-001-fashion.s3.eu-north-1.amazonaws.com/nature-footage-demo/CBE200629_0003.mp4",
    "https://test-001-fashion.s3.eu-north-1.amazonaws.com/nature-footage-demo/CBE220409_0010.mp4",
    "https://test-001-fashion.s3.eu-north-1.amazonaws.com/nature-footage-demo/CFI150512_0001.mp4",
    "https://test-001-fashion.s3.eu-north-1.amazonaws.com/nature-footage-demo/CGRA161205_0002.mp4",
    "https://test-001-fashion.s3.eu-north-1.amazonaws.com/nature-footage-demo/CMO016_0010.mp4",
  ]


  const urls = videoUrls.length > 0 ? videoUrls : defaultVideoUrls

  useEffect(() => {
    console.log("VideoGrid using URLs:", urls)
  }, [urls])

  const videos = urls.map((url, index) => {
    const filename = url.split("/").pop()?.split(".")[0] || `Video_${index + 1}`

    return {
      id: index + 1,
      videoSrc: url,
      code: filename,
      tags: ["RF", "$"],
    }
  })

  
  const reversedVideos = [...videos].reverse()

  const videoHeight = 190 
  const totalHeight = videoHeight * videos.length 

  const [columnPositions, setColumnPositions] = useState({
    left: 0,
    right: -totalHeight, 
  })

  const animationRef = useRef<number | null>(null)

  // Animation function for moving videos vertically
  const animateColumns = () => {
    setColumnPositions((prev) => {
      return {
        left: prev.left <= -totalHeight ? 0 : prev.left - 0.5,
        right: prev.right >= 0 ? -totalHeight : prev.right + 0.5,
      }
    })

    animationRef.current = requestAnimationFrame(animateColumns)
  }

  useEffect(() => {
    animationRef.current = requestAnimationFrame(animateColumns)

    return () => {
      if (animationRef.current) {
        cancelAnimationFrame(animationRef.current)
      }
    }
  }, [])

  // Repeating sets of videos for each column
  const createRepeatingVideos = (videoSet: typeof videos) => {
    return [...videoSet, ...videoSet, ...videoSet]
  }

  const repeatingVideos = createRepeatingVideos(videos)
  const repeatingReversedVideos = createRepeatingVideos(reversedVideos)

  return (
    <div className="relative h-[600px] w-full overflow-hidden bg-gray-50 rounded-lg">
      <div className="absolute inset-0 grid grid-cols-2 gap-4 px-4">
        {/* Left column - moving up */}
        <div className="relative overflow-hidden" style={{ height: "100%" }}>
          <div
            className="absolute w-full flex flex-col gap-4"
            style={{ transform: `translateY(${columnPositions.left}px)` }}
          >
            {repeatingVideos.map((video, index) => (
              <VideoCard
                key={`left-${video.id}-${index}`}
                videoSrc={video.videoSrc}
                code={video.code}
                tags={video.tags}
              />
            ))}
          </div>
        </div>

        {/* Right column - moving down (starting with videos already visible) */}
        <div className="relative overflow-hidden" style={{ height: "100%" }}>
          <div
            className="absolute w-full flex flex-col gap-4"
            style={{ transform: `translateY(${columnPositions.right}px)` }}
          >
            {repeatingReversedVideos.map((video, index) => (
              <VideoCard
                key={`right-${video.id}-${index}`}
                videoSrc={video.videoSrc}
                code={video.code}
                tags={video.tags}
              />
            ))}
          </div>
        </div>
      </div>

      {/* Gradient overlays for smooth fading */}
      <div className="absolute top-0 left-0 right-0 h-20 gradient-overlay-top z-20 pointer-events-none"></div>
      <div className="absolute bottom-0 left-0 right-0 h-20 gradient-overlay-bottom z-20 pointer-events-none"></div>
    </div>
  )
}
