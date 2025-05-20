import { type NextRequest, NextResponse } from "next/server"
import { BACKEND_URL } from "@/config/api-config"

export async function GET(request: NextRequest, { params }: { params: { filename: string } }): Promise<Response> {
  const filename = params.filename
  if (!filename) {
    return new NextResponse("Filename is required", { status: 400 })
  }

  try {
    // Range header, if any limitation on the streaming is needed to be done
    const rangeHeader = request.headers.get("Range") || "bytes=0-"

    // Proxy streaming endpoint
    const videoPath = filename.includes("species/") ? filename : `species/${filename}`
    const backendUrl = `${BACKEND_URL}/api/video/${encodeURIComponent(videoPath)}`

    console.log(`Streaming video from backend: ${backendUrl}`)
    console.log(`With range header: ${rangeHeader}`)

    const response = await fetch(backendUrl, {
      headers: {
        Range: rangeHeader,
      },
    })

    if (!response.ok && response.status !== 206) {
      console.error(`Failed to fetch video: ${response.statusText} (${response.status})`)
      return new NextResponse(`Failed to fetch video: ${response.statusText}`, {
        status: response.status,
      })
    }

    const contentType = response.headers.get("Content-Type") || "video/mp4"
    const contentLength = response.headers.get("Content-Length")
    const contentRange = response.headers.get("Content-Range")

    console.log(`Response status: ${response.status}`)
    console.log(`Content-Type: ${contentType}`)
    console.log(`Content-Length: ${contentLength}`)
    console.log(`Content-Range: ${contentRange}`)

    const body = await response.arrayBuffer()

    const headers = new Headers()
    headers.set("Content-Type", contentType)
    if (contentLength) headers.set("Content-Length", contentLength)
    if (contentRange) headers.set("Content-Range", contentRange)
    headers.set("Accept-Ranges", "bytes")

    return new NextResponse(body, {
      status: response.status,
      headers,
    })
  } catch (error) {
    console.error("Error streaming video:", error)
    return new NextResponse("Error streaming video", { status: 500 })
  }
}
