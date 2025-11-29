import subprocess
import time
from textual.app import App, ComposeResult
from textual.widgets import Header, Footer, DataTable, Static, Button
from textual.containers import Vertical, Horizontal
from textual.binding import Binding
from app_data_parser import get_upgradable_packages, Package 
from typing import List, Optional
from update_checker import check_for_updates
from config_loader import load_config, get_api_url

class TerminalPackageStore(App[None]):
    
    CSS_PATH = "package_store.css"
    
    packages: List[Package] = []
    selected_package: Optional[Package] = None
    last_update_check: float = 0.0
    
    BINDINGS = [
        Binding("q", "quit", "Quit", show=True),
    ]

    def __init__(self):
        super().__init__()
        # Load configuration from config.json
        self.config = load_config()
        self.TITLE = self.config["app"]["name"]
        self.CURRENT_VERSION = self.config["app"]["version"]
        self.API_URL = get_api_url(self.config)
        self.CHECK_ON_STARTUP = self.config["settings"]["check_updates_on_startup"]
        self.AUTO_REFRESH_INTERVAL = self.config["settings"]["auto_refresh_interval"]

    def compose(self) -> ComposeResult:
        yield Header()
        yield Footer()
        
        with Horizontal():
            with Vertical(id="list-pane"):
                yield Static("Available Upgrades:", classes="section-title")
                
                with Horizontal(id="global-actions"):
                    yield Button("Update All", variant="success", id="btn-update-all")
                    yield Button("Refresh", variant="default", id="btn-refresh")
                
                yield Static("", id="status-messages") 
                    
                yield DataTable(id="app-table")
                
            with Vertical(id="detail-pane"):
                yield Static(
                    "Select a package from the left to view details and perform actions.", 
                    id="detail-info"
                )
                # Add version stats widget and check button in the detail pane
                with Horizontal(id="version-check-container"):
                    yield Static("Checking for app updates...", id="app-update-stats")
                    yield Button("Check Now", variant="default", id="btn-check-version")
                
                with Horizontal(id="action-buttons"):
                    yield Button("Update Selected", variant="primary", id="btn-update")
                    yield Button("Uninstall", variant="error", id="btn-uninstall")

    def on_mount(self) -> None:
        self.load_data()
        # Check for app updates on startup if enabled
        if self.CHECK_ON_STARTUP:
            self.call_after_refresh(self.check_app_updates)
        # Set up auto-refresh timer (checks every week if app stays open)
        self.set_interval(self.AUTO_REFRESH_INTERVAL, self.auto_check_updates)

    def load_data(self) -> None:
        self.packages = get_upgradable_packages()
        table = self.query_one(DataTable)
        
        table.clear(columns=True)
        table.add_columns("Name", "Current Version", "Available Version")
        
        self.query_one("#status-messages", Static).update("")
        
        if self.packages:
            
            self.query_one("#global-actions #btn-update-all").display = True
            self.query_one("#action-buttons").display = True
            self.query_one(".section-title", Static).update("Available Upgrades:")
            self.query_one("#detail-info", Static).update("Select a package from the left to view details and perform actions.")
            
            for pkg in self.packages:
                table.add_row(pkg.name, pkg.version, pkg.available_version, key=pkg.id)
                
            table.cursor_type = "row"
            table.focus()
            
            table.cursor = (0, 0)
            
            self.selected_package = self.packages[0]
            self._update_detail_pane()
        else:
            self.selected_package = None
            self.query_one("#global-actions #btn-update-all").display = False
            self.query_one("#action-buttons").display = False
            
            self.query_one(".section-title", Static).update("[bold blue]No Available Upgrades Found[/bold blue]")
            self.query_one("#detail-info", Static).update("[bold green]Everything is up to date![/bold green]")

    async def check_app_updates(self) -> None:
        """Check for app updates and update the UI accordingly."""
        stats_widget = self.query_one("#app-update-stats", Static)
        
        # Show checking status
        stats_widget.update("[dim]Checking for app updates...[/dim]")
        
        update_result = await check_for_updates(self.CURRENT_VERSION, self.API_URL)
        
        if update_result["status"] == "update_available":
            latest_version = update_result["latest_version"]
            stats_widget.update(f"[yellow]App Update Available:[/yellow] v{latest_version} (current: v{self.CURRENT_VERSION})")
        elif update_result["status"] == "latest":
            stats_widget.update(f"[green]App is up to date:[/green] v{self.CURRENT_VERSION}")
        else:  # Error case
            message = update_result.get("message", "Unknown error")
            stats_widget.update(f"[dim]App Update Check Failed: {message}[/dim]")
        
        # Update last check timestamp
        self.last_update_check = time.time()

    async def auto_check_updates(self) -> None:
        """Automatically check for app updates based on interval."""
        current_time = time.time()
        
        # Check if enough time has passed since last check
        if current_time - self.last_update_check >= self.AUTO_REFRESH_INTERVAL:
            await self.check_app_updates()

    def _update_detail_pane(self) -> None:
        if self.selected_package:
            info_text = (
                f"[b]Name:[/b] {self.selected_package.name}\n"
                f"[b]ID:[/b] {self.selected_package.id}\n"
                f"[b]Installed:[/b] {self.selected_package.version}\n"
                f"[b]Available:[/b] [green]{self.selected_package.available_version}[/green]\n"
                f"[b]Source:[/b] {self.selected_package.source}\n\n"
                "Ready for action."
            )
            self.query_one("#detail-info", Static).update(info_text)

    
    def on_data_table_row_selected(self, event: DataTable.RowSelected) -> None:
        package_id = str(event.row_key.value)
        self.selected_package = next((p for p in self.packages if p.id == package_id), None)
        
        self._update_detail_pane()
            
    
    def action_update_package(self, pkg_id: str) -> None:
        self.query_one("#status-messages", Static).update(
            f"[yellow]Upgrading:[/yellow] [b]{pkg_id}[/b]..."
        )

        try:
            subprocess.run(
                ['winget', 'upgrade', '--id', pkg_id, '--interactive', '--accept-package-agreements'],
                check=True
            )
            self.query_one("#status-messages", Static).update(
                f"[green]SUCCESS:[/green] [b]{pkg_id}[/b] upgraded."
            )
            self.load_data()

        except subprocess.CalledProcessError:
            self.query_one("#status-messages", Static).update(
                f"[red]FAILURE:[/red] [b]{pkg_id}[/b] failed to upgrade."
            )
        except FileNotFoundError:
            self.query_one("#status-messages", Static).update("[red]FATAL ERROR:[/red] 'winget' not found.")
            
    def action_update_all(self) -> None:
        if not self.packages:
            self.query_one("#detail-info", Static).update("[yellow]No packages to update.[/yellow]")
            return

        self.query_one("#detail-info", Static).update(
            "[yellow]Attempting to UPGRADE ALL packages...[/yellow]\n\n"
            "This may take a while and could involve multiple interactive prompts."
        )

        success_count = 0
        failure_count = 0
        total_packages = len(self.packages)
        
        packages_to_update = list(self.packages) 

        for i, pkg in enumerate(packages_to_update):
            pkg_id = pkg.id
            self.query_one("#detail-info", Static).update(
                f"[yellow]({i+1}/{total_packages}) Upgrading:[/yellow] [b]{pkg_id}[/b]...\n"
                "Please follow any prompts that appear in the terminal."
            )
            
            try:
                subprocess.run(
                    ['winget', 'upgrade', '--id', pkg_id, '--interactive', '--accept-package-agreements'], 
                    check=True
                )
                success_count += 1
                self.query_one("#detail-info", Static).update(
                    f"[green]({i+1}/{total_packages}) SUCCESS:[/green] [b]{pkg_id}[/b] upgraded."
                )
            except subprocess.CalledProcessError:
                failure_count += 1
                self.query_one("#detail-info", Static).update(
                    f"[red]({i+1}/{total_packages}) FAILURE:[/red] [b]{pkg_id}[/b] failed to upgrade. Skipping."
                )
            except FileNotFoundError:
                self.query_one("#detail-info", Static).update("[red]FATAL ERROR:[/red] 'winget' command not found. Aborting.")
                return

        final_message = (
            f"[bold cyan]UPGRADE ALL COMPLETE![/bold cyan]\n"
            f"[green]Successful updates:[/green] {success_count}\n"
            f"[red]Failed updates:[/red] {failure_count}\n\n"
            "Refreshing package list..."
        )
        self.query_one("#detail-info", Static).update(final_message)
        self.call_after_refresh(self.load_data)
            
    def action_uninstall_package(self, pkg_id: str) -> None:
        
        self.query_one("#detail-info", Static).update(
            f"[red]Attempting UNINSTALL for:[/red] [b]{pkg_id}[/b]...\n\n"
            "A separate uninstaller window or UAC prompt may appear. Follow the steps there."
        )

        try:
            subprocess.run(
                ['winget', 'uninstall', '--id', pkg_id, '--interactive'], 
                check=True
            )
            
            self.query_one("#detail-info", Static).update(
                f"[green]SUCCESS:[/green] [b]{pkg_id}[/b] uninstalled!\n\n"
                "Refreshing package list..."
            )
            self.call_after_refresh(self.load_data)

        except subprocess.CalledProcessError as e:
            self.query_one("#detail-info", Static).update(
                f"[red]FAILURE during UNINSTALL:[/red] Command failed.\n{e.stderr.strip() if e.stderr else 'Check terminal for details.'}"
            )
        except FileNotFoundError:
            self.query_one("#detail-info", Static).update("[red]FATAL ERROR:[/red] 'winget' command not found.")
            

    def on_button_pressed(self, event: Button.Pressed) -> None:
        button_id = event.button.id

        # Global actions that don't need a selected package
        if button_id == "btn-update-all":
            self.action_update_all()
            return
        elif button_id == "btn-refresh":
            self.query_one("#detail-info", Static).update("[bold blue]Checking for available upgrades...[/bold blue]")
            self.load_data()
            # Also re-check for app updates when refreshing
            self.call_after_refresh(self.check_app_updates)
            return
        elif button_id == "btn-check-version":
            # Manual app version check button - no package selection needed
            self.call_after_refresh(self.check_app_updates)
            return

        # Package-specific actions - require a selected package
        if button_id in ["btn-update", "btn-uninstall"]:
            if self.selected_package is None:
                self.query_one("#detail-info", Static).update("[red]Error: Please select a package first.[/red]")
                return
                
            pkg_id = self.selected_package.id

            if button_id == "btn-update":
                self.action_update_package(pkg_id)
            elif button_id == "btn-uninstall":
                self.action_uninstall_package(pkg_id)

def run_app():
    app = TerminalPackageStore()
    app.run()

if __name__ == "__main__":
    run_app()