import json
from urllib.parse import parse_qs
from channels.generic.websocket import AsyncWebsocketConsumer
from channels.db import database_sync_to_async
from rest_framework_simplejwt.tokens import AccessToken
from rest_framework_simplejwt.exceptions import InvalidToken, TokenError
from apps.blog.models import Post


class CommentConsumer(AsyncWebsocketConsumer):
    async def connect(self):
        query_string = self.scope['query_string'].decode()
        params = parse_qs(query_string)
        token_lists = params.get('token', [])

        if not token_lists:
            await self.close(code=4001)
            return 
        
        try:
            token = AccessToken(token_lists[0])
            user_id = token['user_id']
        except (InvalidToken, TokenError):
            await self.close(code=4001)
            return 

        self.slug = self.scope['url_route']['kwargs']['slug']
        post_exits = await self.get_post(self.slug)

        if not post_exits:
            await self.close(code=4004)
            return 


        self.group_name = f'post_{self.slug}'
        await self.channel_layer.group_add(self.group_name, self.channel_name)
        await self.accept()

    async def disconnect(self, close_code):
        if hasattr(self, 'group_name'):
            await self.channel_layer.group_discard(self.group_name, self.channel_name)

    async def comment_created(self, event):
        await self.send(text_data = json.dumps(event['data']))

    
    @database_sync_to_async
    def get_post(self, slug):
        return Post.objects.filter(slug=slug).exists()

