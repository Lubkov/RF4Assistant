"""Wizard options and validated, atomic fishing-spot creation."""
from io import BytesIO
import json
import math

from django.core.exceptions import ValidationError
from django.core.files.base import ContentFile
from django.db import transaction
from django.core.paginator import Paginator
from django.shortcuts import render
from django.db.models import Prefetch

from fish.models import Fish
from django.http import JsonResponse
from django.views.decorators.http import require_GET, require_POST
from django.views.decorators.csrf import ensure_csrf_cookie
from PIL import Image, UnidentifiedImageError

from fish.models import WaterbodyFish
from waterbodies.models import Waterbody
from .models import FishingSpot, FishingSpotCategory, FishingSpotFish, FishingSpotScreenshot

MAX_FILE_BYTES = 10 * 1024 * 1024


@require_GET
def list_spots(request):
    """Public, read-only listing of saved fishing spots."""
    waterbody_id = request.GET.get("waterbody", "")
    fish_id = request.GET.get("fish", "")
    waterbody_id = waterbody_id if waterbody_id.isdecimal() else ""
    fish_id = fish_id if fish_id.isdecimal() else ""

    waterbodies = Waterbody.objects.filter(is_active=True).order_by("sort_order", "level", "name")
    fishes = Fish.objects.filter(is_active=True).order_by("name")
    if waterbody_id:
        fishes = fishes.filter(waterbody_fish__waterbody_id=int(waterbody_id)).distinct()
    if fish_id and not fishes.filter(pk=int(fish_id)).exists():
        fish_id = ""

    spots = FishingSpot.objects.select_related("waterbody")
    if waterbody_id:
        spots = spots.filter(waterbody_id=int(waterbody_id))
    if fish_id:
        spots = spots.filter(fish__pk=int(fish_id))

    spots = spots.prefetch_related(
        Prefetch("screenshots", queryset=FishingSpotScreenshot.objects.order_by("position", "pk")),
        Prefetch("categories", queryset=FishingSpotCategory.objects.order_by("pk")),
        Prefetch("spot_fish", queryset=FishingSpotFish.objects.select_related("fish").order_by("pk")),
    ).order_by("-created_at", "-pk")
    page_obj = Paginator(spots, 20).get_page(request.GET.get("page"))
    for spot in page_obj.object_list:
        images = spot.screenshots.all()
        spot.cover = images[0] if images else None

    return render(request, "fishing_spots/list.html", {
        "page_obj": page_obj,
        "waterbodies_filter": waterbodies,
        "fish_filter": fishes,
        "selected_waterbody": waterbody_id,
        "selected_fish": fish_id,
    })



def bad(message):
    return JsonResponse({"ok": False, "error": str(message)}, status=400)


@require_GET
@ensure_csrf_cookie
def options(request):
    result = []
    for body in Waterbody.objects.filter(is_active=True).select_related("game_map").order_by("level", "name"):
        try:
            game_map = body.game_map
        except Waterbody.game_map.RelatedObjectDoesNotExist:
            game_map = None
        entry = {"id": body.pk, "name": body.name, "level": body.level, "map": None,
                 "fish": list(WaterbodyFish.objects.filter(
                     waterbody=body, fish__is_active=True
                 ).order_by("fish__name").values("fish_id", "fish__name"))}
        if game_map and game_map.image and game_map.has_game_coordinates:
            entry["map"] = {"url": game_map.image.url,
                            "x_min": game_map.game_x_min, "x_max": game_map.game_x_max,
                            "y_min": game_map.game_y_min, "y_max": game_map.game_y_max}
        result.append(entry)
    return JsonResponse({"waterbodies": result})


def parse_list(request, name):
    value = json.loads(request.POST.get(name, "[]"))
    if not isinstance(value, list):
        raise ValueError(f"Неверный формат поля «{name}».")
    return value


def optional_positive(request, name, upper=None):
    value = request.POST.get(name, "").strip()
    if not value:
        return None
    if not value.isascii() or not value.isdecimal():
        raise ValueError(f"Поле «{name}» должно быть положительным целым числом.")
    value = int(value)
    if value < 1 or (upper and value > upper):
        raise ValueError(f"Недопустимое значение поля «{name}».")
    return value


def convert_image(upload):
    if upload.size > MAX_FILE_BYTES:
        raise ValueError("Размер каждого скриншота не должен превышать 10 МБ.")
    if upload.content_type not in ("image/jpeg", "image/png", "image/webp"):
        raise ValueError("Допустимые форматы: PNG, JPG и WebP.")
    try:
        with Image.open(upload) as img:
            if img.format not in ("JPEG", "PNG", "WEBP"):
                raise ValueError("Недопустимый формат изображения.")
            if img.width * img.height > 45_000_000:
                raise ValueError("Слишком большое разрешение изображения.")
            img.load()
            frame = img.convert("RGBA" if "A" in img.getbands() else "RGB")
            buffer = BytesIO()
            frame.save(buffer, "WEBP", quality=84, method=4)
            return ContentFile(buffer.getvalue(), name="screenshot.webp")
    except (OSError, UnidentifiedImageError, Image.DecompressionBombError) as exc:
        raise ValueError("Не удалось прочитать скриншот.") from exc


@require_POST
def create(request):
    try:
        categories = parse_list(request, "categories")
        allowed = set(FishingSpotCategory.Category.values)
        if not 1 <= len(categories) <= 2 or len(set(categories)) != len(categories) or any(
            not isinstance(cat, str) or cat not in allowed for cat in categories
        ):
            raise ValueError("Выберите 1–2 категории.")
        try:
            body = Waterbody.objects.get(pk=int(request.POST.get("waterbody_id", 0)), is_active=True)
        except (Waterbody.DoesNotExist, ValueError, TypeError):
            raise ValueError("Выберите водоём.") from None
        coordinates = request.POST.get("coordinates", "").strip().replace(",", ".").split(":")
        if len(coordinates) != 2 or not all(part.strip() for part in coordinates):
            raise ValueError("Координаты должны быть в формате X:Y.")
        x, y = (float(part.strip()) for part in coordinates)
        if not (math.isfinite(x) and math.isfinite(y)):
            raise ValueError("Некорректные координаты.")
        mixed = request.POST.get("is_mixed_fish") == "true"
        fish_ids = parse_list(request, "fish_ids")
        if any(type(pk) is not int or pk < 1 for pk in fish_ids) or len(set(fish_ids)) != len(fish_ids):
            raise ValueError("Некорректный список рыб.")
        if (mixed and fish_ids) or (not mixed and not 1 <= len(fish_ids) <= 5):
            raise ValueError("Выберите Разнорыбицу отдельно либо 1–5 видов рыб.")
        valid_fish_count = WaterbodyFish.objects.filter(
            waterbody=body, fish_id__in=fish_ids, fish__is_active=True
        ).values("fish_id").distinct().count()
        if valid_fish_count != len(fish_ids):
            raise ValueError("Выбранные рыбы должны обитать в указанном водоёме.")
        uploads = request.FILES.getlist("screenshots")
        if not 4 <= len(uploads) <= 10:
            raise ValueError("Добавьте от 4 до 10 скриншотов.")
        if any(f.size > MAX_FILE_BYTES for f in uploads):
            raise ValueError("Скриншот не должен превышать 10 МБ.")
        spot = FishingSpot(
            waterbody=body, x=x, y=y, clip=optional_positive(request, "clip"),
            depth_cm=optional_positive(request, "depth_cm"),
            retrieve_speed=optional_positive(request, "retrieve_speed", 50),
            is_mixed_fish=mixed, comment=request.POST.get("comment", "").strip(),
        )
        if len(spot.comment) > 20000:
            raise ValueError("Комментарий слишком длинный.")
        spot.full_clean()
        converted = [convert_image(f) for f in uploads]
        saved_images = []
        try:
            with transaction.atomic():
                spot.save()
                FishingSpotCategory.objects.bulk_create([
                    FishingSpotCategory(fishing_spot=spot, category=cat) for cat in categories
                ])
                FishingSpotFish.objects.bulk_create([
                    FishingSpotFish(fishing_spot=spot, fish_id=pk) for pk in fish_ids
                ])
                for index, contents in enumerate(converted, 1):
                    screenshot = FishingSpotScreenshot(fishing_spot=spot, position=index)
                    screenshot.image.save(contents.name, contents, save=False)
                    saved_images.append(screenshot.image.name)
                    screenshot.save()
        except Exception:
            storage = FishingSpotScreenshot._meta.get_field("image").storage
            for filename in saved_images:
                storage.delete(filename)
            raise
        return JsonResponse({"ok": True, "id": spot.pk})
    except (ValueError, TypeError, ValidationError, json.JSONDecodeError) as exc:
        return bad("; ".join(exc.messages) if isinstance(exc, ValidationError) else exc)
