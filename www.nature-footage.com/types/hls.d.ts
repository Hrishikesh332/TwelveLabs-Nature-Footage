// Type definitions for hls.js
interface Window {
  Hls: {
    isSupported(): boolean
    Events: {
      MANIFEST_PARSED: string
      ERROR: string
      MEDIA_ATTACHED: string
      MEDIA_DETACHED: string
    }
    new (config?: {
      maxBufferLength?: number
      maxMaxBufferLength?: number
      enableWorker?: boolean
      [key: string]: any
    }): {
      loadSource(url: string): void
      attachMedia(element: HTMLVideoElement): void
      on(event: string, callback: (...args: any[]) => void): void
      destroy(): void
    }
  }
}
