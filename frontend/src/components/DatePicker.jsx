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
          <Calendar
            selected={selected}
            today={today}
            onSelect={(iso) => { onChange(iso); setShowCalendar(false) }}
            onClose={() => setShowCalendar(false)}
          />
        )}
      </div>
    </div>
  )
}

function Calendar({ selected, today, onSelect, onClose }) {
  const [viewDate, setViewDate] = useState(selected ? new Date(selected + 'T00:00') : new Date())

  const year = viewDate.getFullYear()
  const month = viewDate.getMonth()

  const monthName = viewDate.toLocaleDateString('en-US', { month: 'long', year: 'numeric' })

  const prevMonth = () => setViewDate(new Date(year, month - 1, 1))
  const nextMonth = () => setViewDate(new Date(year, month + 1, 1))

  // Build calendar grid
  const firstDay = new Date(year, month, 1).getDay()
  const daysInMonth = new Date(year, month + 1, 0).getDate()

  const days = []
  for (let i = 0; i < firstDay; i++) days.push(null)
  for (let i = 1; i <= daysInMonth; i++) days.push(i)

  const toISO = (d) => d.toISOString().split('T')[0]
  const todayISO = toISO(today)

  return (
    <div style={{
      position: 'absolute',
      top: 76,
      left: '50%',
      transform: 'translateX(-50%)',
      zIndex: 100,
      background: '#1a1a1a',
      border: '1px solid #404040',
      borderRadius: 12,
      padding: 16,
      boxShadow: '0 12px 32px rgba(0,0,0,0.6)',
      width: 280,
    }}>
      {/* Header with month navigation */}
      <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', marginBottom: 12 }}>
        <button onClick={prevMonth} style={navBtnStyle}>←</button>
        <span style={{ fontSize: 15, fontWeight: 600, color: '#e5e5e5' }}>{monthName}</span>
        <button onClick={nextMonth} style={navBtnStyle}>→</button>
      </div>

      {/* Day headers */}
      <div style={{ display: 'grid', gridTemplateColumns: 'repeat(7, 1fr)', gap: 2, marginBottom: 4 }}>
        {['Su', 'Mo', 'Tu', 'We', 'Th', 'Fr', 'Sa'].map(d => (
          <div key={d} style={{ textAlign: 'center', fontSize: 11, color: '#737373', padding: 4 }}>{d}</div>
        ))}
      </div>

      {/* Day grid */}
      <div style={{ display: 'grid', gridTemplateColumns: 'repeat(7, 1fr)', gap: 2 }}>
        {days.map((day, i) => {
          if (!day) return <div key={`empty-${i}`} />

          const dateObj = new Date(year, month, day)
          const iso = toISO(dateObj)
          const isSelected = iso === selected
          const isToday = iso === todayISO
          const isPast = dateObj < today && !isToday

          return (
            <button
              key={iso}
              onClick={() => !isPast && onSelect(iso)}
              disabled={isPast}
              style={{
                width: 34,
                height: 34,
                borderRadius: '50%',
                border: isSelected ? '2px solid #d97706' : 'none',
                background: isSelected ? '#292524' : 'transparent',
                color: isPast ? '#404040' : isSelected ? '#f59e0b' : isToday ? '#d97706' : '#d4d4d4',
                fontWeight: isSelected || isToday ? 600 : 400,
                fontSize: 13,
                cursor: isPast ? 'default' : 'pointer',
                display: 'flex',
                alignItems: 'center',
                justifyContent: 'center',
              }}
            >
              {day}
            </button>
          )
        })}
      </div>

      {/* Close */}
      <button
        onClick={onClose}
        style={{ marginTop: 12, width: '100%', padding: 8, borderRadius: 6, border: '1px solid #333', background: 'transparent', color: '#737373', cursor: 'pointer', fontSize: 12 }}
      >
        Close
      </button>
    </div>
  )
}

const navBtnStyle = {
  background: 'transparent',
  border: '1px solid #404040',
  borderRadius: 6,
  color: '#a3a3a3',
  cursor: 'pointer',
  padding: '4px 10px',
  fontSize: 14,
}

export default DatePicker
