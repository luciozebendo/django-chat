import asyncio
import os

import pytest
from channels_redis.core import RedisChannelLayer

REDIS_URL = os.environ.get("REDIS_URL")


@pytest.mark.skipif(not REDIS_URL, reason="needs a Redis server (set REDIS_URL)")
async def test_idle_connection_survives_more_than_5_seconds():
    """Regression test: with redis-py 8, waiting for messages on an idle room raised
    TimeoutError after 5 s, which closed every WebSocket in the room."""
    layer = RedisChannelLayer(hosts=[REDIS_URL])
    channel = await layer.new_channel()
    with pytest.raises(asyncio.TimeoutError):  # our own timeout, not a Redis error
        await asyncio.wait_for(layer.receive(channel), timeout=7)
    await layer.flush()
