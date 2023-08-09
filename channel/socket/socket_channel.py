import sys

from bridge.context import *
from bridge.reply import Reply, ReplyType
from channel.chat_channel import ChatChannel, check_prefix
from channel.chat_message import ChatMessage
from common.log import logger
from config import conf
import socket


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
            # print(reply.content)
            self.client_socket.send(reply.content.encode('utf-8'))
        sys.stdout.flush()
        return

    def startup(self):
        context = Context()

        # 创建一个TCP套接字
        server_socket = socket.socket(socket.AF_INET, socket.SOCK_STREAM)

        # 绑定套接字到特定地址和端口
        host = "127.0.0.1"
        port = 12345
        server_socket.bind((host, port))

        # 开始监听传入的连接
        server_socket.listen(1)

        print(f"等待连接在 {host}:{port} ...")

        # 等待客户端连接
        self.client_socket, self.client_address = server_socket.accept()
        print(f"连接成功：{self.client_socket}:{self.client_address}")
        msg_id = 0
        try:
            while True:
                received_data, addr = self.client_socket.recvfrom(1024)
                prompt = received_data.decode('utf-8')
                if not prompt:
                    break
                print(f"prompt: {prompt}")
                msg_id += 1
                trigger_prefixs = conf().get("single_chat_prefix", [""])
                if check_prefix(prompt, trigger_prefixs) is None:
                    prompt = trigger_prefixs[0] + prompt  # 给没触发的消息加上触发前缀

                context = self._compose_context(ContextType.TEXT, prompt, msg=SocketMessage(msg_id, prompt))
                if context:
                    self.produce(context)
                else:
                    raise Exception("context is None")
        except Exception as e:
            print("An error occurred:", e)
            self.client_socket.close()
            server_socket.close()
