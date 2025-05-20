"use client"

import { useEffect, useRef } from "react"

export default function PoweredByText() {
  const canvasRef = useRef<HTMLCanvasElement>(null)

  useEffect(() => {
    const canvas = canvasRef.current
    if (!canvas) return

    const ctx = canvas.getContext("2d")
    if (!ctx) return

    canvas.width = 400
    canvas.height = 60

    // Clear canvas
    ctx.clearRect(0, 0, canvas.width, canvas.height)

    ctx.font = "italic 16px Arial"
    ctx.fillStyle = "#333"
    ctx.textAlign = "center"
    ctx.textBaseline = "middle"

    // Label
    const text = "POWERED BY TWELVELABS"
    const centerX = canvas.width / 2
    const centerY = canvas.height / 2
    const radius = 120

    ctx.save()
    ctx.translate(centerX, centerY + radius - 10)

    // Draw the curved Label
    const angleStep = 0.8 / radius
    let angle = -Math.PI / 2 - (text.length / 2) * angleStep

    for (let i = 0; i < text.length; i++) {
      ctx.save()
      ctx.rotate(angle)
      ctx.fillText(text[i], 0, -radius)
      ctx.restore()
      angle += angleStep
    }

    ctx.restore()
  }, [])

  return (
    <div className="flex justify-center mb-2">
      <canvas ref={canvasRef} width="400" height="60" className="max-w-full" aria-label="Powered by TwelveLabs" />
    </div>
  )
}
