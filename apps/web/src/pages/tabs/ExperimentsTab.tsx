import { useEffect, useState } from "react";
import { useParams } from "react-router-dom";
import {
    api,
    type Experiment,
    type ReferenceAsset,
    type MotionAsset,
    type ExperimentPreprocessCreate,
    type ExperimentCreate,
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

export function ExperimentsTab() {
    const { projectId } = useParams<{ projectId: string }>();
    const [experiments, setExperiments] = useState<Experiment[]>([]);
    const [loading, setLoading] = useState(true);
    const [showCreateModal, setShowCreateModal] = useState(false);

    const fetchExperiments = async () => {
        if (!projectId) return;
        try {
            const data = await api.listExperiments(projectId);
            setExperiments(data);
        } catch (err) {
            console.error("Failed to fetch experiments:", err);
        } finally {
            setLoading(false);
        }
    };

    useEffect(() => {
        fetchExperiments();
    }, [projectId]);

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
                        <h2 className="text-lg font-semibold text-white">Experiments</h2>
                        <p className="text-sm text-gray-400">
                            Manage preprocessed inputs and generation configurations
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
                        New Experiment
                    </Button>
                </div>

                {experiments.length === 0 ? (
                    <EmptyState
                        title="No experiments yet"
                        description="Create an experiment by combining a reference image with a motion video, or by using a pre-processed input directory."
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
                                    d="M19.428 15.428a2 2 0 00-1.022-.547l-2.387-.477a6 6 0 00-3.86.517l-.318.158a6 6 0 01-3.86.517L6.05 15.21a2 2 0 00-1.806.547M8 4h8l-1 1v5.172a2 2 0 00.586 1.414l5 5c1.26 1.26.367 3.414-1.415 3.414H4.828c-1.782 0-2.674-2.154-1.414-3.414l5-5A2 2 0 009 10.172V5L8 4z"
                                />
                            </svg>
                        }
                    />
                ) : (
                    <div className="space-y-3">
                        {experiments.map((exp) => (
                            <div
                                key={exp.id}
                                className="p-4 rounded-lg bg-surface-200/50 hover:bg-surface-200 transition-colors"
                            >
                                <div className="flex items-start justify-between">
                                    <div>
                                        <h3 className="font-medium text-white">{exp.name}</h3>
                                        {exp.description && (
                                            <p className="text-sm text-gray-400 mt-1">
                                                {exp.description}
                                            </p>
                                        )}
                                        <div className="flex items-center gap-3 mt-2 text-xs text-gray-500">
                                            {exp.reference_id && (
                                                <span>Ref: {exp.reference_id.slice(0, 8)}...</span>
                                            )}
                                            {exp.motion_id && (
                                                <span>Motion: {exp.motion_id.slice(0, 8)}...</span>
                                            )}
                                            {exp.preprocess_task_id && (
                                                <Badge variant="info">Preprocessing</Badge>
                                            )}
                                        </div>
                                    </div>
                                    <div className="flex items-center gap-2">
                                        {exp.input_dir && (
                                            <Badge variant="success">Ready</Badge>
                                        )}
                                    </div>
                                </div>
                            </div>
                        ))}
                    </div>
                )}
            </Card>

            <CreateExperimentModal
                isOpen={showCreateModal}
                onClose={() => setShowCreateModal(false)}
                projectId={projectId!}
                onSuccess={fetchExperiments}
            />
        </div>
    );
}

function CreateExperimentModal({
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
    const [mode, setMode] = useState<"preprocess" | "directory">("preprocess");
    const [refs, setRefs] = useState<ReferenceAsset[]>([]);
    const [motions, setMotions] = useState<MotionAsset[]>([]);
    const [loading, setLoading] = useState(false);
    const [assetsLoading, setAssetsLoading] = useState(true);
    const [error, setError] = useState("");

    const [formData, setFormData] = useState({
        name: "",
        description: "",
        reference_id: "",
        motion_id: "",
        source_input_dir: "",
        prompt_override: "",
        size: "1024*576",
        frame_num: 81,
    });

    useEffect(() => {
        const fetchAssets = async () => {
            try {
                const [refList, motionList] = await Promise.all([
                    api.listReferenceAssets(projectId),
                    api.listMotionAssets(projectId),
                ]);
                setRefs(refList);
                setMotions(motionList);
            } catch (err) {
                console.error("Failed to fetch assets:", err);
            } finally {
                setAssetsLoading(false);
            }
        };
        if (isOpen) {
            fetchAssets();
        }
    }, [projectId, isOpen]);

    const handleSubmit = async () => {
        if (!formData.name) {
            setError("Experiment name is required");
            return;
        }

        if (mode === "preprocess") {
            if (!formData.reference_id || !formData.motion_id) {
                setError("Please select both a reference image and a motion video");
                return;
            }
        } else {
            if (!formData.source_input_dir) {
                setError("Input directory is required");
                return;
            }
        }

        setLoading(true);
        setError("");

        try {
            if (mode === "preprocess") {
                const payload: ExperimentPreprocessCreate = {
                    name: formData.name,
                    description: formData.description || undefined,
                    reference_id: formData.reference_id,
                    motion_id: formData.motion_id,
                    config: {
                        prompt_override: formData.prompt_override || undefined,
                        size: formData.size,
                        frame_num: formData.frame_num,
                    },
                };
                await api.createExperimentWithPreprocess(projectId, payload);
            } else {
                const payload: ExperimentCreate = {
                    name: formData.name,
                    description: formData.description || undefined,
                    source_input_dir: formData.source_input_dir,
                    config: {
                        prompt_override: formData.prompt_override || undefined,
                        size: formData.size,
                        frame_num: formData.frame_num,
                    },
                };
                await api.createExperiment(projectId, payload);
            }
            onClose();
            resetForm();
            onSuccess();
        } catch (err: any) {
            setError(err.message || "Failed to create experiment");
        } finally {
            setLoading(false);
        }
    };

    const resetForm = () => {
        setFormData({
            name: "",
            description: "",
            reference_id: "",
            motion_id: "",
            source_input_dir: "",
            prompt_override: "",
            size: "1024*576",
            frame_num: 81,
        });
        setMode("preprocess");
        setError("");
    };

    return (
        <Modal isOpen={isOpen} onClose={onClose} title="Create Experiment">
            <div className="space-y-4">
                <Input
                    label="Experiment Name"
                    placeholder="My experiment"
                    value={formData.name}
                    onChange={(name) => setFormData({ ...formData, name })}
                />
                <Input
                    label="Description (optional)"
                    placeholder="Describe this experiment"
                    value={formData.description}
                    onChange={(description) => setFormData({ ...formData, description })}
                />

                {/* Mode Toggle */}
                <div className="space-y-2">
                    <label className="block text-sm font-medium text-gray-300">
                        Creation Mode
                    </label>
                    <div className="flex gap-2">
                        <button
                            onClick={() => setMode("preprocess")}
                            className={`flex-1 py-2 px-3 rounded-lg text-sm font-medium transition-colors ${mode === "preprocess"
                                ? "bg-primary-500/20 text-primary-400 border border-primary-500/50"
                                : "bg-surface-200 text-gray-400 border border-white/10"
                                }`}
                        >
                            From Assets
                        </button>
                        <button
                            onClick={() => setMode("directory")}
                            className={`flex-1 py-2 px-3 rounded-lg text-sm font-medium transition-colors ${mode === "directory"
                                ? "bg-primary-500/20 text-primary-400 border border-primary-500/50"
                                : "bg-surface-200 text-gray-400 border border-white/10"
                                }`}
                        >
                            From Directory
                        </button>
                    </div>
                </div>

                {mode === "preprocess" ? (
                    <>
                        {assetsLoading ? (
                            <div className="flex justify-center py-4">
                                <LoadingSpinner size="sm" />
                            </div>
                        ) : (
                            <>
                                <Select
                                    label="Reference Image"
                                    value={formData.reference_id}
                                    onChange={(reference_id) =>
                                        setFormData({ ...formData, reference_id })
                                    }
                                    placeholder="Select a reference image"
                                    options={refs.map((r) => ({ value: r.id, label: r.name }))}
                                />
                                <Select
                                    label="Motion Video"
                                    value={formData.motion_id}
                                    onChange={(motion_id) =>
                                        setFormData({ ...formData, motion_id })
                                    }
                                    placeholder="Select a motion video"
                                    options={motions.map((m) => ({
                                        value: m.id,
                                        label: m.name,
                                    }))}
                                />
                            </>
                        )}
                    </>
                ) : (
                    <Input
                        label="Input Directory"
                        placeholder="path/to/pair_dir"
                        value={formData.source_input_dir}
                        onChange={(source_input_dir) =>
                            setFormData({ ...formData, source_input_dir })
                        }
                    />
                )}

                {/* Config options */}
                <div className="border-t border-white/10 pt-4 mt-4">
                    <h4 className="text-sm font-medium text-gray-300 mb-3">
                        Generation Config
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
                    </div>
                    <Input
                        label="Prompt Override (optional)"
                        placeholder="Custom prompt"
                        value={formData.prompt_override}
                        onChange={(prompt_override) =>
                            setFormData({ ...formData, prompt_override })
                        }
                        className="mt-3"
                    />
                </div>

                {error && <p className="text-sm text-error-500">{error}</p>}

                <div className="flex justify-end gap-3 pt-2">
                    <Button variant="ghost" onClick={onClose}>
                        Cancel
                    </Button>
                    <Button variant="primary" onClick={handleSubmit} disabled={loading}>
                        {loading ? <LoadingSpinner size="sm" /> : "Create Experiment"}
                    </Button>
                </div>
            </div>
        </Modal>
    );
}
