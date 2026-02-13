"""Leadgen ingest modules."""

__all__ = ["GoogleMapsIngest"]


def __getattr__(name: str):
    if name == "GoogleMapsIngest":
        from app.leadgen.ingest.google_maps import GoogleMapsIngest

        return GoogleMapsIngest
    raise AttributeError(f"module {__name__!r} has no attribute {name!r}")
