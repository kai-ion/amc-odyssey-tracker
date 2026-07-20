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
  const [availability, setAvailability] = useState({})
  const [loading, setLoading] = useState(false)
  const [lastChecked, setLastChecked] = useState(null)
  const [filter, setFilter] = useState('all') // all, available, soldout

  function getToday() {
    return new Date().toISOString().split('T')[0]
  }

  const checkAvailability = async () => {
    setLoading(true)
    try {
      const res = await fetch(`${API_URL}/check?date=${selectedDate}`)
      const data = await res.json()
      setAvailability(data.results || {})
      setLastChecked(new Date().toLocaleTimeString())
    } catch (err) {
      // If backend is down, use mock data for demo
      const mock = {}
      THEATERS.forEach(t => {
        mock[t.id] = {
          available: Math.random() > 0.7,
          showtimes: Math.random() > 0.7 ? ['2:00 PM', '6:30 PM', '10:00 PM'].slice(0, Math.floor(Math.random() * 3) + 1) : [],
          soldOut: Math.random() > 0.8,
          has70mm: true,
        }
      })
      setAvailability(mock)
      setLastChecked(new Date().toLocaleTimeString() + ' (demo)')
    }
    setLoading(false)
  }

  useEffect(() => {
    checkAvailability()
  }, [selectedDate])

  const filteredTheaters = THEATERS.filter(t => {
    if (filter === 'all') return true
    const status = availability[t.id]
    if (filter === 'available') return status?.available
    if (filter === 'soldout') return status?.soldOut || (!status?.available && status?.showtimes?.length === 0)
    return true
  })

  const availableCount = THEATERS.filter(t => availability[t.id]?.available).length

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
            onClick={checkAvailability}
            disabled={loading}
            style={{
              padding: '8px 20px',
              borderRadius: 6,
              border: '1px solid #d97706',
              background: 'transparent',
              color: '#d97706',
              cursor: loading ? 'wait' : 'pointer',
              fontSize: 13,
              marginLeft: 'auto',
            }}
          >
            {loading ? 'Checking...' : 'Refresh'}
          </button>
        </div>

        {/* Status bar */}
        <div style={{ display: 'flex', gap: 24, marginBottom: 24, fontSize: 13, color: '#737373' }}>
          <span>{availableCount} of {THEATERS.length} theaters available</span>
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
