from pathlib import Path

from vds_git_orchestrator.manifest import Manifest, ManifestFilters, Repository, load_manifest


def test_load_manifest_roundtrip(tmp_path: Path) -> None:
    manifest_path = tmp_path / "repos.yaml"
    manifest_path.write_text(
        """
repositories:
  - name: service-a
    path: services/service-a
    project: lep
    branch: release
    tags: ["core", "backend"]
    hooks:
      pre_pull:
        - "./scripts/check.sh"
  - name: web-ui
    path: web/web-ui
    project: insurance
    branch: main
"""
    )

    manifest = load_manifest(manifest_path)

    assert len(manifest.repositories) == 2
    repo_a = manifest.repositories[0]
    assert repo_a.name == "service-a"
    assert repo_a.path == Path("services/service-a")
    assert repo_a.project == "lep"
    assert repo_a.branch == "release"
    assert repo_a.tags == {"core", "backend"}
    assert repo_a.hooks["pre_pull"] == ["./scripts/check.sh"]

    repo_b = manifest.repositories[1]
    assert repo_b.name == "web-ui"
    assert repo_b.branch == "main"
    assert repo_b.tags == set()


def test_manifest_filtering_by_project_tag_and_name(tmp_path: Path) -> None:
    repo_root = tmp_path / "workspace"
    repo_root.mkdir()

    manifest = Manifest(
        repositories=[
            Repository(
                name="service-a",
                path=repo_root / "service-a",
                project="lep",
                branch="release",
                tags={"core", "backend"},
            ),
            Repository(
                name="service-b",
                path=repo_root / "service-b",
                project="insurance",
                branch="release",
                tags={"event"},
            ),
            Repository(
                name="web-ui",
                path=repo_root / "web-ui",
                project="insurance",
                branch="main",
                tags={"frontend"},
            ),
        ]
    )

    filters = ManifestFilters(project="insurance", include_tags={"frontend"})
    results = manifest.filter(filters)
    assert [repo.name for repo in results] == ["web-ui"]

    filters = ManifestFilters(name_match="service-*", exclude_tags={"event"})
    results = manifest.filter(filters)
    assert [repo.name for repo in results] == ["service-a"]
