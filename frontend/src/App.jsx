import React, { useState, useEffect } from 'react'
import TheaterGrid from './components/TheaterGrid'
import DatePicker from './components/DatePicker'
import Header from './components/Header'

const API_URL = import.meta.env.VITE_API_URL || 'http://localhost:5000'

const THEATERS = [
  { id: "amc-lincoln-square-13", name: "AMC Lincoln Square 13", location: "New York, NY", state: "NY" },
  { id: "amc-metreon-16", name: "AMC Metreon 16", location: "San Francisco, CA", state: "CA" },
  { id: "amc-universal-citywalk-19", name: "AMC Universal CityWalk", location: "Universal City, CA", state: "CA" },
  { id: "amc-century-city-15", name: "AMC Century City 15", location: "Los Angeles, CA", state: "CA" },
  { id: "amc-king-of-prussia-16", name: "AMC King of Prussia 16", location: "King of Prussia, PA", state: "PA" },
  { id: "amc-navy-pier-imax", name: "AMC Navy Pier IMAX", location: "Chicago, IL", state: "IL" },
  { id: "amc-northpark-15", name: "AMC NorthPark 15", location: "Dallas, TX", state: "TX" },
  { id: "amc-aventura-24", name: "AMC Aventura 24", location: "Aventura, FL", state: "FL" },
  { id: "amc-tysons-corner-16", name: "AMC Tysons Corner 16", location: "McLean, VA", state: "VA" },
  { id: "amc-garden-state-16", name: "AMC Garden State 16", location: "Paramus, NJ", state: "NJ" },
]

function App() {
  const [selectedDate, setSelectedDate] = useState(getToday())
  const [selectedTheaters, setSelectedTheaters] = useState(() => {
    const validIds = new Set(THEATERS.map(t => t.id))
    const saved = localStorage.getItem('selectedTheaters')
    if (saved) {
      // Keep only IDs that still exist (handles migration from old numeric IDs)
      const parsed = JSON.parse(saved).filter(id => validIds.has(id))
      if (parsed.length > 0) return new Set(parsed)
    }
    return new Set(THEATERS.map(t => t.id))
  })
  const [availability, setAvailability] = useState({})
  const [loading, setLoading] = useState(false)
  const [lastChecked, setLastChecked] = useState(null)
  const [filter, setFilter] = useState('all') // all, available, soldout
  const [showTheaterPicker, setShowTheaterPicker] = useState(false)
  const [scanning, setScanning] = useState(false)
  const [findResult, setFindResult] = useState(null)

  function getToday() {
    return new Date().toISOString().split('T')[0]
  }

  const checkAvailability = async () => {
    setLoading(true)
    try {
      const controller = new AbortController()
      const timeout = setTimeout(() => controller.abort(), 10000) // 10s timeout

      const res = await fetch(`${API_URL}/check?date=${selectedDate}`, { signal: controller.signal })
      clearTimeout(timeout)
      const data = await res.json()
      setAvailability(data.results || {})
      setLastChecked(new Date().toLocaleTimeString())
    } catch (err) {
      const mock = {}
      THEATERS.forEach(t => { mock[t.id] = { notChecked: true } })
      setAvailability(mock)
      setLastChecked(new Date().toLocaleTimeString() + ' (backend unavailable)')
    }
    setLoading(false)
  }

  useEffect(() => {
    checkAvailability()
  }, [selectedDate])

  const findNextAvailable = async () => {
    setScanning(true)
    try {
      const theaterIds = [...selectedTheaters].join(',')
      const controller = new AbortController()
      const timeout = setTimeout(() => controller.abort(), 60000) // 60s for full scan

      const res = await fetch(`${API_URL}/find-next?theaters=${theaterIds}`, { signal: controller.signal })
      clearTimeout(timeout)
      const data = await res.json()

      if (data.found) {
        setFindResult(data)
      } else {
        setFindResult({ found: false, message: 'No available 70mm showings found. Tickets may not be on sale yet.' })
      }
    } catch (err) {
      setFindResult({ found: false, message: 'Could not reach server. Make sure the backend is running.' })
    }
    setScanning(false)
  }

  const updateSelectedTheaters = (next) => {
    setSelectedTheaters(next)
    localStorage.setItem('selectedTheaters', JSON.stringify([...next]))
  }

  const toggleTheater = (id) => {
    const next = new Set(selectedTheaters)
    if (next.has(id)) next.delete(id)
    else next.add(id)
    updateSelectedTheaters(next)
  }

  const selectAllTheaters = () => updateSelectedTheaters(new Set(THEATERS.map(t => t.id)))
  const clearAllTheaters = () => updateSelectedTheaters(new Set())

  const filteredTheaters = THEATERS.filter(t => {
    if (!selectedTheaters.has(t.id)) return false
    if (filter === 'all') return true
    const status = availability[t.id]
    if (filter === 'available') return status?.available
    if (filter === 'soldout') return status?.soldOut || (!status?.available && status?.showtimes?.length === 0)
    return true
  })

  const availableCount = THEATERS.filter(t => selectedTheaters.has(t.id) && availability[t.id]?.available).length

  return (
    <div style={{ minHeight: '100vh', background: '#0a0a0a', color: '#e5e5e5', fontFamily: 'system-ui, -apple-system, sans-serif' }}>
      <Header />

      <main style={{ maxWidth: 1100, margin: '0 auto', padding: '0 20px 40px' }}>
        {/* Controls */}
        <div style={{ display: 'flex', gap: 16, alignItems: 'center', flexWrap: 'wrap', marginBottom: 24 }}>
          <DatePicker selected={selectedDate} onChange={setSelectedDate} />

          <div style={{ display: 'flex', gap: 8 }}>
            {['all', 'available', 'soldout'].map(f => (
              <button
                key={f}
                onClick={() => setFilter(f)}
                style={{
                  padding: '8px 16px',
                  borderRadius: 6,
                  border: 'none',
                  background: filter === f ? '#d97706' : '#262626',
                  color: filter === f ? '#000' : '#a3a3a3',
                  cursor: 'pointer',
                  fontSize: 13,
                  fontWeight: filter === f ? 600 : 400,
                }}
              >
                {f === 'all' ? 'All Theaters' : f === 'available' ? 'Available' : 'Sold Out'}
              </button>
            ))}
          </div>

          <button
            onClick={findNextAvailable}
            disabled={scanning || loading}
            style={{
              padding: '8px 16px',
              borderRadius: 6,
              border: 'none',
              background: scanning ? '#525252' : '#d97706',
              color: scanning ? '#a3a3a3' : '#000',
              cursor: scanning ? 'wait' : 'pointer',
              fontSize: 13,
              fontWeight: 600,
              marginLeft: 'auto',
            }}
          >
            {scanning ? 'Scanning dates...' : 'Find Next Available'}
          </button>

          {loading && !scanning && (
            <span style={{ fontSize: 13, color: '#d97706' }}>
              ⟳ Checking...
            </span>
          )}
        </div>

        {/* Theater Picker Toggle */}
        <div style={{ marginBottom: 16 }}>
          <button
            onClick={() => setShowTheaterPicker(!showTheaterPicker)}
            style={{
              padding: '8px 16px',
              borderRadius: 6,
              border: '1px solid #404040',
              background: '#1a1a1a',
              color: '#a3a3a3',
              cursor: 'pointer',
              fontSize: 13,
            }}
          >
            {showTheaterPicker ? '▼' : '▶'} Select Theaters ({selectedTheaters.size}/{THEATERS.length})
          </button>

          {showTheaterPicker && (
            <div style={{
              marginTop: 12,
              padding: 16,
              background: '#171717',
              border: '1px solid #333',
              borderRadius: 10,
            }}>
              <div style={{ display: 'flex', gap: 8, marginBottom: 12 }}>
                <button onClick={selectAllTheaters} style={{ padding: '4px 12px', borderRadius: 4, border: '1px solid #525252', background: 'transparent', color: '#a3a3a3', cursor: 'pointer', fontSize: 12 }}>
                  Select All
                </button>
                <button onClick={clearAllTheaters} style={{ padding: '4px 12px', borderRadius: 4, border: '1px solid #525252', background: 'transparent', color: '#a3a3a3', cursor: 'pointer', fontSize: 12 }}>
                  Clear All
                </button>
              </div>
              <div style={{ display: 'grid', gridTemplateColumns: 'repeat(auto-fill, minmax(280px, 1fr))', gap: 8 }}>
                {THEATERS.map(t => (
                  <label
                    key={t.id}
                    style={{
                      display: 'flex',
                      alignItems: 'center',
                      gap: 8,
                      padding: '8px 12px',
                      borderRadius: 6,
                      background: selectedTheaters.has(t.id) ? '#292524' : 'transparent',
                      border: `1px solid ${selectedTheaters.has(t.id) ? '#d97706' : '#333'}`,
                      cursor: 'pointer',
                      transition: 'all 0.15s',
                    }}
                  >
                    <input
                      type="checkbox"
                      checked={selectedTheaters.has(t.id)}
                      onChange={() => toggleTheater(t.id)}
                      style={{ accentColor: '#d97706' }}
                    />
                    <div>
                      <div style={{ fontSize: 13, color: '#e5e5e5' }}>{t.name}</div>
                      <div style={{ fontSize: 11, color: '#737373' }}>{t.location}</div>
                    </div>
                  </label>
                ))}
              </div>
            </div>
          )}
        </div>

        {/* Status bar */}
        <div style={{ display: 'flex', gap: 24, marginBottom: 24, fontSize: 13, color: '#737373' }}>
          <span>{availableCount} of {selectedTheaters.size} theaters available</span>
          {lastChecked && <span>Last checked: {lastChecked}</span>}
        </div>

        {lastChecked && lastChecked.includes('unavailable') && (
          <div style={{
            padding: '12px 16px',
            marginBottom: 20,
            borderRadius: 8,
            background: '#1c1917',
            border: '1px solid #44403c',
            fontSize: 13,
            color: '#a8a29e',
          }}>
            Could not reach AMC servers. Make sure the backend is running (<code>python server.py</code>) and try again.
          </div>
        )}

        {/* Find Next Available result */}
        {findResult && (
          <div style={{
            padding: '16px 20px',
            marginBottom: 20,
            borderRadius: 10,
            background: findResult.found ? '#052e16' : '#1c1917',
            border: `1px solid ${findResult.found ? '#166534' : '#44403c'}`,
          }}>
            {findResult.found ? (
              <div>
                <div style={{ fontSize: 14, fontWeight: 600, color: '#4ade80', marginBottom: 8 }}>
                  Tickets Available!
                </div>
                <div style={{ fontSize: 15, color: '#e5e5e5', marginBottom: 4 }}>
                  {findResult.theater} — {findResult.location}
                </div>
                <div style={{ fontSize: 13, color: '#a3a3a3', marginBottom: 12 }}>
                  Showtimes: {findResult.showtimes?.join(', ')}
                </div>
                <a
                  href={findResult.url}
                  target="_blank"
                  rel="noopener noreferrer"
                  style={{
                    display: 'inline-block',
                    padding: '8px 20px',
                    borderRadius: 6,
                    background: '#d97706',
                    color: '#000',
                    textDecoration: 'none',
                    fontWeight: 600,
                    fontSize: 13,
                  }}
                >
                  Book Now →
                </a>
              </div>
            ) : (
              <div style={{ fontSize: 13, color: '#a8a29e' }}>
                {findResult.message}
              </div>
            )}
            <button
              onClick={() => setFindResult(null)}
              style={{ marginTop: 10, background: 'transparent', border: 'none', color: '#737373', cursor: 'pointer', fontSize: 12 }}
            >
              Dismiss
            </button>
          </div>
        )}

        {/* Theater Grid */}
        <TheaterGrid
          theaters={filteredTheaters}
          availability={availability}
          date={selectedDate}
        />
      </main>
    </div>
  )
}

export default App
