"""Command-line interface for Track-A-Bet TabHelper."""
import sys
from datetime import datetime
from typing import Optional

import click
from rich.console import Console
from rich.table import Table
from rich.panel import Panel
from rich.text import Text
from rich import box

from . import database as db
from .parser import parse_bet_string, parse_cli_args
from .config import load_config, save_config

console = Console()


@click.group()
def cli():
    """Track-A-Bet TabHelper - Log & track bets from the terminal."""
    db.init_db()


@cli.command()
@click.argument("bet_input", nargs=-1, required=True)
@click.option("--sport", "-s", help="Sport (football, basketball, tennis, etc.)")
@click.option("--selection", "-sel", help="Your selection (e.g. 'Man Utd -1.5')")
@click.option("--odds", "-o", type=float, help="Decimal odds")
@click.option("--stake", "-st", type=float, help="Stake amount")
@click.option("--bookmaker", "-b", help="Bookmaker name")
@click.option("--market", "-m", help="Market type (moneyline, spread, totals, etc.)")
@click.option("--tipster", "-t", help="Tipster tag for this bet")
@click.option("--notes", "-n", help="Additional notes")
def log(bet_input, sport, selection, odds, stake, bookmaker, market, tipster, notes):
    """Log a bet.

    Supports natural language input:
        trackabet log "Man Utd -1.5 @ 2.10 $50"

    Or structured input:
        trackabet log "Arsenal vs Chelsea" -s football -sel "Over 2.5" -o 1.85 -st 100
    """
    full_text = " ".join(bet_input)

    # Try natural language parsing first
    parsed = parse_bet_string(full_text)

    if parsed and parsed["odds"] > 0:
        bet_data = parsed
        # Override with explicit CLI flags
        if sport:
            bet_data["sport"] = sport
        if selection:
            bet_data["selection"] = selection
        if odds:
            bet_data["odds"] = odds
        if stake:
            bet_data["stake"] = stake
        if bookmaker:
            bet_data["bookmaker"] = bookmaker
        if market:
            bet_data["market_type"] = market
        if tipster:
            bet_data["tipster"] = tipster
        if notes:
            bet_data["notes"] = notes
    else:
        # Structured mode - first arg is event name
        bet_data = parse_cli_args(
            full_text,
            sport=sport or "other",
            selection=selection or full_text,
            odds=odds or 0.0,
            stake=stake or 0.0,
            bookmaker=bookmaker or "bet365",
            market_type=market or "moneyline",
            tipster=tipster or "",
            notes=notes or "",
        )

    if not bet_data.get("stake") or bet_data["stake"] <= 0:
        console.print("[red]❌ Error:[/] Stake is required (use --stake or include in natural language)")
        return

    if not bet_data.get("odds") or bet_data["odds"] < 1.0:
        console.print("[red]❌ Error:[/] Valid odds are required (use --odds or include in natural language)")
        return

    bet_id = db.add_bet(bet_data)

    # Build display
    config = load_config()
    payout = bet_data["stake"] * bet_data["odds"]
    profit = payout - bet_data["stake"]

    info = Table.grid(padding=(0, 1))
    info.add_column()
    info.add_column()

    info.add_row("Event:", f"[bold]{bet_data['event']}[/]")
    info.add_row("Selection:", f"[cyan]{bet_data['selection']}[/]")
    info.add_row("Odds:", f"[yellow]{bet_data['odds']:.2f}[/]")
    info.add_row("Stake:", f"${bet_data['stake']:.2f}")
    info.add_row("Payout:", f"${payout:.2f}")
    info.add_row("To Win:", f"[green]${profit:.2f}[/]")
    info.add_row("Bookmaker:", bet_data.get("bookmaker", "bet365").title())
    info.add_row("Sport:", bet_data.get("sport", "other").title())
    if bet_data.get("tipster"):
        info.add_row("Tipster:", f"[magenta]{bet_data['tipster']}[/]")

    panel = Panel(info, title="[bold green]✅ Bet Logged[/]", box=box.ROUNDED)
    console.print(panel)
    console.print(f"  [dim]Bet ID: #{bet_id} | {datetime.now().strftime('%Y-%m-%d %H:%M')}[/]")


@cli.command()
@click.option("--limit", "-l", type=int, default=20, help="Number of bets to show")
@click.option("--sport", "-s", help="Filter by sport")
@click.option("--pending", "-p", is_flag=True, help="Show only pending bets")
def list(limit, sport, pending):
    """Show recent bets."""
    bets = db.get_recent_bets(limit=limit, sport=sport)

    if not bets:
        console.print("[yellow]No bets found.[/]")
        return

    if pending:
        bets = [b for b in bets if b["status"] == "pending"]

    table = Table(box=box.ROUNDED, show_lines=True)
    table.add_column("#", style="dim", width=3)
    table.add_column("Event", style="bold")
    table.add_column("Selection", style="cyan")
    table.add_column("Odds", justify="right")
    table.add_column("Stake", justify="right")
    table.add_column("Status")
    table.add_column("Date", style="dim")

    for bet in bets:
        status_style = {
            "pending": "[yellow]⏳ Pending[/]",
            "won": "[green]✅ Won[/]",
            "lost": "[red]❌ Lost[/]",
            "push": "[blue]↔️ Push[/]",
        }.get(bet["status"], bet["status"])

        table.add_row(
            str(bet["id"]),
            bet["event"][:35] + ("..." if len(bet["event"]) > 35 else ""),
            bet["selection"][:20] + ("..." if len(bet["selection"]) > 20 else ""),
            f"{bet['odds']:.2f}",
            f"${bet['stake']:.2f}",
            status_style,
            bet["created_at"][:10],
        )

    console.print(table)
    console.print(f"\n[dim]Showing {len(bets)} bets[/]")


@cli.command()
def stats():
    """Show betting statistics."""
    stats = db.get_stats()

    if stats["total_bets"] == 0:
        console.print("[yellow]No bets logged yet. Use `trackabet log` to get started![/]")
        return

    win_rate = (stats["wins"] / (stats["wins"] + stats["losses"]) * 100) if (stats["wins"] + stats["losses"]) > 0 else 0
    roi = (stats["total_profit"] / stats["total_staked"] * 100) if stats["total_staked"] > 0 else 0

    grid = Table.grid(padding=(0, 2))
    grid.add_column(style="bold")
    grid.add_column()

    grid.add_row("Total Bets:", f"{stats['total_bets']}")
    grid.add_row("Won:", f"[green]{stats['wins']}[/]")
    grid.add_row("Lost:", f"[red]{stats['losses']}[/]")
    grid.add_row("Pending:", f"[yellow]{stats['pending']}[/]")
    grid.add_row("Win Rate:", f"{win_rate:.1f}%")
    grid.add_row("Total Staked:", f"${stats['total_staked']:.2f}")
    grid.add_row("Total P/L:", f"{'[green]+' if stats['total_profit'] >= 0 else '[red]'}{stats['total_profit']:.2f}[/]")
    grid.add_row("ROI:", f"{'[green]' if roi >= 0 else '[red]'}{roi:+.2f}%[/]")
    grid.add_row("Avg Odds:", f"{stats['avg_odds']:.2f}")
    grid.add_row("Avg Stake:", f"${stats['avg_stake']:.2f}")

    panel = Panel(grid, title="📊 Betting Stats", box=box.ROUNDED)
    console.print(panel)


@cli.command()
def dashboard():
    """Open the web dashboard in browser."""
    import webbrowser
    from .web import start_server
    config = load_config()
    port = config.get("web_port", 6789)
    host = config.get("web_host", "127.0.0.1")

    url = f"http://{host}:{port}"
    console.print(f"[green]Starting web dashboard at {url} ...[/]")
    webbrowser.open(url)
    start_server(host=host, port=port)


@cli.command()
@click.option("--email", prompt="Your Track-A-Bet email", help="Email for Track-A-Bet login")
def login(email):
    """Associate your Track-A-Bet email for sync."""
    db.set_session_email(email)
    console.print(f"[green]✅ Email saved:[/] {email}")
    console.print("[dim]You'll need to be logged into Track-A-Bet in your browser for sync to work.[/]")


@cli.command()
def whoami():
    """Show current session info."""
    email = db.get_session_email()
    if email:
        console.print(f"[green]Logged in as:[/] {email}")
    else:
        console.print("[yellow]No session set. Use `trackabet login` to set your email.[/]")


@cli.command()
def open_trackabet():
    """Open Track-A-Bet dashboard in browser."""
    import webbrowser
    webbrowser.open("https://trackabet.bettingiscool.com")
    console.print("[green]Opened Track-A-Bet in your browser.[/]")


@cli.command("save-cookie")
@click.argument("cookie_value", required=False)
def save_cookie(cookie_value):
    """Save your Track-A-Bet session cookie for API access.

    Get the cookie value from Safari Developer Tools → Network tab →
    click any request to trackabet.bettingiscool.com → Request headers → Cookie.

    The full Cookie header value (session=...; cf_clearance=...) is saved
    and used for future syncs.
    """
    if cookie_value:
        config = load_config()
        config["session_cookie"] = cookie_value
        save_config(config)
        console.print("[green]✅ Session cookie saved![/]")
        console.print("[dim]You can now run `trackabet sync` to pull your bets.[/]")
        return

    console.print("[bold]📋 How to get your cookie:[/]")
    console.print()
    console.print("1. Open Safari and log into [underline]https://trackabet.bettingiscool.com[/]")
    console.print("2. Go to [bold]Develop → Show Web Inspector[/] (or right-click → Inspect)")
    console.print("3. Click the [bold]Network[/] tab")
    console.print("4. Refresh the page")
    console.print("5. Click any request to [bold]trackabet.bettingiscool.com[/]")
    console.print("6. Find the [bold]Cookie[/] header in the Request headers")
    console.print("7. Copy the entire Cookie value and run:")
    console.print()
    console.print("  [bold]trackabet save-cookie \"session=...; cf_clearance=...\"[/]")
    console.print()


@cli.command()
@click.option("--from-file", "-f", type=str, help="Import from a JSON file instead of API")
def sync(from_file):
    """Sync bets from Track-A-Bet into the local database.

    Uses the saved session cookie (set with `trackabet save-cookie`).
    New bets are added, existing ones are skipped.
    """
    from .import_from_trackabet import sync_from_api, import_from_file

    if from_file:
        console.print(f"[blue]Importing from {from_file}...[/]")
        import_from_file(from_file)
    else:
        config = load_config()
        if not config.get("session_cookie"):
            console.print("[red]❌ No session cookie saved.[/]")
            console.print("Run [bold]trackabet save-cookie[/] first to set it up.")
            return
        console.print("[blue]Syncing from Track-A-Bet...[/]")
        sync_from_api()

    # Show updated stats
    stats = db.get_stats()
    win_rate = (stats["wins"] / (stats["wins"] + stats["losses"]) * 100) if (stats["wins"] + stats["losses"]) > 0 else 0
    roi = (stats["total_profit"] / stats["total_staked"] * 100) if stats["total_staked"] > 0 else 0

    console.print(f"\n[bold]📊 Updated stats:[/]")
    console.print(f"  Total: {stats['total_bets']}  |  Won: [green]{stats['wins']}[/]  |  Lost: [red]{stats['losses']}[/]  |  Pending: [yellow]{stats['pending']}[/]")
    console.print(f"  P/L: [green]+${stats['total_profit']:.2f}[/]  |  ROI: [green]+{roi:.2f}%[/]  |  Win Rate: {win_rate:.1f}%")


@cli.command()
@click.argument("bet_id", type=int)
@click.option("--status", type=click.Choice(["won", "lost", "push", "pending"]))
@click.option("--profit", type=float)
@click.option("--clv", type=float)
@click.option("--notes", type=str)
def update(bet_id, status, profit, clv, notes):
    """Update a bet's result."""
    updates = {}
    if status:
        updates["status"] = status
    if profit is not None:
        updates["profit"] = profit
    if clv is not None:
        updates["clv"] = clv
    if notes:
        updates["notes"] = notes

    if not updates:
        console.print("[yellow]No updates specified.[/]")
        return

    db.update_bet(bet_id, **updates)
    console.print(f"[green]✅ Bet #{bet_id} updated.[/]")


@cli.command()
@click.argument("bet_id", type=int)
def show(bet_id):
    """Show details of a specific bet."""
    bet = db.get_bet(bet_id)
    if not bet:
        console.print(f"[red]❌ Bet #{bet_id} not found.[/]")
        return

    info = Table.grid(padding=(0, 1))
    info.add_column(style="bold")
    info.add_column()

    info.add_row("ID:", f"#{bet['id']}")
    info.add_row("Event:", bet["event"])
    info.add_row("Sport:", bet["sport"].title())
    info.add_row("Market:", bet["market_type"].title())
    info.add_row("Selection:", f"[cyan]{bet['selection']}[/]")
    info.add_row("Odds:", f"[yellow]{bet['odds']:.2f}[/]")
    info.add_row("Stake:", f"${bet['stake']:.2f}")
    info.add_row("Payout:", f"${bet['stake'] * bet['odds']:.2f}")
    info.add_row("To Win:", f"[green]${bet['stake'] * bet['odds'] - bet['stake']:.2f}[/]")
    info.add_row("Bookmaker:", bet["bookmaker"].title())
    info.add_row("Status:", {"pending": "⏳ Pending", "won": "✅ Won", "lost": "❌ Lost", "push": "↔️ Push"}.get(bet["status"], bet["status"]))
    if bet["profit"]:
        info.add_row("Profit:", f"{'[green]' if bet['profit'] >= 0 else '[red]'}${bet['profit']:.2f}[/]")
    if bet["clv"]:
        info.add_row("CLV:", f"{bet['clv']*100:+.2f}%")
    if bet["tipster"]:
        info.add_row("Tipster:", f"[magenta]{bet['tipster']}[/]")
    if bet["notes"]:
        info.add_row("Notes:", bet["notes"])
    info.add_row("Created:", bet["created_at"])

    panel = Panel(info, title=f"📋 Bet #{bet['id']}", box=box.ROUNDED)
    console.print(panel)


@cli.command()
@click.option("--port", default=None, type=int, help="Web server port")
@click.option("--host", default=None, type=str, help="Web server host")
def web(port, host):
    """Launch the web dashboard."""
    config = load_config()
    from .web import start_server
    start_server(
        host=host or config.get("web_host", "127.0.0.1"),
        port=port or config.get("web_port", 6789),
    )


if __name__ == "__main__":
    cli()
