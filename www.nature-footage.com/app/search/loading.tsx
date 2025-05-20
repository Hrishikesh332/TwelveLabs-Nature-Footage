export default function Loading() {
  return (
    <div className="min-h-screen flex flex-col items-center justify-center bg-white">
      <div className="relative w-24 h-24">
        <div className="absolute inset-0 rounded-full border-t-4 border-b-4 border-brand-teal-500 animate-spin"></div>
        <div className="absolute inset-2 rounded-full border-r-4 border-l-4 border-brand-green-500 animate-spin animation-delay-150"></div>
        <div className="absolute inset-4 rounded-full border-t-4 border-b-4 border-brand-teal-300 animate-spin animation-delay-300"></div>
        <div className="absolute inset-6 rounded-full border-r-4 border-l-4 border-brand-green-300 animate-spin animation-delay-450"></div>
      </div>
      <p className="mt-6 text-lg text-brand-teal-600 font-medium">Loading nature footage...</p>
    </div>
  )
}
