from django.contrib.auth.models import Group
from django.db.models.signals import post_migrate, post_save
from django.dispatch import receiver

from accounts.models import User
from accounts.roles import ROLE_GROUPS, sync_role_groups


@receiver(post_migrate)
def ensure_role_groups(sender, **kwargs):
    sync_role_groups()


@receiver(post_save, sender=User)
def assign_role_group(sender, instance, **kwargs):
    if instance.is_superuser and instance.role != User.Role.ADMIN:
        User.objects.filter(pk=instance.pk).update(role=User.Role.ADMIN)
        instance.role = User.Role.ADMIN

    group_name = ROLE_GROUPS.get(instance.role)
    if not group_name:
        return
    try:
        target = Group.objects.get(name=group_name)
    except Group.DoesNotExist:
        return
    managed_names = set(ROLE_GROUPS.values())
    instance.groups.remove(*instance.groups.filter(name__in=managed_names))
    instance.groups.add(target)
