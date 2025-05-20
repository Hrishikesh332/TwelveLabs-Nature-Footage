export interface Clip {
  confidence: string
  end: number
  start: number
  score: number
  thumbnail_url: string
}

export interface VideoResult {
  clips: Clip[]
  filename: string
  score: number
  thumbnail_url: string
  video_id: string
  video_url: string
}

export interface Pagination {
  has_more: boolean
  next_page_token: string
  prev_page_token?: string | null
  limit_per_page?: number
  total_pages: number
  total_results: number
}

export interface SearchResponse {
  options: string[]
  pagination: Pagination
  query: string
  results: VideoResult[]
  success: boolean
}
