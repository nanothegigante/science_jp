from pathlib import Path
from gensim.models import Word2Vec
import matplotlib.pyplot as plt
from sklearn.decomposition import PCA
import umap

MODEL_DIR = Path("models")
TARGET = "科学"
TOPN = 20


def plot_year(year, model):
    words = [TARGET]
    sims = model.wv.most_similar(TARGET, topn=TOPN)
    words += [w for w, _ in sims]

    vecs = [model.wv[w] for w in words]

    # PCA
    pca = PCA(n_components=2)
    coords = pca.fit_transform(vecs)

    plt.figure(figsize=(6,6))
    for i, w in enumerate(words):
        x, y = coords[i]
        plt.scatter(x, y)
        plt.text(x, y, w)

    plt.title(f"PCA {year}")
    plt.tight_layout()
    plt.savefig(f"plots/pca_{year}.png")
    plt.close()


def plot_umap_year(year, model):
    words = [TARGET]
    sims = model.wv.most_similar(TARGET, topn=TOPN)
    words += [w for w, _ in sims]

    vecs = [model.wv[w] for w in words]

    reducer = umap.UMAP()
    coords = reducer.fit_transform(vecs)

    plt.figure(figsize=(6,6))
    for i, w in enumerate(words):
        x, y = coords[i]
        plt.scatter(x, y)
        plt.text(x, y, w)

    plt.title(f"UMAP {year}")
    plt.tight_layout()
    plt.savefig(f"plots/umap_{year}.png")
    plt.close()


Path("plots").mkdir(exist_ok=True)

for file in sorted(MODEL_DIR.glob("20*.model")):
    year = file.stem
    print("plotting", year)

    model = Word2Vec.load(file)

    if TARGET not in model.wv:
        continue

    plot_year(year, model)
    plot_umap_year(year, model)

print("done")