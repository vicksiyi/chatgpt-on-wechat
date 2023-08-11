
import time

from langchain.chains import ConversationalRetrievalChain
from langchain.chat_models import ChatOpenAI
from langchain.embeddings.openai import OpenAIEmbeddings
from langchain.prompts import (
    ChatPromptTemplate,
    PromptTemplate,
    SystemMessagePromptTemplate,
    HumanMessagePromptTemplate,
)
from langchain.vectorstores import FAISS

from bot.bot import Bot
from bot.chatgpt.chat_gpt_session import ChatGPTSession
from bot.openai.open_ai_image import OpenAIImage
from bot.session_manager import SessionManager
from bridge.context import Context, ContextType
from bridge.reply import Reply, ReplyType
from common.log import logger
from config import conf


class DrBot(Bot, OpenAIImage):
    # authentication failed
    #AUTH_FAILED_CODE = 401
    #NO_QUOTA_CODE = 406

    def __init__(self):
        super().__init__()
        self.sessions = SessionManager(ChatGPTSession, model=conf().get("model") or "gpt-3.5-turbo-0301");
        openai_api_key = conf().get("open_ai_api_key")
        embeddings = OpenAIEmbeddings(openai_api_key = openai_api_key)
        self.vs = FAISS.load_local("bot/langchain/ai_dr_db",embeddings)
        system_template = """
        请扮演了解伤寒论的智能医生，使用以下提供的[伤寒论知识]回答用户的问题；
        如果用户的输入和病症或者伤寒论本身无关，则拒绝回答该问题; 
        如果用户输入症状，当症状完全匹配你伤寒论中对应治疗方案的时候，告诉用户需要使用什么治疗方案；
        如果用户输入的症状不能完全匹配你所知的治疗方案，则询问用户是否还有其他的症状,
        如果用户表示没有其他症状则列举出可能性最大的治疗方案，
        如果治疗方案对应的症状中有症状和用户症状完全冲突，如“不发热”与“发热”冲突，则不能推荐该方案；

        [伤寒论知识]：
        {context}
        """
        _template = """以下是一段ChatHistory，涉及Human与一个assistant的对话，忽略assistant的回复，将Human所述进行总结，以Human的角度形成一个新问题：
        
        ChatHistory:
        {chat_history}
        Human: {question}
        新问题:"""
        condense_question_prompt = PromptTemplate.from_template(_template)

        # Create the chat prompt templates
        messages = [
            SystemMessagePromptTemplate.from_template(system_template),
            HumanMessagePromptTemplate.from_template("{question}")
        ]

        qa_prompt = ChatPromptTemplate.from_messages(messages)

        self.qa = ConversationalRetrievalChain.from_llm(
            ChatOpenAI(openai_api_key=openai_api_key, temperature=0, model="gpt-3.5-turbo-0301"),
            self.vs.as_retriever(search_kwargs={"k": 3}),
            condense_question_prompt=condense_question_prompt,
            verbose=True,
            chain_type='stuff',
            combine_docs_chain_kwargs={"prompt": qa_prompt}
            )



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
            if session.messages[0].get("role") == "system":
                session.messages.pop(0)
            messages = session.messages
            chat_history = []
            for i in range(len(messages)):
                if messages[i]['role'] == 'user':
                    chat_history.append((messages[i]['content'], ''))

            result = self.qa({'question': query, 'chat_history': chat_history})
            reply_content = result['answer']

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