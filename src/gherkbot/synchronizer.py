from pathlib import Path

from gherkbot.converter import convert_ast_to_robot
from gherkbot.parser import parse_feature


def _get_relevant_files(base_dir: Path, extension: str) -> list[Path]:
    """Recursively finds all files with a given extension in a directory."""
    return list(base_dir.rglob(f"*{extension}"))


def sync_directories(input_dir: Path, output_dir: Path) -> None:
    """Synchronizes the .robot files in the output directory with the .feature files in the input directory."""
    if not output_dir.exists():
        output_dir.mkdir(parents=True)

    feature_files = _get_relevant_files(input_dir, ".feature")
    robot_files = _get_relevant_files(output_dir, ".robot")

    feature_files_map = {f.relative_to(input_dir): f for f in feature_files}
    robot_files_map = {
        f.relative_to(output_dir).with_suffix(".feature"): f for f in robot_files
    }

    # --- CREATE / UPDATE ---
    for relative_path, feature_file in feature_files_map.items():
        robot_file_path_in_map = robot_files_map.get(relative_path)
        output_robot_file = output_dir / relative_path.with_suffix(".robot")

        if not robot_file_path_in_map:
            # Create
            output_robot_file.parent.mkdir(parents=True, exist_ok=True)
            feature_content = feature_file.read_text()
            ast = parse_feature(feature_content)
            if ast:
                robot_content = convert_ast_to_robot(ast)
                output_robot_file.write_text(robot_content)
        elif feature_file.stat().st_mtime > robot_file_path_in_map.stat().st_mtime:
            # Update
            feature_content = feature_file.read_text()
            ast = parse_feature(feature_content)
            if ast:
                robot_content = convert_ast_to_robot(ast)
                robot_file_path_in_map.write_text(robot_content)

    # --- DELETE ---
    feature_relative_paths = set(feature_files_map.keys())
    robot_relative_paths_as_feature = set(robot_files_map.keys())

    relative_paths_to_delete = robot_relative_paths_as_feature - feature_relative_paths

    for relative_path in relative_paths_to_delete:
        robot_file_to_delete = robot_files_map[relative_path]
        robot_file_to_delete.unlink()
        parent_dir = robot_file_to_delete.parent
        if parent_dir != output_dir and not any(parent_dir.iterdir()):
            parent_dir.rmdir()

