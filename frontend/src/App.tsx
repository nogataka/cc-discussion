import { BrowserRouter, Routes, Route, Link, Navigate } from 'react-router-dom'
import { QueryClient, QueryClientProvider } from '@tanstack/react-query'
import { RoomPage } from './pages/RoomPage'
import { ErrorBoundary } from './components/ErrorBoundary'

const queryClient = new QueryClient({
  defaultOptions: {
    queries: {
      refetchOnWindowFocus: false,
      retry: 1,
    },
  },
})

function App() {
  return (
    <ErrorBoundary>
      <QueryClientProvider client={queryClient}>
        <BrowserRouter>
          <div className="min-h-screen bg-background">
            {/* Header - Full Width */}
            <header className="sticky top-0 z-50 h-[73px] bg-slate-900 border-b border-slate-700">
              <div className="h-full px-4 flex items-center">
                <Link to="/" className="flex items-center gap-2">
                  <img src="/vite.svg" alt="Discussion Room Logo" className="w-8 h-8" />
                  <h1 className="text-xl font-bold text-white tracking-tight">
                    Discussion Room
                  </h1>
                </Link>
              </div>
            </header>

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
