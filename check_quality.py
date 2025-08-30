import chromadb
from sentence_transformers import SentenceTransformer
import sys

# --- Configuration ---
CHROMA_HOST = "localhost"
CHROMA_PORT = 8000
COLLECTION_NAME = "strugatsky_universe-4"
EMBEDDING_MODEL_NAME = "ai-forever/sbert_large_mt_nlu_ru"

def get_embedding_function():
    """Загружает модель, использовавшуюся для создания эмбеддингов."""
    try:
        model = SentenceTransformer(EMBEDDING_MODEL_NAME)
        # ChromaDB ожидает, что функция вернет список списков
        def embedding_function_wrapper(texts):
            return model.encode(texts).tolist()
        return embedding_function_wrapper
    except Exception as e:
        print(f"Ошибка при загрузке модели: {e}. Убедитесь, что у вас есть доступ к интернету.")
        sys.exit(1)

def main():
    """
    Основная функция для выполнения поисковых запросов.
    """
    print("--- Запуск проверки качества индекса ---")

    try:
        client = chromadb.HttpClient(host=CHROMA_HOST, port=CHROMA_PORT)
        # Проверяем, что ChromaDB доступна
        client.heartbeat()
        print("✅ Успешное подключение к ChromaDB.")
        
        # Получаем коллекцию по её имени
        collection = client.get_collection(name=COLLECTION_NAME)
        print(f"✅ Коллекция '{COLLECTION_NAME}' загружена.")
        print(f"   Содержит {collection.count()} документов.")

    except Exception as e:
        print(f"Ошибка: Не удалось подключиться к ChromaDB. Убедитесь, что контейнер запущен.")
        print(f"   Выполните команду 'docker-compose up -d' и попробуйте снова.")
        sys.exit(1)

    # Загружаем ту же модель, что и для создания векторов
    embedding_func = get_embedding_function()

    # --- Тестовые запросы ---
    test_queries = [
        "Есть ли дети у Маии Тоиво?",
        "Опиши любую обитаемую планету",
        "Кто из персонажей модифицировал себя?",
        "С кем взаимодействует Судольф Тикорски?",
        "Какие столицы существуют на планетах?",
        "На каких планетах побывал Максим Ламмерер?",
        "Расскажи о семье Максима Ламмерера",
    ]

    print("\n--- Запуск тестовых запросов ---")

    for i, query_text in enumerate(test_queries):
        # Получаем вектор для запроса
        query_embedding = embedding_func([query_text])[0]
        
        # Выполняем поиск по вектору в базе данных
        results = collection.query(
            query_embeddings=[query_embedding],
            n_results=5,  # Получаем 5 самых релевантных результатов
            include=['documents', 'distances', 'metadatas']
        )
        
        print(f"\nЗапрос #{i+1}: '{query_text}'")
        print("--------------------------------------------------")
        
        if not results['documents'][0]:
            print("   Результатов не найдено. Возможно, коллекция пуста.")
            continue

        for doc, distance, metadata in zip(results['documents'][0], results['distances'][0], results['metadatas'][0]):
            source = metadata.get('source', 'unknown source')
            print(f"  > Фрагмент из '{source}' (дистанция: {distance:.4f})")
            print(f"  {doc[:150]}...\n") # Выводим первые 150 символов
        
    print("--- Проверка завершена ---")


if __name__ == "__main__":
    main()