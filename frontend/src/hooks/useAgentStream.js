import { useState, useEffect, useRef, useCallback } from 'react'

/**
 * useAgentStream
 * Connects to WatchR WebSocket stream for a job.
 * Auto-reconnects on disconnect (max 3 attempts).
 *
 * Returns: { steps, status, reconnect }
 * status: 'connecting' | 'running' | 'done' | 'failed' | 'disconnected'
 */
export function useAgentStream(jobId) {
  const [steps, setSteps]   = useState([])
  const [status, setStatus] = useState('connecting')
  const wsRef               = useRef(null)
  const attemptsRef         = useRef(0)
  const maxAttempts         = 3

  const connect = useCallback(() => {
    if (!jobId) return
    if (wsRef.current?.readyState === WebSocket.OPEN) return

    const proto = window.location.protocol === 'https:' ? 'wss:' : 'ws:'
    const url   = `${proto}//${window.location.host}/ws/agent/${jobId}`
    const ws    = new WebSocket(url)
    wsRef.current = ws

    ws.onopen = () => {
      setStatus('running')
      attemptsRef.current = 0
    }

    ws.onmessage = ({ data }) => {
      let msg
      try { msg = JSON.parse(data) } catch { return }

      switch (msg.type) {
        case 'step':
          setSteps(prev => [...prev, {
            step:    msg.step,
            message: msg.message,
            preview: msg.preview || '',
            ts:      new Date().toISOString(),
          }])
          break
        case 'done':
          setStatus('done')
          ws.close()
          break
        case 'failed':
          setStatus('failed')
          ws.close()
          break
        case 'ping':
        case 'connected':
          break
        default:
          break
      }
    }

    ws.onerror = () => {
      setStatus('disconnected')
    }

    ws.onclose = () => {
      // Auto-reconnect unless terminal state
      if (status !== 'done' && status !== 'failed') {
        if (attemptsRef.current < maxAttempts) {
          attemptsRef.current += 1
          setTimeout(connect, 2000 * attemptsRef.current)
        } else {
          setStatus('disconnected')
        }
      }
    }
  }, [jobId])

  useEffect(() => {
    connect()
    return () => {
      wsRef.current?.close()
    }
  }, [connect])

  return { steps, status, reconnect: connect }
}
