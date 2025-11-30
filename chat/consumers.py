import json
import re
from channels.generic.websocket import AsyncWebsocketConsumer
from channels.db import database_sync_to_async

class ChatConsumer(AsyncWebsocketConsumer):
    async def connect(self):
        user = self.scope.get("user")
        print(f"[consumer] connect attempt user={user}")
        if user is None or user.is_anonymous:
            print("[consumer] rejecting anonymous connection")
            await self.close()  # Reject unauthenticated
        else:
            self.room_name = "global_chat"
            await self.channel_layer.group_add(self.room_name, self.channel_name)
            await self.accept()
            print(f"[consumer] accepted connection for {user.username}, channel={self.channel_name}")

    async def disconnect(self, close_code):
        user = self.scope.get("user")
        print(f"[consumer] disconnect user={user} code={close_code}")
        if user and not user.is_anonymous:
            await self.channel_layer.group_discard(self.room_name, self.channel_name)

    async def receive(self, text_data):
        data = json.loads(text_data)
        message = data.get('message', '')
        image_url = data.get('image_url')
        username = self.scope["user"].username  # REAL UNIQUE USERNAME

        # Extract simple @mentions (alphanumeric + underscore)
        mentions = re.findall(r'@([A-Za-z0-9_]+)', message or '')
        print(f"[consumer] receive from={username} message={message!r} image={image_url} mentions={mentions}")

        await self.channel_layer.group_send(
            self.room_name,
            {
                'type': 'chat_message',
                'message': message,
                'image_url': image_url,
                'username': username,
                'mentions': mentions,
            }
        )

    async def chat_message(self, event):
        # log outgoing broadcast
        print(f"[consumer] broadcasting to client: {event.get('username')} msg={event.get('message')!r} image={event.get('image_url')} mentions={event.get('mentions')}")
        await self.send(text_data=json.dumps({
            'message': event.get('message', ''),
            'image_url': event.get('image_url'),
            'username': event['username'],
            'mentions': event.get('mentions', []),
        }))