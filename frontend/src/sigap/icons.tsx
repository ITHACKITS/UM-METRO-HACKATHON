/* Small inline icons for the Sigap workflow. */
import type { ReactNode } from "react";

interface IconProps {
  children: ReactNode;
  size?: number;
}

function Icon({ children, size = 24 }: IconProps) {
  return (
    <svg
      aria-hidden="true"
      className="icon"
      fill="none"
      height={size}
      viewBox="0 0 24 24"
      width={size}
    >
      {children}
    </svg>
  );
}

export const LeafIcon = () => (
  <Icon>
    <path d="M19.8 4.2C12.5 4.5 6.3 7.3 5.1 12.8c-.6 2.7.8 5 3.5 5.4 5.7.8 10.2-6.1 11.2-14Z" stroke="currentColor" strokeWidth="1.8" />
    <path d="M4.2 20c2.7-5.4 6.4-8.4 11.6-10.9" stroke="currentColor" strokeLinecap="round" strokeWidth="1.8" />
  </Icon>
);

export const BugIcon = () => (
  <Icon>
    <path d="M8.2 9.2A3.8 3.8 0 0 1 12 5.4a3.8 3.8 0 0 1 3.8 3.8v5.2A3.8 3.8 0 0 1 12 18.2a3.8 3.8 0 0 1-3.8-3.8V9.2Z" stroke="currentColor" strokeWidth="1.8" />
    <path d="M12 5.4V3m-3 3L7.3 4.2M15 6l1.7-1.8M8.2 11H4.8m3.4 3.5H4.8M15.8 11h3.4m-3.4 3.5h3.4M12 9v9.2" stroke="currentColor" strokeLinecap="round" strokeWidth="1.8" />
  </Icon>
);

export const CameraIcon = () => (
  <Icon size={28}>
    <path d="M4.2 7.8h3l1.4-2h6.8l1.4 2h3v10.4H4.2V7.8Z" stroke="currentColor" strokeLinejoin="round" strokeWidth="1.8" />
    <circle cx="12" cy="13" r="3.2" stroke="currentColor" strokeWidth="1.8" />
  </Icon>
);

export const UploadIcon = () => (
  <Icon size={28}>
    <path d="M4.5 15.5v3.8h15v-3.8M12 16V4.8m0 0L7.8 9M12 4.8 16.2 9" stroke="currentColor" strokeLinecap="round" strokeLinejoin="round" strokeWidth="1.8" />
  </Icon>
);

export const ShieldIcon = () => (
  <Icon size={19}>
    <path d="M12 3 5.7 5.6v4.8c0 4.1 2.5 7.6 6.3 9.6 3.8-2 6.3-5.5 6.3-9.6V5.6L12 3Z" stroke="currentColor" strokeLinejoin="round" strokeWidth="1.8" />
    <path d="m9.2 11.5 1.8 1.8 3.8-4" stroke="currentColor" strokeLinecap="round" strokeLinejoin="round" strokeWidth="1.8" />
  </Icon>
);
