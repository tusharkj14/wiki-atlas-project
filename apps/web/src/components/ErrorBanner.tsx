'use client'

interface Props {
  message: string
  onDismiss: () => void
}

export default function ErrorBanner({ message, onDismiss }: Props) {
  return (
    <div className="flex items-start gap-3 bg-red-50 border border-red-200 text-red-800 rounded-lg px-4 py-3 text-sm mx-4 mt-3">
      <svg
        xmlns="http://www.w3.org/2000/svg"
        className="h-5 w-5 flex-shrink-0 mt-0.5"
        viewBox="0 0 20 20"
        fill="currentColor"
      >
        <path
          fillRule="evenodd"
          d="M10 18a8 8 0 100-16 8 8 0 000 16zM8.707 7.293a1 1 0 00-1.414 1.414L8.586 10l-1.293 1.293a1 1 0 101.414 1.414L10 11.414l1.293 1.293a1 1 0 001.414-1.414L11.414 10l1.293-1.293a1 1 0 00-1.414-1.414L10 8.586 8.707 7.293z"
          clipRule="evenodd"
        />
      </svg>
      <span className="flex-1">{message}</span>
      <button onClick={onDismiss} className="text-red-500 hover:text-red-700 flex-shrink-0" aria-label="Dismiss">
        <svg
          xmlns="http://www.w3.org/2000/svg"
          className="h-4 w-4"
          fill="none"
          viewBox="0 0 24 24"
          stroke="currentColor"
        >
          <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M6 18L18 6M6 6l12 12" />
        </svg>
      </button>
    </div>
  )
}
