"""Main CLI entry point for pgdelta."""

import platform
import sys
from pathlib import Path
from typing import Annotated

import typer
from rich.console import Console
from rich.panel import Panel
from rich.progress import Progress, SpinnerColumn, TextColumn
from rich.table import Table

from pgdelta import __version__

console = Console()
app = typer.Typer(
    name="pgdelta",
    help="🐘 PostgreSQL schema differ and DDL generator",
    rich_markup_mode="rich",
    no_args_is_help=True,
)


def version_callback(value: bool) -> None:
    """Print version and exit."""
    if value:
        console.print(
            f"[bold blue]pgdelta[/bold blue] version [green]{__version__}[/green]"
        )
        raise typer.Exit()


@app.callback()
def main(
    version: Annotated[
        bool | None,
        typer.Option(
            "--version",
            callback=version_callback,
            is_eager=True,
            help="Show version and exit",
        ),
    ] = None,
) -> None:
    """🐘 PostgreSQL schema differ and DDL generator."""
    pass


@app.command("diff-headless")
def diff_headless(
    master_sql: Annotated[
        str | None, typer.Option(help="📊 SQL to create the master schema")
    ] = None,
    branch_sql: Annotated[
        str | None, typer.Option(help="🎯 SQL to create the branch schema")
    ] = None,
    initial_sql: Annotated[
        str | None,
        typer.Option(
            "--initial-sql",
            help="⚙️ Optional SQL to run in both databases before comparison",
        ),
    ] = None,
    postgres_image: Annotated[
        str,
        typer.Option(
            "-i", "--postgres-image", help="🐳 PostgreSQL Docker image to use"
        ),
    ] = "postgres:17",
    output: Annotated[
        Path | None,
        typer.Option("-o", "--output", help="📝 Output file (default: stdout)"),
    ] = None,
    verify: Annotated[
        bool,
        typer.Option(
            "--verify/--no-verify", help="✅ Verify generated SQL with roundtrip test"
        ),
    ] = True,
    verbose: Annotated[
        bool, typer.Option("-v", "--verbose", help="📢 Show verbose output")
    ] = False,
) -> None:
    """🐳 Generate diff between schemas using isolated Docker containers."""
    try:
        from sqlalchemy import create_engine, text
        from sqlalchemy.orm import Session
        from testcontainers.postgres import PostgresContainer

        from pgdelta.catalog import extract_catalog
        from pgdelta.changes.dispatcher import generate_sql

        # Handle empty or missing SQL (treat as empty schema)
        master_sql = master_sql or ""
        branch_sql = branch_sql or ""
        initial_sql = initial_sql or ""

        with Progress(
            SpinnerColumn(),
            TextColumn("[progress.description]{task.description}"),
            console=console,
        ) as progress:
            task = progress.add_task("[cyan]Setting up container...", total=None)

            if verbose:
                console.print(
                    f"[blue]📦 Using PostgreSQL image: {postgres_image}[/blue]"
                )
                console.print(
                    "[blue]🐳 Creating temporary PostgreSQL container...[/blue]"
                )

            # Create single PostgreSQL container
            with PostgresContainer(postgres_image) as postgres_container:
                if verbose:
                    console.print("[blue]✅ Container started successfully[/blue]")

                # Get base connection URL
                base_url = postgres_container.get_connection_url()

                # Create master and branch databases
                progress.update(
                    task, description="[cyan]Creating master and branch databases..."
                )

                # CREATE DATABASE cannot run inside a transaction, so use autocommit
                admin_engine = create_engine(base_url, isolation_level="AUTOCOMMIT")

                with admin_engine.connect() as admin_conn:
                    admin_conn.execute(text("CREATE DATABASE pgdelta_master;"))
                    admin_conn.execute(text("CREATE DATABASE pgdelta_branch;"))

                # Create engines for master and branch databases
                # Parse the URL to replace only the database name part
                from urllib.parse import urlparse, urlunparse

                parsed_url = urlparse(base_url)

                # Replace the database name in the path
                master_path = "/pgdelta_master"
                branch_path = "/pgdelta_branch"

                master_parsed = parsed_url._replace(path=master_path)
                branch_parsed = parsed_url._replace(path=branch_path)

                master_url = urlunparse(master_parsed)
                branch_url = urlunparse(branch_parsed)

                master_engine = create_engine(master_url)
                branch_engine = create_engine(branch_url)

                with (
                    Session(master_engine) as master_session,
                    Session(branch_engine) as branch_session,
                ):
                    if verbose and initial_sql:
                        progress.update(
                            task, description="[cyan]Running initial SQL..."
                        )

                    # Run initial SQL if provided
                    if initial_sql.strip():
                        master_session.execute(text(initial_sql))
                        branch_session.execute(text(initial_sql))

                    progress.update(
                        task, description="[cyan]Executing master schema SQL..."
                    )

                    # Execute master SQL (if not empty)
                    if master_sql.strip():
                        master_session.execute(text(master_sql))
                    master_session.commit()

                    progress.update(
                        task, description="[cyan]Executing branch schema SQL..."
                    )

                    # Execute branch SQL (if not empty)
                    if branch_sql.strip():
                        branch_session.execute(text(branch_sql))
                    branch_session.commit()

                    progress.update(
                        task, description="[cyan]Extracting schema catalogs..."
                    )

                    # Extract catalogs
                    master_catalog = extract_catalog(master_session)
                    branch_catalog = extract_catalog(branch_session)

                    # Generate changes to transform master to match branch
                    changes = master_catalog.diff(branch_catalog)

                    if not changes:
                        progress.stop()
                        console.print(
                            Panel(
                                "[green]✅ No changes detected between schemas[/green]",
                                title="Result",
                            )
                        )
                        return

                    progress.update(
                        task, description="[cyan]Generating SQL statements..."
                    )

                    # Generate SQL statements
                    sql_statements = []
                    for change in changes:
                        sql = generate_sql(change)
                        sql_statements.append(sql)

                    # Output SQL statements
                    if output:
                        with open(output, "w") as f:
                            for sql in sql_statements:
                                f.write(sql + "\n")
                    else:
                        for sql in sql_statements:
                            console.print(sql)

                    # Verify the generated SQL if requested
                    verification_passed = False
                    if verify:
                        progress.update(
                            task, description="[cyan]Verifying generated SQL..."
                        )

                        try:
                            # Apply the generated SQL to master database
                            for sql in sql_statements:
                                master_session.execute(text(sql))
                            master_session.commit()

                            # Extract final catalog and compare
                            final_catalog = extract_catalog(master_session)
                            verification_passed = branch_catalog.semantically_equals(
                                final_catalog
                            )

                            if verification_passed:
                                console.print(
                                    "[green]✅ Verification passed - generated SQL is correct[/green]"
                                )
                            else:
                                console.print(
                                    "[yellow]⚠️ Verification failed - generated SQL may not be complete[/yellow]"
                                )

                        except Exception as e:
                            console.print(
                                f"[yellow]⚠️ Verification failed with error: {e}[/yellow]"
                            )
                            verification_passed = False

                    progress.stop()
                    console.print(
                        f"[green]✅ Generated {len(sql_statements)} SQL statements[/green]"
                    )

    except ImportError as err:
        console.print(
            "[red]❌ Container diff dependencies not installed. Install with: pip install pgdelta[dev][/red]"
        )
        raise typer.Exit(1) from err
    except Exception as e:
        console.print(f"[red]❌ Error: {e}[/red]")
        if verbose:
            import traceback

            console.print(f"[red]{traceback.format_exc()}[/red]")
        raise typer.Exit(1) from e


@app.command()
def info() -> None:
    """Show pgdelta and system information."""

    def format_bytes(bytes_value: int) -> str:
        """Format bytes to human readable format."""
        value: float = float(bytes_value)
        for unit in ["B", "KB", "MB", "GB", "TB"]:
            if value < 1024.0:
                return f"{value:.1f} {unit}"
            value /= 1024.0
        return f"{value:.1f} PB"

    # Application info table
    app_table = Table(
        title="🐘 pgdelta Information", show_header=True, header_style="bold magenta"
    )
    app_table.add_column("Property", style="cyan", no_wrap=True)
    app_table.add_column("Value", style="green")

    app_table.add_row("Version", __version__)
    app_table.add_row(
        "Python Version",
        f"{sys.version.split()[0]} ({platform.python_implementation()})",
    )
    app_table.add_row("Python Executable", sys.executable)

    console.print(app_table)
    console.print()

    # System info table
    system_table = Table(
        title="💻 System Information", show_header=True, header_style="bold blue"
    )
    system_table.add_column("Property", style="cyan", no_wrap=True)
    system_table.add_column("Value", style="green")

    # Operating System
    system_table.add_row(
        "Operating System", f"{platform.system()} {platform.release()}"
    )
    system_table.add_row("OS Version", platform.version())
    system_table.add_row("Machine Type", platform.machine())
    system_table.add_row("Architecture", platform.architecture()[0])
    system_table.add_row("Processor", platform.processor() or "Unknown")
    system_table.add_row("Platform", platform.platform())
    console.print(system_table)


if __name__ == "__main__":
    app()
