import base64
import binascii
import json

from channels.db import database_sync_to_async
from channels.generic.websocket import AsyncWebsocketConsumer
from django.conf import settings
from django.core.files.base import ContentFile
from django.urls import reverse

from .models import Message, Room


class ChatConsumer(AsyncWebsocketConsumer):
    """One instance per open WebSocket. Messages are saved, then broadcast to the room's group."""

    async def connect(self):
        self.user = self.scope.get("user")
        if self.user is None or not self.user.is_authenticated:
            await self.close(code=4001)
            return

        self.room = await self.get_room(self.scope["url_route"]["kwargs"]["room_name"])
        if self.room is None:
            await self.close(code=4004)
            return

        self.room_group_name = f"chat_{self.room.pk}"
        await self.channel_layer.group_add(self.room_group_name, self.channel_name)
        await self.accept()

    async def disconnect(self, close_code):
        if hasattr(self, "room_group_name"):
            await self.channel_layer.group_discard(self.room_group_name, self.channel_name)

    async def receive(self, text_data=None, bytes_data=None):
        """Handle a message sent from the browser (see room.html)."""
        try:
            data = json.loads(text_data or "")
        except json.JSONDecodeError:
            return await self.send_error("Invalid message format.")

        if data.get("type") == "file":
            try:
                content = decode_data_url(data.get("data", ""))
            except ValueError as exc:
                return await self.send_error(str(exc))
            message = await self.save_file(data.get("name") or "file", content)
        else:
            text = str(data.get("message", "")).strip()
            if not text:
                return
            message = await self.save_text(text)

        # The author always comes from the authenticated session, never from the client.
        await self.channel_layer.group_send(
            self.room_group_name, {"type": "chat_message", "message": serialize(message)}
        )

    async def chat_message(self, event):
        """Called for every member of the group when a message is broadcast."""
        await self.send(text_data=json.dumps(event["message"]))

    async def send_error(self, error):
        await self.send(text_data=json.dumps({"error": error}))

    @database_sync_to_async
    def get_room(self, slug):
        return Room.objects.filter(slug=slug).first()

    @database_sync_to_async
    def save_text(self, text):
        return Message.objects.create(user=self.user, room=self.room, content=text)

    @database_sync_to_async
    def save_file(self, name, content):
        name = name[-255:]
        message = Message(user=self.user, room=self.room, attachment_name=name)
        message.attachment.save(name, ContentFile(content), save=True)
        return message


def decode_data_url(data_url):
    """Turn a browser data URL ("data:<type>;base64,<data>") into bytes, enforcing the size limit."""
    _, sep, encoded = data_url.partition(";base64,")
    if not sep:
        raise ValueError("Invalid file data.")
    max_size = settings.CHAT_MAX_FILE_SIZE
    # Base64 uses 4 characters for every 3 bytes: reject oversized files before decoding.
    if len(encoded) * 3 // 4 > max_size + 3:
        raise ValueError(f"File too large (max {max_size // (1024 * 1024)} MB).")
    try:
        content = base64.b64decode(encoded, validate=True)
    except (binascii.Error, ValueError):
        raise ValueError("Invalid file data.")
    if len(content) > max_size:
        raise ValueError(f"File too large (max {max_size // (1024 * 1024)} MB).")
    return content


def serialize(message):
    payload = {
        "id": message.pk,
        "username": message.user.username,
        "content": message.content,
    }
    if message.attachment:
        payload["file_name"] = message.attachment_name
        payload["file_url"] = reverse("download_file", args=[message.room.slug, message.pk])
    return payload
