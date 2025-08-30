import os
import time
import subprocess
import chromadb
import tiktoken
from langchain.text_splitter import RecursiveCharacterTextSplitter
from sentence_transformers import SentenceTransformer
from contextlib import contextmanager

# --- Configuration ---
# Folders with your markdown files
DATA_FOLDERS = ["output_characters", "output_planets"]
CHROMA_HOST = "localhost"
CHROMA_PORT = 8000
COLLECTION_NAME = "strugatsky_universe-4"
EMBEDDING_MODEL_NAME = "ai-forever/sbert_large_mt_nlu_ru"

def start_chroma_container():
    """Starts the ChromaDB Docker container and waits for it to become healthy."""
    print("1. Starting ChromaDB container...")
    try:
        subprocess.run(["docker-compose", "up", "-d"], check=True)
        print("   Container started. Waiting for it to be healthy...")
        
        while True:
            try:
                client = chromadb.HttpClient(host=CHROMA_HOST, port=CHROMA_PORT)
                if client.heartbeat():
                    print("   ChromaDB is up and running!")
                    break
            except Exception:
                print("   ChromaDB not ready yet, retrying in 2 seconds...")
                time.sleep(2)
    except FileNotFoundError:
        print("Error: docker-compose not found. Please ensure it's installed and in your PATH.")
        exit(1)
    except subprocess.CalledProcessError as e:
        print(f"Error starting Docker container: {e}")
        exit(1)

def get_text_from_folders(folder_paths):
    """
    Reads and concatenates text from all files in multiple folders,
    keeping track of the source file.
    """
    documents = []
    
    for folder_path in folder_paths:
        if not os.path.exists(folder_path):
            print(f"Error: Folder '{folder_path}' not found.")
            return None
        
        print(f"   Reading files from: '{folder_path}'...")
        for filename in os.listdir(folder_path):
            if filename.endswith(".md"):
                file_path = os.path.join(folder_path, filename)
                print(f"      Reading file: {filename}")
                with open(file_path, "r", encoding="utf-8") as f:
                    content = f.read()
                    documents.append({
                        "content": content,
                        "metadata": {"source": file_path}
                    })
    return documents

def split_text_into_chunks(documents):
    encoding = tiktoken.get_encoding("cl100k_base")

    def count_tokens(text: str) -> int:
        """Подсчитывает количество токенов в строке."""
        return len(encoding.encode(text))

    text_splitter = RecursiveCharacterTextSplitter(
        chunk_size=200, # Размер чанка в символах
        chunk_overlap=30, # Количество символов, которые будут пересекаться между чанками
        length_function=count_tokens, # Используем нашу функцию подсчёта токенов
        separators=["\n\n", "\n", ". ", " ", ""] # Порядок разделителей
    )
    
    # Process each document separately to preserve source metadata
    chunks = []
    for doc in documents:
        split_chunks = text_splitter.create_documents([doc["content"]])
        for chunk in split_chunks:
            chunk.metadata = doc["metadata"]
            chunks.append(chunk)

    print(f"2. Text split into {len(chunks)} chunks.")
    return chunks

def get_embedding_function():
    """Loads the sentence-transformers model for creating embeddings."""
    print("3. Loading embedding model...")
    with timer("Загрузка модели"):
        model = SentenceTransformer(EMBEDDING_MODEL_NAME)
    
    # This wrapper function aligns with how ChromaDB expects embedding functions
    def embedding_function(texts):
        with timer("Кодирование текста"):
            return model.encode(texts).tolist()
    
    print("   Model loaded successfully.")
    return embedding_function

def main():
    """Main function to run the entire ingestion process."""
    # Ensure all data folders exist
    for folder in DATA_FOLDERS:
        if not os.path.exists(folder):
            os.makedirs(folder)
            print(f"Created folder '{folder}'. Please place your .md files inside.")
            
    # Exit if any folder is initially empty
    if not all(os.listdir(f) for f in DATA_FOLDERS):
        print("Please place .md files into the created folders. Exiting.")
        return

    start_chroma_container()

    documents = get_text_from_folders(DATA_FOLDERS)
    if not documents:
        print("No documents found to process. Exiting.")
        return

    with timer("Разбиваем текст на чанки"):
        chunks = split_text_into_chunks(documents)
    
    chunk_texts = [chunk.page_content for chunk in chunks]
    chunk_metadatas = [chunk.metadata for chunk in chunks]

    embedding_func = get_embedding_function()
    
    print("4. Creating embeddings and uploading to ChromaDB...")
    client = chromadb.HttpClient(host=CHROMA_HOST, port=CHROMA_PORT)

    try:
        client.delete_collection(COLLECTION_NAME)
        print(f"Collection '{COLLECTION_NAME}' has been deleted.")
    except Exception:
        pass
    
    collection = client.get_or_create_collection(
        name=COLLECTION_NAME,
        embedding_function=None
    )
   
    embeddings = embedding_func(chunk_texts)
    
    ids = [f"id{i}" for i in range(len(chunk_texts))]
    
    collection.add(
        documents=chunk_texts,
        embeddings=embeddings,
        metadatas=chunk_metadatas,
        ids=ids
    )

    print("\n✅ Ingestion complete! The vector index has been created.")
    print(f"   Collection '{COLLECTION_NAME}' now contains {collection.count()} documents.")

@contextmanager
def timer(name="Блок"):
    """
    Контекстный менеджер для замера времени выполнения блока кода.
    
    Пример использования:
    with timer("Сложный расчёт"):
        # ... ваш код ...
    """
    start_time = time.perf_counter()
    try:
        yield
    finally:
        end_time = time.perf_counter()
        elapsed_time = end_time - start_time
        print(f"[{name}] выполнился за {elapsed_time:.4f} секунд.")

if __name__ == "__main__":
    with timer("Создание векторного индекса"):
        main()

