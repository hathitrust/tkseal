"""CLI interface for TKSeal."""

import sys

import click

from tkseal import __version__
from tkseal.diff import Diff
from tkseal.exceptions import TKSealError
from tkseal.secret_state import SecretState


@click.group()
def cli() -> None:
    """TKSeal - Kubernetes sealed secrets management tool."""
    pass


@cli.command()
def version() -> None:
    """Show the current version."""
    click.echo(__version__)


@cli.command()
def ready() -> None:
    """Check that the CLI dependencies are available in your shell."""
    from tkseal.kubectl import KubeCtl
    from tkseal.kubeseal import KubeSeal
    from tkseal.tk import TK

    if KubeCtl.exists():
        click.echo("✅ Kubectl is installed")
    else:
        click.echo("❌ Kubectl is NOT installed")

    if TK.exists():
        click.echo("✅ tk is installed")
    else:
        click.echo("❌ tk is NOT installed")

    if KubeSeal.exists():
        click.echo("✅ Kubeseal is installed")
    else:
        click.echo("❌ Kubeseal is NOT installed")


@cli.command()
@click.argument("path", type=click.Path(exists=True))
def diff(path: str) -> None:
    """Show differences between plain_secrets.json and cluster secrets.

    PATH: Path to Tanka environment directory or .jsonnet file

    This shows what would change in the cluster based on plain_secrets.json
    """
    try:
        # Create SecretState from path
        secret_state = SecretState.from_path(path)

        # Create Diff instance and run comparison
        diff_obj = Diff(secret_state)
        result = diff_obj.plain()

        # Display results
        if result.has_differences:
            click.echo(result.diff_output)
        else:
            click.echo("No differences")

    except TKSealError as e:
        click.echo(f"Error: {e}", err=True)
        sys.exit(1)


def main() -> None:
    """Entry point for the CLI application."""
    cli()


if __name__ == "__main__":
    main()
