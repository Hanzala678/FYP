import azure.functions as func
from langchain_openai import AzureChatOpenAI, AzureOpenAIEmbeddings
import logging
import chromadb
import chromadb.utils.embedding_functions as embedding_functions
from langchain_core.prompts import ChatPromptTemplate
from langchain_core.prompts import PromptTemplate
from langchain.chains import LLMChain
import json
import os
from prompts import system_prompt, first_year, second_year, third_year, fourth_year, general_prompt, context_prompt, generation_prompt

api_key = os.environ["api_key"]
api_base = os.environ['api_base']
embeddings_model_name = os.environ["embeddings_model_name"]
chat_model_name = os.environ["chat_model_name"]

app = func.FunctionApp(http_auth_level=func.AuthLevel.FUNCTION)

@app.route(route="http_trigger")
def http_trigger(req: func.HttpRequest) -> func.HttpResponse:
    logging.info('Python HTTP trigger function processed a request.')
    req_body = req.get_json()

    # Determine the complete system prompt based on the source parameter
    source = req_body.get("source", "")
    query = req_body.get("query", "")
    
    if source == '1st_year':
        year_prompt = first_year
    elif source == '2nd_year':
        year_prompt = second_year
    elif source == '3rd_year':
        year_prompt = third_year
    elif source == '4th_year':
        year_prompt = fourth_year
    else:
        year_prompt = general_prompt

    complete_system_prompt = f"{system_prompt}\n\n{year_prompt}\n\n{context_prompt}"
    
    embeddings_fn = embedding_functions.OpenAIEmbeddingFunction(
                api_key=api_key,
                api_base=api_base,
                api_type="azure",
                api_version="2023-05-15",
                model_name=embeddings_model_name
            )
    
    llm = AzureChatOpenAI(
        azure_deployment=chat_model_name,
        api_version="2023-05-15",
        azure_endpoint=api_base,
        api_key=api_key
    )
    
    client = chromadb.PersistentClient(path="./data/chromadb")
    
    collection = client.get_collection(name=f"documents_{source}", embedding_function=embeddings_fn)
    
    data = collection.query(
                query_texts=[query],
                n_results=10
            )
    
    logging.info(data)

    prompt = ChatPromptTemplate.from_messages(
    [
        ("system", complete_system_prompt),
        ("human", "{query}"),
    ])

    chain = prompt | llm

    response = chain.invoke({
        "context": data,
        "query": query
    })
    logging.info(response)

    try:
        return func.HttpResponse(json.dumps({"response": response.content}), mimetype="application/json")
    except Exception as e:
        logging.error(e)
        return func.HttpResponse(
             "An Error Occurred",
             status_code=500
        )
