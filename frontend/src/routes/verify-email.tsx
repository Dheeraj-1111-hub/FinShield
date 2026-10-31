import { createFileRoute, Link, useNavigate, useSearch } from '@tanstack/react-router'
import { useState, useEffect } from 'react'
import { api } from '@/lib/api-client'
import { ShieldAlert, CheckCircle } from 'lucide-react'

export const Route = createFileRoute('/verify-email')({
  component: VerifyEmail,
})

function VerifyEmail() {
  const search: any = useSearch({ from: '/verify-email' })
  const token = search.token
  const [status, setStatus] = useState<'loading' | 'success' | 'error'>('loading')
  const [message, setMessage] = useState('')

  useEffect(() => {
    if (!token) {
      setStatus('error')
      setMessage('Missing verification token.')
      return
    }

    api.post('/auth/verify-email', { token })
      .then(() => {
        setStatus('success')
        setMessage('Your email has been successfully verified.')
      })
      .catch((err) => {
        setStatus('error')
        setMessage(err.response?.data?.error?.message || err.response?.data?.detail || 'Verification failed. The token may be invalid or expired.')
      })
  }, [token])

  return (
    <div className="min-h-screen flex items-center justify-center bg-[var(--background-main)]">
      <div className="w-full max-w-md p-8 bg-[var(--surface-main)] rounded-xl border border-[var(--border-main)]">
        <div className="flex justify-center mb-6">
          {status === 'loading' && <div className="w-12 h-12 border-4 border-t-[var(--accent-primary)] border-[var(--border-main)] rounded-full animate-spin"></div>}
          {status === 'success' && <CheckCircle className="w-12 h-12 text-green-500" />}
          {status === 'error' && <ShieldAlert className="w-12 h-12 text-red-500" />}
        </div>
        
        <h2 className="text-2xl font-bold text-center text-[var(--text-main)] mb-2">
          {status === 'loading' && 'Verifying Email...'}
          {status === 'success' && 'Email Verified'}
          {status === 'error' && 'Verification Failed'}
        </h2>
        
        <p className="text-center text-[var(--text-muted)] mb-6">
          {status === 'loading' && 'Please wait while we verify your email address.'}
          {status !== 'loading' && message}
        </p>

        <div className="flex justify-center">
          <Link to="/login" className="px-6 py-2 bg-[var(--accent-primary)] text-white rounded-lg hover:bg-[var(--accent-hover)] transition-colors">
            Go to Login
          </Link>
        </div>
      </div>
    </div>
  )
}
