from pathlib import Path

from gherkbot.converter import convert_ast_to_robot
from gherkbot.parser import parse_feature


def _get_relevant_files(base_dir: Path, extension: str) -> list[Path]:
    """Recursively finds all files with a given extension in a directory."""
    return list(base_dir.rglob(f"*{extension}"))


def sync_directories(input_dir: Path, output_dir: Path) -> None:
    """Synchronizes a directory of .feature files to a directory of .robot files."""
    # console.log(f"Starting sync from '{input_dir}' to '{output_dir}'...")

    source_files = _get_relevant_files(input_dir, ".feature")
    dest_files = _get_relevant_files(output_dir, ".robot")

    source_map = {p.relative_to(input_dir).with_suffix(".robot"): p for p in source_files}
    dest_map = {p.relative_to(output_dir): p for p in dest_files}

    source_rel_paths = set(source_map.keys())
    dest_rel_paths = set(dest_map.keys())

    # 1. Create new files
    paths_to_create = source_rel_paths - dest_rel_paths
    for rel_path in paths_to_create:
        source_file = source_map[rel_path]
        dest_file = output_dir / rel_path
        dest_file.parent.mkdir(parents=True, exist_ok=True)
        content = source_file.read_text()
        ast = parse_feature(content)
        if ast:
            robot_content = convert_ast_to_robot(ast)
            dest_file.write_text(robot_content)
            # console.log(f"Created: {dest_file}")

    # 2. Delete old files
    paths_to_delete = dest_rel_paths - source_rel_paths
    for rel_path in paths_to_delete:
        dest_file = dest_map[rel_path]
        dest_file.unlink()
        # console.log(f"Deleted: {dest_file}")
        # Clean up empty parent directories
        try:
            dest_file.parent.rmdir()
            # console.log(f"Removed empty directory: {dest_file.parent}")
        except OSError:
            pass  # Directory is not empty

    # 3. Update existing files
    paths_to_update = source_rel_paths.intersection(dest_rel_paths)
    for rel_path in paths_to_update:
        source_file = source_map[rel_path]
        dest_file = dest_map[rel_path]

        if source_file.stat().st_mtime > dest_file.stat().st_mtime:
            content = source_file.read_text()
            ast = parse_feature(content)
            if ast:
                robot_content = convert_ast_to_robot(ast)
                dest_file.write_text(robot_content)
                # console.log(f"Updated: {dest_file}")
