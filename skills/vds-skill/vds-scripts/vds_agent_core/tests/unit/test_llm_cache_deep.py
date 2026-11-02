"""Deep tests for LLM cache — disk read exception, disk write, clear, AnalysisCache."""

from vds_agent_core.llm.cache import (
    AnalysisCache,
    LLMResponseCache,
)


class TestLLMCacheDiskReadException:
    """Cover lines 132-133: exception during disk cache read."""

    def test_corrupt_cache_file_logs_warning_returns_none(self, tmp_path) -> None:
        """Corrupt JSON cache file returns None and logs warning."""
        cache_dir = tmp_path / "cache"
        cache_dir.mkdir()

        cache = LLMResponseCache(cache_root=str(cache_dir))
        key = cache._compute_key("test prompt", "test-model")

        cache_path = cache_dir / f"{key}.json"
        cache_path.write_text("not valid json {{{")

        entry = cache.get("test prompt", "test-model")
        assert entry is None

    def test_malformed_json_returns_none(self, tmp_path) -> None:
        """Malformed JSON that parses but fails validation returns None."""
        cache_dir = tmp_path / "cache"
        cache_dir.mkdir()

        cache = LLMResponseCache(cache_root=str(cache_dir))
        key = cache._compute_key("broken", "gpt-4")

        cache_path = cache_dir / f"{key}.json"
        cache_path.write_text('{"not": "a valid entry"}')

        entry = cache.get("broken", "gpt-4")
        assert entry is None


class TestLLMCacheDiskWrite:
    """Cover lines 170-171: disk write path in set()."""

    def test_set_writes_to_disk(self, tmp_path) -> None:
        """Setting a cache entry writes a JSON file to disk."""
        cache_dir = tmp_path / "cache"
        cache_dir.mkdir()

        cache = LLMResponseCache(cache_root=str(cache_dir))
        cache.set(
            prompt="what is pi?",
            model="gpt-4",
            response="3.14159",
            input_tokens=10,
            output_tokens=5,
        )

        key = cache._compute_key("what is pi?", "gpt-4")
        cache_path = cache_dir / f"{key}.json"
        assert cache_path.exists()

        entry = cache.get("what is pi?", "gpt-4")
        assert entry is not None
        assert entry.response == "3.14159"


class TestLLMCacheClear:
    """Cover lines 182-183: clear() iterating and deleting cache files."""

    def test_clear_removes_persisted_files(self, tmp_path) -> None:
        """Clear removes cache entries from disk."""
        cache_dir = tmp_path / "cache"
        cache_dir.mkdir()

        cache = LLMResponseCache(cache_root=str(cache_dir))
        cache.set("prompt-a", "model", "response-a")
        cache.set("prompt-b", "model", "response-b")

        key_a = cache._compute_key("prompt-a", "model")
        key_b = cache._compute_key("prompt-b", "model")
        assert (cache_dir / f"{key_a}.json").exists()
        assert (cache_dir / f"{key_b}.json").exists()

        count = cache.clear()
        assert count >= 2

        assert not (cache_dir / f"{key_a}.json").exists()
        assert not (cache_dir / f"{key_b}.json").exists()

        entry = cache.get("prompt-a", "model")
        assert entry is None


class TestAnalysisCacheGetSet:
    """Cover AnalysisCache get/set paths."""

    def test_analysis_cache_stores_and_retrieves(self, tmp_path) -> None:
        """AnalysisCache can store and retrieve results."""
        cache = AnalysisCache(cache_dir=tmp_path / "analysis")

        cache.set(
            content="analyze this repo",
            context={"repo": "my-repo"},
            result={"language": "python", "frameworks": ["fastapi"]},
        )
        result = cache.get("analyze this repo", {"repo": "my-repo"})
        assert result is not None
        assert result["language"] == "python"

    def test_analysis_cache_miss_returns_none(self, tmp_path) -> None:
        """Missing analysis key returns None."""
        cache = AnalysisCache(cache_dir=tmp_path / "analysis")
        assert cache.get("nonexistent", {"repo": "nope"}) is None
