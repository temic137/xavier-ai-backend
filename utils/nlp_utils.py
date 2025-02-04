import cohere
import json
import logging
import nltk
from nltk.tokenize import sent_tokenize, word_tokenize
import json
import re
from pymongo import MongoClient      
import torch
import nltk
from nltk.corpus import stopwords
from nltk.stem import WordNetLemmatizer
from nltk.tokenize import word_tokenize, sent_tokenize
import logging
import faiss
import numpy as np
import torch
from huggingface_hub import InferenceClient

nltk.download('stopwords')
lemmatizer = WordNetLemmatizer()
stop_words = set(stopwords.words('english'))

import os
from dotenv import load_dotenv

load_dotenv()

huggingface_token = os.getenv('HUGGINGFACE_API_TOKEN')

cohere_token =  os.getenv('COHERE_CLIENT')


cohere_client = cohere.Client(api_key=cohere_token)



huggingface_client = InferenceClient(api_key=huggingface_token)

# groq_client = os.getenv('GROQAPI')

def preprocess_text(text):
   
    text = text.lower()
    tokens = word_tokenize(text)
    tokens = [token for token in tokens if token.isalpha()]
    return ' '.join(tokens)

def preprocess_data(pdf_data, folder_data, web_data):
    
    structured_data = []

    logging.debug(f"Preprocessing PDF data: {len(pdf_data)} items")
    logging.debug(f"Preprocessing folder data: {len(folder_data)} items")
    logging.debug(f"Preprocessing web data: {bool(web_data)}")

    # Process PDF and folder data
    for item in pdf_data + folder_data:
        if isinstance(item, dict) and 'text' in item:
            sentences = nltk.sent_tokenize(item['text'])
            structured_data.extend([{'type': 'text', 'content': sent, 'source': 'pdf/folder'} for sent in sentences])

    # Process web data 
    if web_data:
        logging.debug(f"Web data keys: {web_data.keys()}")
        if isinstance(web_data, list) and len(web_data) > 0:
            web_data = web_data[0]
        
        if isinstance(web_data, dict):
            if 'title' in web_data:
                structured_data.append({'type': 'title', 'content': web_data['title'], 'source': 'web'})
            
            if 'sections' in web_data:
                for section in web_data['sections']:
                    if isinstance(section, dict):
                        if 'heading' in section:
                            structured_data.append({'type': 'heading', 'content': section['heading'], 'source': 'web'})
                        if 'content' in section:
                            structured_data.extend([{'type': 'web_content', 'content': item, 'source': 'web'} for item in section['content']])
            
            if 'sub_pages' in web_data:
                for sub_page in web_data['sub_pages']:
                    structured_data.extend(preprocess_data([], [], [sub_page]))

    logging.info(f"Preprocessed data: {len(structured_data)} items")
    return structured_data






from rank_bm25 import BM25Okapi
import numpy as np
from typing import List, Dict
import logging
from nltk.tokenize import word_tokenize
import nltk

# Download required NLTK data
try:
    nltk.download('punkt', quiet=True)
except:
    pass

def prepare_bm25_index(documents: List[str]) -> BM25Okapi:
    """
    Prepare BM25 index from a list of documents.
    """
    tokenized_documents = [word_tokenize(doc.lower()) for doc in documents]
    return BM25Okapi(tokenized_documents)

def get_relevant_passages(question: str, documents: List[str], bm25: BM25Okapi, top_k: int = 3) -> List[str]:
    """
    Retrieve the most relevant passages using BM25 scoring.
    """
    tokenized_question = word_tokenize(question.lower())
    scores = bm25.get_scores(tokenized_question)
    top_indices = np.argsort(scores)[-top_k:][::-1]
    return [documents[i] for i in top_indices]






def generate_answer(question: str, documents: List[str], max_length: int = 500, context_threshold: int = 4000) -> str:
    """
    Generate an answer based on the question and context, using passage retrieval only for large contexts.

    Args:
        question: The question to answer
        documents: List of document passages
        max_length: Maximum length of the generated answer
        context_threshold: Character threshold above which to use passage retrieval
    """
    try:
        
        total_context_length = sum(len(doc) for doc in documents)

        # Determine whether to use passage retrieval
        if total_context_length > context_threshold:
            # Use BM25 for large contexts
            bm25 = prepare_bm25_index(documents)
            relevant_info = get_relevant_passages(question, documents, bm25)
            context = " ".join(relevant_info)
        else:
            # Use full context for smaller documents
            context = " ".join(documents)

        print(f"context: {context}")
        messages = [
            {
                "role": "system",
                "content": """You are a customer service representative providing helpful, direct, and concise responses. Follow these guidelines:

Response Structure:
- Do not include the word 'Response:' or similar phrases in your answers
- Keep answers short and clear
- Focus only on what is necessary to answer the question
- Use natural, conversational language
- Directly address the question first
- Skip unnecessary pleasantries and marketing language
- Avoid lengthy introductions, provide answers immediately

Additional Guidance:
- If the information is not found in the context, say 'I'm sorry, I don't have that information.'
- If the response requires follow-up or clarification, suggest the next step clearly."""

            },
            {
                "role": "user",
                "content": f"""Context: {context}
    Question: {question}

    Provide a precise and helpful response based on the context above. Only use the information provided. If unsure, say 'I'm sorry, I don't have that information.' Do not include the word 'Response:' in your answer."""
            }
        ]

        response = huggingface_client.chat.completions.create(
            # model="HuggingFaceH4/zephyr-7b-beta",
            model="mistralai/Mistral-7B-Instruct-v0.2",
            messages=messages,
            temperature=0.0,
            max_tokens=500
        )

        return response.choices[0].message.content

    except Exception as e:
        logging.error(f"Error generating answer: {str(e)}")
        return "I apologize, but I encountered an issue while processing your question."


# def generate_answer(question: str, documents: List[str], max_length: int = 500, context_threshold: int = 4000) -> str:
#     """
#     Generate an answer based on the question and context using Groq's LLM.

#     Args:
#         question: The question to answer
#         documents: List of document passages
#         max_length: Maximum length of the generated answer
#         context_threshold: Character threshold above which to use passage retrieval
#     """
#     try:
#         from groq import Groq
        
       
#         client = Groq(api_key=groq_client)
        
#         total_context_length = sum(len(doc) for doc in documents)

        
#         if total_context_length > context_threshold:
#             # Use BM25 for large contexts
#             bm25 = prepare_bm25_index(documents)
#             relevant_info = get_relevant_passages(question, documents, bm25)
#             context = " ".join(relevant_info)
#         else:
#             # Use full context for smaller documents
#             context = " ".join(documents)

#         print(f"context: {context}")
        
#         chat_completion = client.chat.completions.create(
#             messages=[
#                 {
#                     "role": "system",
#                     "content": """You are a customer service representative providing helpful, direct, and concise responses. Follow these guidelines:

# Response Structure:
# - Do not include the word 'Response:' or similar phrases in your answers
# - Keep answers short and clear
# - Focus only on what is necessary to answer the question
# - Use natural, conversational language
# - Directly address the question first
# - Skip unnecessary pleasantries and marketing language
# - Avoid lengthy introductions, provide answers immediately

# Additional Guidance:
# - If the information is not found in the context, say 'I'm sorry, I don't have that information.'
# - If the response requires follow-up or clarification, suggest the next step clearly."""
#                 },
#                 {
#                     "role": "user",
#                     "content": f"""Context: {context}
# Question: {question}

# Provide a precise and helpful response based on the context above. Only use the information provided. If unsure, say 'I'm sorry, I don't have that information.' Do not include the word 'Response:' in your answer."""
#                 }
#             ],
#             model="llama3-70b-8192",
#             temperature=0.5,
#             max_tokens=max_length
#         )

#         return chat_completion.choices[0].message.content

#     except Exception as e:
#         logging.error(f"Error generating answer: {str(e)}")
#         return "I apologize, but I encountered an issue while processing your question."



def get_general_answer(data, question):
    try:
        # Process input data 
        chatbot_data = json.loads(data) if isinstance(data, str) else data
        if isinstance(chatbot_data, list) and chatbot_data:
            chatbot_data = chatbot_data[-1]
        
        if not isinstance(chatbot_data, dict):
            raise ValueError("Invalid data format.")
        
        
        pdf_data = chatbot_data.get('pdf_data', [])
        folder_data = chatbot_data.get('folder_data', [])
        web_data = chatbot_data.get('web_data', {})
        
        # Preprocess and structure the data
        structured_data = preprocess_data(pdf_data, folder_data, web_data)
        text_data = [item['content'] for item in structured_data if 'content' in item]
        

        answer = generate_answer(question, text_data)
        
        return answer
        
    except Exception as e:
        logging.error(f"Error processing question: {str(e)}")
        return "I apologize, but I ran into an issue while processing your question. Could you try rephrasing it?"



def preprocess_text(text):
   
    text = text.lower()
    tokens = word_tokenize(text)

    
    tokens = [lemmatizer.lemmatize(token) for token in tokens if token not in stop_words and token.isalpha()]

    
    return ' '.join(tokens)


def split_complex_query(query):
    sentences = sent_tokenize(query)
    questions = [s for s in sentences if s.strip().endswith('?')]
    return questions if questions else [query]


def post_process_answer(answer, question):
    if not any(keyword in answer.lower() for keyword in question.lower().split()):
        answer = f"To answer your question about {question.lower()}: {answer}"
    
    if any(keyword in answer.lower() for keyword in ['might', 'maybe', 'possibly', 'not sure']):
        answer += " Please note that this answer is based on the available information and may not be completely certain."
    
    return answer


def get_inventory_rag_answer(data, query):
    try:
        chatbot_data = json.loads(data) if isinstance(data, str) else data
        inventory_data = chatbot_data.get('db_data', [{}])[0].get('text', [])
        inventory_data = json.loads(inventory_data) if isinstance(inventory_data, str) else inventory_data

        questions = split_complex_query(query)
        final_answer = ""

        for question in questions:
            inventory_summary = "\n".join([f"{item['name']}: ${item['price']:.2f}, {item['quantity']} in stock" for item in inventory_data])
            answer = generate_answer(question, [inventory_summary])
            answer = post_process_answer(answer, question)
            final_answer += answer + " "

        return final_answer.strip()
    except Exception as e:
        logging.error(f"Error generating inventory answer: {str(e)}")
        return "I apologize, there seems to be an issue with processing your query."
