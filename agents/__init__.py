"""Art Manager agent package.

Importing this package is side-effect-free: the data models are exported
eagerly (they only need pydantic), while ``ArtManagerAgent`` is resolved lazily
on first access so that importing the package does not require nooa, an API key,
or network access.
"""

from .models import ArtPiece

__all__ = ["ArtManagerAgent", "ArtPiece"]


def __getattr__(name: str):
    if name == "ArtManagerAgent":
        from .art_manager import ArtManagerAgent

        return ArtManagerAgent
    raise AttributeError(f"module {__name__!r} has no attribute {name!r}")
