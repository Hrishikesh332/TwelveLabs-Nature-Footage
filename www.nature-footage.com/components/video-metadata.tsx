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
} from "lucide-react"
import { BACKEND_URL } from "@/config/api-config"

interface VideoMetadataProps {
  videoId: string
}

interface VideoMetadata {
  analysis_action: string
  analysis_additional_details: string
  analysis_complete: boolean
  analysis_environment: string
  analysis_environment_climate: string
  analysis_environment_location: string
  analysis_environment_position: string
  analysis_environment_time: string
  analysis_environment_weatherconditions: string
  analysis_narrative_flow: string
  analysis_shot: string
  analysis_subject: string
  analysis_subject_classification: string
  analysis_subject_color: string
  analysis_subject_count: string
  analysis_subject_speciescategory: string
  analysis_subject_specific_identification: string
  analysis_subject_type: string
  analysis_summary: string
  analysis_timestamp: number
  analysis_version: string
}

export default function VideoMetadata({ videoId }: VideoMetadataProps) {
  const [metadata, setMetadata] = useState<VideoMetadata | null>(null)
  const [isLoading, setIsLoading] = useState(true)
  const [error, setError] = useState<string | null>(null)

  useEffect(() => {
    const fetchMetadata = async () => {
      if (!videoId) return

      setIsLoading(true)
      setError(null)

      try {
        // Check if we have cached metadata for this video
        const cachedMetadata = sessionStorage.getItem(`metadata_${videoId}`)
        if (cachedMetadata) {
          try {
            const parsedMetadata = JSON.parse(cachedMetadata)
            setMetadata(parsedMetadata)
            setIsLoading(false)
            console.log("Using cached metadata for:", videoId)
            return
          } catch (err) {
            console.error("Error parsing cached metadata:", err)
          }
        }

        // Fetch metadata from API
        const response = await fetch(`${BACKEND_URL}/api/metadata/${videoId}`)

        if (!response.ok) {
          throw new Error(`Failed to fetch metadata: ${response.status} ${response.statusText}`)
        }

        const data = await response.json()
        setMetadata(data)

        // Cache the metadata
        sessionStorage.setItem(`metadata_${videoId}`, JSON.stringify(data))
      } catch (err) {
        console.error("Error fetching video metadata:", err)
        setError(err instanceof Error ? err.message : "Failed to load video metadata")
      } finally {
        setIsLoading(false)
      }
    }

    fetchMetadata()
  }, [videoId])

  const parseJsonString = (jsonString: string) => {
    try {
      return JSON.parse(jsonString)
    } catch (err) {
      return null
    }
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

  if (!metadata) {
    return (
      <div className="bg-gray-50 rounded-lg p-6 mt-4">
        <p className="text-gray-500 text-center">No details available for this video.</p>
      </div>
    )
  }

  return (
    <div className="bg-gray-50 rounded-lg p-4 mt-4">
      <h2 className="text-xl font-semibold mb-4 flex items-center">
        <Info className="h-5 w-5 mr-2 text-brand-teal-600" />
        Video Details
      </h2>

      {/* Shot Summary Section */}
      <div className="bg-white rounded-lg p-4 mb-4 border border-gray-200">
        <h3 className="font-medium text-lg text-brand-teal-700 mb-2">Shot Summary</h3>
        <div className="flex flex-wrap gap-2">
          <span className="px-2 py-1 bg-brand-teal-100 text-brand-teal-800 rounded-md text-sm flex items-center">
            <Camera className="h-4 w-4 mr-1" />
            {metadata.analysis_shot}
          </span>
          <span className="px-2 py-1 bg-brand-green-100 text-brand-green-800 rounded-md text-sm flex items-center">
            <Move className="h-4 w-4 mr-1" />
            {metadata.analysis_action}
          </span>
          <span className="px-2 py-1 bg-blue-100 text-blue-800 rounded-md text-sm flex items-center">
            <Fish className="h-4 w-4 mr-1" />
            {metadata.analysis_subject_speciescategory}
          </span>
        </div>
      </div>

      {/* Environment Section */}
      <div className="bg-white rounded-lg p-4 mb-4 border border-gray-200">
        <h3 className="font-medium text-lg text-brand-teal-700 mb-2">Environment</h3>
        <div className="grid grid-cols-2 gap-3">
          <div className="flex items-center">
            <Map className="h-4 w-4 text-brand-teal-600 mr-2" />
            <div>
              <p className="text-xs text-gray-500">Location</p>
              <p className="text-sm font-medium">{metadata.analysis_environment_location}</p>
            </div>
          </div>
          <div className="flex items-center">
            <Clock className="h-4 w-4 text-brand-teal-600 mr-2" />
            <div>
              <p className="text-xs text-gray-500">Time</p>
              <p className="text-sm font-medium">{metadata.analysis_environment_time}</p>
            </div>
          </div>
          <div className="flex items-center">
            <Cloud className="h-4 w-4 text-brand-teal-600 mr-2" />
            <div>
              <p className="text-xs text-gray-500">Weather</p>
              <p className="text-sm font-medium">{metadata.analysis_environment_weatherconditions}</p>
            </div>
          </div>
          <div className="flex items-center">
            <Compass className="h-4 w-4 text-brand-teal-600 mr-2" />
            <div>
              <p className="text-xs text-gray-500">Position</p>
              <p className="text-sm font-medium">{metadata.analysis_environment_position}</p>
            </div>
          </div>
          <div className="flex items-center">
            <Thermometer className="h-4 w-4 text-brand-teal-600 mr-2" />
            <div>
              <p className="text-xs text-gray-500">Climate</p>
              <p className="text-sm font-medium">{metadata.analysis_environment_climate}</p>
            </div>
          </div>
        </div>
      </div>

      {/* Subject Section */}
      <div className="bg-white rounded-lg p-4 mb-4 border border-gray-200">
        <h3 className="font-medium text-lg text-brand-teal-700 mb-2">Subject</h3>
        <div className="grid grid-cols-2 gap-3">
          <div className="flex items-center">
            <div className="w-8 h-8 rounded-full bg-brand-teal-100 flex items-center justify-center text-brand-teal-600 mr-2">
              🦋
            </div>
            <div>
              <p className="text-xs text-gray-500">Type</p>
              <p className="text-sm font-medium">{metadata.analysis_subject_type}</p>
            </div>
          </div>
          <div className="flex items-center">
            <div className="w-8 h-8 rounded-full bg-brand-teal-100 flex items-center justify-center text-brand-teal-600 mr-2">
              🐠
            </div>
            <div>
              <p className="text-xs text-gray-500">Classification</p>
              <p className="text-sm font-medium">{metadata.analysis_subject_classification}</p>
            </div>
          </div>
          <div className="flex items-center">
            <div className="w-8 h-8 rounded-full bg-brand-green-100 flex items-center justify-center text-brand-green-600 mr-2">
              🦈
            </div>
            <div>
              <p className="text-xs text-gray-500">Species</p>
              <p className="text-sm font-medium">{metadata.analysis_subject_speciescategory}</p>
            </div>
          </div>
          <div className="flex items-center">
            <div className="w-8 h-8 rounded-full bg-brand-green-100 flex items-center justify-center text-brand-green-600 mr-2">
              🎨
            </div>
            <div>
              <p className="text-xs text-gray-500">Color</p>
              <p className="text-sm font-medium">{metadata.analysis_subject_color}</p>
            </div>
          </div>
          <div className="flex items-center">
            <div className="w-8 h-8 rounded-full bg-brand-teal-100 flex items-center justify-center text-brand-teal-600 mr-2">
              👥
            </div>
            <div>
              <p className="text-xs text-gray-500">Count</p>
              <p className="text-sm font-medium">{metadata.analysis_subject_count}</p>
            </div>
          </div>
          <div className="flex items-center">
            <div className="w-8 h-8 rounded-full bg-brand-green-100 flex items-center justify-center text-brand-green-600 mr-2">
              🔍
            </div>
            <div>
              <p className="text-xs text-gray-500">Specific ID</p>
              <p className="text-sm font-medium">{metadata.analysis_subject_specific_identification}</p>
            </div>
          </div>
        </div>
      </div>

      {/* Narrative Flow Section */}
      <div className="bg-white rounded-lg p-4 mb-4 border border-gray-200">
        <h3 className="font-medium text-lg text-brand-teal-700 mb-2 flex items-center">
          <Layers className="h-4 w-4 mr-2" />
          Narrative Flow
        </h3>
        <p className="text-sm text-gray-700">{metadata.analysis_narrative_flow}</p>
      </div>

      {/* Additional Details Section */}
      <div className="bg-white rounded-lg p-4 border border-gray-200">
        <h3 className="font-medium text-lg text-brand-teal-700 mb-2">Additional Details</h3>
        <p className="text-sm text-gray-700">{metadata.analysis_additional_details}</p>
      </div>
    </div>
  )
}
