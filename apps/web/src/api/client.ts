import type {
    Project,
    ProjectCreate,
    ReferenceAsset,
    ReferenceAssetCreate,
    MotionAsset,
    MotionAssetCreate,
    Experiment,
    ExperimentCreate,
    ExperimentPreprocessCreate,
    ExperimentPreprocessCreated,
    SteadyDancerJobCreate,
    JobCreated,
    JobStatus,
    JobSummary,
    HealthStatus,
    ApiError,
} from "./types";

const API_BASE_URL =
    import.meta.env.VITE_API_BASE_URL ?? "http://localhost:8000";
const API_KEY = import.meta.env.VITE_API_KEY ?? "";

class ApiClient {
    private baseUrl: string;
    private apiKey: string;

    constructor(baseUrl: string, apiKey: string) {
        this.baseUrl = baseUrl;
        this.apiKey = apiKey;
    }

    private async request<T>(
        endpoint: string,
        options: RequestInit = {}
    ): Promise<T> {
        const headers: HeadersInit = {
            "Content-Type": "application/json",
            ...(this.apiKey && { "X-API-Key": this.apiKey }),
            ...options.headers,
        };

        const response = await fetch(`${this.baseUrl}${endpoint}`, {
            ...options,
            headers,
        });

        if (!response.ok) {
            const errorData = (await response.json()) as ApiError;
            throw new ApiClientError(
                errorData.detail.message,
                errorData.detail.code,
                response.status,
                errorData.detail.extra
            );
        }

        // Handle empty responses (e.g., 204 No Content)
        const contentType = response.headers.get("content-type");
        if (contentType?.includes("application/json")) {
            return response.json() as Promise<T>;
        }
        return {} as T;
    }

    // Health
    async getHealth(): Promise<HealthStatus> {
        return this.request<HealthStatus>("/health");
    }

    // Projects
    async listProjects(): Promise<Project[]> {
        return this.request<Project[]>("/projects");
    }

    async createProject(data: ProjectCreate): Promise<Project> {
        return this.request<Project>("/projects", {
            method: "POST",
            body: JSON.stringify(data),
        });
    }

    async getProject(projectId: string): Promise<Project> {
        return this.request<Project>(`/projects/${projectId}`);
    }

    // Reference Assets
    async listReferenceAssets(projectId: string): Promise<ReferenceAsset[]> {
        return this.request<ReferenceAsset[]>(`/projects/${projectId}/refs`);
    }

    async createReferenceAsset(
        projectId: string,
        data: ReferenceAssetCreate
    ): Promise<ReferenceAsset> {
        return this.request<ReferenceAsset>(`/projects/${projectId}/refs`, {
            method: "POST",
            body: JSON.stringify(data),
        });
    }

    async getReferenceAsset(
        projectId: string,
        refId: string
    ): Promise<ReferenceAsset> {
        return this.request<ReferenceAsset>(`/projects/${projectId}/refs/${refId}`);
    }

    // Motion Assets
    async listMotionAssets(projectId: string): Promise<MotionAsset[]> {
        return this.request<MotionAsset[]>(`/projects/${projectId}/motions`);
    }

    async createMotionAsset(
        projectId: string,
        data: MotionAssetCreate
    ): Promise<MotionAsset> {
        return this.request<MotionAsset>(`/projects/${projectId}/motions`, {
            method: "POST",
            body: JSON.stringify(data),
        });
    }

    async getMotionAsset(
        projectId: string,
        motionId: string
    ): Promise<MotionAsset> {
        return this.request<MotionAsset>(
            `/projects/${projectId}/motions/${motionId}`
        );
    }

    // Experiments
    async listExperiments(projectId: string): Promise<Experiment[]> {
        return this.request<Experiment[]>(`/projects/${projectId}/experiments`);
    }

    async createExperiment(
        projectId: string,
        data: ExperimentCreate
    ): Promise<Experiment> {
        return this.request<Experiment>(`/projects/${projectId}/experiments`, {
            method: "POST",
            body: JSON.stringify(data),
        });
    }

    async createExperimentWithPreprocess(
        projectId: string,
        data: ExperimentPreprocessCreate
    ): Promise<ExperimentPreprocessCreated> {
        return this.request<ExperimentPreprocessCreated>(
            `/projects/${projectId}/experiments/preprocess`,
            {
                method: "POST",
                body: JSON.stringify(data),
            }
        );
    }

    async getExperiment(
        projectId: string,
        experimentId: string
    ): Promise<Experiment> {
        return this.request<Experiment>(
            `/projects/${projectId}/experiments/${experimentId}`
        );
    }

    // Jobs
    async listProjectJobs(projectId: string): Promise<JobSummary[]> {
        return this.request<JobSummary[]>(
            `/projects/${projectId}/steadydancer/jobs`
        );
    }

    async createProjectJob(
        projectId: string,
        data: SteadyDancerJobCreate
    ): Promise<JobCreated> {
        return this.request<JobCreated>(
            `/projects/${projectId}/steadydancer/jobs`,
            {
                method: "POST",
                body: JSON.stringify(data),
            }
        );
    }

    async createExperimentJob(
        projectId: string,
        experimentId: string,
        data: SteadyDancerJobCreate
    ): Promise<JobCreated> {
        return this.request<JobCreated>(
            `/projects/${projectId}/experiments/${experimentId}/steadydancer/jobs`,
            {
                method: "POST",
                body: JSON.stringify(data),
            }
        );
    }

    async getJobStatus(projectId: string, jobId: string): Promise<JobStatus> {
        return this.request<JobStatus>(
            `/projects/${projectId}/steadydancer/jobs/${jobId}`
        );
    }

    async cancelJob(
        projectId: string,
        jobId: string,
        reason?: string
    ): Promise<JobStatus> {
        return this.request<JobStatus>(
            `/projects/${projectId}/steadydancer/jobs/${jobId}/cancel`,
            {
                method: "POST",
                body: JSON.stringify({ reason }),
            }
        );
    }

    getJobVideoUrl(projectId: string, jobId: string): string {
        const url = `${this.baseUrl}/projects/${projectId}/steadydancer/jobs/${jobId}/download`;
        if (this.apiKey) {
            return `${url}?api_key=${encodeURIComponent(this.apiKey)}`;
        }
        return url;
    }

    async listExperimentJobs(
        projectId: string,
        experimentId: string
    ): Promise<JobSummary[]> {
        return this.request<JobSummary[]>(
            `/projects/${projectId}/experiments/${experimentId}/steadydancer/jobs`
        );
    }
}

export class ApiClientError extends Error {
    code: string;
    status: number;
    extra?: Record<string, unknown>;

    constructor(
        message: string,
        code: string,
        status: number,
        extra?: Record<string, unknown>
    ) {
        super(message);
        this.name = "ApiClientError";
        this.code = code;
        this.status = status;
        this.extra = extra;
    }
}

export const api = new ApiClient(API_BASE_URL, API_KEY);
