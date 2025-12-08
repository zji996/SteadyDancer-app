import { useEffect, useState } from "react";
import { useParams } from "react-router-dom";
import {
    api,
    type ReferenceAsset,
    type MotionAsset,
    type ReferenceAssetCreate,
    type MotionAssetCreate,
} from "../../api";
import {
    Card,
    Button,
    Input,
    Modal,
    LoadingSpinner,
    EmptyState,
} from "../../components";

export function AssetsTab() {
    const { projectId } = useParams<{ projectId: string }>();
    const [refs, setRefs] = useState<ReferenceAsset[]>([]);
    const [motions, setMotions] = useState<MotionAsset[]>([]);
    const [loading, setLoading] = useState(true);
    const [showRefModal, setShowRefModal] = useState(false);
    const [showMotionModal, setShowMotionModal] = useState(false);

    const fetchAssets = async () => {
        if (!projectId) return;
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
            setLoading(false);
        }
    };

    useEffect(() => {
        fetchAssets();
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
            {/* Reference Images */}
            <Card>
                <div className="flex items-center justify-between mb-4">
                    <div>
                        <h2 className="text-lg font-semibold text-white">
                            Reference Images
                        </h2>
                        <p className="text-sm text-gray-400">
                            Character reference images for video generation
                        </p>
                    </div>
                    <Button variant="secondary" onClick={() => setShowRefModal(true)}>
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
                        Add Image
                    </Button>
                </div>

                {refs.length === 0 ? (
                    <EmptyState
                        title="No reference images"
                        description="Add reference images to use as character sources for video generation."
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
                                    d="M4 16l4.586-4.586a2 2 0 012.828 0L16 16m-2-2l1.586-1.586a2 2 0 012.828 0L20 14m-6-6h.01M6 20h12a2 2 0 002-2V6a2 2 0 00-2-2H6a2 2 0 00-2 2v12a2 2 0 002 2z"
                                />
                            </svg>
                        }
                    />
                ) : (
                    <div className="grid grid-cols-2 md:grid-cols-4 gap-4">
                        {refs.map((ref) => (
                            <div
                                key={ref.id}
                                className="group relative bg-surface-200 rounded-lg overflow-hidden aspect-square"
                            >
                                <div className="absolute inset-0 flex items-center justify-center text-gray-500">
                                    <svg
                                        className="w-8 h-8"
                                        fill="none"
                                        stroke="currentColor"
                                        viewBox="0 0 24 24"
                                    >
                                        <path
                                            strokeLinecap="round"
                                            strokeLinejoin="round"
                                            strokeWidth={1.5}
                                            d="M4 16l4.586-4.586a2 2 0 012.828 0L16 16m-2-2l1.586-1.586a2 2 0 012.828 0L20 14m-6-6h.01M6 20h12a2 2 0 002-2V6a2 2 0 00-2-2H6a2 2 0 00-2 2v12a2 2 0 002 2z"
                                        />
                                    </svg>
                                </div>
                                <div className="absolute bottom-0 inset-x-0 bg-gradient-to-t from-black/80 to-transparent p-3">
                                    <p className="text-sm font-medium text-white truncate">
                                        {ref.name}
                                    </p>
                                    <p className="text-xs text-gray-400 truncate">
                                        {ref.image_path.split("/").pop()}
                                    </p>
                                </div>
                            </div>
                        ))}
                    </div>
                )}
            </Card>

            {/* Motion Videos */}
            <Card>
                <div className="flex items-center justify-between mb-4">
                    <div>
                        <h2 className="text-lg font-semibold text-white">Motion Videos</h2>
                        <p className="text-sm text-gray-400">
                            Driving videos for motion transfer
                        </p>
                    </div>
                    <Button variant="secondary" onClick={() => setShowMotionModal(true)}>
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
                        Add Video
                    </Button>
                </div>

                {motions.length === 0 ? (
                    <EmptyState
                        title="No motion videos"
                        description="Add driving videos to provide motion sources for generation."
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
                                    d="M15 10l4.553-2.276A1 1 0 0121 8.618v6.764a1 1 0 01-1.447.894L15 14M5 18h8a2 2 0 002-2V8a2 2 0 00-2-2H5a2 2 0 00-2 2v8a2 2 0 002 2z"
                                />
                            </svg>
                        }
                    />
                ) : (
                    <div className="grid grid-cols-2 md:grid-cols-4 gap-4">
                        {motions.map((motion) => (
                            <div
                                key={motion.id}
                                className="group relative bg-surface-200 rounded-lg overflow-hidden aspect-video"
                            >
                                <div className="absolute inset-0 flex items-center justify-center text-gray-500">
                                    <svg
                                        className="w-8 h-8"
                                        fill="none"
                                        stroke="currentColor"
                                        viewBox="0 0 24 24"
                                    >
                                        <path
                                            strokeLinecap="round"
                                            strokeLinejoin="round"
                                            strokeWidth={1.5}
                                            d="M14.752 11.168l-3.197-2.132A1 1 0 0010 9.87v4.263a1 1 0 001.555.832l3.197-2.132a1 1 0 000-1.664z"
                                        />
                                        <path
                                            strokeLinecap="round"
                                            strokeLinejoin="round"
                                            strokeWidth={1.5}
                                            d="M21 12a9 9 0 11-18 0 9 9 0 0118 0z"
                                        />
                                    </svg>
                                </div>
                                <div className="absolute bottom-0 inset-x-0 bg-gradient-to-t from-black/80 to-transparent p-3">
                                    <p className="text-sm font-medium text-white truncate">
                                        {motion.name}
                                    </p>
                                    <p className="text-xs text-gray-400 truncate">
                                        {motion.video_path.split("/").pop()}
                                    </p>
                                </div>
                            </div>
                        ))}
                    </div>
                )}
            </Card>

            {/* Add Reference Modal */}
            <AddReferenceModal
                isOpen={showRefModal}
                onClose={() => setShowRefModal(false)}
                projectId={projectId!}
                onSuccess={fetchAssets}
            />

            {/* Add Motion Modal */}
            <AddMotionModal
                isOpen={showMotionModal}
                onClose={() => setShowMotionModal(false)}
                projectId={projectId!}
                onSuccess={fetchAssets}
            />
        </div>
    );
}

function AddReferenceModal({
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
    const [formData, setFormData] = useState<ReferenceAssetCreate>({
        name: "",
        source_image_path: "",
    });
    const [loading, setLoading] = useState(false);
    const [error, setError] = useState("");

    const handleSubmit = async () => {
        if (!formData.name || !formData.source_image_path) {
            setError("Name and image path are required");
            return;
        }
        setLoading(true);
        setError("");
        try {
            await api.createReferenceAsset(projectId, formData);
            onClose();
            setFormData({ name: "", source_image_path: "" });
            onSuccess();
        } catch (err: any) {
            setError(err.message || "Failed to add reference image");
        } finally {
            setLoading(false);
        }
    };

    return (
        <Modal isOpen={isOpen} onClose={onClose} title="Add Reference Image">
            <div className="space-y-4">
                <Input
                    label="Name"
                    placeholder="Character name"
                    value={formData.name}
                    onChange={(name) => setFormData({ ...formData, name })}
                />
                <Input
                    label="Image Path"
                    placeholder="assets/examples/ref.png or /absolute/path/to/image.png"
                    value={formData.source_image_path}
                    onChange={(source_image_path) =>
                        setFormData({ ...formData, source_image_path })
                    }
                />
                <p className="text-xs text-gray-500">
                    Enter an absolute path or a path relative to the repository root.
                </p>
                {error && <p className="text-sm text-error-500">{error}</p>}
                <div className="flex justify-end gap-3 pt-2">
                    <Button variant="ghost" onClick={onClose}>
                        Cancel
                    </Button>
                    <Button variant="primary" onClick={handleSubmit} disabled={loading}>
                        {loading ? <LoadingSpinner size="sm" /> : "Add Image"}
                    </Button>
                </div>
            </div>
        </Modal>
    );
}

function AddMotionModal({
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
    const [formData, setFormData] = useState<MotionAssetCreate>({
        name: "",
        source_video_path: "",
    });
    const [loading, setLoading] = useState(false);
    const [error, setError] = useState("");

    const handleSubmit = async () => {
        if (!formData.name || !formData.source_video_path) {
            setError("Name and video path are required");
            return;
        }
        setLoading(true);
        setError("");
        try {
            await api.createMotionAsset(projectId, formData);
            onClose();
            setFormData({ name: "", source_video_path: "" });
            onSuccess();
        } catch (err: any) {
            setError(err.message || "Failed to add motion video");
        } finally {
            setLoading(false);
        }
    };

    return (
        <Modal isOpen={isOpen} onClose={onClose} title="Add Motion Video">
            <div className="space-y-4">
                <Input
                    label="Name"
                    placeholder="Dance motion"
                    value={formData.name}
                    onChange={(name) => setFormData({ ...formData, name })}
                />
                <Input
                    label="Video Path"
                    placeholder="assets/examples/motion.mp4 or /absolute/path/to/video.mp4"
                    value={formData.source_video_path}
                    onChange={(source_video_path) =>
                        setFormData({ ...formData, source_video_path })
                    }
                />
                <p className="text-xs text-gray-500">
                    Enter an absolute path or a path relative to the repository root.
                </p>
                {error && <p className="text-sm text-error-500">{error}</p>}
                <div className="flex justify-end gap-3 pt-2">
                    <Button variant="ghost" onClick={onClose}>
                        Cancel
                    </Button>
                    <Button variant="primary" onClick={handleSubmit} disabled={loading}>
                        {loading ? <LoadingSpinner size="sm" /> : "Add Video"}
                    </Button>
                </div>
            </div>
        </Modal>
    );
}
