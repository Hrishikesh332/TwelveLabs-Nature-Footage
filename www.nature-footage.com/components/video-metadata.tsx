"use client"

import { useState, useEffect } from "react"
import {
  Info,
  Map,
  Clock,
  Cloud,
  Compass,
  Thermometer,
  Camera,
  Move,
  Fish,
  Layers,
  AlertCircle,
  RefreshCw,
  Tags,
  Play,
  FileText,
  Zap,
  Target,
  Eye,
} from "lucide-react"
import { BACKEND_URL } from "@/config/api-config"

interface VideoMetadataProps {
  videoId: string
}

// Updated interface to match actual API response
interface VideoApiResponse {
  _id: string
  created_at: string
  updated_at: string
  system_metadata: {
    duration: number
    filename: string
    fps: number
    height: number
    size: number
    width: number
  }
  user_metadata: {
    analysis_action?: string
    analysis_environment_location?: string
    analysis_environment_position?: string
    analysis_keywords?: string
    analysis_narrativeflow?: string
    analysis_shot?: string
    analysis_subject_classification?: string
    analysis_subject_speciescategory?: string
    analysis_summary?: string
    filename?: string
  }
  hls: {
    status: string
    thumbnail_urls?: string[]
    updated_at: string
    video_url: string
  }
}

export default function VideoMetadata({ videoId }: VideoMetadataProps) {
  const [videoData, setVideoData] = useState<VideoApiResponse | null>(null)
  const [isLoading, setIsLoading] = useState(true)
  const [error, setError] = useState<string | null>(null)

  useEffect(() => {
    const fetchMetadata = async () => {
      if (!videoId) return

      setIsLoading(true)
      setError(null)

      try {
        // Check if we have cached video data for this video
        const cachedData = sessionStorage.getItem(`video_data_${videoId}`)
        if (cachedData) {
          try {
            const parsedData = JSON.parse(cachedData)
            setVideoData(parsedData)
            setIsLoading(false)
            console.log("Using cached video data for:", videoId)
            return
          } catch (err) {
            console.error("Error parsing cached video data:", err)
          }
        }

        // Fetch complete video data from API (includes both system and user metadata)
        const response = await fetch(`${BACKEND_URL}/api/videos/${videoId}`)

        if (!response.ok) {
          throw new Error(`Failed to fetch video data: ${response.status} ${response.statusText}`)
        }

        const data = await response.json()
        setVideoData(data)

        // Cache the video data
        sessionStorage.setItem(`video_data_${videoId}`, JSON.stringify(data))
      } catch (err) {
        console.error("Error fetching video data:", err)
        setError(err instanceof Error ? err.message : "Failed to load video data")
      } finally {
        setIsLoading(false)
      }
    }

    fetchMetadata()
  }, [videoId])

  const formatDuration = (seconds: number) => {
    const minutes = Math.floor(seconds / 60)
    const remainingSeconds = Math.floor(seconds % 60)
    return `${minutes}:${remainingSeconds.toString().padStart(2, '0')}`
  }

  const formatFileSize = (bytes: number) => {
    const mb = bytes / (1024 * 1024)
    return `${mb.toFixed(1)} MB`
  }

  const parseNarrativeFlowWithHighlights = (narrativeText: string) => {
    // Parse the narrative flow to highlight timestamps
    const timeRegex = /(\d{2}:\d{2})(?:–(\d{2}:\d{2}))?/g
    const parts: Array<{
      type: 'text' | 'timestamp'
      content: string
    }> = []
    let lastIndex = 0
    let match

    while ((match = timeRegex.exec(narrativeText)) !== null) {
      // Add text before the timestamp
      if (match.index > lastIndex) {
        parts.push({
          type: 'text',
          content: narrativeText.slice(lastIndex, match.index)
        })
      }

      // Add the timestamp
      const startTime = match[1]
      const endTime = match[2]
      const fullTimestamp = endTime ? `${startTime}–${endTime}` : startTime
      
      parts.push({
        type: 'timestamp',
        content: fullTimestamp
      })

      lastIndex = timeRegex.lastIndex
    }

    // Add remaining text
    if (lastIndex < narrativeText.length) {
      parts.push({
        type: 'text',
        content: narrativeText.slice(lastIndex)
      })
    }

    return parts
  }

  if (isLoading) {
    return (
      <div className="bg-gray-50 rounded-lg p-6 mt-4">
        <div className="flex items-center justify-center">
          <RefreshCw className="h-6 w-6 text-brand-teal-500 animate-spin mr-2" />
          <p className="text-brand-teal-600">Loading video details...</p>
        </div>
      </div>
    )
  }

  if (error) {
    return (
      <div className="bg-red-50 rounded-lg p-6 mt-4">
        <div className="flex items-start">
          <AlertCircle className="h-6 w-6 text-red-500 mr-2 flex-shrink-0" />
          <div>
            <h3 className="font-medium text-red-800">Error loading details</h3>
            <p className="text-red-700 text-sm mt-1">{error}</p>
          </div>
        </div>
      </div>
    )
  }

  if (!videoData) {
    return (
      <div className="bg-gray-50 rounded-lg p-6 mt-4">
        <p className="text-gray-500 text-center">No details available for this video.</p>
      </div>
    )
  }

  const { user_metadata = {}, system_metadata = {} } = videoData || {}

  return (
    <div className="bg-gray-50 rounded-lg p-6 mt-4 space-y-6">
      <h2 className="text-2xl font-bold mb-6 flex items-center text-gray-800">
        <Info className="h-6 w-6 mr-3 text-brand-teal-600" />
        Video Analysis & Details
      </h2>

      {/* Analysis Components - Shot, Action, Subject (Stacked Vertically) */}
      <div className="space-y-4">
        {/* Shot Analysis */}
        {user_metadata.analysis_shot && (
          <div className="bg-white rounded-xl p-6 border border-gray-200 shadow-sm hover:shadow-md transition-shadow">
            <div className="flex items-start">
              <div className="p-3 bg-purple-100 rounded-lg mr-4 flex-shrink-0">
                <Camera className="h-6 w-6 text-purple-600" />
              </div>
              <div className="flex-1">
                <h4 className="font-semibold text-gray-800 text-lg mb-2">Shot Type</h4>
                <p className="text-purple-800 text-base font-medium bg-purple-50 px-4 py-2 rounded-lg">
                  {user_metadata.analysis_shot}
                </p>
              </div>
            </div>
          </div>
        )}

        {/* Action Analysis */}
        {user_metadata.analysis_action && (
          <div className="bg-white rounded-xl p-6 border border-gray-200 shadow-sm hover:shadow-md transition-shadow">
            <div className="flex items-start">
              <div className="p-3 bg-green-100 rounded-lg mr-4 flex-shrink-0">
                <Move className="h-6 w-6 text-green-600" />
              </div>
              <div className="flex-1">
                <h4 className="font-semibold text-gray-800 text-lg mb-2">Action</h4>
                <p className="text-green-800 text-base font-medium bg-green-50 px-4 py-2 rounded-lg">
                  {user_metadata.analysis_action}
                </p>
              </div>
            </div>
          </div>
        )}

        {/* Subject Analysis */}
        {user_metadata.analysis_subject_speciescategory && (
          <div className="bg-white rounded-xl p-6 border border-gray-200 shadow-sm hover:shadow-md transition-shadow">
            <div className="flex items-start">
              <div className="p-3 bg-blue-100 rounded-lg mr-4 flex-shrink-0">
                <Target className="h-6 w-6 text-blue-600" />
              </div>
              <div className="flex-1">
                <h4 className="font-semibold text-gray-800 text-lg mb-2">Subject</h4>
                <p className="text-blue-800 text-base font-medium bg-blue-50 px-4 py-2 rounded-lg">
                  {user_metadata.analysis_subject_speciescategory}
                </p>
                {user_metadata.analysis_subject_classification && (
                  <div className="mt-3 flex flex-wrap gap-2">
                    {user_metadata.analysis_subject_classification.split(', ').map((category, index) => (
                      <span key={index} className="px-3 py-1 bg-gray-100 text-gray-700 rounded-full text-sm font-medium">
                        {category.trim()}
                      </span>
                    ))}
                  </div>
                )}
              </div>
            </div>
          </div>
        )}
      </div>

      {/* Environment Information */}
      {(user_metadata.analysis_environment_location || user_metadata.analysis_environment_position) && (
        <div className="bg-white rounded-xl p-6 border border-gray-200 shadow-sm">
          <h3 className="font-semibold text-xl text-gray-800 mb-4 flex items-center">
            <Map className="h-5 w-5 mr-2 text-brand-teal-600" />
            Environment
          </h3>
          <div className="flex flex-wrap gap-3">
            {user_metadata.analysis_environment_location && (
              <div className="flex items-center bg-emerald-50 px-4 py-2 rounded-lg border border-emerald-200">
                <Map className="h-4 w-4 text-emerald-600 mr-2" />
                <span className="text-emerald-800 font-medium">{user_metadata.analysis_environment_location}</span>
              </div>
            )}
            {user_metadata.analysis_environment_position && (
              <div className="flex items-center bg-amber-50 px-4 py-2 rounded-lg border border-amber-200">
                <Compass className="h-4 w-4 text-amber-600 mr-2" />
                <span className="text-amber-800 font-medium">{user_metadata.analysis_environment_position}</span>
              </div>
            )}
          </div>
        </div>
      )}

      {/* Keywords Section */}
      {user_metadata.analysis_keywords && (
        <div className="bg-white rounded-xl p-6 border border-gray-200 shadow-sm">
          <h3 className="font-semibold text-xl text-gray-800 mb-4 flex items-center">
            <Tags className="h-5 w-5 mr-2 text-brand-teal-600" />
            Keywords & Tags
          </h3>
          <div className="flex flex-wrap gap-2">
            {user_metadata.analysis_keywords.split(', ').map((keyword, index) => (
              <span 
                key={index} 
                className="px-3 py-2 bg-gradient-to-r from-gray-100 to-gray-50 text-gray-700 rounded-lg text-sm font-medium border border-gray-200 hover:border-gray-300 transition-colors"
              >
                {keyword}
              </span>
            ))}
          </div>
        </div>
      )}

      {/* Narrative Flow Section */}
      {user_metadata.analysis_narrativeflow && (
        <div className="bg-white rounded-xl p-6 border border-gray-200 shadow-sm">
          <h3 className="font-semibold text-xl text-gray-800 mb-4 flex items-center">
            <Layers className="h-5 w-5 mr-2 text-brand-teal-600" />
            Narrative Flow
          </h3>
          <div className="text-gray-700 leading-relaxed">
            {parseNarrativeFlowWithHighlights(user_metadata.analysis_narrativeflow).map((part, index) => {
              if (part.type === 'timestamp') {
                return (
                  <span
                    key={index}
                    className="inline-flex items-center px-3 py-1 mx-1 bg-brand-teal-100 text-brand-teal-800 rounded-md font-semibold text-sm border border-brand-teal-200"
                  >
                    <Clock className="h-3 w-3 mr-1" />
                    {part.content}
                  </span>
                )
              }
              return (
                <span key={index} className="text-gray-700">
                  {part.content}
                </span>
              )
            })}
          </div>
        </div>
      )}

      {/* Technical Information */}
      <div className="bg-white rounded-xl p-6 border border-gray-200 shadow-sm">
        <h3 className="font-semibold text-xl text-gray-800 mb-4 flex items-center">
          <FileText className="h-5 w-5 mr-2 text-brand-teal-600" />
          Technical Information
        </h3>
        
        {/* First Row - Duration and Resolution */}
        <div className="grid grid-cols-1 md:grid-cols-2 gap-4 mb-4">
          <div className="flex items-center bg-gray-50 p-4 rounded-lg">
            <Clock className="h-5 w-5 text-gray-600 mr-3" />
            <div>
              <p className="text-sm text-gray-500 mb-1">Duration</p>
              <p className="text-lg font-semibold text-gray-800">{formatDuration(system_metadata.duration)}</p>
            </div>
          </div>
          <div className="flex items-center bg-gray-50 p-4 rounded-lg">
            <Eye className="h-5 w-5 text-gray-600 mr-3" />
            <div>
              <p className="text-sm text-gray-500 mb-1">Resolution</p>
              <p className="text-lg font-semibold text-gray-800">{system_metadata.width}×{system_metadata.height}</p>
            </div>
          </div>
        </div>

        {/* Second Row - Frame Rate and File Size */}
        <div className="grid grid-cols-1 md:grid-cols-2 gap-4 mb-4">
          <div className="flex items-center bg-gray-50 p-4 rounded-lg">
            <Play className="h-5 w-5 text-gray-600 mr-3" />
            <div>
              <p className="text-sm text-gray-500 mb-1">Frame Rate</p>
              <p className="text-lg font-semibold text-gray-800">{system_metadata.fps} fps</p>
            </div>
          </div>
          <div className="flex items-center bg-gray-50 p-4 rounded-lg">
            <FileText className="h-5 w-5 text-gray-600 mr-3" />
            <div>
              <p className="text-sm text-gray-500 mb-1">File Size</p>
              <p className="text-lg font-semibold text-gray-800">{formatFileSize(system_metadata.size)}</p>
            </div>
          </div>
        </div>

        {/* Filename Section */}
        <div className="pt-4 border-t border-gray-100">
          <p className="text-sm text-gray-500 mb-2">Filename</p>
          <p className="text-base font-medium text-gray-700 bg-gray-50 px-4 py-3 rounded-lg font-mono break-all">
            {system_metadata.filename}
          </p>
        </div>
      </div>
    </div>
  )
}
