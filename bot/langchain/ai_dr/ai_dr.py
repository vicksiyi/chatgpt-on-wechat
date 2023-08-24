from langchain.embeddings.openai import OpenAIEmbeddings
from langchain.chains import ConversationalRetrievalChain
from langchain.chat_models import ChatOpenAI
from langchain.vectorstores import FAISS
from config import conf

from langchain.prompts import (
    ChatPromptTemplate,
    PromptTemplate,
    SystemMessagePromptTemplate,
    AIMessagePromptTemplate,
    HumanMessagePromptTemplate,
)

class AI_DR(object):
    def __init__(self,**kwargs):
        super().__init__()
        openai_api_key = conf().get("open_ai_api_key")
        embeddings = OpenAIEmbeddings(openai_api_key=openai_api_key)
        self.vs = FAISS.load_local("bot/langchain/ai_dr/ai_dr_db", embeddings)
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
        _template = """System: 以下是一段ChatHistory，涉及Human与一个assistant的对话，忽略assistant的回复，将Human所述进行整合：

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

    def reply(self,query,messages):
        chat_history = []
        for i in range(len(messages)):
            if messages[i]['role'] == 'user':
                chat_history.append((messages[i]['content'], ''))
        chat_history.pop(-1)
        result = self.qa({'question': query, 'chat_history': chat_history})
        reply_content = result['answer']
        return reply_content





