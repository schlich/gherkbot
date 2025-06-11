"""Gherkbot - Convert Gherkin feature files to Robot Framework format."""

__version__ = "0.1.0"

def main() -> None:
    """Entry point for the gherkbot CLI."""
    from gherkbot.cli import app
    app()
