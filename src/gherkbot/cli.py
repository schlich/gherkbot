"""Command-line interface for gherkbot."""

from pathlib import Path
from typing import Annotated, Optional

import typer
from rich.console import Console
from rich.panel import Panel
from rich.syntax import Syntax

from gherkbot.converter import convert_ast_to_robot
from gherkbot.parser import parse_feature
from gherkbot.synchronizer import sync_directories

app = typer.Typer(
    name="gherkbot",
    help="Convert Gherkin feature files to Robot Framework format.",
    add_completion=False,
)
console = Console()


def version_callback(value: bool) -> None:
    if value:
        from gherkbot import __version__
        console.print(f"gherkbot v{__version__}")
        raise typer.Exit()


@app.callback()
def main(
    version: Annotated[
        Optional[bool],
        typer.Option(
            "--version",
            "-v",
            help="Show version and exit.",
            callback=version_callback,
            is_eager=True,
        ),
    ] = None,
) -> None:
    """Convert Gherkin feature files to Robot Framework format."""
    pass


@app.command("convert")
def convert(
    input_file: Annotated[
        Path, typer.Argument(help="Path to the Gherkin feature file to convert.")
    ],
    output_file: Annotated[
        Optional[Path],
        typer.Option(
            "--output",
            "-o",
            help="Output file path. If not provided, prints to stdout.",
        ),
    ] = None,
    show: Annotated[
        bool,
        typer.Option(
            "--show",
            "-s",
            help="Show the converted output in the console.",
        ),
    ] = False,
) -> None:
    """Convert a Gherkin feature file to Robot Framework format."""
    if not input_file.exists():
        console.print(f"[red]Error:[/red] File '{input_file}' does not exist.")
        raise typer.Exit(1)

    content = input_file.read_text()
    ast = parse_feature(content)

    if ast is None:
        console.print(
            "[red]Error:[/red] Failed to parse the Gherkin feature file."
        )
        raise typer.Exit(1)

    try:
        robot_code = convert_ast_to_robot(ast)
    except Exception as e:
        console.print(f"[red]Error during conversion:[/red] {e}")
        raise typer.Exit(1) from e

    if show or not output_file:
        console.print(
            Panel(
                Syntax(robot_code, "robotframework"),
                title=f"Converted: {input_file.name}",
                border_style="blue",
            )
        )

    if output_file:
        output_file.parent.mkdir(parents=True, exist_ok=True)
        output_file.write_text(robot_code)
        console.print(f"[green]✓[/green] Converted to: {output_file}")


@app.command()
def sync(
    input_dir: Annotated[
        Path, typer.Argument(help="The input directory containing .feature files.")
    ],
    output_dir: Annotated[
        Path,
        typer.Argument(help="The output directory for the generated .robot files."),
    ],
) -> None:
    """Sync .feature files from an input directory to .robot files in an output directory."""
    try:
        sync_directories(input_dir, output_dir)
        console.print("[green]✓[/green] Sync complete.")
    except Exception as e:
        console.print(f"[red]Error during sync:[/red] {e}")
        raise typer.Exit(1) from e


if __name__ == "__main__":
    app()
