"""CLI interface for findata-br."""

from __future__ import annotations

import asyncio
from collections.abc import Coroutine
from datetime import date
from typing import Any

import typer
from rich import print as rprint
from rich.console import Console
from rich.table import Table

from findata import __version__
from findata.banner import render_animated_banner, render_startup_panel
from findata.sources.bcb import focus, ptax, sgs

app = typer.Typer(
    name="findata",
    help="Open-source Brazilian financial data CLI",
    no_args_is_help=True,
    rich_markup_mode="rich",
)

_console = Console()


def _run(coro: Coroutine[Any, Any, Any]) -> Any:
    """Run async function from sync CLI context."""
    return asyncio.run(coro)


def _fmt(val: float | None, spec: str = ".2f") -> str:
    """Format a nullable float, returning '-' when None."""
    return format(val, spec) if val is not None else "-"


def _version_callback(value: bool) -> None:
    if value:
        rprint(f"findata-br [bold]{__version__}[/bold]")
        raise typer.Exit()


@app.callback()
def _root(
    version: bool = typer.Option(
        None, "--version", "-V", callback=_version_callback, is_eager=True,
        help="Show version and exit.",
    ),
) -> None:
    _ = version  # handled by the eager callback above
    """findata-br — Brazilian financial data CLI."""


# ── Banner ─────────────────────────────────────────────────────────

@app.command()
def banner() -> None:
    """Print the animated findata-br banner."""
    render_animated_banner(_console)


# ── BCB commands ───────────────────────────────────────────────────

bcb_app = typer.Typer(help="Banco Central do Brasil data", no_args_is_help=True)
app.add_typer(bcb_app, name="bcb")


@bcb_app.command("series")
def bcb_series() -> None:
    """List all available BCB time series."""
    table = Table(title="BCB Series Catalog")
    table.add_column("Name", style="cyan")
    table.add_column("Code", style="green")
    table.add_column("Description")
    table.add_column("Unit")
    table.add_column("Freq")

    for name, info in sgs.SERIES_CATALOG.items():
        table.add_row(name, str(info["code"]), info["name"], info["unit"], info["freq"])

    rprint(table)


@bcb_app.command("get")
def bcb_get(
    name: str = typer.Argument(help="Series name (selic, ipca, dolar_ptax, etc.)"),
    n: int = typer.Option(10, "--last", "-n", help="Number of recent values"),
) -> None:
    """Get recent values for a BCB time series."""
    try:
        data = _run(sgs.get_series_by_name(name, n))
    except ValueError as exc:
        rprint(f"[red]Error:[/red] {exc}")
        raise typer.Exit(code=1) from exc

    table = Table(title=f"BCB: {name}")
    table.add_column("Date", style="cyan")
    table.add_column("Value", style="green", justify="right")
    for point in data:
        table.add_row(point.data, f"{point.valor:.4f}")
    rprint(table)


@bcb_app.command("ptax")
def bcb_ptax(
    d: str | None = typer.Option(None, "--date", "-d", help="Date (YYYY-MM-DD)"),
) -> None:
    """Get USD/BRL PTAX quote."""
    dt = date.fromisoformat(d) if d else None
    data = _run(ptax.get_ptax_usd(dt))
    if not data:
        rprint("[yellow]No data (weekend/holiday?)[/yellow]")
        return
    for q in data:
        rprint(
            f"[green]Compra:[/green] {q.cotacao_compra:.4f}  "
            f"[green]Venda:[/green] {q.cotacao_venda:.4f}  "
            f"({q.data_hora_cotacao})"
        )


@bcb_app.command("focus")
def bcb_focus(
    indicator: str = typer.Option("IPCA", "--indicator", "-i"),
    top: int = typer.Option(10, "--top", "-n"),
) -> None:
    """Get Focus market expectations (annual)."""
    try:
        data = _run(focus.get_focus_annual(indicator, top))
    except ValueError as exc:
        rprint(f"[red]Error:[/red] {exc}")
        raise typer.Exit(code=1) from exc

    table = Table(title=f"Focus: {indicator} (annual)")
    table.add_column("Date", style="cyan")
    table.add_column("Reference", style="blue")
    table.add_column("Median", style="green", justify="right")
    table.add_column("Mean", justify="right")
    table.add_column("Min", justify="right")
    table.add_column("Max", justify="right")

    for e in data:
        table.add_row(
            e.data, e.data_referencia,
            _fmt(e.mediana), _fmt(e.media), _fmt(e.minimo), _fmt(e.maximo),
        )

    rprint(table)


# ── B3 commands ────────────────────────────────────────────────────

b3_app = typer.Typer(help="B3 stock exchange data (requires [b3] extra)", no_args_is_help=True)
app.add_typer(b3_app, name="b3")


@b3_app.command("quote")
def b3_quote(
    ticker: str = typer.Argument(help="B3 ticker (e.g., PETR4, VALE3)"),
) -> None:
    """Get current stock quote."""
    from findata.sources.b3 import quotes

    q = _run(quotes.get_quote(ticker))
    rprint(f"[bold]{q.ticker}[/bold] — {q.nome or 'N/A'}")
    if q.preco is not None:
        rprint(f"  [green]Preco:[/green] R$ {q.preco:.2f}")
    if q.variacao_dia is not None:
        rprint(f"  [green]Variacao:[/green] {q.variacao_dia:+.2f}%")
    if q.abertura is not None:
        rprint(f"  Abertura: {q.abertura:.2f}")
    if q.volume is not None:
        rprint(f"  Volume: {q.volume:,}")
    if q.setor:
        rprint(f"  Setor: {q.setor}")


@b3_app.command("history")
def b3_history(
    ticker: str = typer.Argument(help="B3 ticker"),
    period: str = typer.Option("1mo", "--period", "-p"),
) -> None:
    """Get stock price history."""
    from findata.sources.b3 import quotes

    data = _run(quotes.get_history(ticker, period))
    table = Table(title=f"{ticker.upper()} — {period}")
    table.add_column("Date", style="cyan")
    table.add_column("Open", justify="right")
    table.add_column("High", justify="right", style="green")
    table.add_column("Low", justify="right", style="red")
    table.add_column("Close", justify="right", style="bold")
    table.add_column("Volume", justify="right")

    for p in data:
        table.add_row(
            p.date, f"{p.open:.2f}", f"{p.high:.2f}",
            f"{p.low:.2f}", f"{p.close:.2f}", f"{p.volume:,}",
        )

    rprint(table)


# ── Tesouro commands ───────────────────────────────────────────────

tesouro_app = typer.Typer(help="Tesouro Direto treasury bonds", no_args_is_help=True)
app.add_typer(tesouro_app, name="tesouro")


@tesouro_app.command("search")
def tesouro_search(
    query: str = typer.Argument(help="Search query (e.g., 'IPCA+', 'Selic')"),
) -> None:
    """Search available treasury bonds."""
    from findata.sources.tesouro import search_bonds

    titles = _run(search_bonds(query))
    if not titles:
        rprint("[yellow]No bonds matched.[/yellow]")
        return
    for t in titles:
        rprint(f"  {t}")


@tesouro_app.command("history")
def tesouro_history(
    titulo: str = typer.Argument(help="Bond name"),
    n: int = typer.Option(20, "--last", "-n"),
) -> None:
    """Get price/rate history for a treasury bond."""
    from findata.sources.tesouro import get_bond_history

    data = _run(get_bond_history(titulo))
    if not data:
        rprint(f"[yellow]No history for '{titulo}'.[/yellow]")
        return
    table = Table(title=titulo)
    table.add_column("Date", style="cyan")
    table.add_column("Buy Rate %", style="green", justify="right")
    table.add_column("Sell Rate %", justify="right")
    table.add_column("Buy PU R$", style="green", justify="right")
    table.add_column("Sell PU R$", justify="right")

    for b in data[-n:]:
        table.add_row(
            b.dt_base,
            _fmt(b.taxa_compra, ".4f"), _fmt(b.taxa_venda, ".4f"),
            _fmt(b.pu_compra), _fmt(b.pu_venda),
        )

    rprint(table)


# ── IBGE commands ──────────────────────────────────────────────────

ibge_app = typer.Typer(help="IBGE economic indicators", no_args_is_help=True)
app.add_typer(ibge_app, name="ibge")


@ibge_app.command("ipca")
def ibge_ipca(
    periods: int = typer.Option(6, "--periods", "-n"),
) -> None:
    """Get IPCA breakdown by major groups."""
    from findata.sources.ibge import get_ipca_breakdown

    data = _run(get_ipca_breakdown(periods))
    table = Table(title="IPCA Breakdown by Group")
    table.add_column("Period", style="cyan")
    table.add_column("Group")
    table.add_column("Value %", style="green", justify="right")

    for d in data:
        table.add_row(d.periodo, d.classificacao or "Geral", _fmt(d.valor))

    rprint(table)


# ── CVM commands ───────────────────────────────────────────────────

cvm_app = typer.Typer(help="CVM — companies and funds", no_args_is_help=True)
app.add_typer(cvm_app, name="cvm")


@cvm_app.command("search")
def cvm_search(
    query: str = typer.Argument(help="Company name to search"),
    only_active: bool = typer.Option(True, "--active/--all"),
) -> None:
    """Search CVM-registered companies."""
    from findata.sources.cvm import search_company

    results = _run(search_company(query, only_active))
    if not results:
        rprint("[yellow]No companies matched.[/yellow]")
        return
    table = Table(title=f"CVM companies matching '{query}'")
    table.add_column("CNPJ", style="cyan")
    table.add_column("Name")
    table.add_column("Situação", style="green")
    table.add_column("Setor")
    for c in results[:50]:
        table.add_row(c.cnpj, c.nome_comercial or c.nome_social, c.situacao, c.setor)
    rprint(table)
    if len(results) > 50:
        rprint(f"[dim](showing 50 of {len(results)} — refine your query)[/dim]")


# ── Serve command ──────────────────────────────────────────────────


@app.command()
def serve(
    host: str = typer.Option("0.0.0.0", help="Host to bind"),
    port: int = typer.Option(8000, help="Port to bind"),
    reload: bool = typer.Option(False, help="Enable hot reload"),
    no_banner: bool = typer.Option(False, "--no-banner", help="Skip the animated banner"),
) -> None:
    """Start the API + MCP server."""
    import uvicorn

    if not no_banner:
        render_animated_banner(_console)
    _console.print(render_startup_panel(host, port))
    uvicorn.run("findata.api.app:app", host=host, port=port, reload=reload)


if __name__ == "__main__":
    app()
