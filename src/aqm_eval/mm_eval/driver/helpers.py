"""Helper utilities for the MM evaluation driver."""

import platform
from pathlib import Path

from aqm_eval.logging_aqm_eval import LOGGER, log_it


@log_it
def create_symlinks(
    src_dir: Path,
    dst_dir: Path,
    dst_prefix: str,
    src_dir_template: tuple[str, ...],
    src_fn_template: tuple[str, ...],
) -> None:
    """
    Create symlinks in dst_dir for files in src_dir that match templates.

    Args:
        src_dir: Source directory to search for files
        dst_dir: Destination directory where symlinks will be created
        dst_prefix: String prefix for destination filenames
        src_dir_template: Directory name patterns to match
        src_fn_template: Filename patterns to match
    """
    if not dst_dir.exists():
        LOGGER(f"creating destination directory {dst_dir=}")
        dst_dir.mkdir(exist_ok=False, parents=True)
    # Find directories matching src_dir_template
    ctr = 0
    for dir_pattern in src_dir_template:
        for subdir in src_dir.glob(dir_pattern):
            if not subdir.is_dir():
                continue
            # Find files in matching directories that match src_fn_template
            for fn_pattern in src_fn_template:
                for src_file in subdir.glob(fn_pattern):
                    if not src_file.is_file():
                        continue
                    # Create symlink if it doesn't already exist
                    dst_file = dst_dir / f"{dst_prefix}_{subdir.name}_{src_file.name}"
                    if not dst_file.exists():
                        if platform.system() == "Windows":  # Here for testing
                            dst_file.hardlink_to(src_file)
                        else:
                            dst_file.symlink_to(src_file)
                        ctr += 1
    LOGGER(f"created {ctr} symlinks")
