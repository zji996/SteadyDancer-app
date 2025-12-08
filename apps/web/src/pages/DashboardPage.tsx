import { useEffect, useState } from "react";
import { Link } from "react-router-dom";
import { api, type Project, type JobSummary } from "../api";
import { Card, Button, Badge, LoadingSpinner } from "../components";

export function DashboardPage() {
    const [projects, setProjects] = useState<Project[]>([]);
    const [recentJobs, setRecentJobs] = useState<JobSummary[]>([]);
    const [loading, setLoading] = useState(true);
    const [stats, setStats] = useState({
        totalProjects: 0,
        runningJobs: 0,
        completedJobs: 0,
    });

    useEffect(() => {
        const fetchData = async () => {
            try {
                const projectList = await api.listProjects();
                setProjects(projectList.slice(0, 5)); // Show recent 5

                // Fetch jobs from all projects
                const allJobs: JobSummary[] = [];
                for (const project of projectList.slice(0, 3)) {
                    const jobs = await api.listProjectJobs(project.id);
                    allJobs.push(...jobs);
                }

                // Sort by id (newest first) and take recent 5
                const sorted = allJobs.slice(0, 5);
                setRecentJobs(sorted);

                // Calculate stats
                const running = allJobs.filter(
                    (j) => j.status === "PENDING" || j.status === "STARTED"
                ).length;
                const completed = allJobs.filter((j) => j.status === "SUCCESS").length;

                setStats({
                    totalProjects: projectList.length,
                    runningJobs: running,
                    completedJobs: completed,
                });
            } catch (error) {
                console.error("Failed to fetch dashboard data:", error);
            } finally {
                setLoading(false);
            }
        };

        fetchData();
    }, []);

    const getJobBadgeVariant = (
        status: string
    ): "success" | "warning" | "error" | "info" | "default" => {
        switch (status) {
            case "SUCCESS":
                return "success";
            case "STARTED":
                return "info";
            case "PENDING":
                return "warning";
            case "FAILURE":
                return "error";
            default:
                return "default";
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
        <div className="space-y-8">
            {/* Header */}
            <div>
                <h1 className="text-3xl font-bold text-gradient">Dashboard</h1>
                <p className="text-gray-400 mt-1">
                    Welcome to SteadyDancer - AI-Powered Video Generation
                </p>
            </div>

            {/* Stats */}
            <div className="grid grid-cols-1 md:grid-cols-3 gap-4">
                <Card className="relative overflow-hidden">
                    <div className="absolute top-0 right-0 w-24 h-24 gradient-primary opacity-10 rounded-full blur-2xl -translate-y-1/2 translate-x-1/2" />
                    <div className="relative">
                        <p className="text-sm text-gray-400">Total Projects</p>
                        <p className="text-3xl font-bold text-white mt-1">
                            {stats.totalProjects}
                        </p>
                    </div>
                </Card>

                <Card className="relative overflow-hidden">
                    <div className="absolute top-0 right-0 w-24 h-24 bg-primary-500 opacity-10 rounded-full blur-2xl -translate-y-1/2 translate-x-1/2" />
                    <div className="relative">
                        <p className="text-sm text-gray-400">Running Jobs</p>
                        <p className="text-3xl font-bold text-primary-400 mt-1">
                            {stats.runningJobs}
                        </p>
                    </div>
                </Card>

                <Card className="relative overflow-hidden">
                    <div className="absolute top-0 right-0 w-24 h-24 bg-success-500 opacity-10 rounded-full blur-2xl -translate-y-1/2 translate-x-1/2" />
                    <div className="relative">
                        <p className="text-sm text-gray-400">Completed Jobs</p>
                        <p className="text-3xl font-bold text-success-500 mt-1">
                            {stats.completedJobs}
                        </p>
                    </div>
                </Card>
            </div>

            {/* Quick Actions */}
            <Card>
                <h2 className="text-lg font-semibold text-white mb-4">Quick Actions</h2>
                <div className="flex flex-wrap gap-3">
                    <Link to="/projects">
                        <Button variant="primary">
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
                            Create Project
                        </Button>
                    </Link>
                    <Link to="/projects">
                        <Button variant="secondary">Browse Projects</Button>
                    </Link>
                </div>
            </Card>

            {/* Recent Projects & Jobs */}
            <div className="grid grid-cols-1 lg:grid-cols-2 gap-6">
                {/* Recent Projects */}
                <Card>
                    <div className="flex items-center justify-between mb-4">
                        <h2 className="text-lg font-semibold text-white">
                            Recent Projects
                        </h2>
                        <Link
                            to="/projects"
                            className="text-sm text-primary-400 hover:text-primary-300"
                        >
                            View all →
                        </Link>
                    </div>
                    {projects.length === 0 ? (
                        <p className="text-gray-400 text-sm">No projects yet</p>
                    ) : (
                        <div className="space-y-3">
                            {projects.map((project) => (
                                <Link
                                    key={project.id}
                                    to={`/projects/${project.id}`}
                                    className="block p-3 rounded-lg bg-surface-200/50 hover:bg-surface-200 transition-colors"
                                >
                                    <p className="font-medium text-white">{project.name}</p>
                                    {project.description && (
                                        <p className="text-sm text-gray-400 truncate">
                                            {project.description}
                                        </p>
                                    )}
                                </Link>
                            ))}
                        </div>
                    )}
                </Card>

                {/* Recent Jobs */}
                <Card>
                    <h2 className="text-lg font-semibold text-white mb-4">Recent Jobs</h2>
                    {recentJobs.length === 0 ? (
                        <p className="text-gray-400 text-sm">No jobs yet</p>
                    ) : (
                        <div className="space-y-3">
                            {recentJobs.map((job) => (
                                <Link
                                    key={job.id}
                                    to={`/projects/${job.project_id}/jobs`}
                                    className="flex items-center justify-between p-3 rounded-lg bg-surface-200/50 hover:bg-surface-200 transition-colors"
                                >
                                    <div>
                                        <p className="font-medium text-white text-sm">
                                            {job.job_type}
                                        </p>
                                        <p className="text-xs text-gray-400">
                                            {job.id.slice(0, 8)}...
                                        </p>
                                    </div>
                                    <Badge variant={getJobBadgeVariant(job.status)}>
                                        {job.status}
                                    </Badge>
                                </Link>
                            ))}
                        </div>
                    )}
                </Card>
            </div>
        </div>
    );
}
