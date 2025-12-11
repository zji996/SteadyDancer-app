from __future__ import annotations

import os
from dataclasses import dataclass
from pathlib import Path
from typing import Union
from uuid import UUID


def _get_repo_root() -> Path:
    """
    Infer the repository root based on this file's location.

    Layout: libs/py_core/projects.py -> libs/py_core -> libs -> <repo_root>
    """
    return Path(__file__).resolve().parents[3]


def get_repo_root() -> Path:
    """
    Public helper to return the repository root directory.
    """
    return _get_repo_root()


def get_data_root() -> Path:
    """
    Return the root directory for SteadyDancer project/job data.

    Priority (for backward compatibility and new DATA_DIR convention):
    - If STEADYDANCER_DATA_DIR is set, use it as-is;
    - Else if DATA_DIR is set, use it as-is;
    - Otherwise, default to <repo_root>/data.
    """
    env_value = os.getenv("STEADYDANCER_DATA_DIR") or os.getenv("DATA_DIR")
    if env_value:
        return Path(env_value).expanduser().resolve()

    repo_root = _get_repo_root()
    return (repo_root / "data").resolve()


def resolve_repo_relative(path: Union[Path, str]) -> Path:
    """
    Resolve a path that is documented as "absolute or repo-root-relative".

    - If `path` is absolute, return it as-is (expanded & resolved);
    - Otherwise, treat it as relative to the repository root.
    """
    p = Path(path)
    if p.is_absolute():
        return p.expanduser().resolve()

    base = _get_repo_root()
    return (base / p).expanduser().resolve()


def to_data_relative(path: Union[Path, str]) -> str:
    """
    Convert an absolute path under the data root into a relative path.

    - If `path` is under get_data_root(), return a POSIX-style relative path;
    - Otherwise, return the original path string unchanged.
    """
    base = get_data_root()
    p = Path(path).expanduser().resolve()
    try:
        rel = p.relative_to(base)
        return rel.as_posix()
    except ValueError:
        return str(p)


def from_data_relative(path_str: str) -> Path:
    """
    Resolve a path string stored in the DB into an absolute filesystem path.

    - If `path_str` is absolute, return it as-is;
    - Otherwise, treat it as relative to get_data_root().
    """
    p = Path(path_str)
    if p.is_absolute():
        return p
    return (get_data_root() / p).resolve()


def get_tmp_root() -> Path:
    """
    Return the root directory for SteadyDancer temporary files.

    - If STEADYDANCER_TMP_DIR is set, use it as-is;
    - Otherwise, default to <data_root>/tmp.
    """
    env_value = os.getenv("STEADYDANCER_TMP_DIR")
    if env_value:
        return Path(env_value).expanduser().resolve()

    return get_data_root() / "tmp"


@dataclass
class JobPaths:
    """
    Resolved filesystem paths for a single job.

    These are organized under:
    <data_root>/projects/{project_id}/jobs/{job_id}/...
    """

    project_root: Path
    job_root: Path
    input_dir: Path
    output_dir: Path
    tmp_dir: Path
    logs_dir: Path


@dataclass
class ReferencePaths:
    """
    Resolved filesystem paths for a single reference asset.

    Layout:
    <data_root>/projects/{project_id}/refs/{ref_id}/
        source/
        meta.json
    """

    project_root: Path
    ref_root: Path
    source_dir: Path
    meta_path: Path


@dataclass
class MotionPaths:
    """
    Resolved filesystem paths for a single motion asset.

    Layout:
    <data_root>/projects/{project_id}/motions/{motion_id}/
        source/
        meta.json
    """

    project_root: Path
    motion_root: Path
    source_dir: Path
    meta_path: Path


@dataclass
class ExperimentPaths:
    """
    Resolved filesystem paths for a single experiment.

    Layout:
    <data_root>/projects/{project_id}/experiments/{experiment_id}/
        input/      # canonical pair_dir or prepared inputs
        config.json # experiment-level configuration
    """

    project_root: Path
    experiment_root: Path
    input_dir: Path
    config_path: Path


def _normalize_uuid(value: Union[UUID, str]) -> str:
    if isinstance(value, UUID):
        return str(value)
    return str(value)


def get_project_root(project_id: Union[UUID, str]) -> Path:
    """
    Compute the root directory for a given project.
    """
    return get_data_root() / "projects" / _normalize_uuid(project_id)


def get_job_root(project_id: Union[UUID, str], job_id: Union[UUID, str]) -> Path:
    """
    Compute the root directory for a given job under a project.
    """
    return get_project_root(project_id) / "jobs" / _normalize_uuid(job_id)


def ensure_job_dirs(project_id: Union[UUID, str], job_id: Union[UUID, str]) -> JobPaths:
    """
    Ensure the standard directory layout for a job exists and return its paths.

    Layout:
    - <data_root>/projects/{project_id}/jobs/{job_id}/
        - input/
        - output/
        - tmp/
        - logs/
    """
    project_root = get_project_root(project_id)
    job_root = get_job_root(project_id, job_id)

    input_dir = job_root / "input"
    output_dir = job_root / "output"
    tmp_dir = job_root / "tmp"
    logs_dir = job_root / "logs"

    for path in (project_root, job_root, input_dir, output_dir, tmp_dir, logs_dir):
        path.mkdir(parents=True, exist_ok=True)

    return JobPaths(
        project_root=project_root,
        job_root=job_root,
        input_dir=input_dir,
        output_dir=output_dir,
        tmp_dir=tmp_dir,
        logs_dir=logs_dir,
    )


def get_reference_root(project_id: Union[UUID, str], ref_id: Union[UUID, str]) -> Path:
    """
    Compute the root directory for a reference asset within a project.
    """
    return get_project_root(project_id) / "refs" / _normalize_uuid(ref_id)


def ensure_reference_dirs(
    project_id: Union[UUID, str],
    ref_id: Union[UUID, str],
) -> ReferencePaths:
    """
    Ensure the directory layout for a reference asset exists and return its paths.
    """
    project_root = get_project_root(project_id)
    ref_root = get_reference_root(project_id, ref_id)
    source_dir = ref_root / "source"
    meta_path = ref_root / "meta.json"

    for path in (project_root, ref_root, source_dir):
        path.mkdir(parents=True, exist_ok=True)

    return ReferencePaths(
        project_root=project_root,
        ref_root=ref_root,
        source_dir=source_dir,
        meta_path=meta_path,
    )


def get_motion_root(project_id: Union[UUID, str], motion_id: Union[UUID, str]) -> Path:
    """
    Compute the root directory for a motion asset within a project.
    """
    return get_project_root(project_id) / "motions" / _normalize_uuid(motion_id)


def ensure_motion_dirs(
    project_id: Union[UUID, str],
    motion_id: Union[UUID, str],
) -> MotionPaths:
    """
    Ensure the directory layout for a motion asset exists and return its paths.
    """
    project_root = get_project_root(project_id)
    motion_root = get_motion_root(project_id, motion_id)
    source_dir = motion_root / "source"
    meta_path = motion_root / "meta.json"

    for path in (project_root, motion_root, source_dir):
        path.mkdir(parents=True, exist_ok=True)

    return MotionPaths(
        project_root=project_root,
        motion_root=motion_root,
        source_dir=source_dir,
        meta_path=meta_path,
    )


def get_experiment_root(
    project_id: Union[UUID, str],
    experiment_id: Union[UUID, str],
) -> Path:
    """
    Compute the root directory for an experiment within a project.
    """
    return get_project_root(project_id) / "experiments" / _normalize_uuid(experiment_id)


def ensure_experiment_dirs(
    project_id: Union[UUID, str],
    experiment_id: Union[UUID, str],
) -> ExperimentPaths:
    """
    Ensure the directory layout for an experiment exists and return its paths.
    """
    project_root = get_project_root(project_id)
    experiment_root = get_experiment_root(project_id, experiment_id)
    input_dir = experiment_root / "input"
    config_path = experiment_root / "config.json"

    for path in (project_root, experiment_root, input_dir):
        path.mkdir(parents=True, exist_ok=True)

    return ExperimentPaths(
        project_root=project_root,
        experiment_root=experiment_root,
        input_dir=input_dir,
        config_path=config_path,
    )
