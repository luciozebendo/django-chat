from django.conf import settings
from django.contrib.auth.decorators import login_required
from django.http import FileResponse
from django.shortcuts import get_object_or_404, render

from .models import Message, Room


@login_required
def rooms(request):
    return render(request, "room/rooms.html", {"rooms": Room.objects.all()})


@login_required
def room(request, slug):
    room = get_object_or_404(Room, slug=slug)
    # Last 50 messages, oldest first.
    messages = room.messages.select_related("user").order_by("-date_added")[:50][::-1]
    return render(
        request,
        "room/room.html",
        {"room": room, "messages": messages, "max_file_size": settings.CHAT_MAX_FILE_SIZE},
    )


@login_required
def download_file(request, slug, pk):
    """Serve an attachment only to logged-in users, and only through the room it was sent to."""
    message = get_object_or_404(Message, pk=pk, room__slug=slug, attachment__gt="")
    return FileResponse(
        message.attachment.open("rb"), as_attachment=True, filename=message.attachment_name
    )
