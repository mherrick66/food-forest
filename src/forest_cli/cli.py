"""CLI entry point for forest-cli."""
from __future__ import annotations

import click
from rich.console import Console
from rich.table import Table
from rich import box

from forest_cli.db import (
    get_connection,
    search_suppliers,
    supplier_detail,
    list_categories,
    list_suppliers,
    add_supplier,
)

console = Console()


@click.group()
def main() -> None:
    """Find local Sarasota suppliers for your food forest."""


@main.command()
@click.argument("query")
def search(query: str) -> None:
    """Search suppliers by item name or category (substring, case-insensitive).

    QUERY: word or phrase to search for (e.g. 'wax myrtle', 'mango', 'drip tape')
    """
    conn = get_connection()
    results = search_suppliers(conn, query)

    if not results:
        console.print(f"[yellow]No suppliers found for '[bold]{query}[/bold]'.[/yellow]")
        return

    console.print(f"\n[green bold]Found {len(results)} supplier(s) matching '[italic]{query}[/italic]':[/green bold]\n")

    for row in results:
        detail = supplier_detail(conn, row["id"])
        _print_supplier_card(detail)


@main.command("list-categories")
def list_categories_cmd() -> None:
    """List all available supply categories."""
    conn = get_connection()
    cats = list_categories(conn)
    console.print("\n[bold cyan]Available categories:[/bold cyan]")
    for cat in cats:
        console.print(f"  [green]•[/green] {cat}")
    console.print()


@main.command("list-suppliers")
@click.option("--category", default=None, help="Filter by category name (e.g. plants, irrigation).")
def list_suppliers_cmd(category: str | None) -> None:
    """List all suppliers, optionally filtered by --category."""
    conn = get_connection()
    suppliers = list_suppliers(conn, category=category)

    if not suppliers:
        msg = f"No suppliers found for category '[bold]{category}[/bold]'." if category else "No suppliers found."
        console.print(f"[yellow]{msg}[/yellow]")
        return

    table = Table(title="Sarasota Food Forest Suppliers", box=box.ROUNDED)
    table.add_column("Name", style="bold cyan", no_wrap=False)
    table.add_column("Address", style="dim")
    table.add_column("Phone", style="green")
    table.add_column("Website", style="blue")

    for s in suppliers:
        table.add_row(
            s["name"] or "",
            s["address"] or "",
            s["phone"] or "",
            s["website"] or "",
        )

    console.print()
    console.print(table)
    console.print()


@main.command("add-supplier")
def add_supplier_cmd() -> None:
    """Interactively add a new supplier to the database."""
    console.print("[bold cyan]Add a new supplier[/bold cyan]\n")

    name = click.prompt("Supplier name")
    address = click.prompt("Address", default="")
    phone = click.prompt("Phone", default="")
    website = click.prompt("Website", default="")
    cats_input = click.prompt("Categories (comma-separated, e.g. plants,fruit_trees)")
    items_input = click.prompt("Items carried (comma-separated)")

    categories = [c.strip() for c in cats_input.split(",") if c.strip()]
    items = [i.strip() for i in items_input.split(",") if i.strip()]

    conn = get_connection()
    supplier_id = add_supplier(conn, name, address, phone, website, categories, items)

    console.print(f"\n[green bold]Added '[italic]{name}[/italic]' (id={supplier_id})[/green bold]")


def _print_supplier_card(detail: dict) -> None:
    """Print a Rich-formatted supplier card."""
    panel_content = []
    if detail.get("address"):
        panel_content.append(f"[dim]Address:[/dim]  {detail['address']}")
    if detail.get("phone"):
        panel_content.append(f"[dim]Phone:[/dim]    [green]{detail['phone']}[/green]")
    if detail.get("website"):
        panel_content.append(f"[dim]Website:[/dim]  [blue]{detail['website']}[/blue]")
    if detail.get("categories"):
        panel_content.append(f"[dim]Categories:[/dim] {', '.join(detail['categories'])}")
    if detail.get("items"):
        panel_content.append(f"[dim]Items:[/dim]    {', '.join(detail['items'])}")

    console.rule(f"[bold cyan]{detail['name']}[/bold cyan]")
    for line in panel_content:
        console.print(f"  {line}")
    console.print()
