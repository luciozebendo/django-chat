from django.contrib.auth.models import User
from django.core.files.base import ContentFile
from django.urls import reverse

from room.models import Message, Room


def test_signup_creates_user_and_logs_in(client, db):
    response = client.post(
        reverse("signup"),
        {"username": "carol", "password1": "s3cure-pass-123", "password2": "s3cure-pass-123"},
    )
    assert response.status_code == 302
    assert User.objects.filter(username="carol").exists()
    assert client.get(reverse("rooms")).status_code == 200


def test_signup_rejects_mismatched_passwords(client, db):
    response = client.post(
        reverse("signup"),
        {"username": "carol", "password1": "s3cure-pass-123", "password2": "different-pass-456"},
    )
    assert response.status_code == 200
    assert not User.objects.filter(username="carol").exists()


def test_login_shows_error_on_wrong_password(client, user):
    response = client.post(reverse("login"), {"username": "alice", "password": "wrong"})
    assert response.status_code == 200
    assert b"Please enter a correct username and password" in response.content


def test_logout_requires_post_and_logs_out(client, user):
    client.force_login(user)
    assert client.post(reverse("logout")).status_code == 302
    assert client.get(reverse("rooms")).status_code == 302


def test_general_room_is_created_by_migration(db):
    assert Room.objects.filter(slug="general").exists()


def test_rooms_require_login(client, room):
    response = client.get(reverse("rooms"))
    assert response.status_code == 302
    assert reverse("login") in response.url


def test_unknown_room_returns_404(client, user):
    client.force_login(user)
    assert client.get(reverse("room", args=["does-not-exist"])).status_code == 404


def test_room_history_escapes_html(client, user, room):
    Message.objects.create(room=room, user=user, content="<script>alert(1)</script>")
    client.force_login(user)
    response = client.get(reverse("room", args=[room.slug]))
    assert b"<script>alert(1)</script>" not in response.content
    assert b"&lt;script&gt;alert(1)&lt;/script&gt;" in response.content


def test_download_file(client, user, room):
    message = Message(room=room, user=user, attachment_name="notes.txt")
    message.attachment.save("notes.txt", ContentFile(b"hello"), save=True)
    client.force_login(user)

    response = client.get(reverse("download_file", args=[room.slug, message.pk]))
    assert response.status_code == 200
    assert b"".join(response.streaming_content) == b"hello"
    assert 'filename="notes.txt"' in response["Content-Disposition"]


def test_download_requires_login(client, user, room):
    message = Message(room=room, user=user, attachment_name="notes.txt")
    message.attachment.save("notes.txt", ContentFile(b"hello"), save=True)
    response = client.get(reverse("download_file", args=[room.slug, message.pk]))
    assert response.status_code == 302


def test_download_through_wrong_room_returns_404(client, user, room):
    other_room = Room.objects.create(name="Other", slug="other")
    message = Message(room=room, user=user, attachment_name="notes.txt")
    message.attachment.save("notes.txt", ContentFile(b"hello"), save=True)
    client.force_login(user)
    assert client.get(reverse("download_file", args=[other_room.slug, message.pk])).status_code == 404
