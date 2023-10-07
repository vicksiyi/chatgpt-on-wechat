import sys

from bridge.context import *
from bridge.reply import Reply, ReplyType
from channel.chat_channel import ChatChannel, check_prefix
from channel.chat_message import ChatMessage
from common.log import logger
from config import conf
import asyncio
import websockets
# 存储所有连接的客户端
connected_clients = set()

def safe_access(lst, index, default=None):
    return lst[index] if len(lst) > index else default

class SocketMessage(ChatMessage):
    def __init__(
        self,
        msg_id,
        content,
        ctype=ContextType.TEXT,
        from_user_id="User",
        to_user_id="Chatgpt",
        other_user_id="Chatgpt",
    ):
        self.msg_id = msg_id
        self.ctype = ctype
        self.content = content
        self.from_user_id = from_user_id
        self.to_user_id = to_user_id
        self.other_user_id = other_user_id


class SocketChannel(ChatChannel):
    NOT_SUPPORT_REPLYTYPE = [ReplyType.VOICE]
    async def send_to_clients(self, msg):
        await asyncio.gather(*[client.send(msg) for client in connected_clients])
    def send(self, reply: Reply, context: Context):
        print("\nBot:")
        if reply.type == ReplyType.IMAGE:
            from PIL import Image

            image_storage = reply.content
            image_storage.seek(0)
            img = Image.open(image_storage)
            print("<IMAGE>")
            img.show()
        elif reply.type == ReplyType.IMAGE_URL:  # 从网络下载图片
            import io

            import requests
            from PIL import Image

            img_url = reply.content
            pic_res = requests.get(img_url, stream=True)
            image_storage = io.BytesIO()
            for block in pic_res.iter_content(1024):
                image_storage.write(block)
            image_storage.seek(0)
            img = Image.open(image_storage)
            print(img_url)
            img.show()
        else:
            print(reply.content)
            async def send_msg():
                for client in connected_clients:
                    await client.send(reply.content)
            asyncio.run(send_msg())
            
        sys.stdout.flush()
        return
    async def handle_client(self, websocket, path):
            # 添加新客户端到连接列表
            connected_clients.add(websocket)
            details = path.split("/")
            user_id = safe_access(details, 1, '')
            enterprise_id = safe_access(details, 2, '')
            from_user_id = '{}_{}'.format(user_id, enterprise_id)
            try:
                async for message in websocket:
                    prompt = message
                    self.msg_id += 1
                    trigger_prefixs = conf().get("single_chat_prefix", [""])
                    if check_prefix(prompt, trigger_prefixs) is None:
                        prompt = trigger_prefixs[0] + prompt  # 给没触发的消息加上触发前缀
                    self.context = self._compose_context(ContextType.TEXT, prompt, msg=SocketMessage(self.msg_id, prompt, ContextType.TEXT, from_user_id))
                    if self.context:
                        self.produce(self.context)
                    else:
                        raise Exception("context is None")
            finally:
                # 客户端断开连接时，从列表中移除
                connected_clients.remove(websocket)
    async def run_server(self):
        server = await websockets.serve(self.handle_client, "localhost", 12345)
        await server.wait_closed()
    def start_server(self):
        self.loop = asyncio.get_event_loop()
        self.loop.run_until_complete(self.run_server())
        self.loop.run_forever()
    def startup(self):
        self.context = Context()

        self.msg_id = 0
        self.start_server()

