# ai-generated: 85% - Claude Code drafted this module from METRIC-SPEC.md sec 1; reviewed and accepted
"""The one error the engine raises: an event log that fails well-formedness (METRIC-SPEC.md sec 1)."""


class MetricsError(ValueError):
    """Raised when an event log is not well formed. The route layer maps this to 400/422."""
