from dataclasses import dataclass
from datetime import datetime
from typing import List, Optional


@dataclass
class CityEntity:
    id: int
    name: str
    slug: str
    region: Optional[str] = None
    official_schedule_url: Optional[str] = None
    is_active: bool = True
    created_at: Optional[datetime] = None
    updated_at: Optional[datetime] = None


@dataclass
class PlaceSubscriptionEntity:
    id: int
    place_id: int
    user_id: int
    user_name: str
    role: str
    status: str
    notifications_enabled: bool
    invited_by_id: Optional[int] = None
    invited_by_name: Optional[str] = None
    created_at: Optional[datetime] = None
    updated_at: Optional[datetime] = None
    approved_at: Optional[datetime] = None


@dataclass
class PlaceSimpleEntity:
    id: int
    owner_id: int
    owner_name: str
    city_id: int
    city_name: str
    title: str
    address: Optional[str] = None
    latitude: Optional[float] = None
    longitude: Optional[float] = None
    created_at: Optional[datetime] = None
    updated_at: Optional[datetime] = None


@dataclass
class PlaceEntity:
    id: int
    owner_id: int
    owner_name: str
    city: CityEntity
    title: str
    address: Optional[str] = None
    latitude: Optional[float] = None
    longitude: Optional[float] = None
    subscriptions: Optional[List[PlaceSubscriptionEntity]] = None
    created_at: Optional[datetime] = None
    updated_at: Optional[datetime] = None


@dataclass
class UserProfileEntity:
    id: int
    user_id: int
    username: str
    email: Optional[str] = None
    primary_city: Optional[CityEntity] = None
    created_at: Optional[datetime] = None
    updated_at: Optional[datetime] = None