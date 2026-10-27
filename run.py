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

async def check_token_cmd():
    from auth import get_token_info
    tok = settings.creators_area_token
    if not tok:
        console.print("[red]Aucun token CREATORS_AREA_TOKEN configure dans .env[/red]")
        return
    info = get_token_info(tok)
    if not info:
        console.print("[yellow]Format de token non reconnu (non JWT). Test de connexion...[/yellow]")
        await bot.verify_connection()
        return

    console.print("\n[bold]Informations sur le token actuel :[/bold]")
    console.print(f"Email : [cyan]{info.get('email')}[/cyan]")
    console.print(f"Discord ID : [cyan]{info.get('discord_id')}[/cyan]")
    console.print(f"Expiration : [cyan]{info.get('exp')}[/cyan]")

    rem = info.get('remaining_hours', 0)
    if info.get('is_expired'):
        console.print(f"[bold red]Statut : EXPIRE (depuis {abs(int(rem))}h)[/bold red]")
    else:
        console.print(f"[bold green]Statut : VALIDE (reste environ {int(rem)}h)[/bold green]")

    if settings.discord_user_token:
        console.print("[dim]Token Discord configure dans .env (auto-refresh actif).[/dim]\n")
    else:
        console.print("[dim]DISCORD_USER_TOKEN non renseigne dans .env.[/dim]\n")

async def set_token_cmd(new_token: str):
    from auth import update_env_variable, restart_pm2_if_available
    from client import CreatorsAreaClient
    tok = new_token.strip().strip('"').strip("'")
    if not tok:
        console.print("[red]Le token fourni est vide.[/red]")
        return

    console.print("[cyan]Verification du nouveau token...[/cyan]")
    test_client = CreatorsAreaClient(token=tok)
    try:
        user_info = await test_client.get_me()
        name = user_info.get('name', 'Inconnu')
        console.print(f"[bold green]Token valide pour :[/bold green] [yellow]{name}[/yellow]")
    except Exception as e:
        console.print(f"[bold red]Token invalide :[/bold red] {e}")
        return

    update_env_variable("CREATORS_AREA_TOKEN", tok)
    settings.creators_area_token = tok
    console.print("[green]Token enregistre dans .env avec succes.[/green]")

    if restart_pm2_if_available():
        console.print("[green]Processus PM2 creators-bot redemarre automatiquement.[/green]")
    else:
        console.print("[dim]Si le bot tourne sous PM2, executez : pm2 restart creators-bot --update-env[/dim]")

async def refresh_token_cmd(custom_discord_token: Optional[str] = None):
    from auth import login_with_discord, restart_pm2_if_available, update_env_variable
    discord_tok = custom_discord_token or settings.discord_user_token
    if not discord_tok:
        console.print("[red]Aucun token Discord fourni. Ajoutez DISCORD_USER_TOKEN dans votre .env ou passez-le en parametre.[/red]")
        return

    console.print("[cyan]Connexion a CreatorsArea via Discord OAuth...[/cyan]")
    ok, res = await login_with_discord(discord_tok)
    if not ok:
        console.print(f"[bold red]Echec de la connexion Discord :[/bold red] {res}")
        return

    if custom_discord_token and custom_discord_token != settings.discord_user_token:
        update_env_variable("DISCORD_USER_TOKEN", custom_discord_token)
        settings.discord_user_token = custom_discord_token

    console.print("[bold green]Nouveau token CreatorsArea genere et enregistre avec succes.[/bold green]")
    if restart_pm2_if_available():
        console.print("[green]Processus PM2 redemarre automatiquement.[/green]")
    else:
        console.print("[dim]Si le bot tourne sous PM2, executez : pm2 restart creators-bot --update-env[/dim]")

def main():
    parser = argparse.ArgumentParser(description="Bot CreatorsArea Auto-Apply")
    parser.add_argument('--dry-run', action='store_true', help="Executer en mode simulation sans postuler")
    parser.add_argument('--live', action='store_true', help="Executer en mode reel avec candidatures directes")
    parser.add_argument('--test-token', action='store_true', help="Tester la validite du token utilisateur")
    parser.add_argument('--test-eval', action='store_true', help="Tester l'evaluateur sur les offres du fichier HAR")
    parser.add_argument('--use-ai', action='store_true', help="Activer l'appel IA lors du test d'evaluation")
    parser.add_argument('--history', action='store_true', help="Afficher l'historique des candidatures en base")
    parser.add_argument('--check-token', action='store_true', help="Afficher les informations et date d'expiration du token")
    parser.add_argument('--set-token', type=str, metavar="TOKEN", help="Definir un nouveau token CreatorsArea et l'enregistrer dans .env")
    parser.add_argument('--refresh-token', nargs='?', const='', metavar="DISCORD_TOKEN", help="Rafraichir le token via Discord OAuth")
    args = parser.parse_args()

    if args.set_token:
        asyncio.run(set_token_cmd(args.set_token))
        return

    if args.refresh_token is not None:
        asyncio.run(refresh_token_cmd(args.refresh_token if args.refresh_token != '' else None))
        return

    if args.check_token:
        asyncio.run(check_token_cmd())
        return

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
        console.print("\n[yellow]Arret du bot par l'utilisateur.[/yellow]")

if __name__ == '__main__':
    main()
