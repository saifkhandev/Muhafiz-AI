import type { Metadata } from "next";
import { Inter, Space_Grotesk, Noto_Nastaliq_Urdu } from "next/font/google";
import "./globals.css";
import { ShieldProvider } from "@/lib/shield-context";

const inter = Inter({
  variable: "--font-inter",
  subsets: ["latin"],
});

const spaceGrotesk = Space_Grotesk({
  variable: "--font-space-grotesk",
  subsets: ["latin"],
});

const notoNastaliqUrdu = Noto_Nastaliq_Urdu({
  variable: "--font-noto-nastaliq",
  subsets: ["arabic"],
  weight: ["400", "500", "600", "700"],
});

export const metadata: Metadata = {
  title: "Muhafiz AI — Scam Detection for Pakistan",
  description:
    "AI-powered scam detection for text messages and call recordings in English, Urdu, Roman Urdu, and Mixed languages.",
};

export default function RootLayout({ children }: LayoutProps<"/">) {
  return (
    <html
      lang="en"
      className={`${inter.variable} ${spaceGrotesk.variable} ${notoNastaliqUrdu.variable} h-full antialiased`}
    >
      <body className="min-h-full flex flex-col bg-background text-text-primary">
        <ShieldProvider>{children}</ShieldProvider>
      </body>
    </html>
  );
}
