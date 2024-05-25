from fastapi import FastAPI, UploadFile, File, HTTPException
from sklearn.feature_extraction.text import TfidfVectorizer
import os
from PyPDF2 import PdfReader
import nltk
from nltk.corpus import stopwords
from nltk.tokenize import word_tokenize
from elasticsearch import Elasticsearch
import urllib3
import re
from dotenv import load_dotenv

load_dotenv()

app = FastAPI()
nltk.download('punkt')
nltk.download('stopwords')

urllib3.disable_warnings(urllib3.exceptions.InsecureRequestWarning)
es = Elasticsearch(
    hosts=["http://elasticsearch:9200"],
    http_auth=(os.getenv('ELASTIC_USERNAME'), os.getenv('ELASTIC_PASSWORD')),
    verify_certs=False,
)

vectorizer = TfidfVectorizer()

@app.on_event("startup")
async def startup_event():
    # Fit the vectorizer on the entire corpus of documents
    if not es.indices.exists(index="documents"):
        es.indices.create(index="documents")
    all_documents = [doc['_source']['content'] for doc in es.search(index='documents', body={"query": {"match_all": {}}})['hits']['hits']]
    if all_documents:
        vectorizer.fit(all_documents)

def process_file(file_path):
    with open(file_path, 'rb') as file:
        reader = PdfReader(file)
        content = ''
        for page in reader.pages:
            content += page.extract_text()
        tokens = word_tokenize(content)
        tokens = [token for token in tokens if token not in stopwords.words()]
        return ' '.join(tokens)

@app.post("/upload/")
async def upload_file(file: UploadFile = File(...)):
    if not file.filename.endswith(".pdf"):
        raise HTTPException(status_code=400, detail="Invalid file type. Only .pdf files are accepted.")
    
    os.makedirs('uploads', exist_ok=True)
    file_location = f"uploads/{file.filename}"
    with open(file_location, "wb+") as file_object:
        file_object.write(file.file.read())
    content = process_file(file_location)
    
    all_documents = [doc['_source']['content'] for doc in es.search(index='documents', body={"query": {"match_all": {}}})['hits']['hits']]
    all_documents.append(content)
    
    vectorizer.fit(all_documents)
    embedding = vectorizer.transform([content]).toarray().tolist()[0]

    es.index(index='documents', id=file.filename, body={'content': content, 'embedding': embedding})

@app.get("/docs/")
async def search_docs(q: str):
    res = es.search(index='documents', body={
        "query": {
            "bool": {
                "should": [
                    {
                        "match": {
                            "content": q
                        }
                    },
                    {
                        "more_like_this": {
                            "fields": ["content"],
                            "like": q,
                            "min_term_freq": 1,
                            "max_query_terms": 12
                        }
                    }
                ]
            }
        }
    })
    ranked_files = [hit['_id'] for hit in res['hits']['hits']]
    return ranked_files

@app.post("/clean_txt_data/")
async def clean_data(file: UploadFile = File(...)):
    if not file.filename.endswith(".txt"):
        raise HTTPException(status_code=400, detail="Invalid file type. Only .txt files are accepted.")
    
    os.makedirs('txt_data', exist_ok=True)
    file_location = f"txt_data/{file.filename}"
    with open(file_location, "wb+") as file_object:
        file_object.write(file.file.read())
    return clean_file(file_location)

def clean_text(content):
    # Define patterns to identify and remove unwanted sections
    patterns = [
        r'\b(?:Revenue Productivity Platform|Platform Overview|Browse by Module|Solutions Overview|By Role|Resources Hub|Company|Get free access|Customer Stories)\b.*?(?=\b(?:For Revenue Enablement|Meet Copilot|For Revenue Operations|By Use Case|Customers|Blog|Request A Demo|Industries|Resources|Sales Enablement)\b|\Z)',
        r'\b(?:Privacy Policy|CSR Policy|Terms of Service|Trust|Sitemap|Do Not Sell or Share My Personal Information)\b.*',  # Remove footer sections
        r'\b(?:Request A Demo|Download Full Case Study|Take the Quiz|Get the Report|Featured Case Study|Featured Resource)\b.*',  # Remove call-to-action sections
    ]

    for pattern in patterns:
        content = re.sub(pattern, '', content, flags=re.DOTALL)

    content = re.sub(r'\s+', ' ', content)
    content = re.sub(r'\s{2,}', '\n', content)
    
    content = content.strip()

    return content

def clean_file(input_file_path):
    with open(input_file_path, 'r', encoding='utf-8') as file:
        content = file.read()

    cleaned_content = clean_text(content)
    
    return cleaned_content
