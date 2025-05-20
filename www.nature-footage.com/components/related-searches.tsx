"use client"

import Link from "next/link"

interface RelatedSearchesProps {
  query?: string
}

export default function RelatedSearches({ query = "" }: RelatedSearchesProps) {

  const relatedSearches = [
    "blacktip friendly",
    "caracal",
    "caracal",
    "blacktip reef shark",
    "blacktiger",
    "cardinalfish",
    "pine grosbeak",
    "narrowstripe cardinalfish",
    "narrowstripe cardinalfish",
    "narrowstripe cardinalfish",
    "caribbean hermit crab",
  ]

  return (
    <div className="mb-8">
      <h2 className="text-sm font-semibold uppercase text-gray-500 mb-3">RELATED SEARCHES:</h2>
      <div className="flex flex-wrap gap-2">
        {relatedSearches.map((search, index) => (
          <Link
            key={index}
            href={`/search?q=${encodeURIComponent(search)}`}
            className="px-3 py-1 bg-gray-100 text-gray-700 rounded-md text-sm hover:bg-gray-200 transition-colors"
          >
            {search}
          </Link>
        ))}
      </div>
    </div>
  )
}
