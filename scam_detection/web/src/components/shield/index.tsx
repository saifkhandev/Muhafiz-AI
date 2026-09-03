"use client";

import { MobileShield } from "./mobile-shield";

interface ShieldProps {
  className?: string;
  forceMobile?: boolean;
}

export function Shield({ className = "" }: ShieldProps) {
  return (
    <div className={`relative ${className}`}>
      <div className="w-full h-full flex items-center justify-center">
        <MobileShield />
      </div>
    </div>
  );
}
