from django.contrib.auth import get_user_model
from django.db import models
from django.utils.translation import gettext_lazy as _

from src.apps.common.models import TimedAndUnixIdBaseModel

User = get_user_model()

class UserProfile(TimedAndUnixIdBaseModel):
    user = models.OneToOneField(
        User,
        on_delete=models.CASCADE,
        related_name="profile",
    )
    primary_city = models.ForeignKey(
        "profiles.City",
        null=True,
        blank=True,
        on_delete=models.SET_NULL,
        related_name="primary_users",
    )

    class Meta:
        db_table = "profiles_userprofile"
        verbose_name = _("User Profile")
        verbose_name_plural = _("User Profiles")
        ordering = ["-id"]

    def __str__(self):
        return f"Profile of {self.user.username}"

    def to_entity(self):
        from src.apps.profiles.entities import UserProfileEntity

        return UserProfileEntity(
            id=self.id,
            user_id=self.user.id,
            username=self.user.username,
            email=getattr(self.user, "email", None),
            primary_city=self.primary_city.to_entity() if self.primary_city else None,
            created_at=self.created_at,
            updated_at=self.updated_at,
        )