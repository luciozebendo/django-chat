import pytest
from django.contrib.auth.models import User

from room.models import Room


@pytest.fixture(autouse=True)
def media_root(settings, tmp_path):
    """Write uploaded files to a temporary folder during tests."""
    settings.MEDIA_ROOT = tmp_path / "media"


@pytest.fixture
def user(db):
    return User.objects.create_user(username="alice", password="s3cure-pass-123")


@pytest.fixture
def other_user(db):
    return User.objects.create_user(username="bob", password="s3cure-pass-123")


@pytest.fixture
def room(db):
    return Room.objects.create(name="Test room", slug="test-room")
