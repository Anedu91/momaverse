from datetime import datetime
from types import SimpleNamespace
from typing import Any


def make_timestamp() -> datetime:
    return datetime(2026, 1, 1, 12, 0, 0)


def make_location_obj(**overrides: Any) -> SimpleNamespace:
    now = make_timestamp()
    defaults = dict(
        id=1,
        name="Test Location",
        short_name=None,
        very_short_name=None,
        address=None,
        description=None,
        lat=40.0,
        lng=-74.0,
        emoji=None,
        alt_emoji=None,
        created_at=now,
        updated_at=now,
    )
    defaults.update(overrides)
    return SimpleNamespace(**defaults)


def make_event_obj(**overrides: Any) -> SimpleNamespace:
    now = make_timestamp()
    defaults = dict(
        id=1,
        name="Test Event",
        short_name=None,
        description=None,
        emoji=None,
        location_id=None,
        location_name=None,
        sublocation=None,
        website_id=None,
        archived=False,
        suppressed=False,
        reviewed=False,
        created_at=now,
        updated_at=now,
    )
    defaults.update(overrides)
    return SimpleNamespace(**defaults)


def make_website_obj(**overrides: Any) -> SimpleNamespace:
    now = make_timestamp()
    defaults = dict(
        id=1,
        name="Test Website",
        description=None,
        base_url="https://example.com",
        max_pages=30,
        disabled=False,
        created_at=now,
        updated_at=now,
    )
    defaults.update(overrides)
    return SimpleNamespace(**defaults)


def make_user_obj(**overrides: Any) -> SimpleNamespace:
    now = make_timestamp()
    defaults = dict(
        id=1,
        email="test@example.com",
        display_name="Test User",
        is_admin=False,
        created_at=now,
    )
    defaults.update(overrides)
    return SimpleNamespace(**defaults)


def make_edit_obj(**overrides: Any) -> SimpleNamespace:
    now = make_timestamp()
    defaults = dict(
        id=1,
        edit_uuid="abc-123",
        table_name="events",
        record_id=42,
        field_name="name",
        action="UPDATE",
        old_value="Old",
        new_value="New",
        source="local",
        user_id=1,
        created_at=now,
        applied_at=None,
    )
    defaults.update(overrides)
    return SimpleNamespace(**defaults)


def make_tag_obj(id: int = 1, name: str = "test-tag") -> SimpleNamespace:
    return SimpleNamespace(id=id, name=name)


def make_alternate_name_obj(**overrides: Any) -> SimpleNamespace:
    defaults = dict(
        id=1,
        alternate_name="Alternate Name",
        website_id=None,
    )
    defaults.update(overrides)
    return SimpleNamespace(**defaults)
