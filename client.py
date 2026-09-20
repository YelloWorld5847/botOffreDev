import httpx
import logging
from typing import List, Dict, Any, Optional
from models import Offer
from config import settings

logger = logging.getLogger('creators_client')

class CreatorsAreaClient:
    BASE_URL = 'https://creatorsarea.fr'

    def __init__(self, token: Optional[str] = None):
        self.token = token or settings.creators_area_token

    def _get_headers(self, referer: Optional[str] = None) -> Dict[str, str]:
        headers = {
            'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/130.0.0.0 Safari/537.36',
            'Accept': 'application/json, text/plain, */*',
            'Accept-Language': 'fr-FR,fr;q=0.9,en-US;q=0.8,en;q=0.7',
            'Origin': self.BASE_URL,
            'Referer': referer or f"{self.BASE_URL}/offres?category=DEVELOPER",
        }
        if self.token:
            headers['Cookie'] = f"creators_area_token={self.token}"
        return headers

    async def get_me(self) -> Dict[str, Any]:
        url = f"{self.BASE_URL}/api/me"
        async with httpx.AsyncClient(timeout=10.0, follow_redirects=True) as client:
            resp = await client.get(url, headers=self._get_headers())
            if resp.status_code in (200, 304):
                return resp.json()
            elif resp.status_code == 401:
                raise PermissionError("Token d'authentification expiré ou invalide.")
            else:
                resp.raise_for_status()

    async def get_offers(self, category: str = 'DEVELOPER', volunteer: bool = True, page: int = 1) -> List[Offer]:
        url = f"{self.BASE_URL}/api/offers"
        params = {'category': category}
        if volunteer:
            params['volunteer'] = 'true'
        if page > 1:
            params['page'] = str(page)

        async with httpx.AsyncClient(timeout=15.0, follow_redirects=True) as client:
            resp = await client.get(url, params=params, headers=self._get_headers())
            if resp.status_code in (200, 304):
                data = resp.json()
                raw_results = data.get('results', [])
                offers = []
                for item in raw_results:
                    try:
                        offers.append(Offer.model_validate(item))
                    except Exception as e:
                        logger.warning(f"Erreur parsing offre: {e}")
                return offers
            else:
                resp.raise_for_status()

    async def apply_offer(self, slug: str, portfolio_url: Optional[str] = None) -> Dict[str, Any]:
        url = f"{self.BASE_URL}/api/offers/apply"
        target_portfolio = portfolio_url or settings.portfolio_url
        payload = {
            'form': {
                'portfolioUrl': target_portfolio
            },
            'slug': slug
        }
        headers = self._get_headers(referer=f"{self.BASE_URL}/offres/{slug}")
        headers['Content-Type'] = 'application/json'

        async with httpx.AsyncClient(timeout=15.0, follow_redirects=True) as client:
            resp = await client.post(url, json=payload, headers=headers)
            if resp.status_code in (200, 201):
                return resp.json()
            elif resp.status_code == 400:
                error_msg = resp.text
                try:
                    error_json = resp.json()
                    error_msg = error_json.get('message', error_msg)
                except Exception:
                    pass
                raise ValueError(f"Impossible de postuler: {error_msg}")
            elif resp.status_code == 401:
                raise PermissionError("Token expiré lors de la postulation.")
            else:
                resp.raise_for_status()

client_instance = CreatorsAreaClient()
