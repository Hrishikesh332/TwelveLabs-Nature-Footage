"use client"

import Image from "next/image"
import Link from "next/link"
import { Github, Globe, Layers, PuzzleIcon as PuzzlePiece } from "lucide-react"
import { useRouter } from "next/navigation"
import { useRef, useState, useEffect } from "react"
import VideoGrid from "@/components/video-grid"
import CategoryButtons from "@/components/category-buttons"
import SearchBar from "@/components/search-bar"

export default function Home() {
  const router = useRouter()
  const searchRef = useRef<HTMLDivElement>(null)
  const browseRef = useRef<HTMLDivElement>(null)
  const [highlightSearch, setHighlightSearch] = useState(false)

  // Add this useEffect to handle URL hash for direct navigation
  useEffect(() => {
    if (typeof window !== "undefined") {
      if (window.location.hash === "#browse") {
        browseRef.current?.scrollIntoView({ behavior: "smooth" })
      }
    }

    // Clear highlight after animation completes
    if (highlightSearch) {
      const timer = setTimeout(() => {
        setHighlightSearch(false)
      }, 3000)
      return () => clearTimeout(timer)
    }
  }, [highlightSearch])

  const browseCategories = [
    { title: "Monkey", count: "410 videos", query: "monkey", image: "monkey.png" },
    { title: "Octopus", count: "340 videos", query: "octopus", image: "octopus.png" },
    { title: "Hibiscus Flower", count: "142 videos", query: "hibiscus flower", image: "hibiscus.png" },
  ]

  const handleCategoryClick = (query: string) => {
    router.push(`/search?q=${encodeURIComponent(query)}`)
  }

  const scrollToSearch = () => {
    window.scrollTo({ top: 0, behavior: "smooth" })
    setHighlightSearch(true)
  }

  const scrollToBrowse = () => {
    browseRef.current?.scrollIntoView({ behavior: "smooth" })
  }

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
            <button onClick={scrollToBrowse} className="text-gray-700 hover:text-brand-teal transition-colors">
              Browse
            </button>
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

      <main className="flex-grow">
        <section className="py-16 md:py-24 relative overflow-hidden">
          {/* Background elements */}
          <div className="absolute inset-0 -z-10">
            <div className="absolute top-20 left-10 w-96 h-96 rounded-full bg-brand-teal-100/30 blur-3xl"></div>
            <div className="absolute bottom-40 right-20 w-[500px] h-[500px] rounded-full bg-brand-green-100/20 blur-3xl"></div>
          </div>

          <div className="container mx-auto px-4">
            <div className="grid grid-cols-1 lg:grid-cols-2 gap-12 items-center">
              <div className="relative z-10">
                <div className="p-2">
                  <div className="flex justify-center mb-4">
                    <Link
                      href="https://twelvelabs.io"
                      target="_blank"
                      rel="noopener noreferrer"
                      className="inline-block px-6 py-2 bg-white rounded-full shadow-md hover:shadow-lg transition-all"
                    >
                      <p className="text-base font-medium text-black">Powered by TwelveLabs</p>
                    </Link>
                  </div>
                  <h1 className="text-4xl md:text-5xl lg:text-6xl font-bold leading-tight mb-6 gradient-text">
                    4K Royalty Free Video to 12K Premium Stock Footage
                  </h1>
                  <p className="text-lg text-gray-700 mb-4">750+ Leading Nature and Underwater Video Professionals</p>
                  <p className="text-lg text-gray-700 mb-8">Over 6,000 Species Worldwide!</p>

                  <div
                    ref={searchRef}
                    className={`${
                      highlightSearch
                        ? "animate-pulse ring-4 ring-brand-teal-400 rounded-lg transition-all duration-500"
                        : ""
                    }`}
                  >
                    <SearchBar />
                  </div>

                  <CategoryButtons />
                </div>
              </div>

              <div className="relative">
                {/* Decorative elements */}
                <div className="absolute -top-10 -left-10 w-20 h-20 rounded-full bg-brand-teal-200/30 animate-float"></div>
                <div
                  className="absolute -bottom-10 -right-10 w-20 h-20 rounded-full bg-brand-green-200/30 animate-float"
                  style={{ animationDelay: "2s" }}
                ></div>

                {/* Video grid with enhanced container */}
                <div className="rounded-2xl overflow-hidden shadow-xl border border-gray-100">
                  <VideoGrid />
                </div>
              </div>
            </div>
          </div>
        </section>

        {/* Browse section */}
        <section id="browse" ref={browseRef} className="py-16 bg-gradient-to-b from-white to-gray-50">
          <div className="container mx-auto px-4">
            <div className="text-center mb-12">
              <h2 className="text-3xl font-bold mb-4 gradient-text inline-block">Browse Section</h2>
              <p className="text-gray-600 max-w-2xl mx-auto">
                Explore our categories of stunning nature footage from around the world.
              </p>
            </div>

            <div className="grid grid-cols-1 md:grid-cols-3 gap-8">
              {browseCategories.map((category, index) => (
                <div
                  key={index}
                  className="bg-white rounded-xl overflow-hidden shadow-md border border-gray-100 hover-scale ripple cursor-pointer transition-all duration-300"
                  onClick={() => handleCategoryClick(category.query)}
                >
                  <div className="h-48 bg-gray-200 relative">
                    <Image src={`/${category.image}`} alt={category.title} fill className="object-cover" />
                    <div className="absolute inset-0 bg-gradient-to-t from-black/60 to-transparent"></div>
                    <div className="absolute bottom-4 left-4">
                      <span className="px-3 py-1 bg-brand-teal-500 text-white text-sm rounded-full">
                        {category.count}
                      </span>
                    </div>
                  </div>
                  <div className="p-5">
                    <h3 className="text-xl font-semibold mb-2 text-brand-teal-700">{category.title}</h3>
                    <p className="text-gray-600 mb-3">Premium {category.title.toLowerCase()} footage</p>
                    <div className="flex justify-between items-center">
                      <span className="text-brand-green-600 font-medium">Explore collection</span>
                      <svg
                        className="w-5 h-5 text-brand-green-600"
                        fill="none"
                        stroke="currentColor"
                        viewBox="0 0 24 24"
                      >
                        <path
                          strokeLinecap="round"
                          strokeLinejoin="round"
                          strokeWidth={2}
                          d="M14 5l7 7m0 0l-7 7m7-7H3"
                        />
                      </svg>
                    </div>
                  </div>
                </div>
              ))}
            </div>
          </div>
        </section>

        {/* Action section */}
        <section className="py-16 bg-gradient-to-r from-brand-teal-500 to-brand-green-500 text-white">
          <div className="container mx-auto px-4 text-center">
            <h2 className="text-3xl font-bold mb-6">Ready to Enhance Your Projects?</h2>
            <p className="text-xl mb-8 max-w-2xl mx-auto">
              Access our premium collection of nature footage and elevate your creative work.
            </p>
            <div className="flex flex-col sm:flex-row gap-4 justify-center">
              <button
                onClick={scrollToSearch}
                className="px-8 py-3 bg-white text-brand-teal-600 font-medium rounded-lg hover:shadow-lg transition-all"
              >
                Explore Now
              </button>
              <Link
                href="https://github.com/Hrishikesh332/TwelveLabs-Nature-Footage"
                target="_blank"
                rel="noopener noreferrer"
                className="px-8 py-3 bg-transparent border border-white text-white font-medium rounded-lg hover:bg-white/10 transition-all"
              >
                Know More
              </Link>
            </div>
          </div>
        </section>
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
            <p className="text-gray-500 text-sm">© 2025 TwelveLabs, Inc. All Rights Reserved</p>
            <div className="flex space-x-6 mt-4 md:mt-0">
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
                href="https://www.twelvelabs.io/product/product-overview"
                target="_blank"
                rel="noopener noreferrer"
                aria-label="Features"
                className="text-gray-400 hover:text-brand-teal-500 transition-colors"
              >
                <Layers className="h-5 w-5" />
              </Link>
              <Link
                href="https://www.twelvelabs.io/product/models-overview"
                target="_blank"
                rel="noopener noreferrer"
                aria-label="Integrations"
                className="text-gray-400 hover:text-brand-teal-500 transition-colors"
              >
                <PuzzlePiece className="h-5 w-5" />
              </Link>
              <Link
                href="https://github.com/Hrishikesh332/TwelveLabs-Nature-Footage"
                target="_blank"
                rel="noopener noreferrer"
                aria-label="GitHub"
                className="text-gray-400 hover:text-brand-teal-500 transition-colors"
              >
                <Github className="h-5 w-5" />
              </Link>
            </div>
          </div>
        </div>
      </footer>
    </div>
  )
}
