from .supabase_service import check_pretest_exists, get_toc

# Helper functions for getting info on textbooks

# Gets the textbook title (without file extension)
def display_title(title: str) -> str:
    if not title:
        return "Untitled textbook"
    return title[:-4] if title.lower().endswith(".pdf") else title


# Tracks the textbook upload progress, updating its state though each stage (status set in procesing file)
def build_textbook_progress(info: dict) -> dict:
    textbook_id = info["id"]
    toc = get_toc(textbook_id)
    chapter_count = len(toc)
    # pretests_ready = sum(
    #     1 for ch in toc if check_pretest_exists(textbook_id, ch["id"])
    # )
    pretests_ready = 0
    for ch in toc:
        try:
            if check_pretest_exists(textbook_id, ch["id"]):
                pretests_ready += 1
        except Exception as e:
            print(f"[textbook_progress] check_pretest_exists failed for chapter {ch['id']}: {e}")

    status = (info.get("status") or "").strip()
    page_count = int(info.get("page_count") or 0)
    chunk_count = int(info.get("chunk_count") or 0)

    if not status:
        status = "ready" if chapter_count and pretests_ready == chapter_count else "processing"

    if status == "ready":
        return {
            "status": "ready",
            "progress_percent": 100,
            "stage_label": "Ready",
            "detail": "Textbook is ready to open.",
            "chapter_count": chapter_count,
            "pretests_ready": pretests_ready,
            "can_open": True,
        }

    if status == "partial":
        return {
            "status": "partial",
            "progress_percent": 100,
            "stage_label": "Complete",
            "detail": "Textbook is usable, but parsing coverage was partial.",
            "chapter_count": chapter_count,
            "pretests_ready": pretests_ready,
            "can_open": True,
        }

    if status == "generating_pretests":
        ratio = (pretests_ready / chapter_count) if chapter_count else 1
        progress_percent = min(99, 80 + round(ratio * 19))

        return {
            "status": "generating_pretests",
            "progress_percent": progress_percent,
            "stage_label": "Generating pretests",
            "detail": (
                f"Building chapter pretests ({pretests_ready}/{chapter_count})."
                if chapter_count
                else "Building chapter pretests."
            ),
            "chapter_count": chapter_count,
            "pretests_ready": pretests_ready,
            "can_open": False,
        }

    if status == "failed":
        return {
            "status": "failed",
            "progress_percent": 100,
            "stage_label": "Failed",
            "detail": "Something went wrong while processing this textbook.",
            "chapter_count": chapter_count,
            "pretests_ready": pretests_ready,
            "can_open": False,
        }
    
    pages_done = min(chunk_count, page_count) if page_count > 0 else 0
    progress_percent = (
        max(5, round((pages_done / page_count) * 80))
        if page_count > 0
        else 5
    )


    return {
        "status": "parsing",
        "progress_percent": progress_percent,
        "stage_label": "Parsing textbook",
        "detail": (
            f"Parsing pages {pages_done}/{page_count}."
            if page_count > 0
            else "Extracting chapters, chunking pages, and indexing content."
        ),
        "chapter_count": chapter_count,
        "pretests_ready": pretests_ready,
        "can_open": False,
    }

# combines general textbook info with progress info
def serialize_textbook_card(info: dict) -> dict:
    progress = build_textbook_progress(info)

    return {
        "id": info["id"],
        "title": info.get("title"),
        "display_title": display_title(info.get("title")),
        "storage_path": info.get("storage_path"),
        "is_starred": bool(info.get("is_starred", True)),
        **progress,
    }