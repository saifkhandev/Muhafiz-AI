"use client";

import {
  createContext,
  useContext,
  useState,
  useCallback,
  ReactNode,
} from "react";
import { AnalysisVerdict, ShieldPulseEvent } from "./types";

interface ShieldContextType {
  lastPulse: ShieldPulseEvent | null;
  triggerPulse: (verdict: AnalysisVerdict) => void;
}

const ShieldContext = createContext<ShieldContextType | undefined>(undefined);

export function ShieldProvider({ children }: { children: ReactNode }) {
  const [lastPulse, setLastPulse] = useState<ShieldPulseEvent | null>(null);

  const triggerPulse = useCallback((verdict: AnalysisVerdict) => {
    setLastPulse({ verdict, timestamp: Date.now() });
  }, []);

  return (
    <ShieldContext.Provider value={{ lastPulse, triggerPulse }}>
      {children}
    </ShieldContext.Provider>
  );
}

export function useShield() {
  const context = useContext(ShieldContext);
  if (!context) {
    throw new Error("useShield must be used within a ShieldProvider");
  }
  return context;
}
