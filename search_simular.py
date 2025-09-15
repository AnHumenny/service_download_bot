import os
from itertools import combinations

def similar(a, b):
    """Сравнивает два имени файлов и возвращает True, если они идентичны."""
    return a.lower() == b.lower()

def find_similar_filenames(folders):
    """Ищет файлы с одинаковыми именами в указанных папках."""

    all_files = []
    for folder in folders:
        try:
            if not os.path.isdir(folder):
                print(f"Папка не существует: {folder}")
                continue
            for root, _, files in os.walk(folder):
                for file in files:
                    if file.lower().endswith(('jpg', 'jpeg', 'png', 'gif')):
                        all_files.append((file, os.path.join(root, file)))
        except Exception as e:
            print(f"Ошибка при обработке папки {folder}: {e}")

    similar_pairs = []
    for (file1, path1), (file2, path2) in combinations(all_files, 2):
        if similar(file1, file2):
            similar_pairs.append((file1, path1, file2, path2))

    if similar_pairs:
        print("\nНайдены файлы с одинаковыми именами:")
        for file1, path1, file2, path2 in similar_pairs:
            print(f" - {file1} ({path1})")
            print(f"   идентичен {file2} ({path2})")
        print(f"Количество пар файлов с одинаковыми именами: {len(similar_pairs)}")
    else:
        print("Файлов с одинаковыми именами не найдено.")

if __name__ == "__main__":
    # Список папок для поиска
    folders = [
        "photos/ППР/Гомель/Попкина/15/30/",
        "photos/ППР/Гомель/Попкина/15/20/"
    ]

    find_similar_filenames(folders)