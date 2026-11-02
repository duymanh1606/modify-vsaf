"""Skill management helpers — extracted from audit_orchestrator (FR-5.2).

The ContentHashValidator Protocol decouples SkillManager from the
audit_orchestrator's concrete validate_skill_content_hash implementation,
making this module usable in any orchestrator without a hard dependency.

Known audit-specific deferred import (documented exception to G-W4.3):
- vds_audit_orchestrator.agents.toolsets.skills_toolset: used only as a
  legacy fallback in prevalidate_skill_toolsets when no ContentHashValidator
  is injected. Callers that inject a validator never trigger this import.
"""

from __future__ import annotations

import functools
import re
from pathlib import Path
from typing import Any, Protocol


class ContentHashValidator(Protocol):
    """Protocol for skill content-hash validation.

    Implement this to plug in audit_orchestrator's validate_skill_content_hash
    or any other hash-checking strategy.
    """

    def validate(self, skill_item: Any, *, raise_on_mismatch: bool = False) -> bool: ...


class SkillManager:
    """Utility methods for skill toolset handling and preloading."""

    def __init__(self, hash_validator: ContentHashValidator | None = None) -> None:
        self._hash_validator = hash_validator

    @staticmethod
    @functools.lru_cache(maxsize=32)
    def load_skill_rubric(skill_name: str, skills_dir: Path) -> str:
        """Load SKILL.md content for prompt injection. Fail-open: returns '' on error."""
        skill_path = skills_dir / skill_name / "SKILL.md"
        try:
            return skill_path.read_text(encoding="utf-8")
        except Exception:
            return ""

    _SKILL_TOOL_NAMES: frozenset[str] = frozenset(
        {
            "list_skills",
            "load_skill",
            "read_skill_resource",
            "run_skill_script",
        }
    )

    @staticmethod
    def parse_skill_name_from_error(error: str) -> str | None:
        patterns = (
            r"skill '([^']+)'",
            r'skill "([^"]+)"',
            r"skill_name['\"]?\s*[:=]\s*['\"]([^'\"]+)['\"]",
        )
        for pattern in patterns:
            match = re.search(pattern, error, flags=re.IGNORECASE)
            if match:
                name = str(match.group(1)).strip()
                if name:
                    return name
        return None

    @classmethod
    def drop_skill_from_toolsets(cls, toolsets: list[Any], skill_name: str) -> tuple[list[Any], int]:
        """Remove only *skill_name* from skills toolsets; keep other skills active."""
        if not skill_name:
            return list(toolsets), 0

        target_aliases = cls._build_skill_aliases(skill_name)
        if not target_aliases:
            return list(toolsets), 0

        removed_count = 0
        updated_toolsets: list[Any] = []
        for toolset in toolsets:
            skills_map = getattr(toolset, "skills", None)
            metadata = getattr(toolset, "_vds_skill_metadata", None)
            if isinstance(skills_map, dict):
                for name in list(skills_map):
                    aliases = cls._build_skill_aliases(str(name))
                    if aliases and aliases.intersection(target_aliases):
                        skills_map.pop(name, None)
                        removed_count += 1
                if isinstance(metadata, list):
                    filtered_metadata = [
                        item
                        for item in metadata
                        if not cls._build_skill_aliases(str(getattr(item, "name", "") or "").strip()).intersection(
                            target_aliases
                        )
                    ]
                    toolset._vds_skill_metadata = filtered_metadata
                tool_bindings = getattr(toolset, "tools", None)
                if skills_map or (isinstance(tool_bindings, dict) and bool(tool_bindings)):
                    updated_toolsets.append(toolset)
                continue
            if isinstance(metadata, list):
                matched = False
                filtered_metadata = []
                for item in metadata:
                    name = str(getattr(item, "name", "") or "").strip()
                    aliases = cls._build_skill_aliases(name)
                    if aliases and aliases.intersection(target_aliases):
                        matched = True
                        continue
                    filtered_metadata.append(item)
                if matched:
                    removed_count += 1
                    toolset._vds_skill_metadata = filtered_metadata
                    if filtered_metadata:
                        updated_toolsets.append(toolset)
                    continue
            updated_toolsets.append(toolset)
        return updated_toolsets, removed_count

    @staticmethod
    def prevalidate_skill_toolsets(
        toolsets: list[Any],
        logger: Any,
        hash_validator: ContentHashValidator | None = None,
    ) -> list[Any]:
        """Pre-validate skill resources; degrade invalid skills without failing run.

        Uses the provided hash_validator if given; otherwise no validation is performed.
        Callers that need hash validation must pass a ContentHashValidator.
        """
        validator = hash_validator

        # No validator injected — skip validation and return toolsets as-is.
        # Callers that need hash validation must inject a ContentHashValidator.
        if validator is None:
            return toolsets

        validated_toolsets: list[Any] = []
        for toolset in toolsets:
            skills_map = getattr(toolset, "skills", None)
            metadata = getattr(toolset, "_vds_skill_metadata", None)
            if not isinstance(skills_map, dict) or not isinstance(metadata, list):
                validated_toolsets.append(toolset)
                continue

            rejected_skills: list[str] = []
            for item in list(metadata):
                skill_name = str(getattr(item, "name", "") or "").strip()
                if not skill_name:
                    continue
                if skill_name not in skills_map:
                    continue
                has_path = hasattr(item, "path")
                has_hash = hasattr(item, "content_hash")
                if has_path and has_hash and not validator.validate(item, raise_on_mismatch=False):
                    rejected_skills.append(skill_name)
            for skill_name in rejected_skills:
                skills_map.pop(skill_name, None)
            if rejected_skills:
                filtered_metadata = [
                    item
                    for item in metadata
                    if str(getattr(item, "name", "") or "").strip() not in set(rejected_skills)
                ]
                toolset._vds_skill_metadata = filtered_metadata
                logger.warning(
                    "agentic_skill_prevalidation_degraded",
                    rejected_skills=sorted(set(rejected_skills)),
                )
            if skills_map:
                validated_toolsets.append(toolset)
            else:
                logger.warning("agentic_skill_toolset_empty_after_prevalidation")
        return validated_toolsets

    @classmethod
    def has_skill_tool_bindings(cls, toolsets: list[Any]) -> bool:
        for toolset in toolsets:
            tools_map = getattr(toolset, "tools", None)
            if not isinstance(tools_map, dict):
                continue
            for tool_name in tools_map:
                if str(tool_name).strip() in cls._SKILL_TOOL_NAMES:
                    return True
        return False

    @classmethod
    def collect_available_skill_names(
        cls,
        toolsets: list[Any],
        *,
        require_skill_tool_bindings: bool = False,
        allow_metadata_fallback: bool = True,
    ) -> list[str]:
        """Return callable skill names from attached skill toolsets."""
        if require_skill_tool_bindings and not cls.has_skill_tool_bindings(toolsets):
            return []

        has_any_runtime_skills_map = any(isinstance(getattr(toolset, "skills", None), dict) for toolset in toolsets)
        names: list[str] = []
        for toolset in toolsets:
            skills_map = getattr(toolset, "skills", None)
            if isinstance(skills_map, dict):
                for name in skills_map:
                    skill_name = str(name or "").strip()
                    if skill_name and skill_name not in names:
                        names.append(skill_name)
                continue

            if not allow_metadata_fallback:
                continue
            if has_any_runtime_skills_map:
                continue
            metadata = getattr(toolset, "_vds_skill_metadata", None)
            if not isinstance(metadata, list):
                continue
            for item in metadata:
                name = str(getattr(item, "name", "") or "").strip()
                if name and name not in names:
                    names.append(name)
        return names

    @staticmethod
    def _normalize_skill_token(value: str) -> str:
        text = str(value or "").strip().lower()
        if not text:
            return ""
        text = re.sub(r"[\s_]+", "-", text)
        text = re.sub(r"-{2,}", "-", text)
        return text

    @classmethod
    def _build_skill_aliases(cls, value: str | None) -> set[str]:
        text = str(value or "").strip()
        if not text:
            return set()
        normalized = cls._normalize_skill_token(text)
        aliases: set[str] = {text, normalized}
        if normalized.endswith("-skill"):
            aliases.add(normalized[: -len("-skill")])
        else:
            aliases.add(f"{normalized}-skill")
        return {alias for alias in aliases if alias}

    @classmethod
    def _resolve_available_skill_match(cls, candidate: str, available_skill_names: list[str]) -> str | None:
        candidate_aliases = cls._build_skill_aliases(candidate)
        if not candidate_aliases:
            return None
        for available in available_skill_names:
            if candidate_aliases.intersection(cls._build_skill_aliases(available)):
                return available
        return None

    @classmethod
    def retain_skills_in_toolsets(
        cls,
        *,
        toolsets: list[Any],
        allowed_skill_names: list[str],
    ) -> tuple[list[Any], int]:
        allowed_aliases: set[str] = set()
        for name in allowed_skill_names:
            allowed_aliases.update(cls._build_skill_aliases(name))
        if not allowed_aliases:
            return list(toolsets), 0

        removed_entries = 0
        updated_toolsets: list[Any] = []
        for toolset in toolsets:
            skills_map = getattr(toolset, "skills", None)
            metadata = getattr(toolset, "_vds_skill_metadata", None)
            if isinstance(skills_map, dict):
                for skill_name in list(skills_map):
                    aliases = cls._build_skill_aliases(skill_name)
                    if aliases and aliases.intersection(allowed_aliases):
                        continue
                    skills_map.pop(skill_name, None)
                    removed_entries += 1
            if isinstance(metadata, list):
                filtered_metadata = []
                for item in metadata:
                    item_name = str(getattr(item, "name", "") or "").strip()
                    aliases = cls._build_skill_aliases(item_name)
                    if aliases and aliases.intersection(allowed_aliases):
                        filtered_metadata.append(item)
                        continue
                    if item_name:
                        removed_entries += 1
                toolset._vds_skill_metadata = filtered_metadata
            updated_toolsets.append(toolset)
        return updated_toolsets, removed_entries

    @staticmethod
    def build_preloaded_skill_context(
        toolsets: list[Any],
        available_skill_names: list[str],
        *,
        max_skills: int = 2,
        max_chars_per_skill: int = 1400,
        preferred_skill_names: list[str] | None = None,
    ) -> tuple[str, list[str]]:
        """Preload compact skill guidance so agentic runs are not model-choice fragile."""
        if not available_skill_names:
            return ("", [])

        default_priority = (
            "cli-development-skill",
            "llm-analysis-skill",
            "research-skill",
            "vds-scripts-skill",
            "audit-orchestrator-skill",
        )
        priority_hints = [str(name).strip() for name in (preferred_skill_names or []) if str(name).strip()]
        priority_hints.extend(default_priority)

        ordered_names: list[str] = []
        for hint in priority_hints:
            matched = SkillManager._resolve_available_skill_match(hint, available_skill_names)
            if matched and matched not in ordered_names:
                ordered_names.append(matched)
        ordered_names.extend(name for name in available_skill_names if name not in ordered_names)

        loaded_names: list[str] = []
        chunks: list[str] = []
        for skill_name in ordered_names:
            if len(loaded_names) >= max_skills:
                break
            for toolset in toolsets:
                skills_map = getattr(toolset, "skills", None)
                if not isinstance(skills_map, dict) or skill_name not in skills_map:
                    continue
                get_skill = getattr(toolset, "get_skill", None)
                if not callable(get_skill):
                    continue
                try:
                    skill = get_skill(skill_name)
                except Exception:
                    continue

                description = str(getattr(skill, "description", "") or "").strip()
                content = str(getattr(skill, "content", "") or "").strip()
                if content:
                    content = content[:max_chars_per_skill].rstrip()
                resources_obj = getattr(skill, "resources", [])
                resource_names: list[str] = []
                if isinstance(resources_obj, list):
                    for item in resources_obj[:4]:
                        resource_name = str(getattr(item, "name", "") or "").strip()
                        if resource_name:
                            resource_names.append(resource_name)
                scripts_obj = getattr(skill, "scripts", [])
                script_names: list[str] = []
                if isinstance(scripts_obj, list):
                    for item in scripts_obj[:4]:
                        script_name = str(getattr(item, "name", "") or "").strip()
                        if script_name:
                            script_names.append(script_name)

                snippet_parts = [
                    f"Skill: {skill_name}",
                    f"Description: {description or 'n/a'}",
                ]
                if resource_names:
                    snippet_parts.append("Resources: " + ", ".join(resource_names))
                if script_names:
                    snippet_parts.append("Scripts: " + ", ".join(script_names))
                if content:
                    snippet_parts.append("Content excerpt:")
                    snippet_parts.append(content)
                chunks.append("\n".join(snippet_parts))
                loaded_names.append(skill_name)
                break

        if not chunks:
            return ("", [])
        return ("\n\n".join(chunks), loaded_names)
