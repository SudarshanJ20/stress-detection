"""Report the local development environment using only the standard library."""

import argparse
from pathlib import Path
import platform
import shutil
import sys


def main() -> None:
    """Print environment details and disk space for a project directory."""
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument(
        "--project-dir",
        type=Path,
        default=Path(__file__).resolve().parents[2],
        help="directory to check (defaults to the editable source project)",
    )
    args = parser.parse_args()
    project_dir = args.project_dir.expanduser().resolve()
    if not project_dir.is_dir():
        parser.error(f"project directory does not exist: {project_dir}")

    free_bytes = shutil.disk_usage(project_dir).free
    print(f"Python: {platform.python_version()}")
    print(f"Executable: {sys.executable}")
    print(f"Operating system: {platform.system()} {platform.mac_ver()[0] or platform.release()}")
    print(f"Architecture: {platform.machine()}")
    print(f"Virtual environment active: {sys.prefix != sys.base_prefix}")
    print(f"Project directory: {project_dir}")
    print(f"Free disk space: {free_bytes / (1024 ** 3):.2f} GiB ({free_bytes} bytes)")


if __name__ == "__main__":
    main()
