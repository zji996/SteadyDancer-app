from __future__ import annotations

from uuid import UUID

from fastapi import APIRouter, Depends, status
from fastapi.responses import FileResponse, RedirectResponse
from sqlalchemy.ext.asyncio import AsyncSession

from apps.api.db import Job, Project, get_session
from apps.api.errors import api_error
from apps.api.schemas.assets import (
    MotionAssetCreate,
    MotionAssetOut,
    ReferenceAssetCreate,
    ReferenceAssetOut,
)
from apps.api.schemas.experiments import (
    ExperimentCreate,
    ExperimentOut,
    ExperimentPreprocessCreate,
    ExperimentPreprocessCreated,
)
from apps.api.schemas.projects import (
    ProjectCreate,
    ProjectJobCancel,
    ProjectJobCreated,
    ProjectJobStatus,
    ProjectJobSummary,
    ProjectOut,
)
from apps.api.schemas.steadydancer import SteadyDancerJobCreate
from apps.api.services import assets as asset_service
from apps.api.services import experiments as experiment_service
from apps.api.services import projects as project_service
from apps.api.services import steadydancer_jobs as job_service
from libs.py_core.projects import from_data_relative
from libs.py_core.s3_storage import generate_presigned_get_url


router = APIRouter(prefix="/projects", tags=["projects"])


@router.get("", response_model=list[ProjectOut])
async def list_projects(
    session: AsyncSession = Depends(get_session),
) -> list[ProjectOut]:
    """
    List all projects.
    """
    projects = await project_service.list_projects(session=session)
    return [ProjectOut.model_validate(p) for p in projects]

@router.post("", response_model=ProjectOut, status_code=status.HTTP_201_CREATED)
async def create_project(
    payload: ProjectCreate,
    session: AsyncSession = Depends(get_session),
) -> ProjectOut:
    """
    Create a new logical project for grouping SteadyDancer jobs.
    """
    try:
        project = await project_service.create_project(
            session=session,
            name=payload.name,
            description=payload.description,
        )
    except project_service.ProjectNameAlreadyExistsError as exc:
        raise api_error(
            status_code=status.HTTP_409_CONFLICT,
            code="PROJECT_NAME_CONFLICT",
            message=str(exc),
        )
    return project


@router.get("/{project_id}", response_model=ProjectOut)
async def get_project(
    project_id: UUID,
    session: AsyncSession = Depends(get_session),
) -> ProjectOut:
    """
    Fetch basic project information by ID.
    """
    project = await project_service.get_project(session=session, project_id=project_id)
    if project is None:
        raise api_error(
            status_code=status.HTTP_404_NOT_FOUND,
            code="PROJECT_NOT_FOUND",
            message="Project not found.",
        )
    return project


@router.post(
    "/{project_id}/steadydancer/jobs",
    response_model=ProjectJobCreated,
    status_code=status.HTTP_201_CREATED,
)
async def create_project_steadydancer_job(
    project_id: UUID,
    payload: SteadyDancerJobCreate,
    session: AsyncSession = Depends(get_session),
) -> ProjectJobCreated:
    """
    Create a SteadyDancer I2V job under a specific project.

    This endpoint delegates the actual job creation and filesystem/Celery
    interactions to the steadydancer_jobs service to keep the HTTP layer thin.
    """
    try:
        job = await job_service.create_project_steadydancer_job(
            session=session,
            project_id=project_id,
            payload=payload,
        )
    except job_service.ProjectNotFoundError:
        raise api_error(
            status_code=status.HTTP_404_NOT_FOUND,
            code="PROJECT_NOT_FOUND",
            message="Project not found.",
        )
    except job_service.InputDirNotFoundError as exc:
        raise api_error(
            status_code=status.HTTP_400_BAD_REQUEST,
            code="INPUT_DIR_NOT_FOUND",
            message=str(exc),
        )
    except job_service.JobPreparationError as exc:
        raise api_error(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            code="JOB_PREPARATION_FAILED",
            message=str(exc),
        )

    return ProjectJobCreated(project_id=project_id, job_id=job.id, task_id=job.task_id)


@router.get(
    "/{project_id}/steadydancer/jobs/{job_id}",
    response_model=ProjectJobStatus,
)
async def get_project_steadydancer_job_status(
    project_id: UUID,
    job_id: UUID,
    session: AsyncSession = Depends(get_session),
) -> ProjectJobStatus:
    """
    Query the status of a SteadyDancer job within a project.

    Combines Celery state with the stored job metadata via the service layer.
    """
    job = await session.get(Job, job_id)
    if job is None or job.project_id != project_id:
        raise api_error(
            status_code=status.HTTP_404_NOT_FOUND,
            code="JOB_NOT_FOUND",
            message="Job not found.",
        )

    state, result, error = await job_service.refresh_project_job_status(session=session, job=job)

    if error is not None:
        raise api_error(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            code="CELERY_TASK_ERROR",
            message="Celery task failed.",
            extra={
                "task_id": job.task_id,
                "state": state,
                "error": error,
            },
        )

    return ProjectJobStatus(
        project_id=project_id,
        job_id=job_id,
        task_id=job.task_id,
        state=state,
        result=result,
    )


@router.post(
    "/{project_id}/steadydancer/jobs/{job_id}/cancel",
    response_model=ProjectJobStatus,
)
async def cancel_project_steadydancer_job(
    project_id: UUID,
    job_id: UUID,
    payload: ProjectJobCancel | None = None,
    session: AsyncSession = Depends(get_session),
) -> ProjectJobStatus:
    """
    Cancel a SteadyDancer job within a project.

    This endpoint issues a Celery revoke and records cancellation metadata
    in the Job row for later inspection.
    """
    job = await session.get(Job, job_id)
    if job is None or job.project_id != project_id:
        raise api_error(
            status_code=status.HTTP_404_NOT_FOUND,
            code="JOB_NOT_FOUND",
            message="Job not found.",
        )

    job = await job_service.cancel_project_job(
        session=session,
        job=job,
        reason=payload.reason if payload is not None else None,
    )

    return ProjectJobStatus(
        project_id=project_id,
        job_id=job_id,
        task_id=job.task_id,
        state=job.status,
        result=None,
    )


@router.get(
    "/{project_id}/steadydancer/jobs/{job_id}/download",
    response_class=FileResponse,
)
async def download_project_steadydancer_job_video(
    project_id: UUID,
    job_id: UUID,
    session: AsyncSession = Depends(get_session),
) -> FileResponse:
    """
    Download the result video file for a completed SteadyDancer job.

    Returns 404 if the job does not exist, does not belong to the project,
    or has no result video yet.
    """
    job = await session.get(Job, job_id)
    if job is None or job.project_id != project_id:
        raise api_error(
            status_code=status.HTTP_404_NOT_FOUND,
            code="JOB_NOT_FOUND",
            message="Job not found.",
        )

    if not job.success or not job.result_video_path:
        raise api_error(
            status_code=status.HTTP_404_NOT_FOUND,
            code="JOB_NO_VIDEO_RESULT",
            message="Job has no completed result video.",
        )

    location = job.result_video_path

    # When job result points to S3, issue a redirect to a presigned URL
    # so the client can download directly from object storage.
    if location.startswith("s3://"):
        try:
            url = generate_presigned_get_url(location)
        except Exception as exc:
            raise api_error(
                status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                code="S3_DOWNLOAD_ERROR",
                message=f"Failed to generate download URL: {exc}",
            )
        return RedirectResponse(url=url, status_code=status.HTTP_307_TEMPORARY_REDIRECT)

    path = from_data_relative(location)
    if not path.is_file():
        raise api_error(
            status_code=status.HTTP_404_NOT_FOUND,
            code="RESULT_FILE_NOT_FOUND",
            message="Result video file not found on disk.",
        )

    return FileResponse(
        path,
        media_type="video/mp4",
        filename=path.name,
    )
@router.get(
    "/{project_id}/steadydancer/jobs",
    response_model=list[ProjectJobSummary],
)
async def list_project_jobs(
    project_id: UUID,
    session: AsyncSession = Depends(get_session),
) -> list[ProjectJobSummary]:
    """
    List all SteadyDancer jobs under a project.
    """
    jobs = await job_service.list_project_jobs(session=session, project_id=project_id)
    return [ProjectJobSummary.model_validate(j) for j in jobs]


@router.post(
    "/{project_id}/refs",
    response_model=ReferenceAssetOut,
    status_code=status.HTTP_201_CREATED,
)
async def create_reference_asset(
    project_id: UUID,
    payload: ReferenceAssetCreate,
    session: AsyncSession = Depends(get_session),
) -> ReferenceAssetOut:
    """
    Register a reference image asset under a project.

    The source image file will be copied into the project's refs directory.
    """
    try:
        asset = await asset_service.create_reference_asset(
            session=session,
            project_id=project_id,
            payload=payload,
        )
    except asset_service.ProjectNotFoundError:
        raise api_error(
            status_code=status.HTTP_404_NOT_FOUND,
            code="PROJECT_NOT_FOUND",
            message="Project not found.",
        )
    except asset_service.SourceFileNotFoundError as exc:
        raise api_error(
            status_code=status.HTTP_400_BAD_REQUEST,
            code="SOURCE_FILE_NOT_FOUND",
            message=str(exc),
        )

    return ReferenceAssetOut.model_validate(asset)


@router.get(
    "/{project_id}/refs",
    response_model=list[ReferenceAssetOut],
)
async def list_reference_assets(
    project_id: UUID,
    session: AsyncSession = Depends(get_session),
) -> list[ReferenceAssetOut]:
    """
    List all reference assets under a project.
    """
    assets = await asset_service.list_reference_assets(
        session=session,
        project_id=project_id,
    )
    return [ReferenceAssetOut.model_validate(a) for a in assets]


@router.get(
    "/{project_id}/refs/{ref_id}",
    response_model=ReferenceAssetOut,
)
async def get_reference_asset(
    project_id: UUID,
    ref_id: UUID,
    session: AsyncSession = Depends(get_session),
) -> ReferenceAssetOut:
    """
    Fetch a reference image asset by ID.
    """
    asset = await asset_service.get_reference_asset(
        session=session,
        project_id=project_id,
        asset_id=ref_id,
    )
    if asset is None:
        raise api_error(
            status_code=status.HTTP_404_NOT_FOUND,
            code="REFERENCE_ASSET_NOT_FOUND",
            message="Reference asset not found.",
        )
    return ReferenceAssetOut.model_validate(asset)


@router.post(
    "/{project_id}/motions",
    response_model=MotionAssetOut,
    status_code=status.HTTP_201_CREATED,
)
async def create_motion_asset(
    project_id: UUID,
    payload: MotionAssetCreate,
    session: AsyncSession = Depends(get_session),
) -> MotionAssetOut:
    """
    Register a motion (driving video) asset under a project.

    The source video file will be copied into the project's motions directory.
    """
    try:
        asset = await asset_service.create_motion_asset(
            session=session,
            project_id=project_id,
            payload=payload,
        )
    except asset_service.ProjectNotFoundError:
        raise api_error(
            status_code=status.HTTP_404_NOT_FOUND,
            code="PROJECT_NOT_FOUND",
            message="Project not found.",
        )
    except asset_service.SourceFileNotFoundError as exc:
        raise api_error(
            status_code=status.HTTP_400_BAD_REQUEST,
            code="SOURCE_FILE_NOT_FOUND",
            message=str(exc),
        )

    return MotionAssetOut.model_validate(asset)


@router.get(
    "/{project_id}/motions",
    response_model=list[MotionAssetOut],
)
async def list_motion_assets(
    project_id: UUID,
    session: AsyncSession = Depends(get_session),
) -> list[MotionAssetOut]:
    """
    List all motion assets under a project.
    """
    assets = await asset_service.list_motion_assets(
        session=session,
        project_id=project_id,
    )
    return [MotionAssetOut.model_validate(a) for a in assets]


@router.get(
    "/{project_id}/motions/{motion_id}",
    response_model=MotionAssetOut,
)
async def get_motion_asset(
    project_id: UUID,
    motion_id: UUID,
    session: AsyncSession = Depends(get_session),
) -> MotionAssetOut:
    """
    Fetch a motion asset by ID.
    """
    asset = await asset_service.get_motion_asset(
        session=session,
        project_id=project_id,
        asset_id=motion_id,
    )
    if asset is None:
        raise api_error(
            status_code=status.HTTP_404_NOT_FOUND,
            code="MOTION_ASSET_NOT_FOUND",
            message="Motion asset not found.",
        )
    return MotionAssetOut.model_validate(asset)


@router.post(
    "/{project_id}/experiments",
    response_model=ExperimentOut,
    status_code=status.HTTP_201_CREATED,
)
async def create_experiment(
    project_id: UUID,
    payload: ExperimentCreate,
    session: AsyncSession = Depends(get_session),
) -> ExperimentOut:
    """
    Create an experiment under a project.

    An experiment links optional reference / motion assets and stores a canonical
    prepared input directory for repeated SteadyDancer runs.
    """
    try:
        exp = await experiment_service.create_experiment(
            session=session,
            project_id=project_id,
            payload=payload,
        )
    except experiment_service.ProjectNotFoundError:
        raise api_error(
            status_code=status.HTTP_404_NOT_FOUND,
            code="PROJECT_NOT_FOUND",
            message="Project not found.",
        )
    except experiment_service.AssetNotFoundError as exc:
        raise api_error(
            status_code=status.HTTP_400_BAD_REQUEST,
            code="ASSET_NOT_FOUND",
            message=str(exc),
        )
    except experiment_service.SourceInputDirNotFoundError as exc:
        raise api_error(
            status_code=status.HTTP_400_BAD_REQUEST,
            code="SOURCE_INPUT_DIR_NOT_FOUND",
            message=str(exc),
        )

    return ExperimentOut.model_validate(exp)


@router.post(
    "/{project_id}/experiments/preprocess",
    response_model=ExperimentPreprocessCreated,
    status_code=status.HTTP_202_ACCEPTED,
)
async def create_experiment_with_preprocess(
    project_id: UUID,
    payload: ExperimentPreprocessCreate,
    session: AsyncSession = Depends(get_session),
) -> ExperimentPreprocessCreated:
    """
    Create an experiment from existing ReferenceAsset + MotionAsset
    and kick off a SteadyDancer preprocess pipeline on the worker.

    The experiment row is created immediately, while the heavy preprocessing
    runs asynchronously via Celery.
    """
    try:
        exp, task_id = await experiment_service.create_experiment_with_preprocess(
            session=session,
            project_id=project_id,
            payload=payload,
        )
    except experiment_service.ProjectNotFoundError:
        raise api_error(
            status_code=status.HTTP_404_NOT_FOUND,
            code="PROJECT_NOT_FOUND",
            message="Project not found.",
        )
    except experiment_service.AssetNotFoundError as exc:
        raise api_error(
            status_code=status.HTTP_400_BAD_REQUEST,
            code="ASSET_NOT_FOUND",
            message=str(exc),
        )

    return ExperimentPreprocessCreated(
        project_id=project_id,
        experiment_id=exp.id,
        task_id=task_id,
    )


@router.get(
    "/{project_id}/experiments",
    response_model=list[ExperimentOut],
)
async def list_experiments(
    project_id: UUID,
    session: AsyncSession = Depends(get_session),
) -> list[ExperimentOut]:
    """
    List all experiments under a project.
    """
    exps = await experiment_service.list_experiments(
        session=session,
        project_id=project_id,
    )
    return [ExperimentOut.model_validate(e) for e in exps]


@router.get(
    "/{project_id}/experiments/{experiment_id}",
    response_model=ExperimentOut,
)
async def get_experiment(
    project_id: UUID,
    experiment_id: UUID,
    session: AsyncSession = Depends(get_session),
) -> ExperimentOut:
    """
    Fetch an experiment by ID.
    """
    exp = await experiment_service.get_experiment(
        session=session,
        project_id=project_id,
        experiment_id=experiment_id,
    )
    if exp is None:
        raise api_error(
            status_code=status.HTTP_404_NOT_FOUND,
            code="EXPERIMENT_NOT_FOUND",
            message="Experiment not found.",
        )
    return ExperimentOut.model_validate(exp)


@router.post(
    "/{project_id}/experiments/{experiment_id}/steadydancer/jobs",
    response_model=ProjectJobCreated,
    status_code=status.HTTP_201_CREATED,
)
async def create_experiment_steadydancer_job(
    project_id: UUID,
    experiment_id: UUID,
    payload: SteadyDancerJobCreate,
    session: AsyncSession = Depends(get_session),
) -> ProjectJobCreated:
    """
    Create a SteadyDancer job from an existing experiment.

    The experiment's canonical input_dir (if present) is used as the source,
    while request parameters can override experiment-level config if needed.
    """
    exp = await experiment_service.get_experiment(
        session=session,
        project_id=project_id,
        experiment_id=experiment_id,
    )
    if exp is None:
        raise api_error(
            status_code=status.HTTP_404_NOT_FOUND,
            code="EXPERIMENT_NOT_FOUND",
            message="Experiment not found.",
        )

    try:
        job = await job_service.create_project_steadydancer_job(
            session=session,
            project_id=project_id,
            payload=payload,
            experiment=exp,
        )
    except job_service.ProjectNotFoundError:
        raise api_error(
            status_code=status.HTTP_404_NOT_FOUND,
            code="PROJECT_NOT_FOUND",
            message="Project not found.",
        )
    except job_service.InputDirNotFoundError as exc:
        raise api_error(
            status_code=status.HTTP_400_BAD_REQUEST,
            code="INPUT_DIR_NOT_FOUND",
            message=str(exc),
        )
    except job_service.JobPreparationError as exc:
        raise api_error(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            code="JOB_PREPARATION_FAILED",
            message=str(exc),
        )

    return ProjectJobCreated(project_id=project_id, job_id=job.id, task_id=job.task_id)


@router.get(
    "/{project_id}/experiments/{experiment_id}/steadydancer/jobs",
    response_model=list[ProjectJobSummary],
)
async def list_experiment_jobs(
    project_id: UUID,
    experiment_id: UUID,
    session: AsyncSession = Depends(get_session),
) -> list[ProjectJobSummary]:
    """
    List all SteadyDancer jobs under a specific experiment.
    """
    jobs = await job_service.list_experiment_jobs(
        session=session,
        project_id=project_id,
        experiment_id=experiment_id,
    )
    return [ProjectJobSummary.model_validate(j) for j in jobs]
