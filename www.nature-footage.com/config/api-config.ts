export const BACKEND_URL = process.env.NEXT_PUBLIC_APP_URL


// Helper function
export function getFullVideoUrl(videoPath: string): string {
  if (!videoPath) return ""

  if (videoPath.startsWith("http")) return videoPath

  // If the path is in the format "/api/video/FILENAME.mp4"
  if (videoPath.startsWith("/api/video/")) {
    const filename = videoPath.split("/").pop() || ""
    return `${BACKEND_URL}${videoPath}`
  }

  // Extract just the filename from the path
  const filename = videoPath.split("/").pop() || videoPath

  // Proxy video streaming endpoint
  if (videoPath.includes("species/") || (!videoPath.startsWith("/") && !videoPath.startsWith("api/"))) {

    const videoEndpoint = `${BACKEND_URL}/api/video/${encodeURIComponent(filename)}`
    console.log(`Using video streaming endpoint for ${filename}: ${videoEndpoint}`)
    return videoEndpoint
  }

  // If the path already starts with a slash
  if (videoPath.startsWith("/")) {
    return `${BACKEND_URL}${videoPath}`
  }

  return `${BACKEND_URL}/${videoPath}`
}
