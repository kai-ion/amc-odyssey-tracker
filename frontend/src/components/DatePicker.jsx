import React, { useState } from 'react'

function DatePicker({ selected, onChange }) {
  const [showCalendar, setShowCalendar] = useState(false)
  const today = new Date()

  const dates = []
  for (let i = 0; i < 5; i++) {
    const d = new Date(today)
    d.setDate(today.getDate() + i)
    dates.push(d)
  }

  const formatDay = (d) => d.toLocaleDateString('en-US', { weekday: 'short' })
  const formatDate = (d) => d.getDate()
  const formatMonth = (d) => d.toLocaleDateString('en-US', { month: 'short' })
  const toISO = (d) => d.toISOString().split('T')[0]

  const handleCalendarSelect = (e) => {
    onChange(e.target.value)
    setShowCalendar(false)
  }

  return (
    <div style={{ display: 'flex', gap: 6, alignItems: 'center' }}>
      {dates.map(d => {
        const iso = toISO(d)
        const isSelected = iso === selected
        const isToday = iso === toISO(today)
        return (
          <button
            key={iso}
            onClick={() => onChange(iso)}
            style={{
              display: 'flex',
              flexDirection: 'column',
              alignItems: 'center',
              padding: '8px 12px',
              borderRadius: 8,
              border: isSelected ? '2px solid #d97706' : '1px solid #333',
              background: isSelected ? '#292524' : 'transparent',
              color: isSelected ? '#f59e0b' : '#a3a3a3',
              cursor: 'pointer',
              minWidth: 50,
              transition: 'all 0.15s',
            }}
          >
            <span style={{ fontSize: 11, opacity: 0.7 }}>{formatDay(d)}</span>
            <span style={{ fontSize: 18, fontWeight: 600 }}>{formatDate(d)}</span>
            <span style={{ fontSize: 10, opacity: 0.5 }}>{formatMonth(d)}</span>
            {isToday && <span style={{ fontSize: 9, color: '#d97706', marginTop: 2 }}>today</span>}
          </button>
        )
      })}

      {/* Calendar button */}
      <div style={{ position: 'relative' }}>
        <button
          onClick={() => setShowCalendar(!showCalendar)}
          style={{
            display: 'flex',
            flexDirection: 'column',
            alignItems: 'center',
            justifyContent: 'center',
            padding: '12px 14px',
            borderRadius: 8,
            border: showCalendar ? '2px solid #d97706' : '1px solid #333',
            background: showCalendar ? '#292524' : 'transparent',
            color: '#a3a3a3',
            cursor: 'pointer',
            minWidth: 50,
            height: 68,
            fontSize: 22,
          }}
          title="Pick a date"
        >
          📅
        </button>

        {showCalendar && (
          <div style={{
            position: 'absolute',
            top: 76,
            left: '50%',
            transform: 'translateX(-50%)',
            zIndex: 100,
            background: '#1a1a1a',
            border: '1px solid #404040',
            borderRadius: 10,
            padding: 12,
            boxShadow: '0 8px 24px rgba(0,0,0,0.5)',
          }}>
            <input
              type="date"
              value={selected}
              min={toISO(today)}
              onChange={handleCalendarSelect}
              style={{
                background: '#262626',
                border: '1px solid #525252',
                borderRadius: 6,
                color: '#e5e5e5',
                padding: '10px 14px',
                fontSize: 15,
                cursor: 'pointer',
                colorScheme: 'dark',
              }}
            />
          </div>
        )}
      </div>
    </div>
  )
}

export default DatePicker
