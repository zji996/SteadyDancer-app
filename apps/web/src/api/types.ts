// API Types based on backend schemas

export interface Project {
    id: string;
    name: string;
    description: string | null;
}

export interface ProjectCreate {
    name: string;
    description?: string | null;
}

export interface ReferenceAsset {
    id: string;
    project_id: string;
    name: string;
    image_path: string;
    meta: Record<string, unknown> | null;
}

export interface ReferenceAssetCreate {
    name: string;
    source_image_path: string;
    meta?: Record<string, unknown> | null;
}

export interface MotionAsset {
    id: string;
    project_id: string;
    name: string;
    video_path: string;
    meta: Record<string, unknown> | null;
}

export interface MotionAssetCreate {
    name: string;
    source_video_path: string;
    meta?: Record<string, unknown> | null;
}

export interface ExperimentConfig {
    prompt_override?: string | null;
    size?: string;
    frame_num?: number;
    sample_guide_scale?: number;
    condition_guide_scale?: number;
    end_cond_cfg?: number;
    base_seed?: number;
    sample_steps?: number | null;
    sample_shift?: number | null;
    sample_solver?: string | null;
    offload_model?: boolean | null;
    cuda_visible_devices?: string | null;
}

export interface Experiment {
    id: string;
    project_id: string;
    reference_id: string | null;
    motion_id: string | null;
    name: string;
    description: string | null;
    input_dir: string | null;
    config: ExperimentConfig | null;
    preprocess_task_id: string | null;
}

export interface ExperimentCreate {
    name: string;
    description?: string | null;
    reference_id?: string | null;
    motion_id?: string | null;
    source_input_dir: string;
    config?: ExperimentConfig | null;
}

export interface ExperimentPreprocessCreate {
    name: string;
    description?: string | null;
    reference_id: string;
    motion_id: string;
    config?: ExperimentConfig | null;
}

export interface ExperimentPreprocessCreated {
    project_id: string;
    experiment_id: string;
    task_id: string;
}

export interface SteadyDancerJobCreate {
    input_dir: string;
    prompt_override?: string | null;
    size?: string;
    frame_num?: number;
    sample_guide_scale?: number;
    condition_guide_scale?: number;
    end_cond_cfg?: number;
    base_seed?: number;
    sample_steps?: number | null;
    sample_shift?: number | null;
    sample_solver?: string | null;
    offload_model?: boolean | null;
    cuda_visible_devices?: string | null;
}

export interface JobCreated {
    project_id: string;
    job_id: string;
    task_id: string;
}

export interface JobStatus {
    project_id: string;
    job_id: string;
    task_id: string;
    state: JobState;
    result: JobResult | null;
}

export interface JobSummary {
    id: string;
    project_id: string;
    experiment_id: string | null;
    task_id: string;
    job_type: string;
    status: string;
    result_video_path: string | null;
}

export interface JobResult {
    success: boolean;
    video_path: string | null;
    stdout: string;
    stderr: string;
    return_code: number;
}

export type JobState =
    | "PENDING"
    | "STARTED"
    | "SUCCESS"
    | "FAILURE"
    | "REVOKED"
    | "EXPIRED";

export interface ApiError {
    detail: {
        code: string;
        message: string;
        extra?: Record<string, unknown>;
    };
}

export interface HealthStatus {
    status: string;
}
