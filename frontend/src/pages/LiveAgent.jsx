import { useEffect, useRef } from 'react'
import { useParams, useNavigate } from 'react-router-dom'
import { useAgentStream } from '../hooks/useAgentStream'
import { CheckCircle2, Circle, Loader2, AlertCircle,
         ArrowLeft, Terminal } from 'lucide-react'
import Navbar from '../components/Navbar'

const PIPELINE = [
  { id: 'trigger_scrape',  label: 'Launch scrapers',      desc: 'Start blog + GitHub collection' },
  { id: 'await_scrape',    label: 'Collect data',          desc: 'Reading blog articles + repos' },
  { id: 'analyze_tech',    label: 'Analyze tech stack',    desc: 'What are they building with?' },
  { id: 'analyze_hiring',  label: 'Decode hiring signals', desc: 'What do open roles reveal?' },
  { id: 'analyze_product', label: 'Predict product moves', desc: 'What will they launch next?' },
  { id: 'synthesize',      label: 'Write report',          desc: 'Executive intelligence brief' },
]

function PipelineStep({ pipeStep, steps, status }) {
  const pipeIds   = PIPELINE.map(p => p.id)
  const stepIds   = steps.map(s => s.step)
  const lastStep  = stepIds.length > 0 ? stepIds[stepIds.length - 1] : ''
  const myIdx     = pipeIds.indexOf(pipeStep.id)
  const lastIdx   = pipeIds.indexOf(lastStep)

  const isDone    = status === 'done' || myIdx < lastIdx
  const isActive  = myIdx === lastIdx && status === 'running'
  const isPending = myIdx > lastIdx

  return (
    <div className={`flex items-start gap-3 p-3 rounded-xl transition-all
      ${isActive  ? 'bg-w-card border border-w-border' : ''}
      ${isDone    ? 'opacity-60' : ''}
      ${isPending ? 'opacity-30' : ''}
    `}>
      <div className="mt-0.5 flex-shrink-0">
        {isDone    && <CheckCircle2 size={16} className="text-w-green" />}
        {isActive  && <Loader2     size={16} className="text-w-blue animate-spin" />}
        {isPending && <Circle      size={16} className="text-w-dim" />}
      </div>
      <div>
        <div className={`text-sm font-medium ${isActive ? 'text-w-text' : 'text-w-muted'}`}>
          {pipeStep.label}
        </div>
        {isActive && (
          <div className="mono text-xs text-w-dim mt-0.5">{pipeStep.desc}</div>
        )}
      </div>
    </div>
  )
}

export default function LiveAgent() {
  const { company, jobId } = useParams()
  const nav                = useNavigate()
  const { steps, status, reconnect } = useAgentStream(jobId)
  const bottomRef          = useRef(null)
  const name               = decodeURIComponent(company)

  const pipeIds    = PIPELINE.map(p => p.id)
  const lastStep   = steps.length > 0 ? steps[steps.length - 1].step : ''
  const lastIdx    = pipeIds.indexOf(lastStep)
  const progress   = status === 'done'
    ? 100
    : Math.max(5, Math.round(((lastIdx + 1) / PIPELINE.length) * 100))

  // Auto-scroll log
  useEffect(() => {
    bottomRef.current?.scrollIntoView({ behavior: 'smooth' })
  }, [steps])

  // Auto-navigate to report when done
  useEffect(() => {
    if (status === 'done') {
      const t = setTimeout(() => nav(`/report/${company}`), 2500)
      return () => clearTimeout(t)
    }
  }, [status, company, nav])

  return (
    <div className="min-h-screen bg-w-bg">
      <Navbar right={
        <div className="flex items-center gap-3">
          {status === 'done' && (
            <span className="mono text-xs text-w-green flex items-center gap-1.5">
              <CheckCircle2 size={12} /> Complete
            </span>
          )}
          {status === 'failed' && (
            <span className="mono text-xs text-w-red flex items-center gap-1.5">
              <AlertCircle size={12} /> Failed
            </span>
          )}
          {status === 'running' && (
            <span className="mono text-xs text-w-blue flex items-center gap-1.5">
              <Loader2 size={12} className="animate-spin" /> {progress}%
            </span>
          )}
          {status === 'disconnected' && (
            <button
              onClick={reconnect}
              className="mono text-xs text-w-yellow border border-w-yellow/30
                         px-2 py-1 rounded hover:bg-w-yellow/10 transition-colors"
            >
              Reconnect
            </button>
          )}
        </div>
      } />

      {/* Progress bar */}
      <div className="h-0.5 bg-w-border">
        <div
          className="h-full bg-w-green transition-all duration-1000 ease-out"
          style={{ width: `${progress}%` }}
        />
      </div>

      <div className="max-w-5xl mx-auto px-6 py-10">
        <div className="mb-8">
          <button
            onClick={() => nav('/')}
            className="flex items-center gap-1.5 text-w-dim hover:text-w-text
                       transition-colors text-sm mb-4"
          >
            <ArrowLeft size={14} /> Back
          </button>
          <h1 className="text-xl font-semibold text-w-text">
            Analyzing <span className="text-w-green">{name}</span>
          </h1>
          <p className="text-w-dim text-sm mt-1">
            {status === 'done'
              ? 'Analysis complete — redirecting to report...'
              : 'Agent is reading their engineering blog and GitHub...'}
          </p>
        </div>

        <div className="grid grid-cols-5 gap-6">

          {/* Pipeline sidebar */}
          <div className="col-span-2">
            <p className="mono text-xs text-w-dim uppercase tracking-widest mb-3">
              Pipeline
            </p>
            <div className="space-y-1">
              {PIPELINE.map(p => (
                <PipelineStep
                  key={p.id}
                  pipeStep={p}
                  steps={steps}
                  status={status}
                />
              ))}
            </div>

            {/* Stats */}
            {status === 'done' && (
              <div className="mt-6 p-4 bg-w-card border border-w-green/20 rounded-xl animate-fade-in">
                <div className="flex items-center gap-2 text-w-green text-sm font-medium mb-1">
                  <CheckCircle2 size={14} /> Report ready
                </div>
                <p className="text-xs text-w-dim">Redirecting in 2 seconds...</p>
                <button
                  onClick={() => nav(`/report/${company}`)}
                  className="mt-3 text-xs text-w-blue hover:underline"
                >
                  Go to report now →
                </button>
              </div>
            )}
          </div>

          {/* Live log */}
          <div className="col-span-3">
            <div className="flex items-center justify-between mb-3">
              <p className="mono text-xs text-w-dim uppercase tracking-widest flex items-center gap-2">
                <Terminal size={11} /> Agent thoughts
              </p>
              <span className="mono text-xs text-w-dim">{steps.length} steps</span>
            </div>

            <div className="bg-w-card border border-w-border rounded-xl overflow-hidden">
              {/* Terminal header */}
              <div className="bg-w-surface border-b border-w-border px-4 py-2 flex items-center gap-2">
                <span className="w-2.5 h-2.5 rounded-full bg-w-red opacity-60" />
                <span className="w-2.5 h-2.5 rounded-full bg-w-yellow opacity-60" />
                <span className="w-2.5 h-2.5 rounded-full bg-w-green opacity-60" />
                <span className="mono text-xs text-w-dim ml-2">watchr-agent</span>
              </div>

              {/* Log entries */}
              <div className="p-4 space-y-3 max-h-96 overflow-y-auto">
                {steps.length === 0 ? (
                  <div className="flex items-center gap-2 text-w-dim mono text-xs">
                    <Loader2 size={12} className="animate-spin" />
                    Initializing agent...
                    <span className="animate-blink">▋</span>
                  </div>
                ) : (
                  steps.map((s, i) => (
                    <div key={i} className="animate-slide-up">
                      <div className="flex items-start gap-2">
                        <span className="mono text-xs text-w-dim flex-shrink-0 mt-0.5">
                          {new Date(s.ts).toLocaleTimeString('en', { hour12: false })}
                        </span>
                        <div className="flex-1 min-w-0">
                          <span className="mono text-xs text-w-green">[{s.step}]</span>
                          <span className="text-xs text-w-text ml-2">{s.message}</span>
                          {s.preview && (
                            <div className="mt-1 mono text-xs text-w-dim bg-w-surface
                                            rounded px-2 py-1 truncate">
                              → {s.preview}
                            </div>
                          )}
                        </div>
                      </div>
                    </div>
                  ))
                )}

                {/* Blinking cursor when running */}
                {status === 'running' && (
                  <div className="mono text-xs text-w-green flex items-center gap-1">
                    <span className="animate-blink">▋</span>
                  </div>
                )}

                <div ref={bottomRef} />
              </div>
            </div>
          </div>
        </div>
      </div>
    </div>
  )
}
