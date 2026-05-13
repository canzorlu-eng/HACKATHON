"""
ChromaDB ingestion script — loads data/reviews.jsonl into the reviews_v1 collection.

Usage (from backend/ directory):
    python -m scripts.ingest [--data-dir ../data] [--chroma-host localhost] [--chroma-port 8001]

Idempotent: uses review id as document id, upserting on each run.
Gate condition: verify with --count flag or run without --dry-run.
"""

import argparse
import json
import sys
from pathlib import Path


def load_reviews(jsonl_path: Path) -> list[dict]:
    reviews = []
    with jsonl_path.open(encoding="utf-8") as f:
        for line in f:
            line = line.strip()
            if line:
                reviews.append(json.loads(line))
    return reviews


def ingest(
    data_dir: Path,
    chroma_host: str,
    chroma_port: int,
    dry_run: bool = False,
) -> None:
    reviews_path = data_dir / "reviews.jsonl"
    if not reviews_path.exists():
        print(f"[ERROR] reviews.jsonl not found at {reviews_path}", file=sys.stderr)
        sys.exit(1)

    reviews = load_reviews(reviews_path)
    print(f"[INFO] Loaded {len(reviews)} reviews from {reviews_path}")

    if dry_run:
        print("[DRY-RUN] Would upsert the following sample:")
        for r in reviews[:3]:
            print(f"  id={r['id']} garment={r['garment_id']} text={r['review_tr'][:60]}...")
        return

    try:
        import chromadb
    except ImportError:
        print("[ERROR] chromadb package not installed. Run: pip install chromadb", file=sys.stderr)
        sys.exit(1)

    print(f"[INFO] Connecting to ChromaDB at {chroma_host}:{chroma_port}")
    try:
        client = chromadb.HttpClient(host=chroma_host, port=chroma_port)
        client.heartbeat()
    except Exception as exc:
        print(f"[ERROR] Cannot reach ChromaDB: {exc}", file=sys.stderr)
        print("[HINT] Start ChromaDB via: docker compose up chromadb", file=sys.stderr)
        sys.exit(1)

    col = client.get_or_create_collection(
        name="reviews_v1",
        metadata={"description": "HIWALOY customer review insights"},
    )
    print(f"[INFO] Collection reviews_v1 currently has {col.count()} documents")

    # Build upsert payload
    ids        = [r["id"]        for r in reviews]
    documents  = [r["review_tr"] for r in reviews]
    metadatas  = [
        {
            "garment_id":     r["garment_id"],
            "purchased_size": str(r.get("purchased_size", "")),
            "fits_true":      str(r.get("fits_true", True)),
            "themes":         r.get("themes", ""),
            "sentiment":      r.get("sentiment", "neutral"),
            "height_cm":      str(r.get("height_cm", 0)),
            "weight_kg":      str(r.get("weight_kg", 0)),
        }
        for r in reviews
    ]

    # Upsert in batches of 50 to avoid large request payloads
    batch_size = 50
    for start in range(0, len(reviews), batch_size):
        end = min(start + batch_size, len(reviews))
        col.upsert(
            ids=ids[start:end],
            documents=documents[start:end],
            metadatas=metadatas[start:end],
        )
        print(f"[INFO] Upserted reviews {start+1}–{end}")

    final_count = col.count()
    print(f"[OK] Ingestion complete — reviews_v1 collection now has {final_count} documents")

    # Quick sanity query
    results = col.query(query_texts=["slim fit gömlek küçük kalıplı"], n_results=3)
    print("[INFO] Sample query 'slim fit gömlek küçük kalıplı':")
    for doc, meta in zip(results["documents"][0], results["metadatas"][0]):
        print(f"  garment={meta['garment_id']} themes={meta['themes']}: {doc[:60]}...")


def main() -> None:
    parser = argparse.ArgumentParser(description="Ingest reviews into ChromaDB")
    parser.add_argument("--data-dir", default="../data", help="Path to data/ directory")
    parser.add_argument("--chroma-host", default="localhost")
    parser.add_argument("--chroma-port", type=int, default=8001)
    parser.add_argument("--dry-run", action="store_true", help="Parse only, do not write to ChromaDB")
    args = parser.parse_args()

    ingest(
        data_dir=Path(args.data_dir),
        chroma_host=args.chroma_host,
        chroma_port=args.chroma_port,
        dry_run=args.dry_run,
    )


if __name__ == "__main__":
    main()
