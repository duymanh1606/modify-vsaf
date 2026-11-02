from __future__ import annotations

import tomllib
from collections.abc import Iterable
from dataclasses import dataclass, field
from fnmatch import fnmatch
from pathlib import Path

import yaml


@dataclass(frozen=True)
class Repository:
    name: str
    path: Path
    project: str
    branch: str
    tags: set[str] = field(default_factory=set)
    hooks: dict[str, list[str]] = field(default_factory=dict)
    _absolute_path: Path = field(repr=False, default=None)

    @property
    def absolute_path(self) -> Path:
        return self._absolute_path or self.path


@dataclass
class Manifest:
    repositories: list[Repository]

    @classmethod
    def merge(cls, manifests: Iterable[Manifest]) -> Manifest:
        repos: list[Repository] = []
        for manifest in manifests:
            repos.extend(manifest.repositories)
        seen = {}
        for repo in repos:
            seen[repo.name] = repo
        return cls(repositories=list(seen.values()))

    def filter(self, filters: ManifestFilters) -> list[Repository]:
        repos = self.repositories
        if filters.project:
            repos = [repo for repo in repos if repo.project == filters.project]
        if filters.name_match:
            repos = [repo for repo in repos if fnmatch(repo.name, filters.name_match)]
        if filters.include_tags:
            repos = [repo for repo in repos if filters.include_tags & repo.tags]
        if filters.exclude_tags:
            repos = [repo for repo in repos if repo.tags.isdisjoint(filters.exclude_tags)]
        return repos


@dataclass
class ManifestFilters:
    project: str | None = None
    name_match: str | None = None
    include_tags: set[str] = field(default_factory=set)
    exclude_tags: set[str] = field(default_factory=set)


def _coerce_tags(raw: Iterable[str] | None) -> set[str]:
    return {tag for tag in (raw or []) if tag}


def load_manifest(path: Path) -> Manifest:
    data = yaml.safe_load(path.read_text())
    repos_raw = data.get("repositories", [])
    repos: list[Repository] = []
    base_dirs, repo_root = _candidate_base_dirs(path)

    for entry in repos_raw:
        name = entry["name"]
        raw_path = Path(entry["path"]).expanduser()
        project = entry.get("project", "lep")
        branch = entry.get("branch", "release")
        tags = _coerce_tags(entry.get("tags"))
        hooks = entry.get("hooks", {}) or {}
        repo_path = _resolve_repo_path(raw_path, base_dirs, repo_root)
        repos.append(
            Repository(
                name=name,
                path=raw_path,
                project=project,
                branch=branch,
                tags=tags,
                hooks={phase: list(commands) for phase, commands in hooks.items()},
                _absolute_path=repo_path,
            )
        )

    return Manifest(repositories=repos)


def _get_project_dir_names(manifest_path: Path) -> set[str]:
    """Derive project directory names from bitbucket_manifest_mapping.toml and enabled projects.

    Args:
        manifest_path: Path to repo-manifest.yaml (used to locate mapping file)

    Returns:
        Set of project directory names (path_prefix values from mapping file)
    """
    # Try to import vds_cli.env - handle case where it's not available
    try:
        from vds_cli.env import load_environment, parse_git_projects
    except ImportError as err:
        # Fallback: try to load from environment variable directly
        import os

        projects_str = os.environ.get("VDS_GIT_PROJECTS")
        if not projects_str:
            raise ValueError(
                "VDS_GIT_PROJECTS must be set in the shared VDS env file. Format: VDS_GIT_PROJECTS=lep,insurance,saving,ekyc"
            ) from err
        enabled_projects = {p.strip() for p in projects_str.split(",") if p.strip()}
    else:
        # Load enabled projects from env
        settings = load_environment()
        if not settings.vds_git_projects:
            raise ValueError(
                "VDS_GIT_PROJECTS must be set in the shared VDS env file. Format: VDS_GIT_PROJECTS=lep,insurance,saving,ekyc"
            )
        enabled_projects = parse_git_projects(settings.vds_git_projects)

    # Load mapping file to get path_prefix values
    mapping_path = manifest_path.parent / "bitbucket_manifest_mapping.toml"
    if not mapping_path.exists():
        raise FileNotFoundError(f"Mapping file not found: {mapping_path}. Cannot derive project directory names.")

    data = tomllib.loads(mapping_path.read_text(encoding="utf-8"))
    projects_section = data.get("projects", {})

    project_dir_names: set[str] = set()
    for _key, raw_cfg in projects_section.items():
        if not isinstance(raw_cfg, dict):
            continue
        project_id = raw_cfg.get("project_id")
        path_prefix = raw_cfg.get("path_prefix")

        # Only include projects that are enabled
        if project_id in enabled_projects and path_prefix:
            project_dir_names.add(path_prefix)

    if not project_dir_names:
        raise ValueError(
            f"No project directory names found for enabled projects: {sorted(enabled_projects)}. "
            "Check bitbucket_manifest_mapping.toml for matching project_id values."
        )

    return project_dir_names


def _candidate_base_dirs(manifest_path: Path) -> tuple[list[Path], Path]:
    """
    Build an ordered list of directories to resolve relative repo paths.

    We walk up from the manifest directory to find the VDS monorepo root.
    The monorepo root is identified by the presence of project directories
    (derived from bitbucket_manifest_mapping.toml and enabled projects) at the root level.

    Special handling: If we're inside `vds-scripts/`, we prefer the parent
    directory (actual VDS root) over `vds-scripts` itself, even if `vds-scripts`
    contains project directories (which would be incorrectly cloned there).

    This allows manifests inside `vds-scripts/` to reference sibling
    directories such as `INSURANCE-project/` located at the monorepo root.
    """

    dirs: list[Path] = []
    repo_root: Path | None = None
    manifest_dir = manifest_path.parent.resolve()

    # Project directory names derived from mapping file and enabled projects
    try:
        project_dir_names = _get_project_dir_names(manifest_path)
    except (ValueError, FileNotFoundError):
        # If we can't load project dir names, fall back to empty set
        # This allows the function to still work for basic path resolution
        # but won't detect VDS root correctly
        project_dir_names = set()

    # Special case: If manifest is in vds-scripts, check parent first
    # (vds-scripts might have incorrectly cloned project dirs inside it)
    if manifest_dir.name == "vds-scripts" and manifest_dir.parent.exists():
        parent = manifest_dir.parent
        # Check if parent has project directories (actual VDS root)
        if project_dir_names and any((parent / proj_dir).exists() for proj_dir in project_dir_names):
            repo_root = parent
            dirs.append(parent)
            # Also add vds-scripts and its parents for fallback
            for candidate in [manifest_dir, *manifest_dir.parents]:
                if candidate not in dirs:
                    dirs.append(candidate)
            return dirs, repo_root

    # Normal case: walk up from manifest directory
    for candidate in [manifest_dir, *manifest_dir.parents]:
        dirs.append(candidate)
        # Check if this directory contains project directories (VDS monorepo root)
        # But skip if this is vds-scripts (might have incorrectly cloned dirs)
        if (
            candidate.name != "vds-scripts"
            and project_dir_names
            and any((candidate / proj_dir).exists() for proj_dir in project_dir_names)
        ):
            repo_root = candidate
            break

    if not dirs:
        dirs = [manifest_dir]
    if repo_root is None:
        # Last resort: use the directory that contains project directories
        # Walk up and check each level (excluding vds-scripts)
        if project_dir_names:
            for candidate in [manifest_dir, *manifest_dir.parents]:
                if candidate.name != "vds-scripts" and any(
                    (candidate / proj_dir).exists() for proj_dir in project_dir_names
                ):
                    repo_root = candidate
                    break
    if repo_root is None:
        repo_root = manifest_dir
    return dirs, repo_root


def _resolve_repo_path(raw_path: Path, base_dirs: list[Path], fallback_root: Path) -> Path:
    if raw_path.is_absolute():
        return raw_path.resolve()

    raw_parts = raw_path.parts
    if raw_parts:
        leading = raw_parts[0]
        # Paths that already name a VDS-root child (e.g. WHO-project/... or
        # INSURANCE-project/...) should prefer resolution from the detected VDS
        # monorepo root, not the first accidental match under a nested worktree.
        if leading == "WHO-project" or leading.endswith("-project"):
            candidate = fallback_root / raw_path
            if candidate.exists():
                return candidate.resolve()

    for base in base_dirs:
        candidate = base / raw_path
        if candidate.exists():
            return candidate.resolve()

    # Fallback to the detected repo root even if the path does not yet exist so
    # clone operations still receive an absolute target in the canonical VDS layout.
    return (fallback_root / raw_path).resolve()
