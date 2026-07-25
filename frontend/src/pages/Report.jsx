import { useState } from 'react'
import { useParams, useNavigate } from 'react-router-dom'
import { useQuery } from '@tanstack/react-query'
import { api } from '../lib/api'
import Navbar from '../components/Navbar'
import {
  ArrowLeft, Brain, Code2, Users, Rocket,
  RefreshCw, AlertTriangle, Zap, TrendingUp,
  ExternalLink, Clock
} from 'lucide-react'

// ── Sub-components ────────────────────────────────────────────

function ScoreBar({ score }) {
  const pct = Math.min(100, (score / 10) * 100)
  const color = pct > 65 ? 'bg-w-green' : pct > 35 ? 'bg-w-yellow' : 'bg-w-red'
  return (
    <div className="flex items-center gap-3">
      <div className="flex-1 h-1.5 bg-w-border rounded-full overflow-hidden">
        <div className={`h-full rounded-full transition-all duration-1000 ${color}`}
             style={{ width: `${pct}%` }} />
      </div>
      <span className="mono text-sm font-medium text-w-text w-6">
        {score.toFixed(1)}
      </span>
    </div>
  )
}

function Chip({ label, variant = 'default' }) {
  const styles = {
    adopting: 'bg-w-green/10 text-w-green border-w-green/20',
    scaling:  'bg-w-blue/10  text-w-blue  border-w-blue/20',
    retiring: 'bg-w-red/10   text-w-red   border-w-red/20',
    high:     'bg-w-green/10 text-w-green border-w-green/20',
    medium:   'bg-w-yellow/10 text-w-yellow border-w-yellow/20',
    low:      'bg-w-dim/10   text-w-dim   border-w-dim/20',
    default:  'bg-w-card     text-w-muted border-w-border',
  }
  return (
    <span className={`mono text-xs px-2 py-0.5 rounded-full border ${styles[variant] || styles.default}`}>
      {label}
    </span>
  )
}

function TechCard({ s }) {
  return (
    <div className="bg-w-surface border border-w-border rounded-xl p-4">
      <div className="flex items-start justify-between gap-2 mb-2">
        <span className="font-medium text-w-text">{s.technology}</span>
        <Chip label={s.signal_type} variant={s.signal_type} />
      </div>
      <p className="text-xs text-w-muted leading-relaxed mb-3">{s.evidence}</p>
      <div className="flex items-center gap-2">
        <div className="flex-1 h-1 bg-w-border rounded-full overflow-hidden">
          <div className="h-full bg-w-blue rounded-full"
               style={{ width: `${s.confidence * 100}%` }} />
        </div>
        <span className="mono text-xs text-w-dim">{Math.round(s.confidence * 100)}%</span>
      </div>
    </div>
  )
}

function HiringCard({ s }) {
  return (
    <div className="bg-w-surface border border-w-border rounded-xl p-4">
      <div className="flex items-start justify-between gap-2 mb-2">
        <span className="font-medium text-w-text">{s.pattern}</span>
        <span className="mono text-xs bg-w-card border border-w-border px-2 py-0.5 rounded text-w-muted">
          ×{s.count}
        </span>
      </div>
      <div className="flex items-start gap-1.5">
        <TrendingUp size={12} className="text-w-green flex-shrink-0 mt-0.5" />
        <p className="text-xs text-w-green leading-relaxed">{s.inferred_initiative}</p>
      </div>
    </div>
  )
}

function ProductCard({ s }) {
  const prob   = s.launch_probability
  const variant = prob > 0.7 ? 'high' : prob > 0.4 ? 'medium' : 'low'
  return (
    <div className="bg-w-surface border border-w-border rounded-xl p-4">
      <div className="flex items-start justify-between gap-2 mb-2">
        <span className="font-medium text-w-text">{s.feature}</span>
        <Chip label={`${Math.round(prob * 100)}% likely`} variant={variant} />
      </div>
      <p className="text-xs text-w-muted leading-relaxed mb-3">{s.evidence}</p>
      <div className="flex items-center gap-1.5 mono text-xs text-w-dim">
        <Clock size={10} /> {s.timeline}
      </div>
    </div>
  )
}

// ── Tabs ──────────────────────────────────────────────────────
const TABS = [
  { id: 'summary',  label: 'Summary',    icon: Brain,   count: null },
  { id: 'tech',     label: 'Tech Stack', icon: Code2,   count: 'tech_signals' },
  { id: 'hiring',   label: 'Hiring',     icon: Users,   count: 'hiring_signals' },
  { id: 'product',  label: 'Products',   icon: Rocket,  count: 'product_signals' },
]

// ── Page ──────────────────────────────────────────────────────
export default function Report() {
  const { company } = useParams()
  const nav         = useNavigate()
  const name        = decodeURIComponent(company)
  const [tab, setTab] = useState('summary')

  const { data: report, isLoading, error, refetch } = useQuery({
    queryKey:       ['report', name],
    queryFn:        () => api.getReport(name),
    refetchInterval: (data) => (!data ? 8000 : false),
  })

  if (isLoading) return (
    <div className="min-h-screen bg-w-bg flex items-center justify-center">
      <div className="flex items-center gap-3 text-w-muted">
        <RefreshCw size={18} className="animate-spin" />
        <span>Loading report...</span>
      </div>
    </div>
  )

  if (error || !report) return (
    <div className="min-h-screen bg-w-bg flex items-center justify-center">
      <div className="text-center">
        <AlertTriangle size={36} className="text-w-yellow mx-auto mb-4" />
        <p className="font-medium text-w-text mb-1">Report not found</p>
        <p className="text-w-muted text-sm mb-6">
          {name} hasn't been analyzed yet.
        </p>
        <button
          onClick={() => nav('/')}
          className="text-w-blue text-sm hover:underline"
        >
          ← Analyze it now
        </button>
      </div>
    </div>
  )

  const tabCount = (key) => report[key]?.length ?? 0

  return (
    <div className="min-h-screen bg-w-bg">
      <Navbar right={
        <div className="flex items-center gap-3 text-xs text-w-dim mono">
          <span>{report.articles_scraped} articles</span>
          <span>·</span>
          <span>{report.sources_used?.join(', ') || 'blog, github'}</span>
        </div>
      } />

      {/* Company header */}
      <div className="border-b border-w-border bg-w-surface">
        <div className="max-w-5xl mx-auto px-6 py-6">
          <button
            onClick={() => nav('/')}
            className="flex items-center gap-1.5 text-w-dim hover:text-w-text
                       transition-colors text-sm mb-4"
          >
            <ArrowLeft size={14} /> All companies
          </button>

          <div className="flex items-start justify-between gap-4">
            <div className="flex items-center gap-4">
              <div className="w-12 h-12 rounded-xl bg-w-border flex items-center
                              justify-center text-lg font-bold text-w-text flex-shrink-0">
                {name[0].toUpperCase()}
              </div>
              <div>
                <h1 className="text-xl font-bold text-w-text">{name}</h1>
                <p className="text-w-dim text-sm mt-0.5">
                  {new Date(report.created_at).toLocaleDateString('en-IN', {
                    dateStyle: 'long'
                  })}
                </p>
              </div>
            </div>

            {/* AI Maturity */}
            <div className="text-right min-w-40">
              <div className="flex items-center gap-1.5 text-xs text-w-dim mb-2 justify-end">
                <Zap size={11} /> AI Maturity Score
              </div>
              <ScoreBar score={report.ai_maturity_score} />
            </div>
          </div>
        </div>

        {/* Tabs */}
        <div className="max-w-5xl mx-auto px-6">
          <div className="flex">
            {TABS.map(t => (
              <button
                key={t.id}
                onClick={() => setTab(t.id)}
                className={`flex items-center gap-2 px-4 py-3 text-sm font-medium
                            border-b-2 transition-colors
                            ${tab === t.id
                              ? 'border-w-green text-w-green'
                              : 'border-transparent text-w-dim hover:text-w-text'
                            }`}
              >
                <t.icon size={14} />
                {t.label}
                {t.count && tabCount(t.count) > 0 && (
                  <span className="mono text-xs bg-w-card border border-w-border
                                   px-1.5 py-0.5 rounded">
                    {tabCount(t.count)}
                  </span>
                )}
              </button>
            ))}
          </div>
        </div>
      </div>

      {/* Content */}
      <div className="max-w-5xl mx-auto px-6 py-8">

        {/* Summary */}
        {tab === 'summary' && (
          <div className="space-y-6 animate-fade-in">
            <div className="bg-w-card border border-w-border rounded-xl p-6">
              <div className="flex items-center gap-2 mb-4">
                <Brain size={16} className="text-w-green" />
                <h3 className="font-semibold text-w-text">Executive Intelligence Brief</h3>
              </div>
              <div className="text-w-muted text-sm leading-relaxed whitespace-pre-wrap">
                {report.executive_summary || 'No summary available.'}
              </div>
            </div>

            {report.ai_maturity_notes && (
              <div className="bg-w-card border border-w-border rounded-xl p-6">
                <div className="flex items-center justify-between mb-4">
                  <div className="flex items-center gap-2">
                    <Zap size={16} className="text-w-yellow" />
                    <h3 className="font-semibold text-w-text">AI / ML Maturity</h3>
                  </div>
                  <div className="w-40">
                    <ScoreBar score={report.ai_maturity_score} />
                  </div>
                </div>
                <p className="text-w-muted text-sm leading-relaxed">
                  {report.ai_maturity_notes}
                </p>
              </div>
            )}

            {/* Quick stats */}
            <div className="grid grid-cols-4 gap-3">
              {[
                { label: 'Tech signals',    value: tabCount('tech_signals') },
                { label: 'Hiring signals',  value: tabCount('hiring_signals') },
                { label: 'Product moves',   value: tabCount('product_signals') },
                { label: 'Articles read',   value: report.articles_scraped },
              ].map(stat => (
                <div key={stat.label}
                     className="bg-w-card border border-w-border rounded-xl p-4 text-center">
                  <div className="text-2xl font-bold text-w-text">{stat.value}</div>
                  <div className="text-xs text-w-dim mt-1">{stat.label}</div>
                </div>
              ))}
            </div>
          </div>
        )}

        {/* Tech */}
        {tab === 'tech' && (
          <div className="animate-fade-in">
            <p className="text-w-muted text-sm mb-5">
              Technology signals extracted from engineering blog posts and GitHub.
            </p>
            {report.tech_signals?.length > 0 ? (
              <div className="grid grid-cols-2 gap-3">
                {report.tech_signals.map((s, i) => <TechCard key={i} s={s} />)}
              </div>
            ) : (
              <p className="text-w-dim text-sm">No tech signals detected.</p>
            )}
          </div>
        )}

        {/* Hiring */}
        {tab === 'hiring' && (
          <div className="animate-fade-in">
            <p className="text-w-muted text-sm mb-5">
              Hiring patterns and the product initiatives they signal.
            </p>
            {report.hiring_signals?.length > 0 ? (
              <div className="grid grid-cols-2 gap-3">
                {report.hiring_signals.map((s, i) => <HiringCard key={i} s={s} />)}
              </div>
            ) : (
              <p className="text-w-dim text-sm">No hiring signals detected.</p>
            )}
          </div>
        )}

        {/* Products */}
        {tab === 'product' && (
          <div className="animate-fade-in">
            <p className="text-w-muted text-sm mb-5">
              Predicted upcoming product launches ranked by probability.
            </p>
            {report.product_signals?.length > 0 ? (
              <div className="space-y-3">
                {report.product_signals
                  .sort((a, b) => b.launch_probability - a.launch_probability)
                  .map((s, i) => <ProductCard key={i} s={s} />)}
              </div>
            ) : (
              <p className="text-w-dim text-sm">No product signals detected.</p>
            )}
          </div>
        )}
      </div>
    </div>
  )
}
