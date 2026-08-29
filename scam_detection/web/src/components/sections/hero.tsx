"use client";

import { useEffect, useRef } from "react";
import Link from "next/link";
import { motion } from "framer-motion";
import { Shield } from "@/components/shield";
import { ArrowRight, ShieldCheck } from "lucide-react";

export function Hero() {
  const heroRef = useRef<HTMLElement>(null);

  useEffect(() => {
    if (typeof window === "undefined") return;
    const reduced = window.matchMedia("(prefers-reduced-motion: reduce)").matches;
    if (reduced) return;
  }, []);

  return (
    <section
      ref={heroRef}
      id="hero"
      className="relative overflow-hidden px-4 pt-16 pb-24 sm:px-6 lg:px-8 lg:pt-24 lg:pb-32"
    >
      {/* Background gradient */}
      <div className="pointer-events-none absolute inset-0 bg-[radial-gradient(ellipse_at_top_right,_rgba(45,212,191,0.12),_transparent_50%)]" />
      <div className="pointer-events-none absolute inset-0 bg-[radial-gradient(ellipse_at_bottom_left,_rgba(229,72,77,0.08),_transparent_50%)]" />

      <div className="relative mx-auto grid max-w-7xl items-center gap-12 lg:grid-cols-2">
        <div className="order-2 lg:order-1">
          <motion.div
            initial={{ opacity: 0, y: 24 }}
            animate={{ opacity: 1, y: 0 }}
            transition={{ duration: 0.6, delay: 0 }}
            className="inline-flex items-center gap-2 rounded-full border border-accent/30 bg-accent/10 px-3 py-1 text-xs font-medium text-accent"
          >
            <ShieldCheck className="h-3.5 w-3.5" />
            V4 model · 99.6% adversarial accuracy
          </motion.div>

          <motion.h1
            initial={{ opacity: 0, y: 24 }}
            animate={{ opacity: 1, y: 0 }}
            transition={{ duration: 0.6, delay: 0.1 }}
            className="mt-6 font-heading text-4xl font-bold leading-tight tracking-tight text-text-primary sm:text-5xl lg:text-6xl"
          >
            Pakistan&apos;s AI shield against{" "}
            <span className="gradient-text">scam calls &amp; messages</span>
          </motion.h1>

          <motion.p
            initial={{ opacity: 0, y: 24 }}
            animate={{ opacity: 1, y: 0 }}
            transition={{ duration: 0.6, delay: 0.2 }}
            className="mt-6 max-w-lg text-lg leading-relaxed text-text-secondary"
          >
            Muhafiz AI detects scams in text messages and call recordings across
            English, Urdu, Roman Urdu, and Mixed languages — no GPU required.
          </motion.p>

          <motion.div
            initial={{ opacity: 0, y: 24 }}
            animate={{ opacity: 1, y: 0 }}
            transition={{ duration: 0.6, delay: 0.3 }}
            className="mt-8 flex flex-wrap gap-4"
          >
            <Link
              href="/analyze"
              className="inline-flex items-center gap-2 rounded-lg bg-accent px-6 py-3 font-semibold text-background transition-opacity hover:opacity-90"
            >
              Analyze Now
              <ArrowRight className="h-4 w-4" />
            </Link>
            <Link
              href="/how-it-works"
              className="inline-flex items-center gap-2 rounded-lg border border-border bg-surface px-6 py-3 font-semibold text-text-primary transition-colors hover:border-accent hover:text-accent"
            >
              How It Works
            </Link>
          </motion.div>

          <motion.div
            initial={{ opacity: 0, y: 24 }}
            animate={{ opacity: 1, y: 0 }}
            transition={{ duration: 0.6, delay: 0.4 }}
            className="mt-10 grid grid-cols-3 gap-4 border-t border-border/60 pt-6"
          >
            <div>
              <p className="font-heading text-2xl font-bold text-accent">1,637</p>
              <p className="text-xs text-text-secondary">training messages</p>
            </div>
            <div>
              <p className="font-heading text-2xl font-bold text-accent">99.6%</p>
              <p className="text-xs text-text-secondary">adversarial accuracy</p>
            </div>
            <div>
              <p className="font-heading text-2xl font-bold text-accent">&lt;10ms</p>
              <p className="text-xs text-text-secondary">per text message</p>
            </div>
          </motion.div>
        </div>

        <motion.div
          initial={{ opacity: 0, scale: 0.95 }}
          animate={{ opacity: 1, scale: 1 }}
          transition={{ duration: 0.8, delay: 0.2 }}
          className="order-1 flex h-[320px] items-center justify-center lg:order-2 lg:h-[520px]"
        >
          <Shield className="h-full w-full" />
        </motion.div>
      </div>
    </section>
  );
}
