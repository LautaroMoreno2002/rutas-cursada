export default function Logo({ size = 26 }) {
  return (
    <svg width={size} height={size} viewBox="0 0 32 32" aria-hidden="true">
      <path d="M5 22 L14 22 L19 10 L27 10" fill="none" stroke="currentColor" strokeWidth="3.5" strokeLinejoin="round" />
      <circle cx="5" cy="22" r="3.6" fill="var(--papel)" stroke="currentColor" strokeWidth="2.6" />
      <circle cx="16.4" cy="16.3" r="2.6" fill="currentColor" />
      <circle cx="27" cy="10" r="3.6" fill="var(--papel)" stroke="currentColor" strokeWidth="2.6" />
    </svg>
  )
}
