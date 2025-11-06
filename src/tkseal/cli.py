"""CLI interface for TKSeal."""

import sys

import click

from tkseal import __version__
from tkseal.diff import Diff
from tkseal.exceptions import TKSealError
from tkseal.pull import Pull
from tkseal.seal import Seal
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
@click.option(
    "--format",
    type=click.Choice(["json", "yaml"], case_sensitive=False),
    default="json",
    help="Output format for secret files (default: json)",
)
def diff(path: str, format: str) -> None:
    """Show differences between plain_secrets file and cluster secrets.

    PATH: Path to Tanka environment directory or .jsonnet file

    This shows what would change in the cluster based on plain_secrets file
    """
    try:
        # Create SecretState from path with specified format
        secret_state = SecretState.from_path(path, format=format)

        # Create a Diff instance and run comparison
        diff_obj = Diff(secret_state)
        result = diff_obj.plain()

        # Display results - Always in JSON format, it is independent of the sealed_secrets format (YAML/JSON)
        if result.has_differences:
            click.echo(result.diff_output)
        else:
            click.echo("No differences")

    except TKSealError as e:
        click.echo(f"Error: {e}", err=True)
        sys.exit(1)


@cli.command()
@click.argument("path", type=click.Path(exists=True))
@click.option(
    "--format",
    type=click.Choice(["json", "yaml"], case_sensitive=False),
    default="json",
    help="Output format for secret files (default: json)",
)
def pull(path: str, format: str) -> None:
    """Pull secrets from the cluster to plain_secrets file.

    PATH: Path to Tanka environment directory or .jsonnet file

    This extracts unencrypted secrets from the Kubernetes cluster
    and saves them to plain_secrets.json or plain_secrets.yaml in the environment directory.
    """
    try:
        # Create SecretState from path with specified format
        secret_state = SecretState.from_path(path, format=format)

        # Create Pull instance and show differences
        pull_obj = Pull(secret_state)
        result = pull_obj.run()

        # Check and warn about forbidden secrets
        forbidden_secrets = secret_state.get_forbidden_secrets()
        if forbidden_secrets:
            click.secho(
                "\nThese secrets are system-managed and will not be included in plain_secrets.json:",
                fg="yellow",
            )
            for secret in forbidden_secrets:
                click.secho(f"  - {secret.name} (type: {secret.type})", fg="yellow")

        # Show informational message
        plain_secrets_file = f"plain_secrets.{format}"
        click.secho(
            f'This shows how "{plain_secrets_file}" would change based on what\'s in the Kubernetes cluster',
            fg="yellow",
        )

        # Create Pull instance and show differences
        pull_obj = Pull(secret_state)
        result = pull_obj.run()

        # Display diff results
        if result.has_differences:
            click.echo(result.diff_output)

            # Confirm before writing
            if click.confirm("Are you sure?"):
                pull_obj.write()
                click.echo(f"Successfully pulled secrets to {plain_secrets_file}")
        else:
            click.echo("No differences")

    except TKSealError as e:
        click.echo(f"Error: {e}", err=True)
        sys.exit(1)


@cli.command()
@click.argument("path", type=click.Path(exists=True))
@click.option(
    "--format",
    type=click.Choice(["json", "yaml"], case_sensitive=False),
    default="json",
    help="Output format for secret files (default: json)",
)
def seal(path: str, format: str) -> None:
    """Seal plain_secrets file to sealed_secrets file.

    PATH: Path to Tanka environment directory or .jsonnet file

    Takes secrets from plain_secrets file, encrypts them using kubeseal,
    and saves the resulting SealedSecret resources to sealed_secrets file.
    """
    try:
        # Create SecretState from path with specified format
        secret_state = SecretState.from_path(path, format=format)

        sealed_secrets_file = f"sealed_secrets.{format}"

        # Show informational message
        # click.secho(
        #    f'This shows what would change in the cluster based on "plain_secrets.{format}"',
        #    fg="yellow",
        # )

        # Show diff to preview changes
        # diff_obj = Diff(secret_state)
        # result = diff_obj.plain()

        # Display diff results
        # if result.has_differences:
        #    click.echo(result.diff_output)

        # Confirm before sealing
        if click.confirm("Are you sure?"):
            seal_obj = Seal(secret_state)
            seal_obj.run()
            click.echo(f"Successfully sealed secrets to {sealed_secrets_file}")
        # else:
        #    click.echo("No differences")

    except TKSealError as e:
        click.echo(f"Error: {e}", err=True)
        sys.exit(1)


def main() -> None:
    """Entry point for the CLI application."""
    cli()


if __name__ == "__main__":
    main()
