# users/consumers.py
import json
from channels.generic.websocket import AsyncWebsocketConsumer

class TaskConsumer(AsyncWebsocketConsumer):
    async def connect(self):
        self.task_id = self.scope["url_route"]["kwargs"]["task_id"]
        self.group = f"task_{self.task_id}"
        await self.channel_layer.group_add(self.group, self.channel_name)
        await self.accept()

    async def disconnect(self, close_code):
        await self.channel_layer.group_discard(self.group, self.channel_name)

    # broadcast payload from driver_ping
    async def pos_update(self, event):
        await self.send(json.dumps({
            "type": "pos",
            "lat": event["lat"],
            "lng": event["lng"],
            "driver": event["driver"],
            "ts": event["ts"],
        }))
