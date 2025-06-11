from pathlib import Path
from unittest.mock import patch

from typer.testing import CliRunner

from gherkbot import __version__
from gherkbot.cli import app

runner = CliRunner()


def test_version():
    result = runner.invoke(app, ["--version"])
    assert result.exit_code == 0
    assert f"gherkbot v{__version__}" in result.stdout


def test_convert_show(capsys):
    test_content = """
    Feature: Test Feature
      Scenario: Test Scenario
        Given a test step
    """

    with (
        patch("pathlib.Path.exists", return_value=True),
        patch("pathlib.Path.read_text", return_value=test_content),
        patch("gherkbot.parser.parse_feature") as mock_parse,
        patch(
            "gherkbot.converter.convert_ast_to_robot",
            return_value="*** Test Cases ***\nTest Case\n    Step",
        ),
    ):
        mock_parse.return_value = {"feature": {"name": "Test Feature"}}

        result = runner.invoke(app, ["convert", "test.feature", "--show"])

        assert result.exit_code == 0
        # Check for the panel title and test case content in the rich output
        assert "Converted: test.feature" in result.stdout
        assert "Test Scenario" in result.stdout
        assert "Given a test step" in result.stdout


def test_convert_output_file(tmp_path):
    output_file = tmp_path / "output.robot"
    test_content = """
    Feature: Test Feature
      Scenario: Test Scenario
        Given a test step
    """

    with (
        patch("pathlib.Path.exists", return_value=True),
        patch("pathlib.Path.read_text", return_value=test_content),
        patch("gherkbot.parser.parse_feature") as mock_parse,
        patch(
            "gherkbot.converter.convert_ast_to_robot",
            return_value="*** Test Cases ***\nTest Case\n    Step",
        ),
    ):
        mock_parse.return_value = {"feature": {"name": "Test Feature"}}

        result = runner.invoke(app, ["convert", "test.feature", "-o", str(output_file)])

        assert result.exit_code == 0
        assert output_file.exists()
        assert "Converted to:" in result.stdout


def test_convert_file_not_found() -> None:
    """Test that an error is raised when the input file is not found."""
    result = runner.invoke(app, ["convert", "non_existent_file.feature"])
    assert result.exit_code == 1
    assert "File 'non_existent_file.feature' does not exist." in result.stdout


def test_sync_command_e2e(tmp_path: Path) -> None:
    """End-to-end test for the sync command."""
    # Arrange
    input_dir = tmp_path / "input"
    output_dir = tmp_path / "output"
    input_dir.mkdir()

    # Create a feature file
    feature_file = input_dir / "test.feature"
    feature_file.write_text("Feature: E2E Test")

    # Act
    result = runner.invoke(app, ["sync", str(input_dir), str(output_dir)])

    # Assert
    assert result.exit_code == 0
    assert "Sync complete." in result.stdout
    robot_file = output_dir / "test.robot"
    assert robot_file.exists()
    assert "Feature: E2E Test" in robot_file.read_text()


def test_convert_parse_error():
    with (
        patch("pathlib.Path.exists", return_value=True),
        patch("pathlib.Path.read_text", return_value="invalid"),
    ):
        result = runner.invoke(app, ["convert", "invalid.feature"])
        assert result.exit_code == 1
        assert "Failed to parse" in result.stdout


def test_sync_command_e2e_update(tmp_path: Path) -> None:
    """End-to-end test for the sync command's update functionality."""
    # Arrange
    input_dir = tmp_path / "input"
    output_dir = tmp_path / "output"
    input_dir.mkdir()

    # Create a feature file
    feature_file = input_dir / "test_update.feature"
    feature_file.write_text("Feature: Initial Version")

    # Act 1: Initial sync
    runner.invoke(app, ["sync", str(input_dir), str(output_dir)])
    robot_file = output_dir / "test_update.robot"
    assert "Initial Version" in robot_file.read_text()

    # Arrange 2: Modify the feature file
    import time

    time.sleep(0.1)  # Ensure modification time is different
    feature_file.write_text("Feature: Updated Version")

    # Act 2: Second sync
    result = runner.invoke(app, ["sync", str(input_dir), str(output_dir)])

    # Assert 2
    assert result.exit_code == 0
    assert "Sync complete." in result.stdout
    assert "Updated Version" in robot_file.read_text()


def test_sync_command_e2e_delete(tmp_path: Path) -> None:
    """End-to-end test for the sync command's delete functionality."""
    # Arrange
    input_dir = tmp_path / "input"
    output_dir = tmp_path / "output"
    input_dir.mkdir()

    # Create a feature file
    feature_file = input_dir / "test_delete.feature"
    feature_file.write_text("Feature: To Be Deleted")

    # Act 1: Initial sync
    runner.invoke(app, ["sync", str(input_dir), str(output_dir)])
    robot_file = output_dir / "test_delete.robot"
    assert robot_file.exists()

    # Arrange 2: Delete the feature file
    feature_file.unlink()

    # Act 2: Second sync
    result = runner.invoke(app, ["sync", str(input_dir), str(output_dir)])

    # Assert 2
    assert result.exit_code == 0
    assert "Sync complete." in result.stdout
    assert not robot_file.exists()


def test_sync_command_e2e_with_arguments(tmp_path: Path) -> None:
    """End-to-end test for the sync command with data tables and docstrings."""
    # Arrange
    input_dir = tmp_path / "input"
    output_dir = tmp_path / "output"
    input_dir.mkdir()

    feature_content = '''
Feature: Advanced Gherkin Features

  Scenario: Scenario with Data Table and DocString
    Given the following users are registered:
      | name  | email         |
      | Alice | alice@e.com   |
      | Bob   | bob@e.com     |
    When I send the following message:
      """
      Hello World!
      This is a test.
      """
    Then the system should process the data correctly
'''
    feature_file = input_dir / "advanced.feature"
    feature_file.write_text(feature_content)

    # Act
    result = runner.invoke(app, ["sync", str(input_dir), str(output_dir)])

    # Assert
    assert result.exit_code == 0
    assert "Sync complete." in result.stdout

    robot_file = output_dir / "advanced.robot"
    assert robot_file.exists()

    robot_content = robot_file.read_text()

    # Check for data table
    assert "Given the following users are registered:" in robot_content
    assert "...    | name | email |" in robot_content
    assert "...    | Alice | alice@e.com |" in robot_content
    assert "...    | Bob | bob@e.com |" in robot_content

    # Check for docstring
    assert "When I send the following message:" in robot_content
    assert "...    Hello World!" in robot_content
    assert "...    This is a test." in robot_content

    # Check for the final step
    assert "Then the system should process the data correctly" in robot_content

    # Assert that stub keywords are generated
    assert "*** Keywords ***" in robot_content
    assert "the following users are registered:" in robot_content
    assert "# TODO: implement keyword \"the following users are registered:\"." in robot_content
    assert "I send the following message:" in robot_content
    assert "# TODO: implement keyword \"I send the following message:\"." in robot_content
    assert "the system should process the data correctly" in robot_content
    assert "# TODO: implement keyword \"the system should process the data correctly\"." in robot_content
    assert robot_content.count("Fail    Not Implemented") == 3
