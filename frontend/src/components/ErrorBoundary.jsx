import React from 'react';
import { motion } from 'framer-motion';
import { FiAlertTriangle, FiRefreshCw } from 'react-icons/fi';

export default class ErrorBoundary extends React.Component {
  constructor(props) {
    super(props);
    this.state = { hasError: false, error: null, retry: 0 };
  }

  static getDerivedStateFromError(error) {
    return { hasError: true, error };
  }

  componentDidCatch(error, errorInfo) {
    console.error('Error caught by boundary:', error, errorInfo);
  }

  handleReset = () => {
    this.setState({ hasError: false, error: null, retry: this.state.retry + 1 });
  };

  render() {
    if (this.state.hasError) {
      return (
        <div className="min-h-screen flex items-center justify-center bg-gradient-to-br from-gray-900 to-black p-4">
          <motion.div
            initial={{ opacity: 0, scale: 0.9 }}
            animate={{ opacity: 1, scale: 1 }}
            className="max-w-md w-full">
            <div className="relative">
              {/* Background glow */}
              <div className="absolute inset-0 bg-red-500/20 rounded-2xl blur-2xl animate-pulse" />
              
              {/* Card */}
              <div className="relative bg-gray-900/80 backdrop-blur-xl border border-red-500/30 rounded-2xl p-8">
                {/* Icon */}
                <motion.div
                  animate={{ rotate: [0, -10, 10, 0] }}
                  transition={{ duration: 2, repeat: Infinity }}
                  className="w-16 h-16 rounded-full bg-red-500/10 border-2 border-red-500/30 flex items-center justify-center mx-auto mb-6">
                  <FiAlertTriangle className="text-red-500" size={32} />
                </motion.div>

                <h1 className="text-2xl font-bold text-center text-white mb-2">Something went wrong</h1>
                <p className="text-gray-400 text-center mb-4 text-sm">
                  We encountered an unexpected error. Our team has been notified.
                </p>

                {/* Error details */}
                {this.state.error && (
                  <div className="bg-gray-800/50 rounded-lg p-3 mb-6 border border-gray-700/50 max-h-24 overflow-y-auto">
                    <p className="text-xs font-mono text-gray-400 text-left break-all">
                      {this.state.error.toString()}
                    </p>
                  </div>
                )}

                {/* Buttons */}
                <div className="space-y-3">
                  <motion.button
                    whileHover={{ scale: 1.02 }}
                    whileTap={{ scale: 0.98 }}
                    onClick={this.handleReset}
                    className="w-full flex items-center justify-center gap-2 px-4 py-3 rounded-lg bg-gradient-to-r from-red-500 to-orange-500 text-white font-semibold hover:shadow-lg hover:shadow-red-500/20 transition">
                    <FiRefreshCw size={16} />
                    Try Again
                  </motion.button>
                  <button
                    onClick={() => window.location.href = '/'}
                    className="w-full px-4 py-3 rounded-lg border border-gray-700 text-gray-300 font-semibold hover:bg-gray-800 transition">
                    Go Home
                  </button>
                </div>
              </div>
            </div>
          </motion.div>
        </div>
      );
    }

    return this.props.children;
  }
}
