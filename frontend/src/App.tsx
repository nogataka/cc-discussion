import { useState } from 'react'
import { BrowserRouter, Routes, Route, Link, Navigate } from 'react-router-dom'
import { QueryClient, QueryClientProvider } from '@tanstack/react-query'
import { Settings } from 'lucide-react'
import { RoomPage } from './pages/RoomPage'
import { ErrorBoundary } from './components/ErrorBoundary'
import { ToolSettingsModal } from './components/ToolSettingsModal'

const queryClient = new QueryClient({
  defaultOptions: {
    queries: {
      refetchOnWindowFocus: false,
      retry: 1,
    },
  },
})

function App() {
  const [showSettings, setShowSettings] = useState(false)

  return (
    <ErrorBoundary>
      <QueryClientProvider client={queryClient}>
        <BrowserRouter>
          <div className="min-h-screen bg-background">
            {/* Header - Full Width */}
            <header className="sticky top-0 z-50 h-[73px] bg-slate-900 border-b border-slate-700">
              <div className="h-full px-4 flex items-center justify-between">
                <Link to="/" className="flex items-center gap-2">
                  <img src="/vite.svg" alt="Discussion Room Logo" className="w-8 h-8" />
                  <h1 className="text-xl font-bold text-white tracking-tight">
                    Discussion Room
                  </h1>
                </Link>
                <button
                  onClick={() => setShowSettings(true)}
                  className="flex items-center gap-2 px-3 py-2 rounded-lg hover:bg-slate-700 text-slate-400 hover:text-white transition-colors"
                >
                  <Settings className="w-5 h-5" />
                  <span className="text-sm">設定</span>
                </button>
              </div>
            </header>

            <ToolSettingsModal
              isOpen={showSettings}
              onClose={() => setShowSettings(false)}
            />

            {/* Main Content */}
            <Routes>
              <Route path="/" element={<Navigate to="/room" replace />} />
              <Route path="/room" element={<RoomPage />} />
              <Route path="/room/:roomId" element={<RoomPage />} />
            </Routes>
          </div>
        </BrowserRouter>
      </QueryClientProvider>
    </ErrorBoundary>
  )
}

export default App
