import React, { useState, useEffect } from 'react'
import TheaterGrid from './components/TheaterGrid'
import DatePicker from './components/DatePicker'
import Header from './components/Header'

const API_URL = import.meta.env.VITE_API_URL || 'http://localhost:5000'

const THEATERS = [
  { id: "1752", name: "AMC Lincoln Square 13", location: "New York, NY", state: "NY" },
  { id: "2254", name: "AMC Metreon 16", location: "San Francisco, CA", state: "CA" },
  { id: "1004", name: "AMC Universal CityWalk", location: "Universal City, CA", state: "CA" },
  { id: "2291", name: "AMC Century City 15", location: "Los Angeles, CA", state: "CA" },
  { id: "2136", name: "AMC King of Prussia 16", location: "King of Prussia, PA", state: "PA" },
  { id: "3174", name: "AMC Navy Pier IMAX", location: "Chicago, IL", state: "IL" },
  { id: "2295", name: "AMC NorthPark 15", location: "Dallas, TX", state: "TX" },
  { id: "2304", name: "AMC Aventura 24", location: "Aventura, FL", state: "FL" },
  { id: "2306", name: "AMC Tysons Corner 16", location: "McLean, VA", state: "VA" },
  { id: "2070", name: "AMC Garden State 16", location: "Paramus, NJ", state: "NJ" },
]

function App() {
  const [selectedDate, setSelectedDate] = useState(getToday())
  const [selectedTheaters, setSelectedTheaters] = useState(() => {
    const saved = localStorage.getItem('selectedTheaters')
    return saved ? new Set(JSON.parse(saved)) : new Set(THEATERS.map(t => t.id))
  })
  const [availability, setAvailability] = useState({})
  const [loading, setLoading] = useState(false)
  const [lastChecked, setLastChecked] = useState(null)
  const [filter, setFilter] = useState('all') // all, available, soldout
  const [showTheaterPicker, setShowTheaterPicker] = useState(false)

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
      // Backend down or timeout — show status as "not yet available"
      const mock = {}
      THEATERS.forEach(t => {
        mock[t.id] = {
          available: false,
          showtimes: [],
          soldOut: false,
          has70mm: true,
          notChecked: true,
        }
      })
      setAvailability(mock)
      setLastChecked(new Date().toLocaleTimeString() + ' (backend unavailable)')
    }
    setLoading(false)
  }

  useEffect(() => {
    checkAvailability()
  }, [selectedDate])

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

          {loading && (
            <span style={{ marginLeft: 'auto', fontSize: 13, color: '#d97706' }}>
              ⟳ Checking availability...
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
