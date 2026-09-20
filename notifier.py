import httpx
import logging
from typing import Optional, List
from datetime import datetime
from models import Offer, EvaluationResult
from config import settings

logger = logging.getLogger('notifier')

class DiscordNotifier:
    def __init__(self, webhook_url: Optional[str] = None):
        self.webhook_url = webhook_url or settings.discord_webhook_url

    async def send_embed(self, title: str, description: str, color: int, fields: Optional[List[dict]] = None, url: Optional[str] = None):
        if not self.webhook_url:
            return

        embed = {
            'title': title,
            'description': description,
            'color': color,
            'fields': fields or [],
            'footer': {'text': 'CreatorsArea Auto-Apply Bot • ' + datetime.now().strftime('%H:%M:%S')},
            'timestamp': datetime.utcnow().isoformat()
        }
        if url:
            embed['url'] = url

        payload = {
            'username': 'CreatorsArea Bot',
            'avatar_url': 'https://creatorsarea.fr/favicon.ico',
            'embeds': [embed]
        }

        try:
            async with httpx.AsyncClient(timeout=5.0) as client:
                await client.post(self.webhook_url, json=payload)
        except Exception as e:
            logger.warning(f"Échec de l'envoi de la notification Discord: {e}")

    async def notify_application_success(self, offer: Offer, eval_res: EvaluationResult, dry_run: bool = False):
        color = 0x3498db if dry_run else 0x2ecc71
        prefix = "[DRY-RUN] " if dry_run else ""
        title = f"{prefix}Candidature envoyee"
        
        price_str = "Benevole" if (offer.pricing and offer.pricing.volunteer) else (f"{offer.pricing.value} EUR" if offer.pricing else "Non specifie")
        tags_str = ', '.join([t.name for t in offer.tags]) if offer.tags else 'Aucun tag'
        offer_url = f"https://creatorsarea.fr/offres/{offer.slug}"

        fields = [
            {'name': 'Titre', 'value': offer.title, 'inline': False},
            {'name': 'Remuneration', 'value': price_str, 'inline': True},
            {'name': 'Tags', 'value': tags_str, 'inline': True},
            {'name': 'Raison', 'value': eval_res.reason, 'inline': False},
            {'name': 'Lien', 'value': f"[Consulter l'offre]({offer_url})", 'inline': False}
        ]

        await self.send_embed(
            title=title,
            description=f"Candidature soumise pour une offre de developpement.",
            color=color,
            fields=fields,
            url=offer_url
        )

    async def notify_error(self, message: str):
        await self.send_embed(
            title="Erreur - Bot CreatorsArea",
            description=message,
            color=0xe74c3c
        )

notifier = DiscordNotifier()
