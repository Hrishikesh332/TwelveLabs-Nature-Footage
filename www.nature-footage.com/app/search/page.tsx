"use client"

import { useEffect, useState } from "react"
import Image from "next/image"
import Link from "next/link"
import { useSearchParams, useRouter } from "next/navigation"
import { Github, Globe, Layers, PuzzleIcon as PuzzlePiece } from "lucide-react"
import SearchBar from "@/components/search-bar"
import VideoResults from "@/components/video-results"
import type { SearchResponse } from "@/types/search"
import { BACKEND_URL } from "@/config/api-config"

export default function SearchPage() {
  const searchParams = useSearchParams()
  const router = useRouter()
  const query = searchParams.get("q") || ""
  const initialLoading = searchParams.get("loading") === "true"
  const [searchData, setSearchData] = useState<SearchResponse | null>(null)
  const [isLoading, setIsLoading] = useState(initialLoading)
  const [isLoadingMore, setIsLoadingMore] = useState(false)
  const [error, setError] = useState<string | null>(null)
  const [errorDetails, setErrorDetails] = useState<string | null>(null)

  // Search Endpoint
  const API_ENDPOINT = `${BACKEND_URL}/api/search`
  const API_NEXT_PAGE_ENDPOINT = `${BACKEND_URL}/api/search/next`

  const fetchSearchResults = async () => {
    if (!query) return

    // Check if we already have results for this query in sessionStorage
    const storedResults = sessionStorage.getItem("searchResults")
    const storedQuery = sessionStorage.getItem("lastSearchQuery")

    // If we have cached results for the same query, use them instead of fetching again
    if (storedResults && storedQuery === query && !initialLoading) {
      try {
        const parsedResults = JSON.parse(storedResults)
        const cachedSearchData = {
          success: true,
          query: query,
          options: ["visual"],
          results: parsedResults,
          pagination: {
            has_more: false,
            next_page_token: "",
            prev_page_token: null,
            limit_per_page: 15,
            total_pages: 1,
            total_results: parsedResults.length || 0,
          },
        }

        setSearchData(cachedSearchData)
        setIsLoading(false)
        console.log("Using cached search results for query:", query)
        return
      } catch (err) {
        console.error("Error parsing cached results:", err)
      }
    }

    setIsLoading(true)
    setError(null)
    setErrorDetails(null)

    // Update URL to remove loading=true
    if (searchParams.get("loading") === "true") {
      const newParams = new URLSearchParams(searchParams.toString())
      newParams.delete("loading")
      router.replace(`/search?${newParams.toString()}`)
    }

    try {
      console.log("Fetching search results for query:", query)

      const response = await fetch(API_ENDPOINT, {
        method: "POST",
        headers: {
          "Content-Type": "application/json",
        },
        body: JSON.stringify({
          query_text: query,
          options: ["visual"],
          page_limit: 15,
        }),
      })

      console.log("Search API response status:", response.status)

      if (!response.ok) {
        const errorData = await response.json().catch(() => ({ error: "Failed to parse error response" }))
        console.error("Search API error:", errorData)
        throw new Error(errorData.error || `Search failed with status: ${response.status}`, {
          cause: errorData.details || "Unknown error",
        })
      }

      const data = await response.json()
      console.log("Search results received:", data.results?.length || 0, "items")


      const processedData: SearchResponse = {
        success: true,
        query: data.query || query,
        options: data.options || ["visual"],
        results: data.results || [],
        pagination: data.pagination || {
          has_more: false,
          next_page_token: "",
          prev_page_token: null,
          limit_per_page: 15,
          total_pages: 1,
          total_results: data.results?.length || 0,
        },
      }

      // After successfully fetching results, store both results and query for caching
      if (processedData.results && processedData.results.length > 0) {
        sessionStorage.setItem("searchResults", JSON.stringify(processedData.results))
        sessionStorage.setItem("lastSearchQuery", query)
      }

      setSearchData(processedData)
    } catch (err) {
      console.error("Error fetching search results:", err)
      setError(err instanceof Error ? err.message : "Failed to load search results. Please try again.")
      setErrorDetails(err instanceof Error && err.cause ? String(err.cause) : null)
    } finally {
      setIsLoading(false)
    }
  }

  const fetchNextPage = async (pageToken: string) => {
    if (!pageToken) return

    setIsLoadingMore(true)

    try {
      console.log("Fetching next page with token:", pageToken)

      const response = await fetch(API_NEXT_PAGE_ENDPOINT, {
        method: "POST",
        headers: {
          "Content-Type": "application/json",
        },
        body: JSON.stringify({
          page_token: pageToken,
        }),
      })

      console.log("Next page API response status:", response.status)

      if (!response.ok) {
        const errorData = await response.json().catch(() => ({ error: "Failed to parse error response" }))
        console.error("Next page API error:", errorData)
        throw new Error(errorData.error || `Failed to load next page with status: ${response.status}`, {
          cause: errorData.details || "Unknown error",
        })
      }

      const data = await response.json()
      console.log("Next page results received:", data.results?.length || 0, "items")

      if (data.results && data.results.length > 0) {
        console.log("Sample result:", JSON.stringify(data.results[0], null, 2))
      }

      const sanitizedResults = (data.results || []).map((result) => {
        let score = result.score
        if (score === null || score === undefined) {
          score = null 
        } else if (typeof score === "string") {
          const parsedScore = Number.parseFloat(score)
          score = isNaN(parsedScore) ? null : parsedScore
        }

        return {
          ...result,
          score: score,
          // To Handle the clips array exists
          clips: Array.isArray(result.clips)
            ? result.clips.map((clip) => {
                let clipScore = clip.score
                if (clipScore === null || clipScore === undefined) {
                  clipScore = null
                } else if (typeof clipScore === "string") {
                  const parsedClipScore = Number.parseFloat(clipScore)
                  clipScore = isNaN(parsedClipScore) ? null : parsedClipScore
                }

                return {
                  ...clip,
                  score: clipScore,
                  confidence: clip.confidence || "medium",
                  start: typeof clip.start === "number" ? clip.start : 0,
                  end: typeof clip.end === "number" ? clip.end : 0,
                }
              })
            : [],
        }
      })

      // We need to preserve the original query and options from the searchData for the next page
      if (searchData) {
        const updatedData = {
          query: searchData.query,
          options: searchData.options,

          pagination: data.pagination || {
            has_more: false,
            next_page_token: "",
            total_pages: 1,
            total_results: 0,
          },
          // Append the new results to the existing ones
          results: [...searchData.results, ...sanitizedResults],
          success: true,
        }

        // Update sessionStorage with all results
        if (updatedData.results && updatedData.results.length > 0) {
          sessionStorage.setItem("searchResults", JSON.stringify(updatedData.results))
        }

        setSearchData(updatedData)
      } else {
        setSearchData({
          query: "",
          options: ["visual"],
          pagination: data.pagination,
          results: sanitizedResults,
          success: true,
        })
      }
    } catch (err) {
      console.error("Error fetching next page:", err)
      setError(err instanceof Error ? err.message : "Failed to load more results. Please try again.")
      setErrorDetails(err instanceof Error && err.cause ? String(err.cause) : null)
    } finally {
      setIsLoadingMore(false)
    }
  }

  useEffect(() => {
    if (query) {
      fetchSearchResults()
    }
  }, [query])

  const handleLoadMore = () => {
    if (searchData?.pagination?.next_page_token) {
      fetchNextPage(searchData.pagination.next_page_token)
    }
  }

  const totalResults = searchData?.pagination?.total_results || 0
  const currentResults = searchData?.results?.length || 0
  const displayCount = `${currentResults} of ${totalResults}`

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
            <div className="hidden md:block w-96">
              <SearchBar />
            </div>
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
        </div>
        <div className="md:hidden container mx-auto px-4 pb-3">
          <SearchBar />
        </div>
      </header>

      <main className="flex-grow container mx-auto px-4 py-8">
        <div className="mb-8">
          <h1 className="text-4xl font-bold mb-2">{query ? `${query} Video Stock Footage` : "Video Stock Footage"}</h1>
          <p className="text-gray-700">750+ Leading Nature and Underwater Video Professionals</p>
          <p className="text-gray-700">Over 6,000 Species Worldwide!</p>

          <div className="flex justify-between items-center mt-4">
            <div className="flex items-center gap-4">
              <div className="flex items-center">
                <span className="inline-flex items-center justify-center w-6 h-6 rounded-full bg-brand-teal-500 text-white text-xs font-medium mr-2">
                  RF
                </span>
                <span className="text-sm text-gray-600">Royalty Free</span>
              </div>
              <div className="flex items-center">
                <span className="inline-flex items-center justify-center w-6 h-6 rounded-full bg-purple-100 text-purple-600 text-xs font-medium mr-2">
                  RM
                </span>
                <span className="text-sm text-gray-600">Rights Managed</span>
              </div>
              <div className="flex items-center">
                <span className="inline-flex items-center justify-center w-6 h-6 rounded-full bg-green-100 text-green-600 text-xs font-medium mr-2">
                  4K
                </span>
                <span className="text-sm text-gray-600">Ultra HD</span>
              </div>
            </div>
            {!isLoading && searchData && (
              <div className="text-sm text-gray-600">
                Showing <span className="font-medium">{displayCount}</span> results
              </div>
            )}
          </div>
        </div>

        {isLoading ? (
          <div className="flex flex-col justify-center items-center py-20">
            <div className="relative w-24 h-24">
              <div className="absolute inset-0 rounded-full border-t-4 border-b-4 border-brand-teal-500 animate-spin"></div>
              <div className="absolute inset-2 rounded-full border-r-4 border-l-4 border-brand-green-500 animate-spin animation-delay-150"></div>
              <div className="absolute inset-4 rounded-full border-t-4 border-b-4 border-brand-teal-300 animate-spin animation-delay-300"></div>
              <div className="absolute inset-6 rounded-full border-r-4 border-l-4 border-brand-green-300 animate-spin animation-delay-450"></div>
            </div>
            <p className="mt-6 text-lg text-brand-teal-600 font-medium">Searching for nature footage...</p>
          </div>
        ) : error ? (
          <div className="text-center py-10">
            <p className="text-red-500 mb-2">{error}</p>
            {errorDetails && (
              <div className="bg-red-50 border border-red-200 rounded-md p-4 mb-4 max-w-2xl mx-auto">
                <p className="text-sm text-red-800 font-mono whitespace-pre-wrap">{errorDetails}</p>
              </div>
            )}
            <button
              onClick={() => fetchSearchResults()}
              className="mt-4 px-4 py-2 bg-brand-teal-500 text-white rounded-md hover:bg-brand-teal-600"
            >
              Try Again
            </button>
          </div>
        ) : searchData && searchData.results && searchData.results.length > 0 ? (
          <>
            <VideoResults results={searchData.results} />

            {searchData && searchData.pagination && searchData.pagination.has_more && (
              <div className="flex justify-center mt-12">
                <button
                  className={`px-6 py-2 border border-gray-300 rounded-lg text-gray-700 hover:bg-gray-50 transition-colors ${
                    isLoadingMore ? "opacity-50 cursor-not-allowed" : ""
                  }`}
                  onClick={handleLoadMore}
                  disabled={isLoadingMore}
                >
                  {isLoadingMore ? (
                    <span className="flex items-center">
                      <svg
                        className="animate-spin -ml-1 mr-3 h-5 w-5 text-brand-teal-500"
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
                      Loading more results...
                    </span>
                  ) : (
                    `Load More Results (${currentResults} of ${totalResults})`
                  )}
                </button>
              </div>
            )}
          </>
        ) : (
          <div className="text-center py-10">
            <p className="text-gray-500">
              {query
                ? "No videos found matching your search. Try a different search term."
                : "Enter a search term to find videos"}
            </p>
          </div>
        )}
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
