import sys
if sys.platform == 'win32':
    try:
        sys.stdout.reconfigure(encoding='utf-8')
        sys.stderr.reconfigure(encoding='utf-8')
    except Exception:
        pass

import asyncio
import logging
import random
from rich.console import Console
from rich.table import Table
from models import Offer
from config import settings
from client import CreatorsAreaClient
from evaluator import Evaluator
from storage import Storage
from notifier import DiscordNotifier

console = Console(legacy_windows=False)
logger = logging.getLogger('bot')

class OfferBot:
    def __init__(self):
        self.client = CreatorsAreaClient()
        self.evaluator = Evaluator()
        self.storage = Storage()
        self.notifier = DiscordNotifier()
        self.running = False

    async def verify_connection(self) -> dict:
        console.print("[bold blue]Vérification de la session CreatorsArea...[/bold blue]")
        try:
            user_info = await self.client.get_me()
            name = user_info.get('name', 'Inconnu')
            discord_id = user_info.get('discord_id', 'N/A')
            console.print(f"[bold green]Connecté avec succès en tant que :[/bold green] [yellow]{name}[/yellow] (Discord ID: {discord_id})")
            return user_info
        except Exception as e:
            console.print(f"[bold red]Erreur de connexion :[/bold red] {e}")
            console.print("[yellow]Assurez-vous que CREATORS_AREA_TOKEN dans votre .env est à jour.[/yellow]")
            raise

    async def scan_once(self, dry_run: bool = False, populate_initial: bool = False):
        try:
            offers = await self.client.get_offers(category='DEVELOPER', volunteer=settings.allow_volunteer)
        except Exception as e:
            console.print(f"[red]Erreur lors de la recuperation des offres : {e}[/red]")
            return 0

        new_count = 0
        for offer in offers:
            if self.storage.is_offer_seen(offer.id):
                continue

            new_count += 1
            eval_res = await self.evaluator.evaluate_with_ai_if_enabled(offer)
            price_display = "Benevole" if (offer.pricing and offer.pricing.volunteer) else (f"{offer.pricing.value} EUR" if offer.pricing else "N/A")
            
            console.print(f"\n[bold cyan][Offre][/bold cyan] {offer.title}")
            console.print(f"Prix: {price_display} | Tags: {', '.join([t.name for t in offer.tags])}")
            
            if eval_res.should_apply:
                console.print(f"[bold green][ELIGIBLE][/bold green] {eval_res.reason}")
                if dry_run or settings.dry_run or populate_initial:
                    mode_label = "[yellow][DRY-RUN] Candidature simulee.[/yellow]" if not populate_initial else "[dim]Offre initiale enregistree.[/dim]"
                    console.print(mode_label)
                    self.storage.save_offer(offer, decision='DRY_RUN' if not populate_initial else 'INITIAL_SEEN', reason=eval_res.reason)
                    if not populate_initial:
                        await self.notifier.notify_application_success(offer, eval_res, dry_run=True)
                else:
                    try:
                        console.print("[blue]Envoi de la candidature...[/blue]")
                        resp = await self.client.apply_offer(offer.slug, settings.portfolio_url)
                        console.print("[bold green]Candidature postulee avec succes.[/bold green]")
                        self.storage.save_offer(offer, decision='APPLIED', reason=eval_res.reason)
                        await self.notifier.notify_application_success(offer, eval_res, dry_run=False)
                    except Exception as e:
                        console.print(f"[bold red]Echec de la candidature :[/bold red] {e}")
                        self.storage.save_offer(offer, decision='ERROR', reason=str(e))
                        await self.notifier.notify_error(f"Echec candidature pour '{offer.title}': {e}")
            else:
                console.print(f"[dim red][IGNORE][/dim red] {eval_res.reason}")
                self.storage.save_offer(offer, decision='REJECTED', reason=eval_res.reason)

        return new_count

    async def run_loop(self, dry_run: bool = False):
        self.running = True
        await self.verify_connection()

        mode_str = "[bold yellow]DRY-RUN (Simulation)[/bold yellow]" if (dry_run or settings.dry_run) else "[bold green]LIVE (Candidatures réelles)[/bold green]"
        console.print(f"\n[bold]Demarrage de la surveillance en mode {mode_str}[/bold]")
        console.print(f"Portfolio URL : [cyan]{settings.portfolio_url}[/cyan]")
        console.print(f"Intervalle de polling : [cyan]{settings.poll_interval_seconds}s[/cyan]")
        console.print(f"Limite d'anciennete : [cyan]{settings.max_offer_age_hours}h[/cyan]")
        console.print(f"Benevolat autorise : [cyan]{'Oui' if settings.allow_volunteer else 'Non'}[/cyan]\n")

        # Premier scan
        console.print("[dim]Verification des offres en cours...[/dim]")
        await self.scan_once(dry_run=dry_run, populate_initial=False)

        console.print("\n[bold green]En attente de nouvelles offres... (Ctrl+C pour arreter)[/bold green]\n")
        while self.running:
            try:
                jitter = random.uniform(-1.0, 1.5)
                delay = max(2.0, settings.poll_interval_seconds + jitter)
                await asyncio.sleep(delay)
                await self.scan_once(dry_run=dry_run, populate_initial=False)
            except asyncio.CancelledError:
                break
            except Exception as e:
                console.print(f"[red]Erreur dans la boucle principale: {e}[/red]")
                await asyncio.sleep(5)

bot = OfferBot()
