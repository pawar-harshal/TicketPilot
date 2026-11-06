/**
 * Original mark for TicketPilot -- a rounded square filled with the
 * product's own indigo-to-purple gradient (the same stops the landing
 * page's Silk shader uses), with a simple four-point spark at its
 * center. The spark reads as "AI-assisted" without being a literal
 * robot/chat-bubble cliche, and without being any real brand's mark --
 * just a plain abstract symbol in our own colors.
 */
function Logo({ size = 32 }) {
  return (
    <svg
      className="qc-logo"
      width={size}
      height={size}
      viewBox="0 0 32 32"
      role="img"
      aria-label="TicketPilot logo"
    >
      <defs>
        <linearGradient id="qc-logo-gradient" x1="0" y1="0" x2="32" y2="32" gradientUnits="userSpaceOnUse">
          <stop offset="0" stopColor="#3D2C8D" />
          <stop offset="1" stopColor="#916BBF" />
        </linearGradient>
      </defs>
      <rect width="32" height="32" rx="9" fill="url(#qc-logo-gradient)" />
      <path
        d="M16 7.5 L18.1 13.9 L24.5 16 L18.1 18.1 L16 24.5 L13.9 18.1 L7.5 16 L13.9 13.9 Z"
        fill="#fff"
      />
    </svg>
  );
}

export default Logo;
