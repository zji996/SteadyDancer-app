import { useEffect, useState } from "react";
import {
    useParams,
    NavLink,
    Outlet,
    useNavigate,
    useLocation,
} from "react-router-dom";
import { api, type Project } from "../api";
import { Card, LoadingSpinner } from "../components";

export function ProjectDetailPage() {
    const { projectId } = useParams<{ projectId: string }>();
    const [project, setProject] = useState<Project | null>(null);
    const [loading, setLoading] = useState(true);
    const navigate = useNavigate();
    const location = useLocation();

    useEffect(() => {
        const fetchProject = async () => {
            if (!projectId) return;
            try {
                const data = await api.getProject(projectId);
                setProject(data);
            } catch (err) {
                console.error("Failed to fetch project:", err);
                navigate("/projects");
            } finally {
                setLoading(false);
            }
        };
        fetchProject();
    }, [projectId, navigate]);

    // Redirect to assets tab by default
    useEffect(() => {
        if (project && location.pathname === `/projects/${projectId}`) {
            navigate(`/projects/${projectId}/assets`, { replace: true });
        }
    }, [project, projectId, location.pathname, navigate]);

    if (loading) {
        return (
            <div className="flex items-center justify-center min-h-[60vh]">
                <LoadingSpinner size="lg" />
            </div>
        );
    }

    if (!project) {
        return null;
    }

    const tabs = [
        { path: "assets", label: "Assets", icon: "📷" },
        { path: "experiments", label: "Experiments", icon: "🧪" },
        { path: "jobs", label: "Jobs", icon: "🎬" },
    ];

    return (
        <div className="space-y-6">
            {/* Breadcrumb */}
            <nav className="flex items-center gap-2 text-sm">
                <NavLink to="/projects" className="text-gray-400 hover:text-white">
                    Projects
                </NavLink>
                <span className="text-gray-600">/</span>
                <span className="text-white">{project.name}</span>
            </nav>

            {/* Project Header */}
            <Card>
                <div className="flex items-start gap-4">
                    <div className="w-14 h-14 rounded-xl gradient-primary flex items-center justify-center flex-shrink-0">
                        <span className="text-white font-bold text-2xl">
                            {project.name.charAt(0).toUpperCase()}
                        </span>
                    </div>
                    <div className="flex-1">
                        <h1 className="text-2xl font-bold text-white">{project.name}</h1>
                        {project.description && (
                            <p className="text-gray-400 mt-1">{project.description}</p>
                        )}
                        <p className="text-xs text-gray-500 mt-2">ID: {project.id}</p>
                    </div>
                </div>
            </Card>

            {/* Tabs */}
            <div className="flex gap-1 p-1 bg-surface-200/50 rounded-lg w-fit">
                {tabs.map((tab) => (
                    <NavLink
                        key={tab.path}
                        to={`/projects/${projectId}/${tab.path}`}
                        className={({ isActive }) =>
                            `px-4 py-2 rounded-md text-sm font-medium transition-colors flex items-center gap-2 ${isActive
                                ? "bg-surface-100 text-white"
                                : "text-gray-400 hover:text-white"
                            }`
                        }
                    >
                        <span>{tab.icon}</span>
                        {tab.label}
                    </NavLink>
                ))}
            </div>

            {/* Tab Content */}
            <Outlet context={{ project }} />
        </div>
    );
}
