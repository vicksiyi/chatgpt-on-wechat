import time

import json
from bot.bot import Bot
from bot.chatgpt.chat_gpt_session import ChatGPTSession
from bot.openai.open_ai_image import OpenAIImage
from bot.session_manager import SessionManager
from bridge.context import Context, ContextType
from bridge.reply import Reply, ReplyType
from common.log import logger
from config import conf

class LangchainBot(Bot):
    def __init__(self):
        with open('/bot/langchain/langchain_config.json') as file:
            depend = json.load(file)
        exec(f"from {depend['folder_file']} import {depend['AIDR_Bot']} as My_Bot()")
        self.model = My_Bot()
        self.sessions = SessionManager(ChatGPTSession, model=conf().get("model") or "gpt-3.5-turbo")

    def reply(self, query, context: Context = None) -> Reply:
        if context.type == ContextType.TEXT:
            return self._chat(query, context)
        elif context.type == ContextType.IMAGE_CREATE:
            ok, retstring = self.create_img(query, 0)
            reply = None
            if ok:
                reply = Reply(ReplyType.IMAGE_URL, retstring)
            else:
                reply = Reply(ReplyType.ERROR, retstring)
            return reply
        else:
            reply = Reply(ReplyType.ERROR, "Bot不支持处理{}类型的消息".format(context.type))
            return reply


    def _chat(self, query, context, retry_count=0):
        if retry_count >= 2:
            # exit from retry 2 times
            logger.warn("[LINKAI] failed after maximum number of retry times")
            return Reply(ReplyType.ERROR, "请再问我一次吧")

        try:
            # load config
            session_id = context["session_id"]
            session = self.sessions.session_query(query, session_id)
            clear_memory_commands = conf().get("clear_memory_commands", ["#清除记忆"])
            if query in clear_memory_commands:
                self.sessions.clear_session(session_id)
                return Reply(ReplyType.INFO, "记忆已清除")


            if session.messages[0].get("role") == "system":
                session.messages.pop(0)
            messages = session.messages

            reply_content = self.model.reply(query,messages)

            logger.info(f"[DrBot] query={query}")
            logger.info(f"[DrBot] reply={reply_content}")
            self.sessions.session_reply(reply_content, session_id)
            return Reply(ReplyType.TEXT, reply_content)

        except Exception as e:
            logger.exception(e)
            # retry
            time.sleep(2)
            logger.warn(f"[LINKAI] do retry, times={retry_count}")
            return self._chat(query, context, retry_count + 1)

