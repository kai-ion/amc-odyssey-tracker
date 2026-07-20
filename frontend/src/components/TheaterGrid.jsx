import React from 'react'

function TheaterGrid({ theaters, availability, date }) {
  return (
    <div style={{
      display: 'grid',
      gridTemplateColumns: 'repeat(auto-fill, minmax(320px, 1fr))',
      gap: 16,
    }}>
      {theaters.map(theater => {
        const status = availability[theater.id] || {}
        return (
          <TheaterCard
            key={theater.id}
            theater={theater}
            status={status}
            date={date}
          />
        )
      })}
    </div>
  )
}

function TheaterCard({ theater, status, date }) {
  const { available, showtimes = [], soldOut, has70mm, notChecked } = status

  let borderColor = '#333'
  let statusText = 'Checking...'
  let statusColor = '#737373'

  if (notChecked) {
    borderColor = '#3f3f46'
    statusText = 'Unable to check'
    statusColor = '#71717a'
  } else if (available) {
    borderColor = '#16a34a'
    statusText = 'AVAILABLE'
    statusColor = '#4ade80'
  } else if (soldOut) {
    borderColor = '#dc2626'
    statusText = 'SOLD OUT'
    statusColor = '#f87171'
  } else if (showtimes.length === 0) {
    borderColor = '#525252'
    statusText = 'No showtimes'
    statusColor = '#737373'
  }

  const bookingUrl = `https://www.amctheatres.com/movies/the-odyssey-76238/showtimes/all/${date}/${theater.id}/all`

  return (
    <div style={{
      background: '#171717',
      border: `1px solid ${borderColor}`,
      borderRadius: 12,
      padding: 20,
      transition: 'all 0.2s',
    }}>
      {/* Header */}
      <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'flex-start', marginBottom: 12 }}>
        <div>
          <h3 style={{ margin: 0, fontSize: 15, fontWeight: 600, color: '#e5e5e5' }}>
            {theater.name}
          </h3>
          <p style={{ margin: '4px 0 0', fontSize: 13, color: '#737373' }}>
            {theater.location}
          </p>
        </div>
        <span style={{
          fontSize: 11,
          fontWeight: 600,
          padding: '4px 8px',
          borderRadius: 4,
          background: available ? 'rgba(22,163,74,0.15)' : soldOut ? 'rgba(220,38,38,0.15)' : 'rgba(82,82,82,0.3)',
          color: statusColor,
        }}>
          {statusText}
        </span>
      </div>

      {/* Format badge */}
      {has70mm && (
        <div style={{
          display: 'inline-block',
          padding: '3px 8px',
          borderRadius: 4,
          background: '#292524',
          border: '1px solid #44403c',
          fontSize: 11,
          color: '#d97706',
          marginBottom: 12,
        }}>
          IMAX 70mm
        </div>
      )}

      {/* Showtimes */}
      {(status.showtimeDetails?.length > 0 || showtimes.length > 0) && (
        <div style={{ display: 'flex', gap: 8, flexWrap: 'wrap', marginBottom: 12 }}>
          {(status.showtimeDetails || showtimes.map(t => ({ time: t }))).map((d, i) => (
            <div key={i} style={{
              display: 'flex',
              flexDirection: 'column',
              alignItems: 'center',
              padding: '6px 12px',
              borderRadius: 6,
              background: available ? '#14532d' : '#292524',
              border: `1px solid ${available ? '#166534' : '#44403c'}`,
              color: available ? '#4ade80' : '#a3a3a3',
              fontSize: 13,
              fontWeight: 500,
            }}>
              <span>{d.time}</span>
              {d.seatsAvailable != null && (
                <span style={{ fontSize: 10, opacity: 0.85, marginTop: 2 }}>
                  {d.seatsAvailable} of {d.seatsTotal} seats
                </span>
              )}
            </div>
          ))}
        </div>
      )}

      {/* Book button */}
      {available && (
        <a
          href={bookingUrl}
          target="_blank"
          rel="noopener noreferrer"
          style={{
            display: 'block',
            textAlign: 'center',
            padding: '10px 16px',
            borderRadius: 8,
            background: '#d97706',
            color: '#000',
            textDecoration: 'none',
            fontWeight: 600,
            fontSize: 14,
            marginTop: 8,
          }}
        >
          Book Tickets →
        </a>
      )}
    </div>
  )
}

export default TheaterGrid
