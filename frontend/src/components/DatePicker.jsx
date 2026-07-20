import React from 'react'

function DatePicker({ selected, onChange }) {
  const today = new Date()
  const dates = []
  for (let i = 0; i < 60; i++) {
    const d = new Date(today)
    d.setDate(today.getDate() + i)
    dates.push(d)
  }

  const formatDay = (d) => d.toLocaleDateString('en-US', { weekday: 'short' })
  const formatDate = (d) => d.getDate()
  const formatMonth = (d) => d.toLocaleDateString('en-US', { month: 'short' })
  const toISO = (d) => d.toISOString().split('T')[0]

  return (
    <div style={{ display: 'flex', gap: 4, overflowX: 'auto', padding: '4px 0' }}>
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
    </div>
  )
}

export default DatePicker
