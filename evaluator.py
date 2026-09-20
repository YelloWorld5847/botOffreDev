import re
import json
import logging
from datetime import datetime, timezone
import httpx
from typing import List, Tuple, Optional
from models import Offer, EvaluationResult
from config import settings

logger = logging.getLogger('evaluator')

# Mots-clés de jeux/modding incompatibles avec une IA de code pure
STRICT_GAME_CLIENT_BLACKLIST = [
    'fivem', 'gta', 'gta5', 'gta v', 'gmod', "garry's mod", 'garrys mod',
    'roblox', 'roblox studio', 'builder roblox',
    'minecraft', 'fabric', 'spigot', 'paper', 'forge',
    'hytale', 'dayz', 's&box', 'sbox', 'black ops', 'bo3', 'zombies',
    'nanos world', 'unity', 'unreal engine', 'modding', 'moddeur',
    'mappeur', 'mapping', 'level design', 'level designer', 'builder',
    'modèle 3d', 'modele 3d', '3d model', 'blender',
    'restauration ordi', 'reparation ordi', 'reparation pc', 'hardware'
]

PURE_GRAPHIC_BLACKLIST = [
    'logo', 'bannière', 'banniere', 'illustration', 'vfx', 'animation 3d'
]

CODE_WHITELIST = [
    'site web', 'siteweb', 'web', 'dev web', 'developpeur web', 'développeur web',
    'bot discord', 'bot vinted', 'bot telegram', 'bot', 'automatisation', 'automation',
    'scraping', 'scraper', 'crawler', 'saas', 'api', 'webhook', 'uxp',
    'react', 'next.js', 'nextjs', 'vue', 'vuejs', 'angular', 'svelte', 'tailwind',
    'node', 'nodejs', 'express', 'python', 'fastapi', 'flask', 'django',
    'php', 'laravel', 'symfony', 'wordpress', 'woocommerce', 'shopify',
    'javascript', 'typescript', 'extension chrome', 'chrome extension', 'plugin',
    'ia', 'intelligence artificielle', 'llm', 'chatgpt', 'openai', 'gemini',
    'devops', 'docker', 'script', 'base de données', 'sql', 'mysql', 'postgres', 'mongodb'
]

AI_SYSTEM_PROMPT = """Tu es un évaluateur expert pour un développeur freelance qui utilise des agents IA de code autonomes (comme Claude Code, Antigravity, Cursor, Codex).

Ce développeur PEUT réaliser de bout en bout avec l'IA tout ce qui relève du code pur :
- Développement Web complet : Frontend (HTML, CSS, JS, React, Vue, Next.js, Tailwind), Backend (Node.js, Python, PHP, FastAPI, Laravel, Django, Express), CMS (WordPress, WooCommerce, Shopify), SaaS.
- Bots & Automatisation : Bots Discord, Telegram, Vinted, Web Scraping (Playwright, Selenium, BeautifulSoup), scripts d'automatisation, intégrations d'API & Webhooks.
- Extensions de navigateur (Chrome Extensions), Scripts d'outils (UXP, Tampermonkey).
- Bases de données (SQL, NoSQL, migrations), DevOps de base (Docker, scripts shell).

Ce développeur NE PEUT PAS réaliser ce qui demande d'installer et tester dans un jeu vidéo, ou des compétences graphiques/3D manuelles :
- Jeux vidéo & Modding de jeux : FiveM (GTA RP), Garry's Mod (GMod), Roblox Studio, Minecraft (mods, plugins avec gameplay), DayZ, Hytale, Nanos World, moteurs de jeu lourds (Unity, Unreal Engine avec physique/graphismes).
- Graphisme pur / 3D : Modélisation 3D (Blender), Mapping / Level design, Montage vidéo (Premiere/After Effects sans code), Logos, Bannières, Maquettes UI seules.
- Réparation matérielle / PC.

Ta tâche :
Analyser attentivement le TITRE, les TAGS et la DESCRIPTION COMPLÈTE de l'offre pour déterminer si elle peut être réalisée à 100% en code pur assisté par une IA comme Claude Code.

Réponds STRICTEMENT sous format JSON valide :
{
  "should_apply": true | false,
  "reason": "Explication claire et concise en français (1 phrase)",
  "confidence": 0.95
}
"""

class Evaluator:
    def __init__(self):
        self.strict_game_blacklist = [t.lower() for t in STRICT_GAME_CLIENT_BLACKLIST]
        self.graphic_blacklist = [t.lower() for t in PURE_GRAPHIC_BLACKLIST]
        self.code_whitelist = [t.lower() for t in CODE_WHITELIST]

    def check_hard_constraints(self, offer: Offer) -> Optional[EvaluationResult]:
        # 0. Limite d'ancienneté de l'offre
        if offer.createdAt and settings.max_offer_age_hours > 0:
            try:
                dt_str = offer.createdAt.replace('Z', '+00:00')
                created_dt = datetime.fromisoformat(dt_str)
                if created_dt.tzinfo is None:
                    created_dt = created_dt.replace(tzinfo=timezone.utc)
                now_dt = datetime.now(timezone.utc)
                age_hours = (now_dt - created_dt).total_seconds() / 3600.0
                if age_hours > settings.max_offer_age_hours:
                    return EvaluationResult(
                        should_apply=False,
                        reason=f"Offre trop ancienne ({int(age_hours)}h > {settings.max_offer_age_hours}h)",
                        confidence=1.0
                    )
            except Exception as e:
                logger.debug(f"Erreur lors du calcul de l'age de l'offre '{offer.createdAt}': {e}")

        # 1. Catégorie
        if offer.kind and offer.kind.upper() != 'DEVELOPER':
            return EvaluationResult(
                should_apply=False,
                reason=f"Catégorie non éligible ({offer.kind})",
                confidence=1.0
            )

        # 2. Budget / Bénévolat (RÈGLE ABSOLUE)
        if offer.pricing:
            if offer.pricing.volunteer and not settings.allow_volunteer:
                return EvaluationResult(
                    should_apply=False,
                    reason="Offre bénévole ignorée (ALLOW_VOLUNTEER=false)",
                    confidence=1.0
                )
            if not offer.pricing.volunteer and offer.pricing.value > 0 and offer.pricing.value < settings.min_price:
                return EvaluationResult(
                    should_apply=False,
                    reason=f"Budget ({offer.pricing.value}€) inférieur au minimum ({settings.min_price}€)",
                    confidence=1.0
                )
        return None

    def evaluate_rules(self, offer: Offer) -> EvaluationResult:
        # 1. Vérification des contraintes strictes (Catégorie, Bénévolat, Budget)
        hard_reject = self.check_hard_constraints(offer)
        if hard_reject:
            return hard_reject

        # 2. Analyse textuelle (Titre + Tags + Description)
        title_lower = (offer.title or '').lower()
        content_lower = (offer.content or '').lower()
        tags_lower = [t.name.lower() for t in offer.tags if t.name]
        all_text = f"{title_lower} {' '.join(tags_lower)} {content_lower}"

        # Exclusion formelle des jeux vidéo / modding
        matched_games = []
        for term in self.strict_game_blacklist:
            pattern = r'\b' + re.escape(term) + r'\b' if len(term) > 3 else re.escape(term)
            if re.search(pattern, all_text):
                matched_games.append(term)

        if matched_games:
            return EvaluationResult(
                should_apply=False,
                reason=f"Exclu jeu/modding : {', '.join(matched_games)}",
                confidence=0.95,
                rejected_keywords=matched_games
            )

        # Validation code pur
        matched_code = []
        for term in self.code_whitelist:
            pattern = r'\b' + re.escape(term) + r'\b' if len(term) > 3 else re.escape(term)
            if re.search(pattern, all_text):
                matched_code.append(term)

        if matched_code:
            return EvaluationResult(
                should_apply=True,
                reason=f"Code pur / IA ({', '.join(matched_code[:3])})",
                confidence=0.90,
                matched_keywords=matched_code
            )

        # Graphisme sans code
        matched_graphic = []
        for term in self.graphic_blacklist:
            pattern = r'\b' + re.escape(term) + r'\b' if len(term) > 3 else re.escape(term)
            if re.search(pattern, all_text):
                matched_graphic.append(term)

        if matched_graphic:
            return EvaluationResult(
                should_apply=False,
                reason=f"Exclu graphisme sans code : {', '.join(matched_graphic)}",
                confidence=0.90,
                rejected_keywords=matched_graphic
            )

        return EvaluationResult(
            should_apply=True,
            reason="Offre de développement générale",
            confidence=0.75
        )

    def evaluate(self, offer: Offer) -> EvaluationResult:
        return self.evaluate_rules(offer)

    async def evaluate_with_ai_if_enabled(self, offer: Offer) -> EvaluationResult:
        # 1. Vérification stricte des contraintes dures (Bénévolat / Budget / Catégorie)
        hard_reject = self.check_hard_constraints(offer)
        if hard_reject:
            return hard_reject

        # 2. Si aucune IA configurée, on utilise les règles
        if settings.ai_provider in ('none', '') or not settings.ai_api_key:
            return self.evaluate_rules(offer)

        # 3. Si l'IA est activée, on lui soumet l'offre pour une décision fine
        try:
            ai_result = await self._call_ai(offer)
            if ai_result:
                # Re-vérifier les contraintes dures par sécurité
                if self.check_hard_constraints(offer):
                    return self.check_hard_constraints(offer)
                return ai_result
        except Exception as e:
            logger.warning(f"Échec de l'évaluation IA: {e}, repli sur les règles heuristiques.")

        return self.evaluate_rules(offer)

    async def _call_ai(self, offer: Offer) -> Optional[EvaluationResult]:
        tags_str = ', '.join([t.name for t in offer.tags if t.name]) or 'Aucun'
        user_message = f"""Offre à analyser :
- Titre : {offer.title}
- Tags : {tags_str}
- Rémunération : {offer.pricing.value if offer.pricing else 0}€ (Bénévole: {offer.pricing.volunteer if offer.pricing else False})
- Description :
{offer.content or 'Aucune description fournie.'}
"""

        provider = settings.ai_provider.lower()
        api_key = settings.ai_api_key

        # 1. OpenRouter (avec modèles gratuits ou payants)
        if provider == 'openrouter':
            model = settings.ai_model or 'google/gemini-2.0-flash-lite:free'
            url = 'https://openrouter.ai/api/v1/chat/completions'
            headers = {
                'Authorization': f'Bearer {api_key}',
                'Content-Type': 'application/json',
                'HTTP-Referer': 'https://creatorsarea.fr',
                'X-Title': 'CreatorsArea Auto Apply'
            }
            payload = {
                'model': model,
                'messages': [
                    {'role': 'system', 'content': AI_SYSTEM_PROMPT},
                    {'role': 'user', 'content': user_message}
                ],
                'temperature': 0.1,
                'response_format': {'type': 'json_object'}
            }
            async with httpx.AsyncClient(timeout=12.0) as client:
                resp = await client.post(url, json=payload, headers=headers)
                if resp.status_code == 200:
                    data = resp.json()
                    content = data['choices'][0]['message']['content']
                    res = json.loads(content)
                    return EvaluationResult(
                        should_apply=bool(res.get('should_apply', False)),
                        reason=str(res.get('reason', 'Évaluation IA OpenRouter')),
                        confidence=float(res.get('confidence', 0.95))
                    )

        # 2. Google Gemini API (Direct)
        elif provider == 'gemini':
            model = settings.ai_model or 'gemini-2.5-flash'
            url = f"https://generativelanguage.googleapis.com/v1beta/models/{model}:generateContent?key={api_key}"
            payload = {
                'system_instruction': {'parts': [{'text': AI_SYSTEM_PROMPT}]},
                'contents': [{'parts': [{'text': user_message}]}],
                'generationConfig': {
                    'response_mime_type': 'application/json',
                    'temperature': 0.1
                }
            }
            async with httpx.AsyncClient(timeout=12.0) as client:
                resp = await client.post(url, json=payload)
                if resp.status_code == 200:
                    data = resp.json()
                    text_resp = data['candidates'][0]['content']['parts'][0]['text']
                    res = json.loads(text_resp)
                    return EvaluationResult(
                        should_apply=bool(res.get('should_apply', False)),
                        reason=str(res.get('reason', 'Évaluation Gemini IA')),
                        confidence=float(res.get('confidence', 0.95))
                    )

        # 3. Groq API
        elif provider == 'groq':
            model = settings.ai_model or 'llama-3.3-70b-versatile'
            url = 'https://api.groq.com/openai/v1/chat/completions'
            headers = {
                'Authorization': f'Bearer {api_key}',
                'Content-Type': 'application/json'
            }
            payload = {
                'model': model,
                'messages': [
                    {'role': 'system', 'content': AI_SYSTEM_PROMPT},
                    {'role': 'user', 'content': user_message}
                ],
                'temperature': 0.1,
                'response_format': {'type': 'json_object'}
            }
            async with httpx.AsyncClient(timeout=10.0) as client:
                resp = await client.post(url, json=payload, headers=headers)
                if resp.status_code == 200:
                    data = resp.json()
                    content = data['choices'][0]['message']['content']
                    res = json.loads(content)
                    return EvaluationResult(
                        should_apply=bool(res.get('should_apply', False)),
                        reason=str(res.get('reason', 'Évaluation Groq IA')),
                        confidence=float(res.get('confidence', 0.95))
                    )

        # 4. OpenAI / Generic
        elif provider in ('openai', 'custom'):
            model = settings.ai_model or 'gpt-4o-mini'
            url = 'https://api.openai.com/v1/chat/completions'
            headers = {
                'Authorization': f'Bearer {api_key}',
                'Content-Type': 'application/json'
            }
            payload = {
                'model': model,
                'messages': [
                    {'role': 'system', 'content': AI_SYSTEM_PROMPT},
                    {'role': 'user', 'content': user_message}
                ],
                'temperature': 0.1,
                'response_format': {'type': 'json_object'}
            }
            async with httpx.AsyncClient(timeout=12.0) as client:
                resp = await client.post(url, json=payload, headers=headers)
                if resp.status_code == 200:
                    data = resp.json()
                    content = data['choices'][0]['message']['content']
                    res = json.loads(content)
                    return EvaluationResult(
                        should_apply=bool(res.get('should_apply', False)),
                        reason=str(res.get('reason', 'Évaluation OpenAI')),
                        confidence=float(res.get('confidence', 0.95))
                    )

        return None

evaluator = Evaluator()
