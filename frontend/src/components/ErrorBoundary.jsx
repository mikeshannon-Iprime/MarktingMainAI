import { Component } from 'react'
import { AlertTriangle } from 'lucide-react'

import { logger } from '../utils/logger'

export class ErrorBoundary extends Component {
  constructor(props) {
    super(props)
    this.state = { hasError: false }
  }

  static getDerivedStateFromError() {
    return { hasError: true }
  }

  componentDidCatch(error, info) {
    logger.error(error, {
      type: 'react_error_boundary',
      componentStack: info?.componentStack,
    })
  }

  handleReset = () => {
    this.setState({ hasError: false })
    window.location.assign('/')
  }

  render() {
    if (this.state.hasError) {
      return (
        <div className="page-stack">
          <div className="banner error" role="alert">
            <AlertTriangle size={16} aria-hidden="true" />
            <span>Something went wrong while rendering this page.</span>
          </div>
          <button type="button" className="primary-button" onClick={this.handleReset}>
            Return to dashboard
          </button>
        </div>
      )
    }

    return this.props.children
  }
}
