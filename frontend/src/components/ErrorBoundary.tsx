import { Component, ReactNode } from 'react'
import { AlertTriangle, RefreshCw } from 'lucide-react'
import { Button } from '@/components/ui/button'
import { Card, CardContent } from '@/components/ui/card'

interface Props {
  children: ReactNode
  fallback?: ReactNode
}

interface State {
  hasError: boolean
  error: Error | null
}

export class ErrorBoundary extends Component<Props, State> {
  constructor(props: Props) {
    super(props)
    this.state = { hasError: false, error: null }
  }

  static getDerivedStateFromError(error: Error): State {
    return { hasError: true, error }
  }

  componentDidCatch(error: Error, errorInfo: React.ErrorInfo) {
    console.error('ErrorBoundary caught an error:', error, errorInfo)
  }

  handleRetry = () => {
    this.setState({ hasError: false, error: null })
  }

  handleReload = () => {
    window.location.reload()
  }

  render() {
    if (this.state.hasError) {
      if (this.props.fallback) {
        return this.props.fallback
      }

      return (
        <div className="min-h-screen flex items-center justify-center p-4">
          <Card className="max-w-md w-full">
            <CardContent className="pt-6">
              <div className="flex flex-col items-center text-center">
                <div className="w-16 h-16 rounded-full bg-destructive/10 flex items-center justify-center mb-4">
                  <AlertTriangle className="w-8 h-8 text-destructive" />
                </div>
                <h2 className="text-xl font-semibold mb-2">Something went wrong</h2>
                <p className="text-muted-foreground mb-4">
                  An unexpected error occurred. Please try again.
                </p>
                {this.state.error && (
                  <pre className="text-xs text-left bg-muted p-3 rounded-lg mb-4 max-w-full overflow-auto">
                    {this.state.error.message}
                  </pre>
                )}
                <div className="flex gap-2">
                  <Button variant="outline" onClick={this.handleRetry}>
                    <RefreshCw className="w-4 h-4 mr-2" />
                    Try Again
                  </Button>
                  <Button onClick={this.handleReload}>
                    Reload Page
                  </Button>
                </div>
              </div>
            </CardContent>
          </Card>
        </div>
      )
    }

    return this.props.children
  }
}
