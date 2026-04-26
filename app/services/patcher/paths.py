from __future__ import annotations

from pathlib import Path, PurePosixPath


def normalize_property_file(path: str, *, property_id: str) -> str:
    """Return a property-relative posix path; reject anything that escapes."""
    pure = PurePosixPath(path.replace("\\", "/"))
    if pure.is_absolute():
        raise ValueError("patch file path must be relative")

    parts = list(pure.parts)
    if parts and parts[0] == "wiki":
        parts = parts[1:]
    if parts and parts[0] == property_id:
        parts = parts[1:]

    if not parts:
        raise ValueError("patch file path must include a filename")
    if any(part in {"", ".", ".."} for part in parts):
        raise ValueError("patch file path must stay inside the property")
    return PurePosixPath(*parts).as_posix()


def property_file_path(property_root: Path, path: str) -> Path:
    relative = normalize_property_file(path, property_id=property_root.name)
    root = property_root.resolve(strict=False)
    candidate = property_root / relative
    resolved = candidate.resolve(strict=False)
    if resolved != root and root not in resolved.parents:
        raise ValueError("patch file path escapes the property")
    return candidate
