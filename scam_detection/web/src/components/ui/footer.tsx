import Link from "next/link";
import { Shield } from "lucide-react";

export function Footer() {
  return (
    <footer className="border-t border-border/60 bg-surface">
      <div className="mx-auto max-w-7xl px-4 py-12 sm:px-6 lg:px-8">
        <div className="flex flex-col items-center justify-between gap-6 md:flex-row">
          <Link href="/" className="flex items-center gap-2">
            <Shield className="h-6 w-6 text-accent" />
            <span className="font-heading text-lg font-bold text-text-primary">
              Muhafiz<span className="text-accent"> AI</span>
            </span>
          </Link>

          <p className="text-center text-sm text-text-secondary">
            Decision-support tool, not a guarantee. Verify directly with official organizations when in doubt.
          </p>

          <div className="flex items-center gap-6 text-sm text-text-secondary">
            <Link href="/" className="hover:text-text-primary transition-colors">
              Home
            </Link>
            <Link href="/analyze" className="hover:text-text-primary transition-colors">
              Analyze
            </Link>
            <Link href="/roadmap" className="hover:text-text-primary transition-colors">
              Roadmap
            </Link>
          </div>
        </div>
        <div className="mt-8 border-t border-border/40 pt-8 text-center text-xs text-text-secondary/60">
          © {new Date().getFullYear()} Muhafiz AI. Built for the Alibaba AI Hackathon — Karachi Regional Round.
        </div>
      </div>
    </footer>
  );
}
