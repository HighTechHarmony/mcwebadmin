import { useState, useEffect, useRef } from 'react'
import { io } from 'socket.io-client'
import Convert from 'ansi-to-html'

const converter = new Convert({ escapeXML: true })

const MAX_LINES = 1000

export default function LogViewer() {
  const [lines, setLines] = useState([])
  const [connected, setConnected] = useState(false)
  const containerRef = useRef(null)
  const bottomRef = useRef(null)
  const autoScroll = useRef(true)

  // Socket.IO connection
  useEffect(() => {
    const socket = io('/console', {
      auth: { token: localStorage.getItem('token') },
    })

    socket.on('connect', () => setConnected(true))
    socket.on('disconnect', () => setConnected(false))

    // When a new line arrives, decide whether to auto-scroll based on the
    // current scroll position _before_ appending the line. This prevents the
    // viewer from jumping to the bottom when the user has scrolled up.
    socket.on('log_line', ({ data }) => {
      const el = containerRef.current
      const isAtBottom = el ? el.scrollHeight - el.scrollTop - el.clientHeight < 40 : true

      setLines((prev) => {
        const next = [...prev, data]
        return next.length > MAX_LINES ? next.slice(next.length - MAX_LINES) : next
      })

      if (isAtBottom) {
        // Wait for the DOM update, then scroll into view
        requestAnimationFrame(() => bottomRef.current?.scrollIntoView({ behavior: 'auto' }))
        autoScroll.current = true
      } else {
        // preserve user's scroll position; mark autoScroll disabled
        autoScroll.current = false
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
