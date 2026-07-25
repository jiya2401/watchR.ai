import { useState } from 'react'
import { useNavigate } from 'react-router-dom'
import { useQuery, useMutation, useQueryClient } from '@tanstack/react-query'
import { Search, Zap, Trash2, FileText, Clock, Eye,
         ChevronRight, AlertCircle } from 'lucide-react'
import { api } from '../lib/api'
import Navbar from '../components/Navbar'

const SUGGESTIONS = ['Razorpay', 'CRED', 'Zepto', 'Groww', 'PhonePe', 'Swiggy', 'Meesho']

export default function Home() {
  const [query, setQuery]   = useState('')
  const [error, setError]   = useState('')
  const nav = useNavigate()
  const qc  = useQueryClient()

  const { data: companies = [], isLoading } = useQuery({
    queryKey: ['companies'],
    queryFn:  api.listCompanies,
  })

  const analyzeMutation = useMutation({
    mutationFn: (name) => api.triggerAnalysis(name),
    onSuccess: (data) => {
      qc.invalidateQueries(['companies'])
      nav(`/live/${encodeURIComponent(data.company)}/${data.job_id}`)
    },
    onError: (e) => setError(e.message),
  })

  const deleteMutation = useMutation({
    mutationFn: api.deleteCompany,
    onSuccess:  () => qc.invalidateQueries(['companies']),
  })

  const handleAnalyze = (name) => {
    const n = (name || query).trim()
    if (!n) return
    setError('')
    analyzeMutation.mutate(n)
  }

  const statusDot = (s) => {
    const map = {
      done:    'bg-w-green',
      running: 'bg-w-blue animate-pulse',
      failed:  'bg-w-red',
      pending: 'bg-w-dim',
    }
    return map[s] || 'bg-w-dim'
  }

  return (
    <div className="min-h-screen bg-w-bg">
      <Navbar right={
        <span className="mono text-xs text-w-dim">
          {companies.length} companies tracked
        </span>
      } />

      <div className="max-w-3xl mx-auto px-6 py-16">

        {/* Hero */}
        <div className="text-center mb-14">
          <div className="inline-flex items-center gap-2 bg-w-card border border-w-border
                          text-w-green mono text-xs px-3 py-1.5 rounded-full mb-6">
            <span className="w-1.5 h-1.5 rounded-full bg-w-green animate-pulse" />
            Powered by Gemini 2.5 · 100% Free
          </div>

          <h1 className="text-4xl font-bold text-w-text mb-4 leading-tight tracking-tight">
            What is your competitor
            <br />
            <span className="text-w-green">secretly building?</span>
          </h1>

          <p className="text-w-muted text-lg max-w-lg mx-auto leading-relaxed">
            Type any Indian startup name. WatchR reads their engineering blog
            and GitHub, then tells you exactly what they're about to launch —
            before the announcement.
          </p>
        </div>

        {/* Search */}
        <div className="mb-3">
          <div className={`flex items-center gap-3 bg-w-card border rounded-xl p-3
                          transition-colors ${error ? 'border-w-red' : 'border-w-border focus-within:border-w-blue'}`}>
            <Search size={18} className="text-w-dim flex-shrink-0 ml-1" />
            <input
              value={query}
              onChange={e => { setQuery(e.target.value); setError('') }}
              onKeyDown={e => e.key === 'Enter' && handleAnalyze()}
              placeholder="Type a company name... e.g. Razorpay"
              className="flex-1 bg-transparent text-w-text placeholder-w-dim
                         outline-none text-base"
            />
            <button
              onClick={() => handleAnalyze()}
              disabled={!query.trim() || analyzeMutation.isPending}
              className="flex items-center gap-2 bg-w-green hover:bg-green-500
                         disabled:opacity-40 disabled:cursor-not-allowed
                         text-black font-semibold text-sm px-5 py-2.5
                         rounded-lg transition-colors flex-shrink-0"
            >
              {analyzeMutation.isPending
                ? <><span className="w-3.5 h-3.5 border-2 border-black border-t-transparent rounded-full animate-spin" /> Launching...</>
                : <><Zap size={14} /> Analyze</>
              }
            </button>
          </div>

          {error && (
            <div className="flex items-center gap-2 mt-2 text-w-red text-sm">
              <AlertCircle size={13} /> {error}
            </div>
          )}
        </div>

        {/* Suggestions */}
        <div className="flex flex-wrap gap-2 mb-14">
          {SUGGESTIONS.map(s => (
            <button
              key={s}
              onClick={() => handleAnalyze(s)}
              disabled={analyzeMutation.isPending}
              className="mono text-xs text-w-muted bg-w-card border border-w-border
                         hover:border-w-border2 hover:text-w-text px-3 py-1.5
                         rounded-full transition-colors"
            >
              {s}
            </button>
          ))}
        </div>

        {/* Company list */}
        {(isLoading || companies.length > 0) && (
          <div>
            <div className="flex items-center justify-between mb-4">
              <h2 className="text-xs font-semibold text-w-dim uppercase tracking-widest">
                Tracked companies
              </h2>
            </div>

            {isLoading ? (
              <div className="space-y-2">
                {[1,2,3].map(i => (
                  <div key={i} className="h-16 bg-w-card border border-w-border rounded-xl animate-pulse" />
                ))}
              </div>
            ) : (
              <div className="space-y-2">
                {companies.map(c => (
                  <div
                    key={c.name}
                    className="group bg-w-card border border-w-border hover:border-w-border2
                               rounded-xl px-5 py-4 flex items-center justify-between
                               transition-colors cursor-default"
                  >
                    <div className="flex items-center gap-4">
                      {/* Avatar */}
                      <div className="w-9 h-9 rounded-lg bg-w-border flex items-center
                                      justify-center font-semibold text-w-text text-sm flex-shrink-0">
                        {c.name[0].toUpperCase()}
                      </div>

                      <div>
                        <div className="flex items-center gap-2">
                          <span className="font-medium text-w-text">{c.name}</span>
                          <span className={`w-1.5 h-1.5 rounded-full ${statusDot(c.status)}`} />
                        </div>
                        <div className="flex items-center gap-3 mt-0.5 mono text-xs text-w-dim">
                          <span className="flex items-center gap-1">
                            <Clock size={10} />
                            {c.last_scraped
                              ? new Date(c.last_scraped).toLocaleDateString('en-IN')
                              : 'Never analyzed'}
                          </span>
                          <span>{c.report_count} report{c.report_count !== 1 ? 's' : ''}</span>
                        </div>
                      </div>
                    </div>

                    {/* Actions — visible on hover */}
                    <div className="flex items-center gap-1 opacity-0 group-hover:opacity-100 transition-opacity">
                      {c.report_count > 0 && (
                        <button
                          onClick={() => nav(`/report/${encodeURIComponent(c.name)}`)}
                          className="flex items-center gap-1.5 text-xs text-w-muted
                                     hover:text-w-text px-3 py-1.5 rounded-lg
                                     hover:bg-w-border transition-colors"
                        >
                          <FileText size={12} /> Report
                        </button>
                      )}
                      <button
                        onClick={() => handleAnalyze(c.name)}
                        disabled={analyzeMutation.isPending}
                        className="flex items-center gap-1.5 text-xs text-w-green
                                   hover:text-green-400 px-3 py-1.5 rounded-lg
                                   hover:bg-w-border transition-colors"
                      >
                        <Zap size={12} /> Re-analyze
                      </button>
                      <button
                        onClick={() => deleteMutation.mutate(c.name)}
                        className="text-w-dim hover:text-w-red p-1.5 rounded-lg
                                   hover:bg-w-border transition-colors"
                      >
                        <Trash2 size={12} />
                      </button>
                    </div>
                  </div>
                ))}
              </div>
            )}
          </div>
        )}

        {/* Empty state */}
        {!isLoading && companies.length === 0 && (
          <div className="text-center py-12 text-w-dim">
            <Eye size={32} className="mx-auto mb-3 opacity-30" />
            <p className="text-sm">No companies tracked yet.</p>
            <p className="text-sm">Type a startup name above to start.</p>
          </div>
        )}
      </div>
    </div>
  )
}
