"use client";

import Link from "next/link";
import { usePathname } from "next/navigation";
import { useEffect, useState } from "react";
import {
  FileText,
  GitCompare,
  CheckCircle2,
  ListTodo,
  History,
  UploadCloud,
  LayoutDashboard,
  Shield,
  Building2,
  ChevronDown,
  UserCheck,
} from "lucide-react";
import { DEMO_USERS, UserRoleInfo, getActiveUser, setActiveUser } from "@/lib/api";

export default function Navbar() {
  const pathname = usePathname();
  const [currentUser, setCurrentUser] = useState<UserRoleInfo>(DEMO_USERS[0]);
  const [dropdownOpen, setDropdownOpen] = useState(false);

  useEffect(() => {
    setCurrentUser(getActiveUser());
    const onUserChanged = () => setCurrentUser(getActiveUser());
    window.addEventListener("clausetrace_user_changed", onUserChanged);
    return () => window.removeEventListener("clausetrace_user_changed", onUserChanged);
  }, []);

  const handleSwitchUser = (user: UserRoleInfo) => {
    setActiveUser(user);
    setDropdownOpen(false);
  };

  const navLinks = [
    { href: "/", label: "Overview", icon: LayoutDashboard },
    { href: "/contracts", label: "Contracts", icon: FileText },
    { href: "/upload", label: "Upload", icon: UploadCloud },
    { href: "/reviews", label: "Requirements Review", icon: CheckCircle2 },
    { href: "/compare", label: "Version Diff", icon: GitCompare },
    { href: "/obligations", label: "Obligations", icon: ListTodo },
    { href: "/audit", label: "Audit Timeline", icon: History },
  ];

  const getRoleBadgeColor = (role: string) => {
    switch (role) {
      case "ANALYST":
        return "bg-blue-100 text-blue-800 border-blue-200";
      case "REVIEWER":
        return "bg-amber-100 text-amber-800 border-amber-200";
      case "ADMIN":
        return "bg-purple-100 text-purple-800 border-purple-200";
      case "AUDITOR":
        return "bg-slate-100 text-slate-800 border-slate-200";
      default:
        return "bg-gray-100 text-gray-800 border-gray-200";
    }
  };

  return (
    <header className="sticky top-0 z-50 w-full border-b border-slate-200 bg-white/95 backdrop-blur shadow-sm">
      <div className="max-w-7xl mx-auto px-4 sm:px-6 lg:px-8">
        <div className="flex h-16 items-center justify-between">
          {/* Logo & Tenant */}
          <div className="flex items-center gap-6">
            <Link href="/" className="flex items-center gap-2.5">
              <div className="flex h-9 w-9 items-center justify-center rounded-lg bg-indigo-600 text-white font-bold shadow-md shadow-indigo-100">
                <Shield className="h-5 w-5" />
              </div>
              <div>
                <span className="text-lg font-bold tracking-tight text-slate-900">ClauseTrace</span>
                <span className="ml-1.5 hidden sm:inline-block rounded px-1.5 py-0.5 text-[10px] font-semibold uppercase tracking-wider bg-slate-100 text-slate-600 border border-slate-200">
                  Enterprise
                </span>
              </div>
            </Link>

            <div className="hidden lg:flex items-center gap-1.5 text-xs text-slate-500 border-l border-slate-200 pl-4 py-1">
              <Building2 className="h-3.5 w-3.5 text-slate-400" />
              <span className="font-medium text-slate-700">Acme Enterprise Corp</span>
            </div>
          </div>

          {/* Nav Links */}
          <nav className="hidden md:flex items-center gap-1">
            {navLinks.map((item) => {
              const Icon = item.icon;
              const isActive = pathname === item.href || (item.href !== "/" && pathname.startsWith(item.href));
              return (
                <Link
                  key={item.href}
                  href={item.href}
                  className={`flex items-center gap-1.5 px-3 py-1.5 rounded-md text-xs font-medium transition-colors ${
                    isActive
                      ? "bg-indigo-50 text-indigo-700 font-semibold"
                      : "text-slate-600 hover:text-slate-900 hover:bg-slate-100/70"
                  }`}
                >
                  <Icon className={`h-4 w-4 ${isActive ? "text-indigo-600" : "text-slate-400"}`} />
                  {item.label}
                </Link>
              );
            })}
          </nav>

          {/* User & Role Switcher */}
          <div className="relative">
            <button
              onClick={() => setDropdownOpen(!dropdownOpen)}
              className="flex items-center gap-2.5 rounded-lg border border-slate-200 px-3 py-1.5 text-left text-xs bg-white hover:bg-slate-50 shadow-sm transition"
            >
              <div className="flex flex-col">
                <span className="font-semibold text-slate-800 leading-tight">{currentUser.name}</span>
                <span className="text-[10px] text-slate-400">{currentUser.email}</span>
              </div>
              <span
                className={`ml-1 rounded px-1.5 py-0.5 text-[10px] font-bold border ${getRoleBadgeColor(
                  currentUser.role
                )}`}
              >
                {currentUser.role}
              </span>
              <ChevronDown className="h-3.5 w-3.5 text-slate-400 ml-0.5" />
            </button>

            {dropdownOpen && (
              <div className="absolute right-0 mt-2 w-64 rounded-xl border border-slate-200 bg-white p-2 shadow-xl z-50">
                <div className="px-2.5 py-1.5 border-b border-slate-100 mb-1">
                  <p className="text-[11px] font-semibold text-slate-400 uppercase tracking-wider">
                    Switch Authenticated Identity
                  </p>
                  <p className="text-[11px] text-slate-500 mt-0.5">
                    Test RBAC permissions and approval workflows
                  </p>
                </div>
                {DEMO_USERS.map((u) => (
                  <button
                    key={u.email}
                    onClick={() => handleSwitchUser(u)}
                    className={`w-full flex items-center justify-between px-2.5 py-2 rounded-lg text-xs transition ${
                      currentUser.email === u.email ? "bg-indigo-50 text-indigo-900 font-semibold" : "hover:bg-slate-50 text-slate-700"
                    }`}
                  >
                    <div className="text-left">
                      <p className="font-medium">{u.name}</p>
                      <p className="text-[10px] text-slate-400">{u.email}</p>
                    </div>
                    <span
                      className={`rounded px-1.5 py-0.5 text-[10px] font-bold border ${getRoleBadgeColor(
                        u.role
                      )}`}
                    >
                      {u.role}
                    </span>
                  </button>
                ))}
              </div>
            )}
          </div>
        </div>
      </div>
    </header>
  );
}
