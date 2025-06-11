from pathlib import Path
from unittest.mock import patch, mock_open

import pytest
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
    
    with patch("pathlib.Path.exists", return_value=True), \
         patch("pathlib.Path.read_text", return_value=test_content), \
         patch("gherkbot.parser.parse_feature") as mock_parse, \
         patch("gherkbot.converter.convert_ast_to_robot", return_value="*** Test Cases ***\nTest Case\n    Step"):
        
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
    
    with patch("pathlib.Path.exists", return_value=True), \
         patch("pathlib.Path.read_text", return_value=test_content), \
         patch("gherkbot.parser.parse_feature") as mock_parse, \
         patch("gherkbot.converter.convert_ast_to_robot", return_value="*** Test Cases ***\nTest Case\n    Step"):
        
        mock_parse.return_value = {"feature": {"name": "Test Feature"}}
        
        result = runner.invoke(app, ["convert", "test.feature", "-o", str(output_file)])
        
        assert result.exit_code == 0
        assert output_file.exists()
        assert "Converted to:" in result.stdout


def test_convert_file_not_found():
    with patch("pathlib.Path.exists", return_value=False):
        result = runner.invoke(app, ["convert", "nonexistent.feature"])
        assert result.exit_code == 1
        assert "does not exist" in result.stdout


def test_convert_parse_error():
    with patch("pathlib.Path.exists", return_value=True), \
         patch("pathlib.Path.read_text", return_value="invalid"):
        
        result = runner.invoke(app, ["convert", "invalid.feature"])
        assert result.exit_code == 1
        assert "Failed to parse" in result.stdout
