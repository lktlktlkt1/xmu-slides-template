#!/usr/bin/env python3
r"""Copy the XMU Beamer template into a destination directory.

Template source priority:
1. The user's maintained fork at ``~/xmu-slides-template`` (or
   ``TEMPLATE_DIR`` when explicitly set).
2. The packaged snapshot under ``templates/xmu/`` as an offline fallback.

The fork is the branding source of truth. The copier does not inject, hide,
or replace logos and credit lines after copying.
"""

from __future__ import annotations

import argparse
import os
import shutil
import sys
from pathlib import Path

PACKAGE_ROOT = Path(__file__).resolve().parent.parent
PACKAGED_ROOT = PACKAGE_ROOT / "templates" / "xmu"
REPO_ROOT = Path(os.environ.get("TEMPLATE_DIR", Path.home() / "xmu-slides-template")).expanduser()
FILE_ASSETS = ("main_template.tex", "latexmkrc")
THEME_ASSET = "xmu-theme"
THEME_FILES = (
    "beamerthemexmu.sty",
    "beamercolorthemexmu.sty",
    "beamerthemexmu-elements.sty",
)


def _is_complete(root: Path) -> bool:
    """Return whether root contains every required XMU template asset."""
    return (
        all((root / name).is_file() for name in FILE_ASSETS)
        and (root / THEME_ASSET).is_dir()
        and all((root / THEME_ASSET / name).is_file() for name in THEME_FILES)
    )


def _choose_root() -> tuple[Path, str]:
    """Return the maintained fork when complete, otherwise the snapshot."""
    if _is_complete(REPO_ROOT):
        return REPO_ROOT, f"XMU template fork {REPO_ROOT}"
    return PACKAGED_ROOT, f"packaged XMU template {PACKAGED_ROOT}"


def copy_template(output: Path, force: bool = False) -> None:
    src, label = _choose_root()
    if not _is_complete(src):
        raise FileNotFoundError(f"incomplete XMU template source: {src}")

    if output.exists() and not output.is_dir():
        raise NotADirectoryError(f"output exists and is not a directory: {output}")
    if output.exists() and any(output.iterdir()) and not force:
        raise FileExistsError(
            f"output directory is not empty: {output}; pass --force to overwrite template assets"
        )

    output.mkdir(parents=True, exist_ok=True)
    for name in FILE_ASSETS:
        shutil.copy2(src / name, output / name)
    theme_output = output / THEME_ASSET
    if theme_output.exists():
        if not force:
            raise FileExistsError(f"theme already exists: {theme_output}; pass --force to overwrite")
        shutil.rmtree(theme_output)
    shutil.copytree(
        src / THEME_ASSET,
        theme_output,
        ignore=shutil.ignore_patterns(".DS_Store"),
    )
    print(f"Copied XMU template from {label} to {output.resolve()}")


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--output", required=True, type=Path, help="Destination directory")
    parser.add_argument("--force", action="store_true", help="Overwrite template assets in a nonempty destination")
    args = parser.parse_args(argv)

    try:
        copy_template(args.output.resolve(), args.force)
    except (OSError, shutil.Error, ValueError) as exc:
        print(f"ERROR: {exc}", file=sys.stderr)
        return 1

    return 0


if __name__ == "__main__":
    raise SystemExit(main())
