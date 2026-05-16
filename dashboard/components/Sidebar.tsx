"use client";
import Link from "next/link";
import { usePathname } from "next/navigation";
import clsx from "clsx";

const links = [
  {
    href: "/",
    label: "Início",
    icon: (
      <svg width="22" height="22" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round">
        <rect x="3" y="3" width="7" height="7"/><rect x="14" y="3" width="7" height="7"/>
        <rect x="14" y="14" width="7" height="7"/><rect x="3" y="14" width="7" height="7"/>
      </svg>
    ),
  },
  {
    href: "/transactions",
    label: "Transações",
    icon: (
      <svg width="22" height="22" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round">
        <line x1="8" y1="6" x2="21" y2="6"/><line x1="8" y1="12" x2="21" y2="12"/>
        <line x1="8" y1="18" x2="21" y2="18"/><line x1="3" y1="6" x2="3.01" y2="6"/>
        <line x1="3" y1="12" x2="3.01" y2="12"/><line x1="3" y1="18" x2="3.01" y2="18"/>
      </svg>
    ),
  },
  {
    href: "/cards",
    label: "Cartões",
    icon: (
      <svg width="22" height="22" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round">
        <rect x="1" y="4" width="22" height="16" rx="2" ry="2"/><line x1="1" y1="10" x2="23" y2="10"/>
      </svg>
    ),
  },
  {
    href: "/forecast",
    label: "Previsão",
    icon: (
      <svg width="22" height="22" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round">
        <polyline points="22 12 18 12 15 21 9 3 6 12 2 12"/>
      </svg>
    ),
  },
  {
    href: "/goals",
    label: "Metas",
    icon: (
      <svg width="22" height="22" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round">
        <circle cx="12" cy="12" r="10"/><circle cx="12" cy="12" r="6"/><circle cx="12" cy="12" r="2"/>
      </svg>
    ),
  },
];

export function Sidebar() {
  const pathname = usePathname();
  if (pathname === "/login") return null;

  return (
    <>
      {/* Desktop sidebar */}
      <aside className="hidden sm:flex w-52 bg-gray-900 border-r border-gray-800 flex-col p-4 gap-2 shrink-0">
        <h1 className="text-lg font-bold text-emerald-400 mb-4">💰 Finance</h1>
        {links.map((l) => (
          <Link
            key={l.href}
            href={l.href}
            className={clsx(
              "px-3 py-2 rounded-lg text-sm transition-colors",
              pathname === l.href
                ? "bg-emerald-700 text-white font-medium"
                : "text-gray-400 hover:bg-gray-800 hover:text-white"
            )}
          >
            {l.label}
          </Link>
        ))}
      </aside>

      {/* Mobile bottom navigation */}
      <nav className="sm:hidden fixed bottom-0 left-0 right-0 z-50 bg-gray-900 border-t border-gray-800 flex">
        {links.map((l) => (
          <Link
            key={l.href}
            href={l.href}
            className={clsx(
              "flex-1 flex flex-col items-center justify-center py-2 gap-0.5 transition-colors",
              pathname === l.href ? "text-emerald-400" : "text-gray-500"
            )}
          >
            {l.icon}
            <span className="text-[10px] leading-tight">{l.label}</span>
          </Link>
        ))}
      </nav>
    </>
  );
}
