import base64

import pytest
from channels.db import database_sync_to_async
from channels.routing import URLRouter
from channels.testing import WebsocketCommunicator
from django.contrib.auth.models import AnonymousUser

from room.models import Message
from room.routing import websocket_urlpatterns

pytestmark = pytest.mark.django_db(transaction=True)


def application_as(user):
    """The WebSocket router with `user` attached to the scope, as AuthMiddlewareStack would do."""
    router = URLRouter(websocket_urlpatterns)

    async def app(scope, receive, send):
        return await router({**scope, "user": user}, receive, send)

    return app


async def connect(user, slug):
    communicator = WebsocketCommunicator(application_as(user), f"/ws/{slug}/")
    connected, code = await communicator.connect()
    return communicator, connected, code


def data_url(content):
    return "data:text/plain;base64," + base64.b64encode(content).decode()


async def test_anonymous_user_is_rejected(room):
    communicator, connected, code = await connect(AnonymousUser(), room.slug)
    assert not connected
    assert code == 4001


async def test_unknown_room_is_rejected(user):
    communicator, connected, code = await connect(user, "does-not-exist")
    assert not connected
    assert code == 4004


async def test_text_message_is_saved_and_broadcast(user, other_user, room):
    alice, connected, _ = await connect(user, room.slug)
    assert connected
    bob, connected, _ = await connect(other_user, room.slug)
    assert connected

    # The client tries to impersonate bob; the server must ignore that.
    await alice.send_json_to({"type": "text", "message": "Hello!", "username": "bob"})

    for communicator in (alice, bob):
        received = await communicator.receive_json_from()
        assert received["username"] == "alice"
        assert received["content"] == "Hello!"

    message = await database_sync_to_async(Message.objects.select_related("user").get)()
    assert message.user.username == "alice"
    assert message.room_id == room.pk

    await alice.disconnect()
    await bob.disconnect()


async def test_messages_stay_in_their_room(user, other_user, room):
    other_room = await database_sync_to_async(room.__class__.objects.create)(name="Other", slug="other")
    alice, _, _ = await connect(user, room.slug)
    bob, _, _ = await connect(other_user, other_room.slug)

    await alice.send_json_to({"type": "text", "message": "Only for this room"})
    await alice.receive_json_from()
    assert await bob.receive_nothing()

    await alice.disconnect()
    await bob.disconnect()


async def test_empty_message_is_ignored(user, room):
    alice, _, _ = await connect(user, room.slug)
    await alice.send_json_to({"type": "text", "message": "   "})
    assert await alice.receive_nothing()
    assert await database_sync_to_async(Message.objects.count)() == 0
    await alice.disconnect()


async def test_file_is_saved_and_broadcast_with_download_link(user, room):
    alice, _, _ = await connect(user, room.slug)
    await alice.send_json_to({"type": "file", "name": "notes.txt", "data": data_url(b"file content")})

    received = await alice.receive_json_from()
    assert received["file_name"] == "notes.txt"
    assert received["file_url"] == f"/rooms/{room.slug}/files/{received['id']}/"

    message = await database_sync_to_async(Message.objects.get)(pk=received["id"])
    with message.attachment.open("rb") as f:
        assert f.read() == b"file content"

    await alice.disconnect()


async def test_oversized_file_is_rejected(user, room, settings):
    settings.CHAT_MAX_FILE_SIZE = 10
    alice, _, _ = await connect(user, room.slug)
    await alice.send_json_to({"type": "file", "name": "big.bin", "data": data_url(b"x" * 100)})

    received = await alice.receive_json_from()
    assert "too large" in received["error"]
    assert await database_sync_to_async(Message.objects.count)() == 0
    await alice.disconnect()


async def test_invalid_payload_returns_error(user, room):
    alice, _, _ = await connect(user, room.slug)
    await alice.send_to(text_data="not json")
    received = await alice.receive_json_from()
    assert received["error"] == "Invalid message format."
    await alice.disconnect()
