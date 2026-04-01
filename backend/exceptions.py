"""Custom exception types for proper error propagation.

Instead of swallowing errors with bare except/print, modules raise typed
exceptions that callers can handle explicitly. Each carries context about
what failed and why.
"""


class SituationalError(Exception):
    """Base exception for all Situational errors."""


class SignalScanError(SituationalError):
    """A signal scanner failed (VIX, yields, currency, sectors, news)."""

    def __init__(self, scanner_name: str, cause: Exception):
        self.scanner_name = scanner_name
        self.cause = cause
        super().__init__(f"Signal scanner '{scanner_name}' failed: {cause}")


class FilingLayerError(SituationalError):
    """A filing intelligence layer failed."""

    def __init__(self, layer: str, source: str, cause: Exception):
        self.layer = layer
        self.source = source
        self.cause = cause
        super().__init__(f"Filing layer '{layer}' source '{source}' failed: {cause}")


class ThesisGenerationError(SituationalError):
    """Thesis generation failed (LLM call or parsing)."""

    def __init__(self, phase: str, cause: Exception):
        self.phase = phase
        self.cause = cause
        super().__init__(f"Thesis generation failed at '{phase}': {cause}")


class ThesisParseError(SituationalError):
    """Could not parse structured JSON from LLM response."""

    def __init__(self, detail: str):
        self.detail = detail
        super().__init__(f"Thesis parse error: {detail}")


class TickerValidationError(SituationalError):
    """Ticker validation against market data failed."""

    def __init__(self, ticker: str, cause: Exception):
        self.ticker = ticker
        self.cause = cause
        super().__init__(f"Ticker validation failed for '{ticker}': {cause}")


class ConfigError(SituationalError):
    """Configuration is missing or invalid."""

    def __init__(self, detail: str):
        self.detail = detail
        super().__init__(f"Configuration error: {detail}")
