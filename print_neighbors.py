from pathlib import Path
from gensim.models import Word2Vec

MODEL_DIR = Path("models")
TARGET = "科学"
TOPN = 15


for file in sorted(MODEL_DIR.glob("20*.model")):
    year = file.stem
    model = Word2Vec.load(str(file))

    print("\n====================")
    print(year)
    print("====================")

    if TARGET not in model.wv:
        print("not found")
        continue

    for word, sim in model.wv.most_similar(TARGET, topn=TOPN):
        print(f"{word:15s} {sim:.3f}")