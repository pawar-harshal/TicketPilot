/**
 * Small, consistent line-icon set for support issue categories -- real
 * iconography instead of emoji, the way an actual delivery app's help
 * center would show them. All 24x24, stroke = currentColor so they pick
 * up whatever color their container sets (see .issue-row__icon /
 * .qc-help-entry__icon).
 */
const commonProps = {
  width: 22,
  height: 22,
  viewBox: "0 0 24 24",
  fill: "none",
  stroke: "currentColor",
  strokeWidth: 1.8,
  strokeLinecap: "round",
  strokeLinejoin: "round",
};

export function DeliveryIcon(props) {
  return (
    <svg {...commonProps} {...props}>
      <rect x="2" y="8" width="13" height="8" rx="1.5" />
      <path d="M15 11h3.5l2.5 2.5V16a1 1 0 0 1-1 1H15" />
      <circle cx="7" cy="18" r="1.8" />
      <circle cx="17.5" cy="18" r="1.8" />
    </svg>
  );
}

export function BillingIcon(props) {
  return (
    <svg {...commonProps} {...props}>
      <rect x="2.5" y="5.5" width="19" height="13" rx="2" />
      <path d="M2.5 9.5h19" />
      <path d="M6 14.5h4" />
    </svg>
  );
}

export function TrackIcon(props) {
  return (
    <svg {...commonProps} {...props}>
      <path d="M12 21s7-7.6 7-12.2A7 7 0 0 0 5 8.8C5 13.4 12 21 12 21Z" />
      <circle cx="12" cy="8.6" r="2.4" />
    </svg>
  );
}

export function OrderIcon(props) {
  return (
    <svg {...commonProps} {...props}>
      <path d="M3.5 7.5 12 3l8.5 4.5L12 12 3.5 7.5Z" />
      <path d="M3.5 7.5V16l8.5 4.5V12" />
      <path d="M20.5 7.5V16L12 20.5" />
    </svg>
  );
}

export function CancelIcon(props) {
  return (
    <svg {...commonProps} {...props}>
      <circle cx="12" cy="12" r="9" />
      <path d="M9 9l6 6M15 9l-6 6" />
    </svg>
  );
}

export function AlertIcon(props) {
  return (
    <svg {...commonProps} {...props}>
      <path d="M12 3 2.5 19.5h19L12 3Z" />
      <path d="M12 10v4" />
      <circle cx="12" cy="16.8" r="0.2" fill="currentColor" stroke="none" />
    </svg>
  );
}

export function StoreIcon(props) {
  return (
    <svg {...commonProps} {...props}>
      <path d="M3 9.5 4.3 4h15.4L21 9.5" />
      <path d="M3 9.5a2.8 2.8 0 0 0 5.4 1.1A2.8 2.8 0 0 0 12 10.6a2.8 2.8 0 0 0 3.6 0 2.8 2.8 0 0 0 5.4-1.1" />
      <path d="M5 11v8.5h14V11" />
    </svg>
  );
}

export function HelpIcon(props) {
  return (
    <svg {...commonProps} {...props}>
      <circle cx="12" cy="12" r="9" />
      <path d="M9.3 9.3a2.7 2.7 0 1 1 3.8 2.4c-.8.4-1.1.9-1.1 1.8" />
      <circle cx="12" cy="16.6" r="0.2" fill="currentColor" stroke="none" />
    </svg>
  );
}

export function ChevronRightIcon(props) {
  return (
    <svg {...commonProps} strokeWidth={2} width={18} height={18} {...props}>
      <path d="m9 6 6 6-6 6" />
    </svg>
  );
}

const ISSUE_ICONS = {
  delivery: DeliveryIcon,
  billing: BillingIcon,
  track: TrackIcon,
  order: OrderIcon,
  cancel: CancelIcon,
  alert: AlertIcon,
  store: StoreIcon,
  help: HelpIcon,
};

export default ISSUE_ICONS;
