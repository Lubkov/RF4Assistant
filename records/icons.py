"""Enrich missing fish/bait icons using the collector's browser session.

Never fetch RF4 icons with a new HTTP client: the official website may serve a
JavaScript anti-bot page to non-browser requests. DB work stays on the ORM thread.
"""
import io
import json
import logging
import uuid
from datetime import datetime, timedelta, timezone
from pathlib import Path
from urllib.parse import urlparse

from django.core.files.base import ContentFile
from django.db import close_old_connections, connections
from PIL import Image, UnidentifiedImageError

from fish.models import Fish
from .models import Bait, Catch

logger = logging.getLogger(__name__)
MAX_ICON_BYTES = 2 * 1024 * 1024
MAX_ICON_DIMENSION = 2048


def _validate_url(url):
    if not url or not isinstance(url, str):
        return False
    try:
        parsed = urlparse(url)
        return (parsed.scheme == 'https'
                and parsed.hostname in {'rf4game.ru', 'www.rf4game.ru'}
                and parsed.path.startswith('/res/')
                and parsed.username is None and parsed.password is None
                and parsed.port in (None, 443))
    except ValueError:
        return False


def _missing(field):
    if not field:
        return True
    try:
        return not field.storage.exists(field.name)
    except (OSError, ValueError):
        return True


def find_missing_icons(limit=80):
    """Find missing icons fairly: fish cannot starve bait downloads.

    The source page shows an icon only for bait1. We therefore derive bait
    images exclusively from catches where the bait was the first bait.
    """
    close_old_connections()
    result = []
    try:
        sources = (
            ('fish', Fish, 'fish_id', 'fish_icon_url'),
            ('bait', Bait, 'bait1_id', 'bait_icon_url'),
        )
        # Give each entity type a budget on every run. An odd extra slot
        # goes to fish, and any unused capacity is available to the other.
        budgets = {'fish': (limit + 1) // 2, 'bait': limit // 2}
        found = {'fish': [], 'bait': []}
        for kind, model, field, url_field in sources:
            seen = set()
            queryset = (Catch.objects.exclude(**{field: None})
                        .exclude(**{url_field: ''})
                        .order_by(field)
                        .values_list(field, url_field).distinct())
            for entity_id, url in queryset.iterator(chunk_size=500):
                if entity_id in seen or not _validate_url(url):
                    continue
                seen.add(entity_id)
                obj = model.objects.filter(pk=entity_id).first()
                if obj is None or not _missing(obj.image):
                    continue
                found[kind].append({'kind': kind, 'id': entity_id, 'url': url})
                # Stop early when this category can fill the entire limit;
                # unused slots from the other category will be reassigned.
                if len(found[kind]) >= limit:
                    break
        # Guaranteed reserved slots for each category.
        result.extend(found['fish'][:budgets['fish']])
        result.extend(found['bait'][:budgets['bait']])
        remaining = limit - len(result)
        if remaining > 0:
            extras = (found['fish'][budgets['fish']:] +
                      found['bait'][budgets['bait']:])
            result.extend(extras[:remaining])
        return result
    finally:
        connections.close_all()


def save_icon(kind, entity_id, image_bytes):
    """Validate/decode and store WebP on the DB worker thread."""
    close_old_connections()
    try:
        if not image_bytes or len(image_bytes) > MAX_ICON_BYTES:
            raise ValueError('Empty or oversized icon')
        model = {'fish': Fish, 'bait': Bait}.get(kind)
        if model is None:
            raise ValueError('Unknown icon type')
        item = model.objects.get(pk=entity_id)
        if not _missing(item.image):
            return False
        with Image.open(io.BytesIO(image_bytes)) as source:
            source.verify()
        with Image.open(io.BytesIO(image_bytes)) as image:
            if not (1 <= image.width <= MAX_ICON_DIMENSION and 1 <= image.height <= MAX_ICON_DIMENSION):
                raise ValueError('Unexpected image dimensions')
            image.load()
            converted = image.convert('RGBA')
            out = io.BytesIO()
            converted.save(out, format='WEBP', quality=85, method=4)
        item.image.save(f'{uuid.uuid4()}.webp', ContentFile(out.getvalue()), save=True)
        return True
    finally:
        connections.close_all()


# Executed in Chromium's page origin, with its cookies and JS challenge solved.
# Return base64 instead of bytes because Playwright transports JSON serializable data.
_BROWSER_FETCH = """async ({url, maxBytes}) => {
    const parsed = new URL(url);
    if (parsed.protocol !== 'https:' ||
        !['rf4game.ru', 'www.rf4game.ru'].includes(parsed.hostname) ||
        !parsed.pathname.startsWith('/res/')) {
        throw new Error('Unexpected icon URL');
    }
    const response = await fetch(url, {credentials: 'same-origin', redirect: 'error'});
    if (!response.ok) throw new Error(`HTTP ${response.status}`);
    const type = (response.headers.get('content-type') || '').toLowerCase();
    if (!type.startsWith('image/')) throw new Error(`Not an image response (${type || 'unknown'})`);
    const length = Number(response.headers.get('content-length') || '0');
    if (length > maxBytes) throw new Error('Image too large');
    const blob = await response.blob();
    if (blob.size > maxBytes) throw new Error('Image too large');
    const dataUrl = await new Promise((resolve, reject) => {
        const reader = new FileReader();
        reader.onerror = () => reject(new Error('Could not read icon'));
        reader.onload = () => resolve(reader.result);
        reader.readAsDataURL(blob);
    });
    return dataUrl.split(',', 2)[1];
}"""


def fill_missing_icons(page, db_executor, *, limit=80, failure_cache=None):
    """Fetch with Playwright, save via ORM thread; a failed icon never fails a catch."""
    import base64

    cache_path = Path(failure_cache) if failure_cache else None
    cooldown = {}
    if cache_path and cache_path.exists():
        try:
            cooldown = json.loads(cache_path.read_text(encoding='utf-8'))
            if not isinstance(cooldown, dict):
                cooldown = {}
        except (OSError, ValueError):
            cooldown = {}
    now = datetime.now(timezone.utc)
    # Ignore old errors after 24 hours: a temporary challenge may disappear.
    active = {}
    for url, timestamp in cooldown.items():
        try:
            if datetime.fromisoformat(timestamp) > now - timedelta(hours=24):
                active[url] = timestamp
        except (ValueError, TypeError):
            continue

    pending = db_executor.submit(find_missing_icons, limit).result()
    stats = {'fish_downloaded': 0, 'bait_downloaded': 0, 'failed': 0}
    failed_urls = set()
    for entry in pending:
        kind, entity_id, url = entry['kind'], entry['id'], entry['url']
        if url in failed_urls or url in active:
            continue  # Do not repeat a known-bad URL within this collection run.
        try:
            base64_data = page.evaluate(_BROWSER_FETCH, {'url': url, 'maxBytes': MAX_ICON_BYTES})
            data = base64.b64decode(base64_data, validate=True)
            saved = db_executor.submit(save_icon, kind, entity_id, data).result()
            if saved:
                stats[f'{kind}_downloaded'] += 1
        except Exception as exc:
            stats['failed'] += 1
            failed_urls.add(url)
            active[url] = now.isoformat()
            logger.warning('Could not download %s icon %s (%s): %s', kind, entity_id, url, exc)
    if cache_path:
        try:
            cache_path.parent.mkdir(parents=True, exist_ok=True)
            temporary = cache_path.with_suffix('.tmp')
            temporary.write_text(json.dumps(active, ensure_ascii=False, indent=2), encoding='utf-8')
            temporary.replace(cache_path)
        except OSError:
            logger.exception('Could not persist RF4 image retry cooldown')
    return stats
