"use client"
import React, { useState, useEffect, useRef } from 'react'

interface Video {
  id: number,
  title: string,
  path: string
}

const mockVideos: Video[] = [
  { id: 1, title: 'Camera 01', path: 'vid1.mp4' },
  { id: 2, title: 'Camera 02', path: 'vid2.mp4' }
]

export default function App() {
  const [selectedVideo, setSelectedVideo] = useState<Video | null>(null)
  const [logs, setLogs] = useState<string[]>([])
  const wsRef = useRef<WebSocket | null>(null)
  const logEndRef = useRef<HTMLDivElement>(null)

  useEffect(() => {
    if (logEndRef.current) {
      logEndRef.current.scrollIntoView({ behavior: 'smooth' })
    }
  }, [logs])

  useEffect(() => {
    if (!selectedVideo) return

    setLogs([])
    const ws = new WebSocket('ws://localhost:8000/ws/process')
    wsRef.current = ws

    ws.onopen = () => {
      ws.send(JSON.stringify({ video_path: selectedVideo.path }))
    }

    ws.onmessage = (event) => {
      const data = JSON.parse(event.data)
      if (data.log) {
        setLogs(prev => [...prev, data.log])
      }
    }

    return () => {
      ws.close()
    }
  }, [selectedVideo])

  const renderLog = (log: string, index: number) => {
    try {
      const cleanLog = log.replace(/```json/g, '').replace(/```/g, '').trim()
      
      if (cleanLog.startsWith('{') && cleanLog.endsWith('}')) {
        const parsed = JSON.parse(cleanLog)
        
        return (
          <div key={index} style={{ backgroundColor: '#1e293b', padding: '15px', borderRadius: '8px', borderLeft: '4px solid #ef4444', marginTop: '10px', marginBottom: '10px' }}>
            <h3 style={{ margin: '0 0 10px 0', color: '#f87171' }}>🚨 {parsed.EmergencyType || 'Emergency Report'}</h3>
            <div style={{ display: 'grid', gridTemplateColumns: '1fr 1fr', gap: '10px', fontSize: '0.9rem', color: '#e2e8f0' }}>
              <div><strong>Action Required:</strong> {parsed.ActionRequired ? 'Yes' : 'No'}</div>
              <div><strong>Confidence:</strong> {parsed.ConfidenceScore}</div>
              <div style={{ gridColumn: 'span 2' }}><strong>Reason:</strong> {parsed.Reason}</div>
              <div style={{ gridColumn: 'span 2' }}><strong>Location:</strong> {parsed.Location}</div>
            </div>
            {parsed.Units && (
              <div style={{ marginTop: '15px' }}>
                <strong style={{ color: '#e2e8f0' }}>Units Dispatched:</strong>
                <div style={{ display: 'flex', flexDirection: 'column', gap: '5px', marginTop: '8px' }}>
                  {parsed.Units.map((u: any, i: number) => (
                    <div key={i} style={{ backgroundColor: '#334155', color: '#94a3b8', padding: '8px 12px', borderRadius: '4px', fontSize: '0.85rem' }}>
                      {u.Count}x {u.Type}
                    </div>
                  ))}
                </div>
              </div>
            )}
          </div>
        )
      }
    } catch (e) {
      
    }

    return (
      <div key={index} style={{ fontFamily: 'monospace', color: '#a7f3d0', backgroundColor: '#064e3b', padding: '10px', borderRadius: '4px', wordWrap: 'break-word' }}>
        {log}
      </div>
    )
  }

  return (
    <div style={{ display: 'flex', height: '100vh', width: '100vw', backgroundColor: '#121212', color: 'white', fontFamily: 'sans-serif', overflow: 'hidden' }}>
       
       <div style={{ width: '50%', padding: '20px', display: 'flex', flexDirection: 'column', boxSizing: 'border-box' }}>
          {selectedVideo ? (
             <div style={{ display: 'flex', flexDirection: 'column', height: '100%', position: 'relative' }}>
                <video 
                  src={selectedVideo.path} 
                  controls 
                  autoPlay 
                  style={{ width: '100%', height: '100%', objectFit: 'contain', backgroundColor: 'black', borderRadius: '8px' }} 
                />
                <button 
                  onClick={() => setSelectedVideo(null)} 
                  style={{ position: 'absolute', top: '10px', right: '10px', padding: '10px 20px', cursor: 'pointer', backgroundColor: '#ff4444', color: 'white', border: 'none', borderRadius: '4px', zIndex: 10 }}
                >
                  Close View
                </button>
             </div>
          ) : (
             <div style={{ display: 'flex', flexDirection: 'column', gap: '20px', overflowY: 'auto', height: '100%', paddingRight: '10px' }}>
                {mockVideos.map(v => (
                   <div 
                     key={v.id} 
                     onClick={() => setSelectedVideo(v)} 
                     style={{ width: '300px', height: '100px', backgroundColor: '#2a2a2a', cursor: 'pointer', display: 'flex', alignItems: 'center', justifyContent: 'center', borderRadius: '8px', fontSize: '1.2rem', transition: 'background-color 0.2s' }}
                     onMouseEnter={(e) => e.currentTarget.style.backgroundColor = '#3a3a3a'}
                     onMouseLeave={(e) => e.currentTarget.style.backgroundColor = '#2a2a2a'}
                   >
                      {v.title}
                   </div>
                ))}
             </div>
          )}
       </div>

       <div style={{ width: '50%', backgroundColor: '#000000', padding: '20px', overflowY: 'auto', borderLeft: '1px solid #333', boxSizing: 'border-box' }}>
          <h2 style={{ marginTop: 0, color: '#4ade80' }}>Live Processing Status</h2>
          <div style={{ display: 'flex', flexDirection: 'column', gap: '10px' }}>
            {logs.map((log, i) => renderLog(log, i))}
            <div ref={logEndRef} />
          </div>
       </div>
       
    </div>
  )
}