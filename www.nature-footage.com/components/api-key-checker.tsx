"use client"

import { useState, useEffect } from "react"
import { AlertCircle, CheckCircle, Copy, RefreshCw } from "lucide-react"

export default function ApiKeyChecker() {
  const [status, setStatus] = useState<"checking" | "valid" | "invalid" | "error">("checking")
  const [message, setMessage] = useState("")
  const [isVisible, setIsVisible] = useState(true)

  const checkApiKey = async () => {
    setStatus("checking")
    try {
      const response = await fetch("/api/check-key", {
        method: "GET",
      })

      if (response.ok) {
        setStatus("valid")
        setMessage("API key is valid and working correctly.")
      } else {
        const data = await response.json()
        setStatus("invalid")
        setMessage(data.details || "API key is invalid or expired. Please check your configuration.")
      }
    } catch (error) {
      setStatus("error")
      setMessage("Could not verify API key. Please check your network connection.")
    }
  }

  useEffect(() => {
    checkApiKey()
  }, [])

  if (!isVisible) return null

  return (
    <div
      className={`mb-6 p-4 rounded-lg ${
        status === "valid"
          ? "bg-green-50 border border-green-200"
          : status === "invalid"
            ? "bg-red-50 border border-red-200"
            : status === "error"
              ? "bg-yellow-50 border border-yellow-200"
              : "bg-blue-50 border border-blue-200"
      }`}
    >
      <div className="flex items-start">
        <div className="flex-shrink-0 mt-0.5">
          {status === "valid" && <CheckCircle className="h-5 w-5 text-green-500" />}
          {status === "invalid" && <AlertCircle className="h-5 w-5 text-red-500" />}
          {status === "error" && <AlertCircle className="h-5 w-5 text-yellow-500" />}
          {status === "checking" && <RefreshCw className="h-5 w-5 text-blue-500 animate-spin" />}
        </div>
        <div className="ml-3 flex-1">
          <h3
            className={`text-sm font-medium ${
              status === "valid"
                ? "text-green-800"
                : status === "invalid"
                  ? "text-red-800"
                  : status === "error"
                    ? "text-yellow-800"
                    : "text-blue-800"
            }`}
          >
            {status === "valid"
              ? "API Key Valid"
              : status === "invalid"
                ? "API Key Invalid"
                : status === "error"
                  ? "Verification Error"
                  : "Checking API Key"}
          </h3>
          <div
            className={`mt-1 text-sm ${
              status === "valid"
                ? "text-green-700"
                : status === "invalid"
                  ? "text-red-700"
                  : status === "error"
                    ? "text-yellow-700"
                    : "text-blue-700"
            }`}
          >
            <p>{message}</p>

            {status === "invalid" && (
              <div className="mt-2">
                <p className="font-medium">Troubleshooting steps:</p>
                <ol className="list-decimal ml-5 mt-1 space-y-1">
                  <li>Verify that your API key is correctly set in your environment variables</li>
                  <li>Check if your API key has expired in the TwelveLabs dashboard</li>
                  <li>Generate a new API key if necessary</li>
                  <li>Ensure the API key has the correct permissions</li>
                </ol>

                <div className="mt-3 p-3 bg-gray-100 rounded text-sm font-mono">
                  <div className="flex justify-between items-center mb-1">
                    <span className="text-gray-700">Environment Variable:</span>
                    <button
                      className="text-gray-500 hover:text-gray-700"
                      onClick={() => {
                        navigator.clipboard.writeText("API_KEY=your_api_key_here")
                        alert("Copied to clipboard!")
                      }}
                    >
                      <Copy className="h-4 w-4" />
                    </button>
                  </div>
                  <code>API_KEY=your_api_key_here</code>
                </div>
              </div>
            )}
          </div>
        </div>
        <div className="ml-auto pl-3">
          <div className="flex">
            <button
              type="button"
              className="inline-flex text-gray-400 hover:text-gray-500"
              onClick={() => setIsVisible(false)}
            >
              <span className="sr-only">Dismiss</span>
              <svg className="h-5 w-5" viewBox="0 0 20 20" fill="currentColor">
                <path
                  fillRule="evenodd"
                  d="M4.293 4.293a1 1 0 011.414 0L10 8.586l4.293-4.293a1 1 0 111.414 1.414L11.414 10l4.293 4.293a1 1 0 01-1.414 1.414L10 11.414l-4.293 4.293a1 1 0 01-1.414-1.414L8.586 10 4.293 5.707a1 1 0 010-1.414z"
                  clipRule="evenodd"
                />
              </svg>
            </button>
          </div>
        </div>
      </div>
    </div>
  )
}
