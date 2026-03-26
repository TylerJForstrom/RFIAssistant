import pandas as pd
from sklearn.feature_extraction.text import TfidfVectorizer
from sklearn.decomposition import TruncatedSVD
from scipy.cluster.hierarchy import linkage, fcluster


def build_issue_analysis(csv_path: str = "data/raw/rfis.csv", n_clusters: int = 4):
    df = pd.read_csv(csv_path).copy()

    for col in ["rfi_id", "subject", "question_text", "response_text", "trade", "spec_section", "project_name"]:
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

    if len(df) == 1:
        df["cluster"] = 1
    else:
        max_components = min(10, max(1, X.shape[1] - 1), len(df) - 1)
        svd = TruncatedSVD(n_components=max_components, random_state=42)
        reduced = svd.fit_transform(X)

        k = min(n_clusters, len(df))
        if len(df) < 2:
            df["cluster"] = 1
        else:
            Z = linkage(reduced, method="ward")
            df["cluster"] = fcluster(Z, t=k, criterion="maxclust")

    top_trades = (
        df["trade"]
        .replace("", "Unknown")
        .value_counts()
        .reset_index()
    )
    top_trades.columns = ["trade", "count"]

    top_spec_sections = (
        df["spec_section"]
        .replace("", "Unknown")
        .value_counts()
        .reset_index()
    )
    top_spec_sections.columns = ["spec_section", "count"]

    top_subjects = (
        df["subject"]
        .replace("", "Unknown")
        .value_counts()
        .reset_index()
    )
    top_subjects.columns = ["subject", "count"]

    cluster_summary = (
        df.groupby("cluster")
        .agg(
            count=("rfi_id", "count"),
            example_trade=("trade", lambda x: x.mode().iloc[0] if not x.mode().empty else "Unknown"),
            example_spec=("spec_section", lambda x: x.mode().iloc[0] if not x.mode().empty else "Unknown"),
            sample_subject=("subject", lambda x: x.iloc[0] if len(x) > 0 else "Unknown"),
        )
        .reset_index()
        .sort_values("count", ascending=False)
    )

    cluster_details = []
    for cluster_id in sorted(df["cluster"].unique()):
        cluster_df = df[df["cluster"] == cluster_id].copy()
        items = cluster_df[[
            "rfi_id",
            "project_name",
            "trade",
            "spec_section",
            "subject",
            "question_text",
            "response_text"
        ]].to_dict(orient="records")

        cluster_details.append({
            "cluster_id": int(cluster_id),
            "count": int(len(cluster_df)),
            "items": items
        })

    return {
        "top_trades": top_trades.to_dict(orient="records"),
        "top_spec_sections": top_spec_sections.to_dict(orient="records"),
        "top_subjects": top_subjects.to_dict(orient="records"),
        "cluster_summary": cluster_summary.to_dict(orient="records"),
        "cluster_details": cluster_details,
    }
