import { useEffect, useState, useCallback } from "react";
import { useParams } from "react-router-dom";
import {
    api,
    type JobSummary,
    type JobStatus,
    type Experiment,
    type SteadyDancerJobCreate,
} from "../../api";
import {
    Card,
    Button,
    Input,
    Select,
    Modal,
    Badge,
    LoadingSpinner,
    EmptyState,
} from "../../components";

export function JobsTab() {
    const { projectId } = useParams<{ projectId: string }>();
    const [jobs, setJobs] = useState<JobSummary[]>([]);
    const [loading, setLoading] = useState(true);
    const [showCreateModal, setShowCreateModal] = useState(false);
    const [selectedJob, setSelectedJob] = useState<JobSummary | null>(null);
    const [jobDetail, setJobDetail] = useState<JobStatus | null>(null);

    const fetchJobs = useCallback(async () => {
        if (!projectId) return;
        try {
            const data = await api.listProjectJobs(projectId);
            setJobs(data);
        } catch (err) {
            console.error("Failed to fetch jobs:", err);
        } finally {
            setLoading(false);
        }
    }, [projectId]);

    useEffect(() => {
        fetchJobs();
        // Poll every 5 seconds for running jobs
        const interval = setInterval(fetchJobs, 5000);
        return () => clearInterval(interval);
    }, [fetchJobs]);

    const handleViewJob = async (job: JobSummary) => {
        setSelectedJob(job);
        try {
            const detail = await api.getJobStatus(job.project_id, job.id);
            setJobDetail(detail);
        } catch (err) {
            console.error("Failed to fetch job details:", err);
        }
    };

    const handleCancel = async (job: JobSummary) => {
        if (!confirm("Are you sure you want to cancel this job?")) return;
        try {
            await api.cancelJob(job.project_id, job.id, "User cancelled");
            fetchJobs();
        } catch (err) {
            console.error("Failed to cancel job:", err);
        }
    };

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
            case "REVOKED":
                return "error";
            default:
                return "default";
        }
    };

    if (loading) {
        return (
            <div className="flex items-center justify-center py-12">
                <LoadingSpinner />
            </div>
        );
    }

    return (
        <div className="space-y-6">
            <Card>
                <div className="flex items-center justify-between mb-4">
                    <div>
                        <h2 className="text-lg font-semibold text-white">
                            Generation Jobs
                        </h2>
                        <p className="text-sm text-gray-400">
                            Track your SteadyDancer video generation tasks
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
                                d="M14.752 11.168l-3.197-2.132A1 1 0 0010 9.87v4.263a1 1 0 001.555.832l3.197-2.132a1 1 0 000-1.664z"
                            />
                            <path
                                strokeLinecap="round"
                                strokeLinejoin="round"
                                strokeWidth={2}
                                d="M21 12a9 9 0 11-18 0 9 9 0 0118 0z"
                            />
                        </svg>
                        New Job
                    </Button>
                </div>

                {jobs.length === 0 ? (
                    <EmptyState
                        title="No jobs yet"
                        description="Create a job to start generating videos with SteadyDancer."
                        icon={
                            <svg
                                className="w-10 h-10"
                                fill="none"
                                stroke="currentColor"
                                viewBox="0 0 24 24"
                            >
                                <path
                                    strokeLinecap="round"
                                    strokeLinejoin="round"
                                    strokeWidth={1.5}
                                    d="M7 4v16M17 4v16M3 8h4m10 0h4M3 12h18M3 16h4m10 0h4M4 20h16a1 1 0 001-1V5a1 1 0 00-1-1H4a1 1 0 00-1 1v14a1 1 0 001 1z"
                                />
                            </svg>
                        }
                    />
                ) : (
                    <div className="overflow-x-auto">
                        <table className="w-full">
                            <thead>
                                <tr className="border-b border-white/10">
                                    <th className="text-left py-3 px-4 text-sm font-medium text-gray-400">
                                        Job ID
                                    </th>
                                    <th className="text-left py-3 px-4 text-sm font-medium text-gray-400">
                                        Type
                                    </th>
                                    <th className="text-left py-3 px-4 text-sm font-medium text-gray-400">
                                        Status
                                    </th>
                                    <th className="text-left py-3 px-4 text-sm font-medium text-gray-400">
                                        Experiment
                                    </th>
                                    <th className="text-right py-3 px-4 text-sm font-medium text-gray-400">
                                        Actions
                                    </th>
                                </tr>
                            </thead>
                            <tbody>
                                {jobs.map((job) => (
                                    <tr
                                        key={job.id}
                                        className="border-b border-white/5 hover:bg-surface-200/30"
                                    >
                                        <td className="py-3 px-4 text-sm text-gray-300 font-mono">
                                            {job.id.slice(0, 8)}...
                                        </td>
                                        <td className="py-3 px-4 text-sm text-white">
                                            {job.job_type}
                                        </td>
                                        <td className="py-3 px-4">
                                            <Badge variant={getJobBadgeVariant(job.status)}>
                                                {job.status}
                                            </Badge>
                                        </td>
                                        <td className="py-3 px-4 text-sm text-gray-400">
                                            {job.experiment_id
                                                ? `${job.experiment_id.slice(0, 8)}...`
                                                : "-"}
                                        </td>
                                        <td className="py-3 px-4 text-right">
                                            <div className="flex justify-end gap-2">
                                                <Button
                                                    variant="ghost"
                                                    size="sm"
                                                    onClick={() => handleViewJob(job)}
                                                >
                                                    View
                                                </Button>
                                                {job.status === "SUCCESS" && job.result_video_path && (
                                                    <a
                                                        href={api.getJobVideoUrl(job.project_id, job.id)}
                                                        target="_blank"
                                                        rel="noopener noreferrer"
                                                    >
                                                        <Button variant="secondary" size="sm">
                                                            Download
                                                        </Button>
                                                    </a>
                                                )}
                                                {(job.status === "PENDING" ||
                                                    job.status === "STARTED") && (
                                                        <Button
                                                            variant="danger"
                                                            size="sm"
                                                            onClick={() => handleCancel(job)}
                                                        >
                                                            Cancel
                                                        </Button>
                                                    )}
                                            </div>
                                        </td>
                                    </tr>
                                ))}
                            </tbody>
                        </table>
                    </div>
                )}
            </Card>

            {/* Create Job Modal */}
            <CreateJobModal
                isOpen={showCreateModal}
                onClose={() => setShowCreateModal(false)}
                projectId={projectId!}
                onSuccess={fetchJobs}
            />

            {/* Job Detail Modal */}
            <JobDetailModal
                isOpen={!!selectedJob}
                onClose={() => {
                    setSelectedJob(null);
                    setJobDetail(null);
                }}
                job={selectedJob}
                detail={jobDetail}
            />
        </div>
    );
}

function CreateJobModal({
    isOpen,
    onClose,
    projectId,
    onSuccess,
}: {
    isOpen: boolean;
    onClose: () => void;
    projectId: string;
    onSuccess: () => void;
}) {
    const [experiments, setExperiments] = useState<Experiment[]>([]);
    const [loading, setLoading] = useState(false);
    const [expLoading, setExpLoading] = useState(true);
    const [error, setError] = useState("");

    const [formData, setFormData] = useState({
        experiment_id: "",
        input_dir: "",
        size: "1024*576",
        frame_num: 81,
        base_seed: -1,
        sample_guide_scale: 5.0,
    });

    useEffect(() => {
        const fetchExperiments = async () => {
            try {
                const data = await api.listExperiments(projectId);
                setExperiments(data.filter((e) => e.input_dir)); // Only ready experiments
            } catch (err) {
                console.error("Failed to fetch experiments:", err);
            } finally {
                setExpLoading(false);
            }
        };
        if (isOpen) {
            fetchExperiments();
        }
    }, [projectId, isOpen]);

    const handleSubmit = async () => {
        const inputDir =
            formData.experiment_id
                ? experiments.find((e) => e.id === formData.experiment_id)?.input_dir
                : formData.input_dir;

        if (!inputDir) {
            setError("Please select an experiment or provide an input directory");
            return;
        }

        setLoading(true);
        setError("");

        try {
            const payload: SteadyDancerJobCreate = {
                input_dir: inputDir,
                size: formData.size,
                frame_num: formData.frame_num,
                base_seed: formData.base_seed,
                sample_guide_scale: formData.sample_guide_scale,
            };

            if (formData.experiment_id) {
                await api.createExperimentJob(
                    projectId,
                    formData.experiment_id,
                    payload
                );
            } else {
                await api.createProjectJob(projectId, payload);
            }

            onClose();
            resetForm();
            onSuccess();
        } catch (err: any) {
            setError(err.message || "Failed to create job");
        } finally {
            setLoading(false);
        }
    };

    const resetForm = () => {
        setFormData({
            experiment_id: "",
            input_dir: "",
            size: "1024*576",
            frame_num: 81,
            base_seed: -1,
            sample_guide_scale: 5.0,
        });
        setError("");
    };

    return (
        <Modal isOpen={isOpen} onClose={onClose} title="Create Generation Job">
            <div className="space-y-4">
                {expLoading ? (
                    <div className="flex justify-center py-4">
                        <LoadingSpinner size="sm" />
                    </div>
                ) : experiments.length > 0 ? (
                    <Select
                        label="Select Experiment"
                        value={formData.experiment_id}
                        onChange={(experiment_id) =>
                            setFormData({ ...formData, experiment_id, input_dir: "" })
                        }
                        placeholder="Choose a prepared experiment"
                        options={experiments.map((e) => ({
                            value: e.id,
                            label: e.name,
                        }))}
                    />
                ) : (
                    <div className="p-3 rounded-lg bg-warning-500/10 border border-warning-500/20">
                        <p className="text-sm text-warning-500">
                            No experiments with prepared inputs. Create an experiment first or
                            provide an input directory directly.
                        </p>
                    </div>
                )}

                {!formData.experiment_id && (
                    <Input
                        label="Or Input Directory"
                        placeholder="path/to/input_dir"
                        value={formData.input_dir}
                        onChange={(input_dir) =>
                            setFormData({ ...formData, input_dir, experiment_id: "" })
                        }
                    />
                )}

                <div className="border-t border-white/10 pt-4">
                    <h4 className="text-sm font-medium text-gray-300 mb-3">
                        Generation Parameters
                    </h4>
                    <div className="grid grid-cols-2 gap-3">
                        <Input
                            label="Resolution"
                            value={formData.size}
                            onChange={(size) => setFormData({ ...formData, size })}
                        />
                        <Input
                            label="Frame Count"
                            type="number"
                            value={String(formData.frame_num)}
                            onChange={(v) =>
                                setFormData({ ...formData, frame_num: parseInt(v) || 81 })
                            }
                        />
                        <Input
                            label="Seed (-1 = random)"
                            type="number"
                            value={String(formData.base_seed)}
                            onChange={(v) =>
                                setFormData({ ...formData, base_seed: parseInt(v) || -1 })
                            }
                        />
                        <Input
                            label="CFG Scale"
                            type="number"
                            value={String(formData.sample_guide_scale)}
                            onChange={(v) =>
                                setFormData({
                                    ...formData,
                                    sample_guide_scale: parseFloat(v) || 5.0,
                                })
                            }
                        />
                    </div>
                </div>

                {error && <p className="text-sm text-error-500">{error}</p>}

                <div className="flex justify-end gap-3 pt-2">
                    <Button variant="ghost" onClick={onClose}>
                        Cancel
                    </Button>
                    <Button variant="primary" onClick={handleSubmit} disabled={loading}>
                        {loading ? <LoadingSpinner size="sm" /> : "Start Generation"}
                    </Button>
                </div>
            </div>
        </Modal>
    );
}

function JobDetailModal({
    isOpen,
    onClose,
    job,
    detail,
}: {
    isOpen: boolean;
    onClose: () => void;
    job: JobSummary | null;
    detail: JobStatus | null;
}) {
    if (!job) return null;

    const getStatusColor = (status: string) => {
        switch (status) {
            case "SUCCESS":
                return "text-success-500";
            case "STARTED":
                return "text-primary-400";
            case "PENDING":
                return "text-warning-500";
            case "FAILURE":
                return "text-error-500";
            default:
                return "text-gray-400";
        }
    };

    return (
        <Modal isOpen={isOpen} onClose={onClose} title="Job Details">
            <div className="space-y-4">
                <div className="grid grid-cols-2 gap-4">
                    <div>
                        <p className="text-xs text-gray-400">Job ID</p>
                        <p className="text-sm text-white font-mono">{job.id}</p>
                    </div>
                    <div>
                        <p className="text-xs text-gray-400">Status</p>
                        <p className={`text-sm font-medium ${getStatusColor(job.status)}`}>
                            ● {job.status}
                        </p>
                    </div>
                    <div>
                        <p className="text-xs text-gray-400">Task ID</p>
                        <p className="text-sm text-white font-mono">{job.task_id}</p>
                    </div>
                    <div>
                        <p className="text-xs text-gray-400">Type</p>
                        <p className="text-sm text-white">{job.job_type}</p>
                    </div>
                </div>

                {detail?.result && (
                    <div className="border-t border-white/10 pt-4">
                        <h4 className="text-sm font-medium text-gray-300 mb-2">Result</h4>
                        {detail.result.success && detail.result.video_path && (
                            <div className="p-3 rounded-lg bg-success-500/10 border border-success-500/20 mb-3">
                                <p className="text-sm text-success-500">
                                    Video generated successfully!
                                </p>
                                <a
                                    href={api.getJobVideoUrl(job.project_id, job.id)}
                                    target="_blank"
                                    rel="noopener noreferrer"
                                    className="mt-2 inline-block"
                                >
                                    <Button variant="secondary" size="sm">
                                        Download Video
                                    </Button>
                                </a>
                            </div>
                        )}
                        {detail.result.stderr && (
                            <div className="mt-2">
                                <p className="text-xs text-gray-400 mb-1">Logs</p>
                                <pre className="text-xs text-gray-300 bg-surface-200 rounded p-2 max-h-32 overflow-auto">
                                    {detail.result.stderr}
                                </pre>
                            </div>
                        )}
                    </div>
                )}

                <div className="flex justify-end pt-2">
                    <Button variant="ghost" onClick={onClose}>
                        Close
                    </Button>
                </div>
            </div>
        </Modal>
    );
}
