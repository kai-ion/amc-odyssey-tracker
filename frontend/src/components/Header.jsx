import React from 'react'

function Header() {
  return (
    <header style={{
      padding: '40px 20px 24px',
      textAlign: 'center',
      borderBottom: '1px solid #262626',
      marginBottom: 32,
    }}>
      <h1 style={{
        fontSize: 36,
        fontWeight: 700,
        margin: 0,
        letterSpacing: '-0.5px',
        background: 'linear-gradient(135deg, #d97706, #f59e0b)',
        WebkitBackgroundClip: 'text',
        WebkitTextFillColor: 'transparent',
      }}>
        The Odyssey
      </h1>
      <p style={{ color: '#737373', margin: '8px 0 0', fontSize: 15 }}>
        70mm &amp; IMAX 70mm Showtime Tracker
      </p>
      <p style={{ color: '#525252', margin: '4px 0 0', fontSize: 12 }}>
        Christopher Nolan &middot; 2025 &middot; Find available 70mm screenings near you
      </p>
    </header>
  )
}

export default Header
