"use client";

import Link from "next/link";
import { usePathname } from "next/navigation";
import { Shield, Menu, X } from "lucide-react";
import { useState } from "react";
import { useLanguage } from "@/lib/i18n/context";
import { LanguageSwitcher } from "./language-switcher";

export function Header() {
  const pathname = usePathname();
  const [mobileOpen, setMobileOpen] = useState(false);
  const { t } = useLanguage();

  const navLinks = [
    { href: "/", label: t("nav.home") },
    { href: "/analyze", label: t("nav.analyze") },
    { href: "/how-it-works", label: t("nav.howItWorks") },
    { href: "/examples", label: t("nav.examples") },
    { href: "/roadmap", label: t("nav.roadmap") },
  ];

  return (
    <header className="sticky top-0 z-50 border-b border-border/60 bg-background/80 backdrop-blur-md">
      <div className="mx-auto flex max-w-7xl items-center justify-between px-4 py-4 sm:px-6 lg:px-8">
        <Link href="/" className="flex items-center gap-2 group">
          <Shield className="h-7 w-7 text-accent transition-transform group-hover:scale-110" />
          <span className="font-heading text-xl font-bold text-text-primary">
            Muhafiz<span className="text-accent"> AI</span>
          </span>
        </Link>

        <nav className="hidden md:flex items-center gap-6">
          {navLinks.map((link) => {
            const active = pathname === link.href;
            return (
              <Link
                key={link.href}
                href={link.href}
                className={`text-sm font-medium transition-colors ${
                  active
                    ? "text-[#818CF8]"
                    : "text-text-secondary hover:text-text-primary"
                }`}
              >
                {link.label}
              </Link>
            );
          })}
        </nav>

        <div className="hidden md:flex items-center gap-3">
          <LanguageSwitcher />
          <Link
            href="/analyze"
            className="inline-flex items-center rounded-lg border border-[#818CF8] bg-surface px-4 py-2 text-sm font-semibold text-[#818CF8] transition-all hover:border-border hover:text-text-primary hover:shadow-[0_0_15px_rgba(129,140,248,0.2)]"
          >
            {t("nav.tryItNow")}
          </Link>
        </div>

        <div className="md:hidden flex items-center gap-2">
          <LanguageSwitcher />
          <button
            className="text-text-primary"
            onClick={() => setMobileOpen(!mobileOpen)}
            aria-label="Toggle menu"
          >
            {mobileOpen ? <X className="h-6 w-6" /> : <Menu className="h-6 w-6" />}
          </button>
        </div>
      </div>

      {mobileOpen && (
        <div className="md:hidden border-t border-border/60 bg-surface px-4 py-4">
          <nav className="flex flex-col gap-4">
            {navLinks.map((link) => (
              <Link
                key={link.href}
                href={link.href}
                onClick={() => setMobileOpen(false)}
                className={`text-sm font-medium ${
                  pathname === link.href ? "text-[#818CF8]" : "text-text-secondary"
                }`}
              >
                {link.label}
              </Link>
            ))}
            <Link
              href="/analyze"
              onClick={() => setMobileOpen(false)}
              className="mt-2 inline-flex items-center justify-center rounded-lg border border-[#818CF8] bg-surface px-4 py-2 text-sm font-semibold text-[#818CF8] transition-all hover:border-border hover:text-text-primary"
            >
              {t("nav.tryItNow")}
            </Link>
          </nav>
        </div>
      )}
    </header>
  );
}
