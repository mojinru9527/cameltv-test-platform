import { Component, type ReactNode } from 'react'
import { AlertTriangle, RefreshCw } from 'lucide-react'
import { Button } from '@/components/ui/button'

interface Props { children: ReactNode }
interface State { hasError: boolean; error: Error | null }

export class ErrorBoundary extends Component<Props, State> {
  state: State = { hasError: false, error: null }

  static getDerivedStateFromError(error: Error): State {
    return { hasError: true, error }
  }

  handleReset = () => {
    this.setState({ hasError: false, error: null })
  }

  render() {
    if (this.state.hasError) {
      return (
        <div className="flex min-h-screen items-center justify-center bg-gray-50 dark:bg-gray-950 p-8">
          <div className="max-w-md text-center">
            <AlertTriangle className="mx-auto mb-4 h-12 w-12 text-red-500" />
            <h1 className="mb-2 text-xl font-semibold text-gray-900 dark:text-gray-100">
              页面出现异常
            </h1>
            <p className="mb-6 text-sm text-gray-600 dark:text-gray-400">
              {this.state.error?.message || '未知错误'}
            </p>
            <div className="flex justify-center gap-3">
              <Button variant="outline" onClick={() => window.location.reload()}>
                <RefreshCw className="mr-2 h-4 w-4" />
                刷新页面
              </Button>
              <Button onClick={this.handleReset}>
                重试
              </Button>
            </div>
          </div>
        </div>
      )
    }
    return this.props.children
  }
}

export default ErrorBoundary
