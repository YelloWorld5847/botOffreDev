import sys
import os

# Enable UTF-8 for console output on Windows
if sys.platform == 'win32':
    try:
        sys.stdout.reconfigure(encoding='utf-8')
        sys.stderr.reconfigure(encoding='utf-8')
    except Exception:
        pass

import asyncio
import argparse
import json
import base64
from pathlib import Path
from rich.console import Console
from rich.table import Table
from models import Offer
from config import settings
from bot import bot
from evaluator import evaluator
from storage import storage

console = Console(legacy_windows=False)

async def test_evaluator_on_har(use_ai: bool = False):
    har_path = Path('creatorsarea.fr.har')
    if not har_path.exists():
        console.print("[red]Fichier creatorsarea.fr.har introuvable pour le test.[/red]")
        return

    with open(har_path, 'r', encoding='utf-8') as f:
        har = json.load(f)

    all_offers = []
    for entry in har['log']['entries']:
        url = entry['request']['url']
        if 'api/offers' in url:
            resp = entry['response']['content']
            text = resp.get('text', '')
            if resp.get('encoding') == 'base64':
                text = base64.b64decode(text).decode('utf-8', errors='ignore')
            try:
                data = json.loads(text)
                if isinstance(data, dict) and 'results' in data:
                    for item in data['results']:
                        all_offers.append(Offer.model_validate(item))
            except Exception:
                pass

    unique_offers = list({o.id: o for o in all_offers}.values())

    mode_label = f"avec IA ({settings.ai_provider})" if (use_ai and settings.ai_provider != 'none') else "par Règles Heuristiques"
    console.print(f"\n[bold cyan]TEST DU FILTRAGE SUR {len(unique_offers)} OFFRES [{mode_label}][/bold cyan]\n")
    
    table = Table(title=f"Résultats du Filtrage Intelligent ({mode_label})")
    table.add_column("Statut", style="bold", width=14)
    table.add_column("Titre", style="cyan", width=42)
    table.add_column("Prix", justify="right", width=10)
    table.add_column("Tags", style="dim", width=20)
    table.add_column("Raison / Décision", style="italic", width=45)

    accepted = 0
    rejected = 0

    for offer in unique_offers:
        if use_ai:
            res = await evaluator.evaluate_with_ai_if_enabled(offer)
        else:
            res = evaluator.evaluate_rules(offer)

        price_str = "Bénévole" if (offer.pricing and offer.pricing.volunteer) else (f"{offer.pricing.value}€" if offer.pricing else "N/A")
        tags_str = ', '.join([t.name for t in offer.tags])

        if res.should_apply:
            accepted += 1
            table.add_row("[green]POSTULER[/green]", offer.title[:40], price_str, tags_str[:18], f"[green]{res.reason}[/green]")
        else:
            rejected += 1
            table.add_row("[red]IGNORER[/red]", offer.title[:40], price_str, tags_str[:18], f"[red]{res.reason}[/red]")

    console.print(table)
    console.print(f"\n[bold]Bilan : {len(unique_offers)} offres | [green]Postulées : {accepted}[/green] | [red]Ignorées : {rejected}[/red][/bold]\n")

def show_history():
    history = storage.get_history(50)
    if not history:
        console.print("[yellow]Aucune offre enregistrée dans la base de données.[/yellow]")
        return

    table = Table(title="Historique des Offres Traitées")
    table.add_column("Date", style="dim")
    table.add_column("Statut", style="bold")
    table.add_column("Titre", style="cyan")
    table.add_column("Prix", justify="right")
    table.add_column("Raison", style="italic")

    for row in history:
        dec = row['decision']
        if dec == 'APPLIED':
            status = '[green]POSTULÉ[/green]'
        elif dec in ('DRY_RUN', 'INITIAL_SEEN'):
            status = '[yellow]DRY-RUN[/yellow]'
        elif dec == 'REJECTED':
            status = '[dim red]REJETÉ[/dim red]'
        else:
            status = f'[red]{dec}[/red]'

        price_str = "Bénévole" if row['volunteer'] else f"{row['price']}€"
        table.add_row(row['processed_at'][:19], status, row['title'][:35], price_str, row['reason'] or '')

    console.print(table)

def main():
    parser = argparse.ArgumentParser(description="Bot CreatorsArea Auto-Apply")
    parser.add_argument('--dry-run', action='store_true', help="Exécuter en mode simulation sans postuler")
    parser.add_argument('--live', action='store_true', help="Exécuter en mode réel avec candidatures directes")
    parser.add_argument('--test-token', action='store_true', help="Tester la validité du token utilisateur")
    parser.add_argument('--test-eval', action='store_true', help="Tester l'évaluateur sur les offres du fichier HAR")
    parser.add_argument('--use-ai', action='store_true', help="Activer l'appel IA lors du test d'évaluation")
    parser.add_argument('--history', action='store_true', help="Afficher l'historique des candidatures en base")
    args = parser.parse_args()

    if args.test_eval:
        asyncio.run(test_evaluator_on_har(use_ai=args.use_ai))
        return

    if args.history:
        show_history()
        return

    if args.test_token:
        asyncio.run(bot.verify_connection())
        return

    dry_run = True if args.dry_run else (False if args.live else settings.dry_run)
    try:
        asyncio.run(bot.run_loop(dry_run=dry_run))
    except KeyboardInterrupt:
        console.print("\n[yellow]Arrêt du bot par l'utilisateur.[/yellow]")

if __name__ == '__main__':
    main()
