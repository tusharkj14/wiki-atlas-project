interface Props {
  visible: boolean
}

export default function LoadingOverlay({ visible }: Props) {
  if (!visible) return null

  return (
    <div className="absolute inset-0 z-[1000] flex items-center justify-center bg-black/30 backdrop-blur-sm">
      <div className="bg-white rounded-xl shadow-xl px-8 py-6 flex flex-col items-center gap-4 max-w-sm text-center">
        <div className="h-10 w-10 border-4 border-gray-200 border-t-blue-600 rounded-full animate-spin" />
        <div>
          <p className="font-semibold text-gray-800">Extracting locations...</p>
          <p className="text-sm text-gray-500 mt-1">
            This may take up to a minute for new articles.
          </p>
        </div>
      </div>
    </div>
  )
}
