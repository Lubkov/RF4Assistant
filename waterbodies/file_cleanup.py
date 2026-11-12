"""Delete superseded image files once database changes are committed."""
from django.db import transaction
from django.db.models.signals import post_delete, post_save, pre_save
from django.dispatch import receiver

from .models import Waterbody, WaterbodyMap


def _schedule_cleanup(field_file):
    if not field_file or not field_file.name:
        return
    name = field_file.name
    storage = field_file.storage
    db_alias = field_file.instance._state.db or "default"

    def cleanup():
        # Guard against another row reusing a path (including another model).
        if (Waterbody.objects.using(db_alias).filter(image=name).exists() or
                WaterbodyMap.objects.using(db_alias).filter(image=name).exists()):
            return
        storage.delete(name)

    transaction.on_commit(cleanup, using=db_alias)


@receiver(pre_save, sender=Waterbody, dispatch_uid="rf4_waterbody_old_image")
@receiver(pre_save, sender=WaterbodyMap, dispatch_uid="rf4_waterbody_map_old_image")
def remember_old_image(sender, instance, using, **kwargs):
    instance._rf4_previous_image = None
    if instance.pk is not None:
        previous = sender.objects.using(using).filter(pk=instance.pk).only("image").first()
        if previous is not None:
            instance._rf4_previous_image = previous.image


@receiver(post_save, sender=Waterbody, dispatch_uid="rf4_waterbody_replaced_image")
@receiver(post_save, sender=WaterbodyMap, dispatch_uid="rf4_waterbody_map_replaced_image")
def delete_replaced_image(sender, instance, **kwargs):
    previous = getattr(instance, "_rf4_previous_image", None)
    if previous and previous.name != instance.image.name:
        _schedule_cleanup(previous)
    instance._rf4_previous_image = None


@receiver(post_delete, sender=Waterbody, dispatch_uid="rf4_waterbody_deleted_image")
@receiver(post_delete, sender=WaterbodyMap, dispatch_uid="rf4_waterbody_map_deleted_image")
def delete_removed_image(sender, instance, **kwargs):
    _schedule_cleanup(instance.image)
