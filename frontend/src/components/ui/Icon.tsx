/**
 * The icon set, drawn to match the reference's weight: 1.6px strokes on a 24px
 * grid, round joins, no fills. Icons are decorative by default and hidden from
 * assistive technology — every one of them sits next to a real text label.
 */

export type IconName =
  | 'arrow-right'
  | 'chart'
  | 'check'
  | 'chevron-down'
  | 'external'
  | 'info'
  | 'link'
  | 'market'
  | 'message'
  | 'plus'
  | 'refresh'
  | 'send'
  | 'settings'
  | 'shield'
  | 'sidebar'
  | 'user'
  | 'warning'

const PATHS: Record<IconName, React.ReactNode> = {
  'arrow-right': <path d="M4 12h15m0 0-5.5-5.5M19 12l-5.5 5.5" />,
  chart: <path d="M4 19h16M6.5 16V9.5M11 16V5.5M15.5 16v-4M20 16v-8" />,
  check: <path d="m5 12.5 4.5 4.5L19 7" />,
  'chevron-down': <path d="m6.5 9.5 5.5 5.5 5.5-5.5" />,
  external: <path d="M13.5 5H19v5.5M19 5l-7 7M17 14v4a1.5 1.5 0 0 1-1.5 1.5H6A1.5 1.5 0 0 1 4.5 18V8.5A1.5 1.5 0 0 1 6 7h4" />,
  info: (
    <>
      <circle cx="12" cy="12" r="8.25" />
      <path d="M12 11v5.25M12 7.9v.1" />
    </>
  ),
  link: <path d="M10 13.5a3.5 3.5 0 0 0 5 0l3-3a3.54 3.54 0 0 0-5-5l-1.5 1.5M14 10.5a3.5 3.5 0 0 0-5 0l-3 3a3.54 3.54 0 0 0 5 5l1.5-1.5" />,
  market: (
    <>
      <path d="M4 19h16" />
      <path d="m5.5 14.5 4-4.5 3.5 3 5.5-6.5" />
    </>
  ),
  message: (
    <>
      <path d="M20 14.5A2.5 2.5 0 0 1 17.5 17H9l-4.5 3.5V6.5A2.5 2.5 0 0 1 7 4h10.5A2.5 2.5 0 0 1 20 6.5Z" />
      <path d="M12 10.4v.1" />
    </>
  ),
  plus: <path d="M12 5.5v13M5.5 12h13" />,
  refresh: <path d="M19.5 12a7.5 7.5 0 1 1-2.4-5.5M19.5 4.5V10H14" />,
  send: <path d="M4.5 12 20 5l-7 15-2.4-6.2z" />,
  settings: (
    <>
      <circle cx="12" cy="12" r="3" />
      <path d="M12 3.5v2M12 18.5v2M4.9 7.75l1.75 1M17.35 15.25l1.75 1M4.9 16.25l1.75-1M17.35 8.75l1.75-1" />
    </>
  ),
  shield: (
    <>
      <path d="M12 3.5 5 6v6c0 4 3 7 7 8.5 4-1.5 7-4.5 7-8.5V6z" />
      <path d="m9.25 12 2 2 3.5-3.75" />
    </>
  ),
  sidebar: (
    <>
      <rect x="4" y="4.5" width="16" height="15" rx="2.5" />
      <path d="M10 4.5v15" />
    </>
  ),
  user: (
    <>
      <circle cx="12" cy="9" r="3.25" />
      <path d="M5.5 19.5a6.5 6.5 0 0 1 13 0" />
    </>
  ),
  warning: (
    <>
      <path d="M12 4.5 21 19.5H3z" />
      <path d="M12 10v4.25M12 16.9v.1" />
    </>
  ),
}

type IconProps = {
  name: IconName
  size?: number
  /** When set, the icon is announced; otherwise it is hidden as decorative. */
  label?: string | undefined
  className?: string | undefined
  strokeWidth?: number | undefined
}

export function Icon({ name, size = 18, label, className, strokeWidth = 1.6 }: IconProps) {
  return (
    <svg
      viewBox="0 0 24 24"
      width={size}
      height={size}
      className={className}
      fill="none"
      stroke="currentColor"
      strokeWidth={strokeWidth}
      strokeLinecap="round"
      strokeLinejoin="round"
      {...(label ? { role: 'img' as const, 'aria-label': label } : { 'aria-hidden': true })}
    >
      {PATHS[name]}
    </svg>
  )
}
