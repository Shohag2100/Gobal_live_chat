import json
import re
from channels.generic.websocket import AsyncWebsocketConsumer
from channels.db import database_sync_to_async
from django.contrib.auth import get_user_model

from .models import PrivateMessage

User = get_user_model()

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
        action = data.get('action') or data.get('type')
        username = self.scope["user"].username

        if action == 'join_private':
            target = data.get('to')
            if not target:
                return
            try:
                target_user = await database_sync_to_async(User.objects.get)(username=target)
            except Exception:
                return
            group = self._private_group_name(self.scope['user'].id, target_user.id)
            await self.channel_layer.group_add(group, self.channel_name)
            await self.send(json.dumps({'info': f'joined private chat with {target}'}))
            print(f"[consumer] {username} joined private group {group}")
            return

        if action == 'leave_private':
            target = data.get('to')
            if not target:
                return
            try:
                target_user = await database_sync_to_async(User.objects.get)(username=target)
            except Exception:
                return
            group = self._private_group_name(self.scope['user'].id, target_user.id)
            await self.channel_layer.group_discard(group, self.channel_name)
            await self.send(json.dumps({'info': f'left private chat with {target}'}))
            print(f"[consumer] {username} left private group {group}")
            return

        # default/global chat or private send
        message = data.get('message', '')
        image_url = data.get('image_url')

        # If action indicates a private message, route it differently
        if action == 'private_message' or data.get('private'):
            to = data.get('to')
            if not to:
                return
            try:
                recipient = await database_sync_to_async(User.objects.get)(username=to)
            except Exception:
                return

            # save message to DB
            pm = await database_sync_to_async(self._create_private_message)(self.scope['user'], recipient, message, image_url)

            group = self._private_group_name(self.scope['user'].id, recipient.id)
            await self.channel_layer.group_send(
                group,
                {
                    'type': 'private_message',
                    'message': message,
                    'image_url': image_url,
                    'username': username,
                    'to': recipient.username,
                    'timestamp': pm.timestamp.isoformat() if pm else None,
                    'id': pm.id if pm else None,
                }
            )
            print(f"[consumer] private from={username} to={recipient.username} message={message!r}")
            return

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

    async def private_message(self, event):
        # sent to participants of a private group
        print(f"[consumer] delivering private event to client: from={event.get('username')} to={event.get('to')} msg={event.get('message')!r}")
        await self.send(text_data=json.dumps({
            'private': True,
            'message': event.get('message', ''),
            'image_url': event.get('image_url'),
            'username': event.get('username'),
            'to': event.get('to'),
            'timestamp': event.get('timestamp'),
            'id': event.get('id'),
        }))

    def _private_group_name(self, a, b):
        # deterministic ordering so both users compute the same group name
        x, y = sorted([int(a), int(b)])
        return f'private_{x}_{y}'

    def _create_private_message(self, sender, recipient, content, image_url=None):
        # synchronous helper used via database_sync_to_async
        pm = PrivateMessage(sender=sender, recipient=recipient, content=content or '')
        # if image_url points to a MEDIA path, we don't download it here; leave image blank
        pm.save()
        return pm