"use client";

import { useEffect, useState } from "react";
import { useShield } from "@/lib/shield-context";

export function MobileShield() {
  const { lastPulse } = useShield();
  const [pulseClass, setPulseClass] = useState("shield-pulse-idle");

  useEffect(() => {
    if (!lastPulse) return;
    const cls = lastPulse.verdict === "Scam" ? "shield-pulse-scam" : "shield-pulse-safe";
    setPulseClass(cls);
    const timeout = setTimeout(() => {
      setPulseClass("shield-pulse-idle");
    }, 600);
    return () => clearTimeout(timeout);
  }, [lastPulse]);

  return (
    <div className={`relative flex items-center justify-center rounded-full p-8 ${pulseClass}`}>
      <svg
        viewBox="0 0 200 240"
        fill="none"
        xmlns="http://www.w3.org/2000/svg"
        className="w-48 h-56"
      >
        <defs>
          <linearGradient id="shieldGrad" x1="0" y1="0" x2="200" y2="240" gradientUnits="userSpaceOnUse">
            <stop offset="0%" stopColor="#2DD4BF" stopOpacity="0.9" />
            <stop offset="100%" stopColor="#0B0F14" stopOpacity="0.4" />
          </linearGradient>
          <filter id="glow">
            <feGaussianBlur stdDeviation="4" result="coloredBlur" />
            <feMerge>
              <feMergeNode in="coloredBlur" />
              <feMergeNode in="SourceGraphic" />
            </feMerge>
          </filter>
        </defs>
        <path
          d="M100 10 L180 40 L180 120 C180 175 145 215 100 230 C55 215 20 175 20 120 L20 40 Z"
          stroke="#2DD4BF"
          strokeWidth="2"
          fill="url(#shieldGrad)"
          filter="url(#glow)"
          opacity="0.85"
        />
        <path
          d="M100 40 L150 60 L150 115 C150 155 128 185 100 198 C72 185 50 155 50 115 L50 60 Z"
          stroke="#2DD4BF"
          strokeWidth="1.5"
          strokeDasharray="6 4"
          fill="none"
          opacity="0.6"
        />
        <circle cx="100" cy="120" r="25" stroke="#2DD4BF" strokeWidth="1.5" fill="none" opacity="0.5" />
        <path
          d="M88 120 L96 128 L112 110"
          stroke="#2DD4BF"
          strokeWidth="3"
          strokeLinecap="round"
          strokeLinejoin="round"
          fill="none"
          opacity="0.8"
        />
      </svg>
    </div>
  );
}
