"use client"

import { Search } from "lucide-react"
import { useState, type FormEvent } from "react"
import { useRouter } from "next/navigation"

export default function SearchBar() {
  const [query, setQuery] = useState("")
  const [isLoading, setIsLoading] = useState(false)
  const router = useRouter()

  const handleSearch = async (e: FormEvent) => {
    e.preventDefault()

    if (!query.trim()) return

    setIsLoading(true)

    // Navigate to search page with loading state
    router.push(`/search?q=${encodeURIComponent(query.trim())}&loading=true`)
  }

  return (
    <form onSubmit={handleSearch} className="relative w-full max-w-3xl">
      <div className="relative">
        <input
          type="text"
          value={query}
          onChange={(e) => setQuery(e.target.value)}
          placeholder="Search high-quality video assets"
          className="w-full pl-4 pr-12 py-2 rounded-lg focus:outline-none focus:ring-2 focus:ring-brand-teal-500 bg-white border border-gray-200"
          disabled={isLoading}
        />
        <button
          type="submit"
          className="absolute inset-y-0 right-0 px-3 flex items-center"
          aria-label="Search"
          disabled={isLoading}
        >
          <div className="h-8 w-8 flex items-center justify-center rounded-full bg-brand-teal-500 text-white hover:bg-brand-teal-600 transition-colors">
            {isLoading ? (
              <div className="h-4 w-4 border-2 border-white border-t-transparent rounded-full animate-spin"></div>
            ) : (
              <Search className="h-4 w-4" />
            )}
          </div>
        </button>
      </div>
    </form>
  )
}
