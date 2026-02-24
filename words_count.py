from pathlib import Path

for p in sorted(Path("txt_clean").glob("*.clean.txt")):
    text = p.read_text(encoding="utf-8")
    tokens = text.split()
    print(p.name, "chars:", len(text), "words:", len(tokens))