"""Tests for vds_platform_core.severity — TDD RED phase."""

import pytest
from vds_platform_core.severity import (
    ErrorCodeMeta,
    ErrorCodeRegistry,
    ErrorRecoverability,
    ErrorSeverity,
)

# ---------------------------------------------------------------------------
# ErrorSeverity enum
# ---------------------------------------------------------------------------


class TestErrorSeverity:
    def test_values_are_strings(self) -> None:
        assert isinstance(ErrorSeverity.CRITICAL, str)
        assert isinstance(ErrorSeverity.HIGH, str)
        assert isinstance(ErrorSeverity.MEDIUM, str)
        assert isinstance(ErrorSeverity.LOW, str)

    def test_str_comparison(self) -> None:
        """StrEnum members compare equal to their string values."""
        assert ErrorSeverity.CRITICAL == "critical"
        assert ErrorSeverity.HIGH == "high"
        assert ErrorSeverity.MEDIUM == "medium"
        assert ErrorSeverity.LOW == "low"

    def test_all_members_present(self) -> None:
        members = {m.value for m in ErrorSeverity}
        assert members == {"critical", "high", "medium", "low"}


# ---------------------------------------------------------------------------
# ErrorRecoverability enum
# ---------------------------------------------------------------------------


class TestErrorRecoverability:
    def test_values_are_strings(self) -> None:
        assert isinstance(ErrorRecoverability.TRANSIENT, str)
        assert isinstance(ErrorRecoverability.RATE_LIMITED, str)
        assert isinstance(ErrorRecoverability.DEGRADED, str)
        assert isinstance(ErrorRecoverability.MANUAL, str)
        assert isinstance(ErrorRecoverability.PERMANENT, str)

    def test_str_comparison(self) -> None:
        assert ErrorRecoverability.TRANSIENT == "transient"
        assert ErrorRecoverability.RATE_LIMITED == "rate_limited"
        assert ErrorRecoverability.DEGRADED == "degraded"
        assert ErrorRecoverability.MANUAL == "manual"
        assert ErrorRecoverability.PERMANENT == "permanent"

    def test_all_members_present(self) -> None:
        members = {m.value for m in ErrorRecoverability}
        assert members == {"transient", "rate_limited", "degraded", "manual", "permanent"}

    def test_registry_accepts_all_five_values(self) -> None:
        """Each of the 5 recoverability values can be stored in a registry entry."""
        reg = ErrorCodeRegistry()
        for recov in ErrorRecoverability:
            meta = ErrorCodeMeta(
                code=f"TST-{recov.value.upper()[:3]}",
                description=f"Test for {recov.value}",
                severity=ErrorSeverity.LOW,
                recoverability=recov,
            )
            reg.register("TST", meta)
        assert len(list(reg.all_codes(prefix="TST"))) == 5


# ---------------------------------------------------------------------------
# ErrorCodeMeta dataclass
# ---------------------------------------------------------------------------


class TestErrorCodeMeta:
    def test_frozen_dataclass(self) -> None:
        meta = ErrorCodeMeta(
            code="CLI-001",
            description="Config missing",
            severity=ErrorSeverity.HIGH,
            recoverability=ErrorRecoverability.PERMANENT,
        )
        with pytest.raises((AttributeError, TypeError)):
            meta.code = "CLI-999"  # type: ignore[misc]

    def test_fields_accessible(self) -> None:
        meta = ErrorCodeMeta(
            code="CLI-001",
            description="Config missing",
            severity=ErrorSeverity.HIGH,
            recoverability=ErrorRecoverability.PERMANENT,
        )
        assert meta.code == "CLI-001"
        assert meta.description == "Config missing"
        assert meta.severity == ErrorSeverity.HIGH
        assert meta.recoverability == ErrorRecoverability.PERMANENT


# ---------------------------------------------------------------------------
# ErrorCodeRegistry
# ---------------------------------------------------------------------------


class TestErrorCodeRegistry:
    def _make_registry(self) -> ErrorCodeRegistry:
        return ErrorCodeRegistry()

    def test_register_and_lookup(self) -> None:
        reg = self._make_registry()
        meta = ErrorCodeMeta(
            code="CLI-001",
            description="Config missing",
            severity=ErrorSeverity.HIGH,
            recoverability=ErrorRecoverability.PERMANENT,
        )
        reg.register("CLI", meta)
        result = reg.lookup("CLI-001")
        assert result is meta

    def test_lookup_missing_returns_none(self) -> None:
        reg = self._make_registry()
        assert reg.lookup("NONEXISTENT-999") is None

    def test_all_codes_empty(self) -> None:
        reg = self._make_registry()
        assert list(reg.all_codes()) == []

    def test_all_codes_returns_registered(self) -> None:
        reg = self._make_registry()
        meta1 = ErrorCodeMeta("CLI-001", "desc1", ErrorSeverity.LOW, ErrorRecoverability.TRANSIENT)
        meta2 = ErrorCodeMeta("CLI-002", "desc2", ErrorSeverity.MEDIUM, ErrorRecoverability.PERMANENT)
        reg.register("CLI", meta1)
        reg.register("CLI", meta2)
        codes = list(reg.all_codes())
        assert len(codes) == 2
        assert meta1 in codes
        assert meta2 in codes

    def test_prefix_scoped_all_codes(self) -> None:
        reg = self._make_registry()
        cli_meta = ErrorCodeMeta("CLI-001", "d1", ErrorSeverity.LOW, ErrorRecoverability.TRANSIENT)
        sonar_meta = ErrorCodeMeta("SONAR-001", "d2", ErrorSeverity.HIGH, ErrorRecoverability.PERMANENT)
        reg.register("CLI", cli_meta)
        reg.register("SONAR", sonar_meta)

        cli_codes = list(reg.all_codes(prefix="CLI"))
        sonar_codes = list(reg.all_codes(prefix="SONAR"))

        assert cli_meta in cli_codes
        assert sonar_meta not in cli_codes
        assert sonar_meta in sonar_codes
        assert cli_meta not in sonar_codes

    def test_prefix_collision_raises(self) -> None:
        """Registering two metas with the same code under the same prefix raises ValueError."""
        reg = self._make_registry()
        meta1 = ErrorCodeMeta("CLI-001", "first", ErrorSeverity.LOW, ErrorRecoverability.TRANSIENT)
        meta2 = ErrorCodeMeta("CLI-001", "duplicate", ErrorSeverity.HIGH, ErrorRecoverability.PERMANENT)
        reg.register("CLI", meta1)
        with pytest.raises(ValueError, match="CLI-001"):
            reg.register("CLI", meta2)

    def test_enumerate_is_iterable(self) -> None:
        reg = self._make_registry()
        meta = ErrorCodeMeta("CLI-001", "d", ErrorSeverity.CRITICAL, ErrorRecoverability.PERMANENT)
        reg.register("CLI", meta)
        found = list(reg.all_codes())
        assert meta in found

    def test_generic_parameterisation(self) -> None:
        """ErrorCodeRegistry[ErrorSeverity, ErrorRecoverability] is valid at runtime."""
        # The generic alias should be constructable without error
        RegType = ErrorCodeRegistry[ErrorSeverity, ErrorRecoverability]  # type: ignore[type-arg]
        reg = RegType()
        assert isinstance(reg, ErrorCodeRegistry)
