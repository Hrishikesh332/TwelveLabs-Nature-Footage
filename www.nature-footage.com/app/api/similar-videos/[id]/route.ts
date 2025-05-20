import { NextResponse } from "next/server"
import { BACKEND_URL } from "@/config/api-config"

export async function GET(request: Request, { params }: { params: { id: string } }) {
  try {
    const videoId = params.id
    if (!videoId) {
      return NextResponse.json({ error: "Video ID is required" }, { status: 400 })
    }

    console.log(`Fetching similar videos for video ID: ${videoId}`)
    console.log(`Calling backend URL: ${BACKEND_URL}/api/similar-videos/${videoId}`)

    // Request for Similar Videos
    const response = await fetch(`${BACKEND_URL}/api/similar-videos/${videoId}`, {
      method: "GET",
      headers: {
        "Content-Type": "application/json",
      },
    })

    console.log(`Backend response status: ${response.status}`)

    if (!response.ok) {
      const errorMessage = `Similar videos API returned status ${response.status}`
      let errorDetails = ""

      try {
        const errorData = await response.json()
        console.error("Error response data:", errorData)
        errorDetails = JSON.stringify(errorData)
      } catch (e) {
        try {
          errorDetails = await response.text()
          console.error("Error response text:", errorDetails)
        } catch (e2) {
          errorDetails = "Could not parse error response"
        }
      }

      return NextResponse.json(
        {
          error: errorMessage,
          details: errorDetails,
        },
        { status: response.status },
      )
    }

    const data = await response.json()
    console.log(`Successfully fetched similar videos: ${data.similar_videos?.length || 0} results`)

    return NextResponse.json(data)
  } catch (error) {
    console.error("Similar videos API error:", error)
    return NextResponse.json(
      {
        error: "Failed to process similar videos request",
        details: error instanceof Error ? error.message : String(error),
      },
      { status: 500 },
    )
  }
}
