"use client"

import { Leaf, Fish, Users, Video } from "lucide-react"
import Link from "next/link"

export default function CategoryButtons() {
  const categories = [
    {
      name: "Nature & Wildlife",
      icon: <Leaf className="h-6 w-6" />,
      href: "/category/nature-wildlife",
    },
    {
      name: "Ocean & Underwater",
      icon: <Fish className="h-6 w-6" />,
      href: "/category/ocean-underwater",
    },
    {
      name: "People & Adventure",
      icon: <Users className="h-6 w-6" />,
      href: "/category/people-adventure",
    },
    {
      name: "4k to 8k Ultra HD",
      icon: <Video className="h-6 w-6" />,
      href: "/category/ultra-hd",
    },
  ]

  return (
    <div className="grid grid-cols-2 md:grid-cols-4 gap-4 mt-8">
      {categories.map((category) => (
        <Link
          key={category.name}
          href={category.href}
          className="flex flex-col items-center justify-center p-4 rounded-lg transition-all duration-300 hover:shadow-md bg-white border border-gray-100 hover:bg-gray-50 group"
        >
          <div className="mb-2 text-gray-700 group-hover:text-black transition-colors">{category.icon}</div>
          <span className="text-sm text-center font-medium">{category.name}</span>
        </Link>
      ))}
    </div>
  )
}
