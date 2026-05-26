import { useState, useEffect, useRef } from 'react'
import { io } from 'socket.io-client'
import Convert from 'ansi-to-html'
import api from '../api'

const converter = new Convert({ escapeXML: true })

const MAX_LINES = 1000

export default function LogViewer({ forceFetchToken = null }) {
  const [lines, setLines] = useState([])
  const [connected, setConnected] = useState(false)
  const containerRef = useRef(null)
  const bottomRef = useRef(null)
  const autoScroll = useRef(true)
  // Fetch history when mounted or when parent signals focus via token
  useEffect(() => {
    let mounted = true

    const fetchHistory = async () => {
      try {
        const res = await api.get(`/console/log?lines=${MAX_LINES}`)
        if (!mounted) return
        if (Array.isArray(res.data.lines)) {
          setLines(res.data.lines)
          // Ensure initial load scrolls to bottom and enables auto-scroll
          requestAnimationFrame(() => {
            bottomRef.current?.scrollIntoView({ behavior: 'auto' })
            autoScroll.current = true
          })
        }
      } catch (err) {
        // ignore — live stream will still provide new lines
      }
    }

    fetchHistory()

    return () => {
      mounted = false
    }
  }, [forceFetchToken && forceFetchToken.token])

  // Socket.IO connection (single mount)
  useEffect(() => {
    const socket = io('/console', {
      auth: { token: localStorage.getItem('token') },
    })

    socket.on('connect', () => setConnected(true))
    socket.on('disconnect', () => setConnected(false))

    socket.on('log_line', ({ data }) => {
      const el = containerRef.current
      const isAtBottom = el ? el.scrollHeight - el.scrollTop - el.clientHeight < 40 : true

      // Update autoScroll state based on current position (before appending)
      autoScroll.current = isAtBottom

      setLines((prev) => {
        const next = [...prev, data]
        return next.length > MAX_LINES ? next.slice(next.length - MAX_LINES) : next
      })

      // If auto-scroll enabled, scroll to bottom after DOM update
      if (autoScroll.current) {
        requestAnimationFrame(() => bottomRef.current?.scrollIntoView({ behavior: 'auto' }))
      }
    })

    return () => socket.disconnect()
  }, [])

  // NOTE: Auto-scrolling is handled in the socket handler so we only scroll
  // when the user was already at (or very near) the bottom prior to the
  // incoming line. This avoids disruptive jumps while reading history.

  // Pause auto-scroll when user scrolls up; resume at bottom
  const handleScroll = () => {
    const el = containerRef.current
    if (!el) return
    autoScroll.current = el.scrollHeight - el.scrollTop - el.clientHeight < 40
  }

  return (
    <div className="log-viewer" ref={containerRef} onScroll={handleScroll}>
      {!connected && (
        <div className="log-disconnected">● Disconnected from log stream</div>
      )}
      {lines.map((line, i) => (
        <div
          key={i}
          className="log-line"
          // ansi-to-html with escapeXML:true sanitises the text portion
          dangerouslySetInnerHTML={{ __html: converter.toHtml(line) }}
        />
      ))}
      <div ref={bottomRef} />
    </div>
  )
}
