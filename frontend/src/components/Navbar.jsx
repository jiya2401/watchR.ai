import { useNavigate } from 'react-router-dom'
import { Eye } from 'lucide-react'

export default function Navbar({ right }) {
  const nav = useNavigate()
  return (
    <nav className="border-b border-w-border bg-w-surface/80 backdrop-blur-sm sticky top-0 z-50">
      <div className="max-w-5xl mx-auto px-6 h-14 flex items-center justify-between">
        <button
          onClick={() => nav('/')}
          className="flex items-center gap-2.5 hover:opacity-80 transition-opacity"
        >
          <div className="w-7 h-7 rounded-md bg-w-green flex items-center justify-center">
            <Eye size={14} className="text-black" />
          </div>
          <span className="font-semibold text-w-text tracking-tight">watchR.ai</span> 
          <span className="mono text-xs text-w-dim bg-w-card px-2 py-0.5 rounded">
            v1.0
          </span>
        </button>
        {right}
      </div>
    </nav>
  )
}
