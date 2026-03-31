import type { Metadata } from "next";
import { Geist, Geist_Mono } from "next/font/google";
import Link from "next/link";
import "./globals.css";

const geistSans = Geist({
  variable: "--font-geist-sans",
  subsets: ["latin"],
});

const geistMono = Geist_Mono({
  variable: "--font-geist-mono",
  subsets: ["latin"],
});

export const metadata: Metadata = {
  title: "Situation Room",
  description: "Autonomous Retail Investment Agent",
};

const navItems = [
  { href: "/", label: "Dashboard", icon: "~" },
  { href: "/chat", label: "Chat", icon: ">" },
  { href: "/signals", label: "Signals", icon: "#" },
  { href: "/filings", label: "Filings", icon: "!" },
  { href: "/graph", label: "Thesis Graph", icon: "*" },
  { href: "/portfolio", label: "Portfolio", icon: "$" },
  { href: "/scorecard", label: "Scorecard", icon: "%" },
];

export default function RootLayout({
  children,
}: {
  children: React.ReactNode;
}) {
  return (
    <html lang="en" className={`${geistSans.variable} ${geistMono.variable} h-full dark`}>
      <body className="min-h-screen bg-[#0a0a1a] text-gray-100 flex">
        {/* Sidebar */}
        <nav className="w-56 bg-[#0d0d20] border-r border-gray-800 p-4 flex flex-col gap-1 shrink-0 sticky top-0 h-screen">
          <div className="mb-6">
            <h1 className="text-lg font-bold text-cyan-400 tracking-tight">Situation Room</h1>
            <p className="text-xs text-gray-500">Autonomous Investment Agent</p>
          </div>
          {navItems.map((item) => (
            <Link
              key={item.href}
              href={item.href}
              className="flex items-center gap-3 px-3 py-2 rounded-lg text-sm text-gray-300 hover:bg-[#1a1a2e] hover:text-cyan-400 transition-colors"
            >
              <span className="text-cyan-500 font-mono w-4">{item.icon}</span>
              {item.label}
            </Link>
          ))}
        </nav>

        {/* Main content */}
        <main className="flex-1 p-6 overflow-y-auto">
          {children}
        </main>
      </body>
    </html>
  );
}
