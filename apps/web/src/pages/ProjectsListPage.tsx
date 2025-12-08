import { useEffect, useState } from "react";
import { Link, useNavigate } from "react-router-dom";
import { api, type Project, type ProjectCreate } from "../api";
import {
    Card,
    Button,
    Input,
    Modal,
    LoadingSpinner,
    EmptyState,
} from "../components";

export function ProjectsListPage() {
    const [projects, setProjects] = useState<Project[]>([]);
    const [loading, setLoading] = useState(true);
    const [showCreateModal, setShowCreateModal] = useState(false);
    const [creating, setCreating] = useState(false);
    const [formData, setFormData] = useState<ProjectCreate>({
        name: "",
        description: "",
    });
    const [error, setError] = useState("");
    const navigate = useNavigate();

    const fetchProjects = async () => {
        try {
            const data = await api.listProjects();
            setProjects(data);
        } catch (err) {
            console.error("Failed to fetch projects:", err);
        } finally {
            setLoading(false);
        }
    };

    useEffect(() => {
        fetchProjects();
    }, []);

    const handleCreate = async () => {
        if (!formData.name.trim()) {
            setError("Project name is required");
            return;
        }

        setCreating(true);
        setError("");

        try {
            const project = await api.createProject(formData);
            setShowCreateModal(false);
            setFormData({ name: "", description: "" });
            navigate(`/projects/${project.id}`);
        } catch (err: any) {
            setError(err.message || "Failed to create project");
        } finally {
            setCreating(false);
        }
    };

    if (loading) {
        return (
            <div className="flex items-center justify-center min-h-[60vh]">
                <LoadingSpinner size="lg" />
            </div>
        );
    }

    return (
        <div className="space-y-6">
            {/* Header */}
            <div className="flex items-center justify-between">
                <div>
                    <h1 className="text-2xl font-bold text-white">Projects</h1>
                    <p className="text-gray-400 mt-1">
                        Manage your SteadyDancer projects
                    </p>
                </div>
                <Button variant="primary" onClick={() => setShowCreateModal(true)}>
                    <svg
                        className="w-4 h-4"
                        fill="none"
                        stroke="currentColor"
                        viewBox="0 0 24 24"
                    >
                        <path
                            strokeLinecap="round"
                            strokeLinejoin="round"
                            strokeWidth={2}
                            d="M12 6v6m0 0v6m0-6h6m-6 0H6"
                        />
                    </svg>
                    New Project
                </Button>
            </div>

            {/* Projects Grid */}
            {projects.length === 0 ? (
                <Card>
                    <EmptyState
                        title="No projects yet"
                        description="Create your first project to get started with SteadyDancer video generation."
                        action={
                            <Button
                                variant="primary"
                                onClick={() => setShowCreateModal(true)}
                            >
                                Create Project
                            </Button>
                        }
                        icon={
                            <svg
                                className="w-12 h-12"
                                fill="none"
                                stroke="currentColor"
                                viewBox="0 0 24 24"
                            >
                                <path
                                    strokeLinecap="round"
                                    strokeLinejoin="round"
                                    strokeWidth={1.5}
                                    d="M3 7v10a2 2 0 002 2h14a2 2 0 002-2V9a2 2 0 00-2-2h-6l-2-2H5a2 2 0 00-2 2z"
                                />
                            </svg>
                        }
                    />
                </Card>
            ) : (
                <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 gap-4">
                    {projects.map((project) => (
                        <Link key={project.id} to={`/projects/${project.id}`}>
                            <Card hoverable className="h-full">
                                <div className="flex items-start gap-3">
                                    <div className="w-10 h-10 rounded-lg gradient-primary flex items-center justify-center flex-shrink-0">
                                        <span className="text-white font-bold">
                                            {project.name.charAt(0).toUpperCase()}
                                        </span>
                                    </div>
                                    <div className="flex-1 min-w-0">
                                        <h3 className="font-semibold text-white truncate">
                                            {project.name}
                                        </h3>
                                        {project.description && (
                                            <p className="text-sm text-gray-400 mt-1 line-clamp-2">
                                                {project.description}
                                            </p>
                                        )}
                                        <p className="text-xs text-gray-500 mt-2">
                                            ID: {project.id.slice(0, 8)}...
                                        </p>
                                    </div>
                                </div>
                            </Card>
                        </Link>
                    ))}
                </div>
            )}

            {/* Create Modal */}
            <Modal
                isOpen={showCreateModal}
                onClose={() => setShowCreateModal(false)}
                title="Create New Project"
            >
                <div className="space-y-4">
                    <Input
                        label="Project Name"
                        placeholder="My Awesome Project"
                        value={formData.name}
                        onChange={(name) => setFormData({ ...formData, name })}
                    />
                    <Input
                        label="Description (optional)"
                        placeholder="Brief description of your project"
                        value={formData.description || ""}
                        onChange={(description) => setFormData({ ...formData, description })}
                        multiline
                        rows={3}
                    />
                    {error && <p className="text-sm text-error-500">{error}</p>}
                    <div className="flex justify-end gap-3 pt-2">
                        <Button variant="ghost" onClick={() => setShowCreateModal(false)}>
                            Cancel
                        </Button>
                        <Button
                            variant="primary"
                            onClick={handleCreate}
                            disabled={creating}
                        >
                            {creating ? <LoadingSpinner size="sm" /> : "Create Project"}
                        </Button>
                    </div>
                </div>
            </Modal>
        </div>
    );
}
