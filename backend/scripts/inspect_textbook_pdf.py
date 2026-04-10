import argparse
from pathlib import Path
import sys

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from app.services.textbook_service import (
    extract_toc,
    parse_and_chunk,
    summarizeChunkDistribution,
)


def main():
    parser = argparse.ArgumentParser(description="Inspect textbook TOC extraction and chunk labeling.")
    parser.add_argument("pdf_path", help="Absolute or relative path to the PDF file")
    parser.add_argument(
        "--chunks",
        action="store_true",
        help="Also run chunking and print per-chapter chunk coverage",
    )
    args = parser.parse_args()

    pdf_path = Path(args.pdf_path).expanduser().resolve()
    if not pdf_path.exists():
        raise SystemExit(f"File not found: {pdf_path}")

    file_bytes = pdf_path.read_bytes()
    chapters, total_pages = extract_toc(file_bytes)

    print(f"PDF: {pdf_path}")
    print(f"Total pages: {total_pages}")
    print(f"Detected chapters: {len(chapters)}")
    print("")

    suspicious = []
    for index, chapter in enumerate(chapters, start=1):
        span = chapter["end_page"] - chapter["start_page"] + 1
        if span <= 2:
            suspicious.append(f"{chapter['title']} has a very short span ({span} pages)")
        print(
            f"{index:>2}. {chapter['title']} | pages {chapter['start_page']}-{chapter['end_page']} "
            f"({span} pages)"
        )

    if suspicious:
        print("\nWarnings:")
        for warning in suspicious:
            print(f"- {warning}")

    if not args.chunks:
        return

    print("\nChunking...\n")
    chunks = parse_and_chunk(
        file_bytes=file_bytes,
        user_id="debug-user",
        textbook_id="debug-textbook",
        toc=chapters,
    )
    distribution = summarizeChunkDistribution(chunks, chapters)
    print(f"Total chunks: {len(chunks)}\n")

    for row in distribution:
        print(
            f"{row['title']} | expected pages {row['start_page']}-{row['end_page']} | "
            f"chunks={row['chunk_count']} | chunk pages {row['min_chunk_page']}-{row['max_chunk_page']}"
        )


if __name__ == "__main__":
    main()
