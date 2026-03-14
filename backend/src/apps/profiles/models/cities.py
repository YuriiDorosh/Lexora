from django.contrib.auth import get_user_model
from django.db import models
from django.utils.translation import gettext_lazy as _

from src.apps.common.models import TimedAndUnixIdBaseModel

User = get_user_model()


class City(TimedAndUnixIdBaseModel):
    name = models.CharField(max_length=255)
    slug = models.SlugField(unique=True)
    region = models.CharField(max_length=255, blank=True)
    official_schedule_url = models.URLField(blank=True)
    is_active = models.BooleanField(default=True)

    class Meta:
        db_table = "profiles_city"
        verbose_name = _("City")
        verbose_name_plural = _("Cities")
        ordering = ["-id"]

    def __str__(self):
        return f"{self.name} - ({self.region})"

    def to_entity(self):
        from src.apps.profiles.entities import CityEntity

        return CityEntity(
            id=self.id,
            name=self.name,
            slug=self.slug,
            region=self.region,
            official_schedule_url=self.official_schedule_url,
            is_active=self.is_active,
            created_at=self.created_at,
            updated_at=self.updated_at,
        )


class Place(TimedAndUnixIdBaseModel):
    owner = models.ForeignKey(
        User,
        on_delete=models.CASCADE,
        related_name="owned_places",
    )
    city = models.ForeignKey(
        "profiles.City",
        on_delete=models.CASCADE,
        related_name="places",
    )
    title = models.CharField(max_length=255)
    address = models.CharField(max_length=500, blank=True, null=True)
    latitude = models.DecimalField(max_digits=9, decimal_places=6)
    longitude = models.DecimalField(max_digits=9, decimal_places=6)

    class Meta:
        db_table = "profiles_place"
        verbose_name = _("Place")
        verbose_name_plural = _("Places")
        ordering = ["-id"]

    def __str__(self):
        return f"{self.title} - {self.city}"

    def to_simple_entity(self):
        from src.apps.profiles.entities import PlaceSimpleEntity

        return PlaceSimpleEntity(
            id=self.id,
            owner_id=self.owner.id,
            owner_name=self.owner.username,
            city_id=self.city.id,
            city_name=self.city.name,
            title=self.title,
            address=self.address,
            latitude=float(self.latitude) if self.latitude is not None else None,
            longitude=float(self.longitude) if self.longitude is not None else None,
            created_at=self.created_at,
            updated_at=self.updated_at,
        )

    def to_entity(self):
        from src.apps.profiles.entities import PlaceEntity

        return PlaceEntity(
            id=self.id,
            owner_id=self.owner.id,
            owner_name=self.owner.username,
            city=self.city.to_entity(),
            title=self.title,
            address=self.address,
            latitude=float(self.latitude) if self.latitude is not None else None,
            longitude=float(self.longitude) if self.longitude is not None else None,
            subscriptions=[subscription.to_entity() for subscription in self.subscriptions.all()],
            created_at=self.created_at,
            updated_at=self.updated_at,
        )


class PlaceSubscription(TimedAndUnixIdBaseModel):
    class Status(models.TextChoices):
        PENDING = "pending", _("Pending")
        ACTIVE = "active", _("Active")
        REJECTED = "rejected", _("Rejected")
        CANCELED = "canceled", _("Canceled")
        REMOVED = "removed", _("Removed")

    class Role(models.TextChoices):
        OWNER = "owner", _("Owner")
        SUBSCRIBER = "subscriber", _("Subscriber")

    place = models.ForeignKey(
        "profiles.Place",
        on_delete=models.CASCADE,
        related_name="subscriptions",
    )
    user = models.ForeignKey(
        User,
        on_delete=models.CASCADE,
        related_name="place_subscriptions",
    )
    role = models.CharField(
        max_length=32,
        choices=Role.choices,
        default=Role.SUBSCRIBER,
    )
    status = models.CharField(
        max_length=32,
        choices=Status.choices,
        default=Status.PENDING,
    )
    notifications_enabled = models.BooleanField(default=True)
    invited_by = models.ForeignKey(
        User,
        null=True,
        blank=True,
        on_delete=models.SET_NULL,
        related_name="sent_place_invites",
    )
    approved_at = models.DateTimeField(null=True, blank=True)

    class Meta:
        db_table = "profiles_place_subscription"
        verbose_name = _("Place Subscription")
        verbose_name_plural = _("Place Subscriptions")
        ordering = ["-id"]
        constraints = [
            models.UniqueConstraint(
                fields=["place", "user"],
                name="unique_place_user_subscription",
            )
        ]

    def __str__(self):
        return f"{self.user} -> {self.place} [{self.status}]"

    def to_entity(self):
        from src.apps.profiles.entities import PlaceSubscriptionEntity

        return PlaceSubscriptionEntity(
            id=self.id,
            place_id=self.place.id,
            user_id=self.user.id,
            user_name=self.user.username,
            role=self.role,
            status=self.status,
            notifications_enabled=self.notifications_enabled,
            invited_by_id=self.invited_by.id if self.invited_by else None,
            invited_by_name=self.invited_by.username if self.invited_by else None,
            created_at=self.created_at,
            updated_at=self.updated_at,
            approved_at=self.approved_at,
        )


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