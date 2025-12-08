import { NavLink, Outlet } from "react-router-dom";
import { useState, useEffect } from "react";
import { api, type HealthStatus } from "../api";

export function Layout() {
    const [health, setHealth] = useState<"loading" | "ok" | "error">("loading");

    useEffect(() => {
        const checkHealth = async () => {
            try {
                const data = await api.getHealth();
                setHealth(data.status === "ok" ? "ok" : "error");
            } catch {
                setHealth("error");
            }
        };
        checkHealth();
        const interval = setInterval(checkHealth, 30000);
        return () => clearInterval(interval);
    }, []);

    const healthColor = {
        loading: "bg-gray-500",
        ok: "bg-success-500",
        error: "bg-error-500",
    }[health];

    return (
        <div className="min-h-screen bg-surface-50">
            {/* Navigation */}
            <nav className="glass border-b border-white/10 sticky top-0 z-50">
                <div className="max-w-7xl mx-auto px-4 sm:px-6 lg:px-8">
                    <div className="flex items-center justify-between h-16">
                        {/* Logo */}
                        <NavLink to="/" className="flex items-center gap-3">
                            <div className="w-8 h-8 rounded-lg gradient-primary flex items-center justify-center">
                                <span className="text-white font-bold text-lg">S</span>
                            </div>
                            <span className="text-xl font-semibold text-gradient">
                                SteadyDancer
                            </span>
                        </NavLink>

                        {/* Nav Links */}
                        <div className="flex items-center gap-6">
                            <NavLink
                                to="/"
                                className={({ isActive }) =>
                                    `text-sm font-medium transition-colors ${isActive
                                        ? "text-primary-400"
                                        : "text-gray-400 hover:text-white"
                                    }`
                                }
                            >
                                Dashboard
                            </NavLink>
                            <NavLink
                                to="/projects"
                                className={({ isActive }) =>
                                    `text-sm font-medium transition-colors ${isActive
                                        ? "text-primary-400"
                                        : "text-gray-400 hover:text-white"
                                    }`
                                }
                            >
                                Projects
                            </NavLink>

                            {/* API Status */}
                            <div className="flex items-center gap-2 text-sm text-gray-400">
                                <div
                                    className={`w-2 h-2 rounded-full ${healthColor} animate-pulse`}
                                />
                                <span>API</span>
                            </div>
                        </div>
                    </div>
                </div>
            </nav>

            {/* Main Content */}
            <main className="max-w-7xl mx-auto px-4 sm:px-6 lg:px-8 py-8">
                <Outlet />
            </main>
        </div>
    );
}
