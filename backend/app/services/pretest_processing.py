import traceback
from app.services.llm_service import LLMService
from app.services.supabase_service import (
    check_pretest_exists,
    store_pretest,
    store_chapter_topics
)
from app.services.vector_service import (
    fetch_all_chunks,
    retrieve_context
)
from celery import shared_task
from app.config import settings


# Builds a light even sample of the chapter for topic extraction (Pass 1)
# Pass 2 handles its own retrieval per topic via retrieve_context
def build_pretest_context(textbook_id, chapter_title, max_chars=20000, num_buckets=14):

    all_results = fetch_all_chunks(textbook_id, chapter_title)
    if not all_results:
        return ""

    hits = sorted(all_results, key=lambda p: p.payload.get("page_start") or 0)

    # Divide chunks into evenly-spaced buckets, pick the longest chunk per bucket
    # so we get one representative sample from each section of the chapter
    n = len(hits)
    bucket_size = max(1, n // num_buckets)
    sampled = []
    for i in range(0, n, bucket_size):
        bucket = hits[i : i + bucket_size]
        best = max(bucket, key=lambda p: len(p.payload.get("text") or ""))
        sampled.append(best)

    # Build context string from sampled chunks
    parts = []
    total = 0
    for hit in sampled:
        text = (hit.payload.get("text") or "").strip()
        citation = hit.payload.get("citation", "")
        if not text:
            continue
        snippet = f"{citation}: {text}" if citation else text
        # Skip oversized chunks but keep going rather than stopping early
        if total + len(snippet) > max_chars:
            continue
        parts.append(snippet)
        total += len(snippet)

    return "\n\n".join(parts)

def generate_chapter_pretest(user_id, textbook_id, chapter, llm):
    chapter_id = chapter["id"]
    chapter_title = chapter["title"]

    # Check if this chapter already has a pretest
    if check_pretest_exists(textbook_id, chapter_id):
        print(f"[pretest] '{chapter_title}' already has a pretest, moving on")
        return

    # Pass 1: Generate/Extract the core topics of that chapter (used for question labeling)
    print(f"[pretest] extracting topics for '{chapter_title}'")
    topic_context = build_pretest_context(textbook_id, chapter_title)
    if not topic_context.strip():
        print(f"[pretest] no context found for '{chapter_title}', skipping")
        return

    # Get the topics generated and clean them up
    try:
        topics = llm.extract_chapter_topics(topic_context)
    except Exception as e:
        print(f"[pretest] topic extraction failed for '{chapter_title}':", repr(e))
        traceback.print_exc()
        return

    topic_labels = [
        (t.get("label") or "").strip()
        for t in topics
        if (t.get("label") or "").strip()
    ]

    if not topic_labels:
        print(f"[pretest] no valid topic labels extracted for '{chapter_title}'")
        return

    try:
        store_chapter_topics(chapter_id, topic_labels)
    except Exception as e:
        print(f"[pretest] failed to store topics for '{chapter_title}':", repr(e))
        traceback.print_exc()

    print(f"[pretest] got {len(topic_labels)} topics: {topic_labels}")

    # Pass 2: for each topic, retrieve the most relevant chunks scoped to this chapter
    # then pass each topic and its context to the LLM in one batch
    topic_contexts = []
    for label in topic_labels:
        context = retrieve_context(
            user_id=user_id,
            textbook_id=textbook_id,
            query=label,
            top_k=6,
            chapter_title=chapter_title
        )

        if not context.strip():
            print(f"[pretest] no context found for topic '{label}', skipping")
            continue

        topic_contexts.append({
            "topic": label,
            "context": context.strip(),
        })

    if not topic_contexts:
        print(f"[pretest] all topics had empty context for '{chapter_title}'")
        return

    # Call the LLM to generate the entire pretest in one batch
    print(f"[pretest] generating 12 questions across {len(topic_contexts)} topics for '{chapter_title}'")
    try:
        questions = llm.generate_pretest_from_topics(topic_contexts)
    except Exception as e:
        print(f"[pretest] LLM call failed for '{chapter_title}':", repr(e))
        traceback.print_exc()
        return

    if not questions:
        print(f"[pretest] no questions returned for '{chapter_title}'")
        return

    # Write questions to Supabase
    try:
        store_pretest(textbook_id, chapter_id, chapter_title, questions)
        print(f"[pretest] stored {len(questions)} questions for '{chapter_title}'")
    except Exception as e:
        print(f"[pretest] failed to store for '{chapter_title}':", repr(e))
        traceback.print_exc()

# Generate a pretest for EVERY chapter
@shared_task
def generate_all_pretests(user_id, textbook_id, toc):
    try:
        llm = LLMService(api_key=settings.NAVIGATOR_API_KEY)
        for chapter in toc:
            generate_chapter_pretest(user_id, textbook_id, chapter, llm)
        print("[pretests] all done")
    except Exception as e:
        print("PRETEST GENERATION FAILED:", repr(e))
        traceback.print_exc()