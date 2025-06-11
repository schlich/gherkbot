from pathlib import Path
from unittest.mock import MagicMock

import time
import pytest
from gherkbot.synchronizer import sync_directories, _get_relevant_files

@pytest.fixture
def temp_dir_with_files(tmp_path: Path) -> Path:
    (tmp_path / "file1.feature").touch()
    (tmp_path / "file2.feature").touch()
    (tmp_path / "file3.txt").touch()
    (tmp_path / "subfolder").mkdir()
    (tmp_path / "subfolder" / "file4.feature").touch()
    (tmp_path / "subfolder" / "file5.robot").touch()
    return tmp_path

def test_get_relevant_files_feature(temp_dir_with_files: Path) -> None:
    """Test _get_relevant_files correctly finds .feature files, including in subdirectories."""
    # Act
    feature_files = _get_relevant_files(temp_dir_with_files, ".feature")

    # Assert
    assert len(feature_files) == 3
    expected_files = {
        temp_dir_with_files / "file1.feature",
        temp_dir_with_files / "file2.feature",
        temp_dir_with_files / "subfolder" / "file4.feature",
    }
    assert set(feature_files) == expected_files

def test_get_relevant_files_robot(temp_dir_with_files: Path) -> None:
    """Test _get_relevant_files correctly finds .robot files."""
    # Act
    robot_files = _get_relevant_files(temp_dir_with_files, ".robot")

    # Assert
    assert len(robot_files) == 1
    expected_files = {temp_dir_with_files / "subfolder" / "file5.robot"}
    assert set(robot_files) == expected_files

def test_get_relevant_files_no_match(temp_dir_with_files: Path) -> None:
    """Test _get_relevant_files returns empty list if no files match extension."""
    # Act
    files = _get_relevant_files(temp_dir_with_files, ".nonexistent")

    # Assert
    assert len(files) == 0

def test_get_relevant_files_empty_dir(tmp_path: Path) -> None:
    """Test _get_relevant_files returns empty list for an empty directory."""
    # Act
    files = _get_relevant_files(tmp_path, ".feature")

    # Assert
    assert len(files) == 0

def test_sync_creates_new_robot_file(mocker: MagicMock, tmp_path: Path) -> None:
    """Test that a new .robot file is created if a corresponding .feature file exists."""
    # Arrange
    input_dir = tmp_path / "input"
    output_dir = tmp_path / "output"
    input_dir.mkdir()
    output_dir.mkdir()

    feature_file = input_dir / "test.feature"
    feature_content = "Feature: Test"
    feature_file.write_text(feature_content)

    robot_file = output_dir / "test.robot"
    robot_content = "*** Test Cases ***\nTest"

    mock_parse = mocker.patch("gherkbot.synchronizer.parse_feature", return_value={"feature": {}})
    mock_convert = mocker.patch("gherkbot.synchronizer.convert_ast_to_robot", return_value=robot_content)

    # Act
    sync_directories(input_dir, output_dir)

    # Assert
    assert robot_file.exists()
    assert robot_file.read_text() == robot_content
    mock_parse.assert_called_once_with(feature_content)
    mock_convert.assert_called_once_with({"feature": {}})


def test_sync_creates_new_robot_file_in_subfolder(mocker: MagicMock, tmp_path: Path) -> None:
    """Test that a new .robot file is created in the correct subfolder."""
    # Arrange
    input_dir = tmp_path / "input"
    output_dir = tmp_path / "output"
    input_dir.mkdir()

    feature_dir = input_dir / "sub"
    feature_dir.mkdir()
    feature_file = feature_dir / "test.feature"
    feature_content = "Feature: Test in subfolder"
    feature_file.write_text(feature_content)

    robot_dir = output_dir / "sub"
    robot_file = robot_dir / "test.robot"
    robot_content = "*** Test Cases ***\nTest in subfolder"

    mock_parse = mocker.patch("gherkbot.synchronizer.parse_feature", return_value={"feature": {}})
    mock_convert = mocker.patch("gherkbot.synchronizer.convert_ast_to_robot", return_value=robot_content)

    # Act
    sync_directories(input_dir, output_dir)

    # Assert
    assert robot_dir.is_dir()
    assert robot_file.exists()
    assert robot_file.read_text() == robot_content
    mock_parse.assert_called_once_with(feature_content)
    mock_convert.assert_called_once_with({"feature": {}})


def test_sync_updates_existing_robot_file(mocker: MagicMock, tmp_path: Path) -> None:
    """Test that an existing .robot file is updated if the .feature file is newer."""
    # Arrange
    input_dir = tmp_path / "input"
    output_dir = tmp_path / "output"
    input_dir.mkdir()
    output_dir.mkdir()

    feature_file = input_dir / "test.feature"
    robot_file = output_dir / "test.robot"

    # Create an older version of the robot file
    robot_file.write_text("old content")
    time.sleep(0.01)  # Ensure the feature file has a newer timestamp

    # Create a newer version of the feature file
    feature_content = "Feature: Newer Content"
    feature_file.write_text(feature_content)

    # Ensure feature file is newer (os.utime might be needed for more reliable timing)
    assert feature_file.stat().st_mtime > robot_file.stat().st_mtime

    updated_robot_content = "*** Test Cases ***\nNewer Content"
    mock_parse = mocker.patch("gherkbot.synchronizer.parse_feature", return_value={"feature": {}})
    mock_convert = mocker.patch("gherkbot.synchronizer.convert_ast_to_robot", return_value=updated_robot_content)

    # Act
    sync_directories(input_dir, output_dir)

    # Assert
    assert robot_file.read_text() == updated_robot_content
    mock_parse.assert_called_once_with(feature_content)
    mock_convert.assert_called_once_with({"feature": {}})


def test_sync_deletes_robot_file_when_feature_file_is_removed(mocker: MagicMock, tmp_path: Path) -> None:
    """Test that a .robot file is deleted if the corresponding .feature file is removed."""
    # Arrange
    input_dir = tmp_path / "input"
    output_dir = tmp_path / "output"
    input_dir.mkdir()
    output_dir.mkdir()

    # Initially, both files exist
    feature_file = input_dir / "test_to_delete.feature"
    feature_file.write_text("Feature: To Be Deleted")
    robot_file = output_dir / "test_to_delete.robot"
    robot_file.write_text("Robot content for deletion")

    # Simulate running sync once to establish the output file
    mocker.patch("gherkbot.synchronizer.parse_feature") # No need to parse/convert for this setup
    mocker.patch("gherkbot.synchronizer.convert_ast_to_robot")
    sync_directories(input_dir, output_dir) # This call ensures the robot_files_map is populated correctly
    assert robot_file.exists() # Verify it was "created/updated" initially

    # Now, remove the feature file
    feature_file.unlink()

    # Reset mocks for the actual test call
    mocker.resetall()

    # Act
    sync_directories(input_dir, output_dir)

    # Assert
    assert not robot_file.exists()


def test_sync_deletes_robot_file_and_empty_subfolder(mocker: MagicMock, tmp_path: Path) -> None:
    """Test that a .robot file is deleted and its empty parent subfolder is also removed."""
    # Arrange
    input_dir = tmp_path / "input"
    output_dir = tmp_path / "output"
    input_dir.mkdir()
    output_dir.mkdir()

    input_sub_dir = input_dir / "sub_del"
    input_sub_dir.mkdir()
    output_sub_dir = output_dir / "sub_del"
    # output_sub_dir.mkdir() # Will be created by the first sync if needed

    feature_file = input_sub_dir / "test_in_sub_to_delete.feature"
    feature_file.write_text("Feature: In Subfolder To Be Deleted")
    robot_file = output_sub_dir / "test_in_sub_to_delete.robot"

    # Simulate running sync once to establish the output file and folder
    mocker.patch("gherkbot.synchronizer.parse_feature", return_value={"feature": {}})
    mocker.patch("gherkbot.synchronizer.convert_ast_to_robot", return_value="content")
    sync_directories(input_dir, output_dir)
    assert robot_file.exists()
    assert output_sub_dir.exists()

    # Now, remove the feature file (and its parent directory if it becomes empty)
    feature_file.unlink()
    # input_sub_dir.rmdir() # Not strictly necessary for this test's focus on output dir

    # Reset mocks for the actual test call
    mocker.resetall()

    # Act
    sync_directories(input_dir, output_dir)

    # Assert
    assert not robot_file.exists()
    assert not output_sub_dir.exists() # Check if the subfolder was removed

