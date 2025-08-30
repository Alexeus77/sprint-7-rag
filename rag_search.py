import sys
import chromadb
import ollama
from sentence_transformers import SentenceTransformer
import time

# --- Конфигурация RAG-системы ---
CHROMA_HOST = "localhost"
CHROMA_PORT = 8000
COLLECTION_NAME = "strugatsky_universe-4"
EMBEDDING_MODEL_NAME = "ai-forever/sbert_large_mt_nlu_ru"
LLM_MODEL_NAME = "gemma2:2b"

def get_embedding_model():
    """Загружает модель, использовавшуюся для создания эмбеддингов."""
    try:
        model = SentenceTransformer(EMBEDDING_MODEL_NAME)
        return model
    except Exception as e:
        print(f"Ошибка при загрузке модели: {e}")
        sys.exit(1)

def main():
    """
    Основная функция для выполнения RAG-запросов.
    """
    print("--- Запуск RAG-системы ---")
    
    # 1. Загрузка компонентов
    try:
        chroma_client = chromadb.HttpClient(host=CHROMA_HOST, port=CHROMA_PORT)
        chroma_client.heartbeat()
        collection = chroma_client.get_collection(name=COLLECTION_NAME)
        print("✅ Успешное подключение к ChromaDB.")

        ollama_client = ollama.Client()
        ollama_client.list() # Проверка связи с Ollama
        print(f"✅ Успешное подключение к Ollama с моделью '{LLM_MODEL_NAME}'.")
        
    except Exception as e:
        print(f"Ошибка подключения: {e}")
        print("Убедитесь, что ChromaDB и Ollama запущены.")
        sys.exit(1)

    embedding_model = get_embedding_model()

    print("\nСистема готова. Введите ваш запрос. Для выхода напишите 'выход' или 'exit'.")

    while True:
        query_text = input("\nВаш запрос: ")
        if query_text.lower() in ["выход", "exit", "quit"]:
            break
            
        start_time = time.time()

        # 2. Поиск в базе (Retrieval)
        try:
            query_embedding = embedding_model.encode(query_text).tolist()
            
            retrieved_chunks = collection.query(
                query_embeddings=[query_embedding],
                n_results=3, # Получаем 3 самых релевантных фрагмента
                include=['documents']
            )

            # Формируем контекст из найденных фрагментов
            context = ""
            if retrieved_chunks['documents'] and retrieved_chunks['documents'][0]:
                context = "\n".join(retrieved_chunks['documents'][0])
                print("✅ Найдены релевантные фрагменты из базы знаний.")
            else:
                print("⚠️ Не удалось найти релевантные фрагменты. Ответ будет на основе общей эрудиции модели.")

        except Exception as e:
            print(f"Ошибка при поиске в базе: {e}. Попробуйте ещё раз.")
            continue

        # 3. Формирование промпта для LLM
        prompt_template = f"""
        System: Ты помощник, который отвечает на вопросы, используя ТОЛЬКО предоставленный контекст.
        Если контекст не содержит ответа на вопрос, скажи "Извините, я не знаю."
        Не используй свои знания. Не отвечай на других языках. Используй только русский язык.

        Контекст:
        ---
        {context}
        ---

        Пользователь:
        {query_text}

        Отвечай строго в следующем формате:

        Размышления:
        1. ...
        2. ...
        3. ...

        Ответ:
        ...
        """

        # 4. Отправка в LLM (Generation)
        try:
            print("⏳ Формирую ответ...")
            response = ollama_client.chat(
                model=LLM_MODEL_NAME,
                messages=[
                    {'role': 'user', 'content': prompt_template}
                ],
                options={
                    "temperature": 0.1,  # Lower to reduce creativity and hallucinations
                    "top_p": 0.2,        # Limit to the most probable tokens
                    "mirostat": 0,       # Disable mirostat for more deterministic output
                }
            )
            llm_answer = response['message']['content']
            
            end_time = time.time()
            elapsed_time = end_time - start_time
            
            # 5. Возврат результата
            print("\n--- Ответ ---")
            if llm_answer.strip().endswith("Извините, я не знаю."):
                print('\033[91m' + llm_answer + '\033[0m')
            else:
                print('\033[92m' + llm_answer + '\033[0m')
            print(f"\nВремя выполнения запроса: {elapsed_time:.2f} сек.")
            
        except Exception as e:
            print(f"Ошибка при обращении к LLM: {e}")
            print("Убедитесь, что Ollama запущен и модель загружена.")

if __name__ == "__main__":
    main()