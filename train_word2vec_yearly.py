from pathlib import Path
from gensim.models import Word2Vec

TOKEN_DIR = Path("tokens")
MODEL_DIR = Path("models")
MODEL_DIR.mkdir(exist_ok=True)

VECTOR_SIZE = 200
WINDOW = 5
MIN_COUNT = 5
EPOCHS = 20


def load_tokens(path):
    text = path.read_text(encoding="utf-8")
    tokens = text.split()
    return [tokens]  # gensimは文リストが必要


for file in sorted(TOKEN_DIR.glob("20*.tokens.txt")):
    year = file.stem.split(".")[0]

    print("training", year)

    sentences = load_tokens(file)

    model = Word2Vec(
        sentences=sentences,
        vector_size=VECTOR_SIZE,
        window=WINDOW,
        min_count=MIN_COUNT,
        sg=1,  # skip-gram
        epochs=EPOCHS,
        workers=4
    )

    save_path = MODEL_DIR / f"{year}.model"
    model.save(str(save_path))

print("done")