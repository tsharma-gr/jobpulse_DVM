"use client";

import Link from "next/link";
import { usePathname } from "next/navigation";
import { Search, Layers, ShieldAlert, CheckCircle, Database } from "lucide-react";

export default function Sidebar() {
  const pathname = usePathname();

  const links = [
    {
      name: "New Search",
      href: "/",
      icon: Search,
      description: "Search individual titles",
    },
    {
      name: "Bulk Search",
      href: "/bulk",
      icon: Layers,
      description: "Upload Excel for batch run",
    },
  ];

  return (
    <aside className="w-60 bg-[#0d1321] border-r border-[#1f2937] flex flex-col justify-between shrink-0 h-screen sticky top-0">
      <div className="flex flex-col gap-6 p-6">
        {/* App Logo */}
        <div className="flex items-center gap-3">
          <div className="h-10 w-10 rounded-xl bg-indigo-600 flex items-center justify-center shadow-lg shadow-indigo-600/30">
            <Database className="h-5 w-5 text-white" />
          </div>
          <div>
            <h1 className="text-xl font-bold tracking-tight text-white flex items-center gap-1.5">
              Job<span className="text-indigo-400 font-extrabold">Pulse</span>
            </h1>
            <p className="text-[10px] text-gray-500 font-mono">UK Vacancy DVM v1.0</p>
          </div>
        </div>

        {/* Navigation Items */}
        <nav className="flex flex-col gap-1.5 mt-8">
          {links.map((link) => {
            const Icon = link.icon;
            const isActive = pathname === link.href;
            return (
              <Link
                key={link.name}
                href={link.href}
                className={`flex items-center gap-3.5 px-4 py-3.5 rounded-xl transition-all duration-300 group ${
                  isActive
                    ? "bg-indigo-600 text-white shadow-lg shadow-indigo-600/20 font-medium"
                    : "text-gray-400 hover:text-white hover:bg-[#1a2333]"
                }`}
              >
                <Icon className={`h-5 w-5 transition-transform duration-300 ${
                  isActive ? "scale-110" : "group-hover:scale-110"
                }`} />
                <div className="flex flex-col">
                  <span className="text-sm">{link.name}</span>
                  <span className={`text-[10px] ${isActive ? "text-indigo-200" : "text-gray-500 group-hover:text-gray-400"}`}>
                    {link.description}
                  </span>
                </div>
              </Link>
            );
          })}
        </nav>
      </div>

      {/* Footer / System Status */}
      <div className="p-6 border-t border-[#1f2937] bg-[#0b0f19]">
        <div className="flex items-center justify-between rounded-xl bg-[#141b2b] p-3 border border-[#1f2937]">
          <div className="flex items-center gap-2.5">
            <span className="flex h-2.5 w-2.5 relative">
              <span className="animate-ping absolute inline-flex h-full w-full rounded-full bg-emerald-400 opacity-75"></span>
              <span className="relative inline-flex rounded-full h-2.5 w-2.5 bg-emerald-500"></span>
            </span>
            <div className="flex flex-col">
              <span className="text-xs text-white font-medium">Scrapers Ready</span>
              <span className="text-[9px] text-gray-500">UK Job Boards Connected</span>
            </div>
          </div>
          <CheckCircle className="h-4 w-4 text-emerald-500" />
        </div>
      </div>
    </aside>
  );
}
