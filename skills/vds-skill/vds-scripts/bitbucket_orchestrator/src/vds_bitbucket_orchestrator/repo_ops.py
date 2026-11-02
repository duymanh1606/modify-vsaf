"""Repository clone and archive operations (git subprocess + REST archive)."""

from __future__ import annotations

import re
import shutil
import subprocess
from dataclasses import dataclass
from pathlib import Path
from typing import TYPE_CHECKING
from urllib.parse import urlparse

import structlog

if TYPE_CHECKING:
    from .client import BitbucketClient

log = structlog.get_logger(__name__)


# ---------------------------------------------------------------------------
# Data models
# ---------------------------------------------------------------------------


@dataclass(frozen=True)
class RepoRef:
    """Parsed repository reference."""

    project_key: str
    repo_slug: str
    source_format: str  # "shorthand" | "browse_url" | "clone_url" | "ssh_url"


@dataclass(frozen=True)
class CloneResult:
    """Result of a clone/pull operation."""

    path: Path
    operation: str  # "clone" | "pull" | "reclone"
    branch: str
    ref: RepoRef


@dataclass(frozen=True)
class ArchiveResult:
    """Result of an archive operation."""

    archive_path: Path
    format: str  # "zip" | "tar.gz" | "tar" | "tgz"
    size_bytes: int
    method: str  # "rest_api" | "local_zip"
    ref: RepoRef


# ---------------------------------------------------------------------------
# URL Parsing
# ---------------------------------------------------------------------------

# Pattern 1: PROJECT/repo (shorthand — no scheme, single slash)
_RE_SHORTHAND = re.compile(r"^([A-Za-z0-9_-]+)/([A-Za-z0-9._-]+)$")

# Pattern 2: http(s)://host/projects/PROJECT/repos/REPO/browse[?...]
_RE_BROWSE = re.compile(r"/projects/([^/]+)/repos/([^/]+)")

# Pattern 3: http(s)://host/scm/PROJECT/REPO.git
_RE_CLONE = re.compile(r"/scm/([^/]+)/([^/]+?)(?:\.git)?$")

# Pattern 4: ssh://git@host[:port]/PROJECT/REPO.git
_RE_SSH = re.compile(r"ssh://[^/]+/([^/]+)/([^/]+?)(?:\.git)?$")


def parse_repo_identifier(identifier: str) -> RepoRef:
    """Parse a repository identifier into a RepoRef.

    Accepts:
      - PROJECT/repo (shorthand)
      - http(s)://host/projects/PROJECT/repos/REPO/browse
      - http(s)://host/scm/PROJECT/REPO.git
      - ssh://git@host[:port]/PROJECT/REPO.git
    """
    cleaned = identifier.strip()

    m = _RE_SHORTHAND.match(cleaned)
    if m:
        return RepoRef(project_key=m.group(1), repo_slug=m.group(2), source_format="shorthand")

    for pattern, fmt in [
        (_RE_BROWSE, "browse_url"),
        (_RE_CLONE, "clone_url"),
        (_RE_SSH, "ssh_url"),
    ]:
        m = pattern.search(cleaned)
        if m:
            return RepoRef(project_key=m.group(1), repo_slug=m.group(2), source_format=fmt)

    msg = (
        f"Cannot parse repository identifier: {identifier!r}\n"
        "Expected formats:\n"
        "  PROJECT/repo\n"
        "  http://host/projects/PROJECT/repos/REPO/browse\n"
        "  http://host/scm/PROJECT/REPO.git\n"
        "  ssh://git@host/PROJECT/REPO.git"
    )
    raise ValueError(msg)


def build_clone_url(
    ref: RepoRef,
    server_url: str,
    username: str | None = None,
    token: str | None = None,
) -> str:
    """Build an authenticated git clone URL from a RepoRef and server settings."""
    parsed = urlparse(server_url)
    scheme = parsed.scheme or "http"
    host = parsed.netloc or parsed.path

    if token:
        auth = f"x-token-auth:{token}"
    elif username:
        auth = username
    else:
        auth = None

    if auth:
        return f"{scheme}://{auth}@{host}/scm/{ref.project_key}/{ref.repo_slug}.git"
    return f"{scheme}://{host}/scm/{ref.project_key}/{ref.repo_slug}.git"


def default_clone_dir(ref: RepoRef, cache_root: Path) -> Path:
    """Return the standard VDS cache path for a cloned repo."""
    return cache_root / "repos" / f"{ref.project_key}-project" / ref.repo_slug


# ---------------------------------------------------------------------------
# Clone
# ---------------------------------------------------------------------------


def clone_repo(
    ref: RepoRef,
    clone_url: str,
    target_dir: Path,
    *,
    branch: str | None = None,
    shallow: bool = False,
    force_reclone: bool = False,
) -> CloneResult:
    """Clone or pull a repository.

    - If target exists and has .git: ``git pull --ff-only``
    - If ``force_reclone``: remove and re-clone
    - Otherwise: fresh ``git clone``
    """
    target = Path(target_dir)

    if force_reclone and target.exists():
        shutil.rmtree(target)
        log.info("reclone_removed_existing", path=str(target))

    if target.exists() and (target / ".git").is_dir():
        cmd = ["git", "-C", str(target), "pull", "--ff-only"]
        result = subprocess.run(cmd, capture_output=True, text=True, check=False)
        if result.returncode != 0:
            log.error("git_pull_failed", stderr=result.stderr.strip())
            raise RuntimeError(f"git pull failed: {result.stderr.strip()}")
        log.info("pull_complete", path=str(target))
        return CloneResult(
            path=target,
            operation="pull",
            branch=branch or "HEAD",
            ref=ref,
        )

    target.parent.mkdir(parents=True, exist_ok=True)
    cmd = ["git", "clone"]
    if branch:
        cmd += ["--branch", branch]
    if shallow:
        cmd += ["--depth", "1"]
    cmd += [clone_url, str(target)]

    result = subprocess.run(cmd, capture_output=True, text=True, check=False)
    if result.returncode != 0:
        # Clean up partial clone
        if target.exists():
            shutil.rmtree(target, ignore_errors=True)
        log.error("git_clone_failed", stderr=result.stderr.strip())
        raise RuntimeError(f"git clone failed: {result.stderr.strip()}")

    log.info("clone_complete", path=str(target), shallow=shallow)
    return CloneResult(
        path=target,
        operation="reclone" if force_reclone else "clone",
        branch=branch or "HEAD",
        ref=ref,
    )


# ---------------------------------------------------------------------------
# Archive
# ---------------------------------------------------------------------------


def download_rest_archive(
    client: BitbucketClient,
    ref: RepoRef,
    output_path: Path,
    *,
    format: str = "zip",
    at: str | None = None,
    path: str | None = None,
) -> ArchiveResult | None:
    """Try Bitbucket Server REST archive endpoint.

    Returns an ArchiveResult on success, or None if the endpoint is not
    available (e.g. Bitbucket Server < 5.1).
    """
    try:
        output_path.parent.mkdir(parents=True, exist_ok=True)
        with open(output_path, "wb") as fd:
            client.download_archive(
                ref.project_key,
                ref.repo_slug,
                fd,
                at=at,
                format=format,
                path=path,
            )
        size = output_path.stat().st_size
        if size == 0:
            output_path.unlink(missing_ok=True)
            log.warning("rest_archive_empty", project=ref.project_key, repo=ref.repo_slug)
            return None
        log.info("rest_archive_downloaded", path=str(output_path), size_bytes=size)
        return ArchiveResult(
            archive_path=output_path,
            format=format,
            size_bytes=size,
            method="rest_api",
            ref=ref,
        )
    except Exception:
        log.warning(
            "rest_archive_failed_falling_back",
            project=ref.project_key,
            repo=ref.repo_slug,
            exc_info=True,
        )
        output_path.unlink(missing_ok=True)
        return None


def _zip_directory(source_dir: Path, output_path: Path, *, include_git: bool) -> int:
    """Create a zip archive of a directory, optionally excluding .git/."""
    import zipfile

    output_path.parent.mkdir(parents=True, exist_ok=True)
    with zipfile.ZipFile(output_path, "w", zipfile.ZIP_DEFLATED) as zf:
        for file_path in sorted(source_dir.rglob("*")):
            if not include_git and ".git" in file_path.parts:
                continue
            if file_path.is_file():
                arcname = file_path.relative_to(source_dir.parent)
                zf.write(file_path, arcname)
    return output_path.stat().st_size


def _targz_directory(source_dir: Path, output_path: Path, *, include_git: bool) -> int:
    """Create a tar.gz archive of a directory."""
    import tarfile

    output_path.parent.mkdir(parents=True, exist_ok=True)

    def _filter(tarinfo: tarfile.TarInfo) -> tarfile.TarInfo | None:
        if not include_git and "/.git/" in f"/{tarinfo.name}/":
            return None
        return tarinfo

    with tarfile.open(output_path, "w:gz") as tf:
        tf.add(source_dir, arcname=source_dir.name, filter=_filter)
    return output_path.stat().st_size


def archive_repo(
    ref: RepoRef,
    client: BitbucketClient,
    clone_url: str,
    cache_root: Path,
    output_path: Path,
    *,
    format: str = "zip",
    at: str | None = None,
    path: str | None = None,
    include_git: bool = False,
) -> ArchiveResult:
    """Archive a repo: REST-first, fallback to clone+zip.

    When ``include_git`` is True, the REST path is skipped because REST
    archives never include ``.git/``.
    """
    # Path A: REST archive (unless include_git requested)
    if not include_git:
        rest_result = download_rest_archive(client, ref, output_path, format=format, at=at, path=path)
        if rest_result is not None:
            return rest_result

    # Path B: Clone + local archive
    clone_dir = default_clone_dir(ref, cache_root)
    clone_repo(ref, clone_url, clone_dir, branch=at)

    if format in ("tar.gz", "tgz"):
        size = _targz_directory(clone_dir, output_path, include_git=include_git)
    else:
        size = _zip_directory(clone_dir, output_path, include_git=include_git)

    log.info("local_archive_created", path=str(output_path), size_bytes=size, format=format)
    return ArchiveResult(
        archive_path=output_path,
        format=format,
        size_bytes=size,
        method="local_zip",
        ref=ref,
    )
