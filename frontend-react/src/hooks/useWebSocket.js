import { useEffect, useRef, useCallback, useState } from 'react'

export function useWebSocket(onMessage) {
  const ws = useRef(null)
  const [connected, setConnected] = useState(false)
  const intervalRef = useRef(null)

  const connect = useCallback((videoRef, canvasRef) => {
    ws.current = new WebSocket('ws://localhost:8000/ws/webcam')

    ws.current.onopen = () => {
      setConnected(true)
      intervalRef.current = setInterval(() => {
        if (!videoRef.current || !canvasRef.current) return
        if (ws.current?.readyState !== WebSocket.OPEN) return
        const ctx = canvasRef.current.getContext('2d')
        ctx.drawImage(videoRef.current, 0, 0, 640, 480)
        const frame = canvasRef.current
          .toDataURL('image/jpeg', 0.7)
          .split(',')[1]
        ws.current.send(JSON.stringify({ frame }))
      }, 500)
    }

    ws.current.onmessage = (e) => {
      const data = JSON.parse(e.data)
      onMessage(data)
    }

    ws.current.onclose = () => {
      setConnected(false)
      if (intervalRef.current) clearInterval(intervalRef.current)
    }

    ws.current.onerror = () => {
      setConnected(false)
    }
  }, [onMessage])

  const disconnect = useCallback(() => {
    if (intervalRef.current) clearInterval(intervalRef.current)
    if (ws.current) ws.current.close()
    setConnected(false)
  }, [])

  useEffect(() => () => disconnect(), [disconnect])

  return { connected, connect, disconnect }
}