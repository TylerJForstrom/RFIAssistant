import pandas as pd
import matplotlib.pyplot as plt
from sklearn.feature_extraction.text import TfidfVectorizer
from sklearn.decomposition import TruncatedSVD
from pathlib import Path

csv_path = Path("data/raw/rfis.csv")
df = pd.read_csv(csv_path)

for col in ["subject", "question_text", "response_text", "trade", "spec_section", "project_name"]:
    if col not in df.columns:
        df[col] = ""
    df[col] = df[col].fillna("").astype(str)

df["combined_text"] = (
    df["subject"] + " " +
    df["question_text"] + " " +
    df["response_text"] + " " +
    df["trade"] + " " +
    df["spec_section"] + " " +
    df["project_name"]
)

vectorizer = TfidfVectorizer(
    stop_words="english",
    ngram_range=(1, 2),
    min_df=1
)
X = vectorizer.fit_transform(df["combined_text"])

n_components = 2 if X.shape[1] >= 2 else 1
svd = TruncatedSVD(n_components=n_components, random_state=42)
coords = svd.fit_transform(X)

if n_components == 1:
    x = coords[:, 0]
    y = [0] * len(x)
else:
    x = coords[:, 0]
    y = coords[:, 1]

plt.figure(figsize=(12, 8))
plt.scatter(x, y)

for i, row in df.iterrows():
    label = f"RFI {row['rfi_id']} ({row['trade']})"
    plt.annotate(label, (x[i], y[i]), xytext=(5, 5), textcoords="offset points")

plt.title("RFI Semantic Clusters (TF-IDF + SVD)")
plt.xlabel("Latent Semantic Dimension 1")
plt.ylabel("Latent Semantic Dimension 2")
plt.tight_layout()

output_path = Path("plots/rfi_clusters.png")
plt.savefig(output_path, dpi=200)
print(f"Saved plot to {output_path}")
