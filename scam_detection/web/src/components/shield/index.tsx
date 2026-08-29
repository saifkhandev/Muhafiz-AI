"use client";

import dynamic from "next/dynamic";
import { MobileShield } from "./mobile-shield";

const ShieldScene = dynamic(
  () => import("./shield-scene").then((mod) => ({ default: mod.ShieldScene })),
  {
    ssr: false,
    loading: () => (
      <div className="w-full h-full flex items-center justify-center">
        <div className="w-24 h-24 rounded-full border-2 border-accent/30 border-t-accent animate-spin" />
      </div>
    ),
  }
);

interface ShieldProps {
  className?: string;
  forceMobile?: boolean;
}

export function Shield({ className = "", forceMobile = false }: ShieldProps) {
  return (
    <div className={`relative ${className}`}>
      <div className="hidden md:block w-full h-full">
        {!forceMobile && <ShieldScene />}
      </div>
      <div className="md:hidden w-full h-full flex items-center justify-center">
        <MobileShield />
      </div>
    </div>
  );
}
