// Line icons for the side menu; they take the text colour, so active and idle states follow the theme
const base = {
  width: 22,
  height: 22,
  viewBox: '0 0 24 24',
  fill: 'none',
  stroke: 'currentColor',
  strokeWidth: 2,
  strokeLinecap: 'round',
  strokeLinejoin: 'round',
  'aria-hidden': true,
}

export const DashboardIcon = () => (
  <svg {...base}>
    <rect x="3" y="3" width="7" height="7" rx="1.5" />
    <rect x="14" y="3" width="7" height="7" rx="1.5" />
    <rect x="3" y="14" width="7" height="7" rx="1.5" />
    <rect x="14" y="14" width="7" height="7" rx="1.5" />
  </svg>
)

export const RegisterIcon = () => (
  <svg {...base}>
    <path d="M12 3v18" />
    <path d="M5 7h14" />
    <path d="M5 7l-3 7a3 3 0 0 0 6 0z" />
    <path d="M19 7l-3 7a3 3 0 0 0 6 0z" />
  </svg>
)

export const GymIcon = () => (
  <svg {...base}>
    <path d="M6 6v12M18 6v12M3 9v6M21 9v6M6 12h12" />
  </svg>
)

export const FoodIcon = () => (
  <svg {...base}>
    <path d="M7 3v7a2 2 0 0 0 2 2v9" />
    <path d="M5 3v5" />
    <path d="M9 3v5" />
    <path d="M17 21V3c-2 1-3 3-3 6v4h3" />
  </svg>
)

export const ProgressIcon = () => (
  <svg {...base}>
    <path d="M3 17l6-6 4 4 8-8" />
    <path d="M14 7h7v7" />
  </svg>
)

export const ProfileIcon = () => (
  <svg {...base}>
    <circle cx="12" cy="8" r="4" />
    <path d="M4 21c0-4 4-6 8-6s8 2 8 6" />
  </svg>
)
