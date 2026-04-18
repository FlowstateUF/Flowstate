import os, tempfile, re
os.environ["HF_HUB_DISABLE_SYMLINKS"] = "1"
os.environ["HF_HUB_DISABLE_SYMLINKS_WARNING"] = "1"
import pymupdf
import tiktoken
from docling.chunking import HybridChunker
from docling.datamodel.base_models import InputFormat
from docling.datamodel.pipeline_options import PdfPipelineOptions, RapidOcrOptions, PictureDescriptionVlmOptions
from docling.document_converter import DocumentConverter, PdfFormatOption
from docling_core.transforms.chunker.tokenizer.openai import OpenAITokenizer


# Removed this as it is bottleneckign uplaod, could be added again later
# smolvlm_picture_description = PictureDescriptionVlmOptions(
#     repo_id="HuggingFaceTB/SmolVLM-256M-Instruct",
#     prompt="Describe this image in the context of a textbook. Focus on any data, labels, or concepts shown."
# )

# pipeline_options = PdfPipelineOptions(
#     generate_page_images=True,
#     generate_picture_images=True,
#     images_scale=1.0,
#     do_ocr=True,
#     do_table_structure=True,
#     do_picture_description=True,
#     ocr_options=RapidOcrOptions(),
#     picture_description_options=smolvlm_picture_description
# )

pipeline_options = PdfPipelineOptions(
    generate_page_images=False,
    generate_picture_images=False,
    images_scale=0.5,
    do_ocr=False,
    do_table_structure=False,
    do_picture_description=False
)

converter = DocumentConverter(
    format_options={InputFormat.PDF: PdfFormatOption(pipeline_options=pipeline_options)}
)

tokenizer = OpenAITokenizer(
    model_name="gpt-4o-mini",
    tokenizer=tiktoken.encoding_for_model("gpt-4o-mini"),
    max_tokens=512
    )
chunker = HybridChunker(tokenizer=tokenizer, max_tokens=512, overlap=64)

MAIN_CHAPTER_REGEX = re.compile(
    r"^\s*(?:chapter\s+)?(\d+)(?!\.\d)\b(?:\s*[.:_-]\s*|\s+)",
    re.IGNORECASE,
)
CHAPTER_NUMBER_WORD_PATTERN = (
    r"one|two|three|four|five|six|seven|eight|nine|ten|"
    r"eleven|twelve|thirteen|fourteen|fifteen|sixteen|seventeen|eighteen|nineteen|"
    r"twenty(?:[\s-]+(?:one|two|three|four|five|six|seven|eight|nine))?|"
    r"thirty(?:[\s-]+(?:one|two|three|four|five|six|seven|eight|nine))?|"
    r"forty(?:[\s-]+(?:one|two|three|four|five|six|seven|eight|nine))?|"
    r"fifty(?:[\s-]+(?:one|two|three|four|five|six|seven|eight|nine))?"
)
WORD_OR_ROMAN_CHAPTER_REGEX = re.compile(
    rf"^\s*chapter\s+(?:{CHAPTER_NUMBER_WORD_PATTERN}|[ivxlcdm]+)\b(?:\s*[.:_-]\s*|\s+)",
    re.IGNORECASE,
)
CHAPTER_PREFIX_REGEX = re.compile(
    rf"^\s*(?:chapter\s+(?:\d+(?!\.\d)\b|{CHAPTER_NUMBER_WORD_PATTERN}\b|[ivxlcdm]+\b)|\d+(?!\.\d)\b)(?:\s*[.:_-]\s*|\s+)",
    re.IGNORECASE,
)
END_REGEX = re.compile(
    r"""(?i)(
        conclusion|
        concluding(\s+remarks)?|
        final\s+(summary|remarks|thoughts)|
        summary|
        synthesis|
        wrap[-\s]?up|
        review\s+and\s+outlook|
        putting\s+it\s+all\s+together|
        capstone|
        integrat(ing|ion)|
        comprehensive\s+(review|summary)|
        case\s+studies?|
        applications?|
        advanced\s+applications?|
        review|
        practice\s+problems?|
        test\s+yourself|
        exam\s+preparation|
        self[-\s]?assessment|
        appendix(\s+[a-z])?|
        appendices|
        math(ematical)?\s+background|
        math\s+review|
        algebra\s+review|
        calculus\s+review|
        technical\s+background|
        derivations?|
        data\s+tables?|
        statistical\s+tables?|
        conversion\s+tables?|
        additional\s+figures?|
        supplementary\s+data|
        worked\s+examples?|
        selected\s+solutions?|
        solutions?\s+to|
        additional\s+exercises?|
        glossary|
        index|
        list\s+of\s+symbols|
        list\s+of\s+abbreviations|
        notation\s+guide
    )""",
    re.VERBOSE
)
FRONT_MATTER_REGEX = re.compile(
    r"""(?i)^(
        contents?|
        table\s+of\s+contents|
        copyright|
        title\s+page|
        dedication|
        foreword|
        preface|
        acknowledg(e)?ments?|
        about\s+the\s+author|
        authors?\s+note|
        how\s+to\s+use\s+this\s+book|
        how\s+to\s+read\s+this\s+book
    )$""",
    re.VERBOSE,
)
def normalize_text(s: str) -> str:
    s = s.replace("\u00a0", " ")
    s = re.sub(r"[ \t]{2,}", " ", s)
    s = re.sub(r"\n{3,}", "\n\n", s)
    return s.strip()

def pdf_page_range(pdf_bytes: bytes, start_page: int, end_page: int) -> bytes:
    src = pymupdf.open(stream=pdf_bytes, filetype="pdf")
    try:
        return pdf_page_range_from_doc(src, start_page, end_page)
    finally:
        src.close()

def pdf_page_range_from_doc(src: pymupdf.Document, start_page: int, end_page: int) -> bytes:
    out = pymupdf.open()
    try:
        out.insert_pdf(src, from_page=start_page-1, to_page=end_page-1)
        return out.tobytes()
    finally:
        out.close()

def isMainChapterTitle(title: str) -> bool:
    normalized = (title or "").strip()
    return bool(MAIN_CHAPTER_REGEX.match(normalized) or WORD_OR_ROMAN_CHAPTER_REGEX.match(normalized))

def stripChapterNumberPrefix(title: str) -> str:
    return CHAPTER_PREFIX_REGEX.sub("", (title or "").strip()).strip()

def isSkippableTocTitle(title: str) -> bool:
    normalized = stripChapterNumberPrefix(title)
    return bool(FRONT_MATTER_REGEX.search(normalized) or END_REGEX.search(normalized))

def selectMainChapterEntries(toc: list[list]) -> list[tuple[int, str, int]]:
    if not toc:
        return []

    levels = sorted({item[0] for item in toc})
    ranked_candidates: list[tuple[int, int, list[tuple[int, str, int]]]] = []

    for level in levels:
        entries = [item for item in toc if item[0] == level]
        numbered_entries = [
            item for item in entries
            if isMainChapterTitle(item[1] or "")
        ]
        if numbered_entries:
            ranked_candidates.append((len(numbered_entries), -level, numbered_entries))

    if ranked_candidates:
        ranked_candidates.sort(reverse=True)
        best_count, _, best_entries = ranked_candidates[0]
        if best_count >= 2:
            return best_entries

    fallback_candidates: list[tuple[int, int, list[tuple[int, str, int]]]] = []
    for level in levels:
        entries = [item for item in toc if item[0] == level]
        filtered_entries = [
            item for item in entries
            if not isSkippableTocTitle(item[1] or "")
        ]
        if filtered_entries:
            fallback_candidates.append((len(filtered_entries), -level, filtered_entries))

    if fallback_candidates:
        fallback_candidates.sort(reverse=True)
        best_count, _, best_entries = fallback_candidates[0]
        if best_count >= 2:
            return best_entries

    return [
        item for item in toc
        if isMainChapterTitle(item[1] or "") and not isSkippableTocTitle(item[1] or "")
    ]

def buildChapterRanges(level_toc: list[tuple[int, str, int]], total_pages: int) -> list[dict]:
    chapters = []

    for i, (_, title, start_page) in enumerate(level_toc):
        if isSkippableTocTitle(title):
            continue

        if i == len(level_toc) - 1:
            end_page = total_pages
        else:
            end_page = level_toc[i + 1][2] - 1

        chapters.append({
            "title": title,
            "start_page": start_page,
            "end_page": max(start_page, end_page),
        })

    return chapters

# Normalizes a page label so lookups are less picky.
def normalizePageLabel(label: str | None) -> str:
    return re.sub(r"\s+", "", (label or "").strip()).lower()

# Looks up the real PDF page for a shown page label.
def lookupPhysicalPageForLabel(textbook: pymupdf.Document, page_label: str | int | None) -> int | None:
    if page_label in (None, "") or not hasattr(textbook, "get_page_numbers"):
        return None

    candidates = []
    raw_label = str(page_label).strip()
    normalized_label = normalizePageLabel(raw_label)

    if raw_label:
        candidates.append(raw_label)
    if normalized_label and normalized_label != raw_label:
        candidates.append(normalized_label)

    for candidate in candidates:
        try:
            hits = textbook.get_page_numbers(candidate, only_one=True)
        except TypeError:
            hits = textbook.get_page_numbers(candidate)
            if hits:
                hits = hits[:1]
        except Exception:
            hits = []

        if hits:
            return int(hits[0]) + 1

    return None

# Uses PDF page labels when the TOC is talking in shown book pages.
def resolveTocStartPages(textbook: pymupdf.Document, level_toc: list[tuple[int, str, int]]) -> list[tuple[int, str, int]]:
    if not level_toc:
        return level_toc

    resolved_entries = []
    translated_count = 0
    previous_page = 0

    for level, title, start_page in level_toc:
        resolved_page = lookupPhysicalPageForLabel(textbook, start_page)
        candidate_page = resolved_page if isinstance(resolved_page, int) else start_page

        if not isinstance(candidate_page, int) or candidate_page < previous_page:
            return level_toc

        if isinstance(resolved_page, int) and resolved_page != start_page:
            translated_count += 1

        resolved_entries.append((level, title, candidate_page))
        previous_page = candidate_page

    return resolved_entries if translated_count >= 1 else level_toc

def getChapterForPage(page: int, toc: list[dict]) -> str:
    if not page or not toc:
        return "Unknown"

    for chapter in toc:
        if chapter["start_page"] <= page <= chapter["end_page"]:
            return chapter["title"]

    previous = [chapter for chapter in toc if chapter["start_page"] <= page]
    return previous[-1]["title"] if previous else toc[0]["title"]

def getChapterForPages(pages: list[int], toc: list[dict]) -> str:
    valid_pages = [page for page in pages if isinstance(page, int)]
    if not valid_pages:
        return "Unknown"

    chapter_counts: dict[str, int] = {}
    for page in valid_pages:
        chapter_title = getChapterForPage(page, toc)
        chapter_counts[chapter_title] = chapter_counts.get(chapter_title, 0) + 1

    top_count = max(chapter_counts.values())
    top_chapters = [title for title, count in chapter_counts.items() if count == top_count]

    if len(top_chapters) == 1:
        return top_chapters[0]

    midpoint_page = valid_pages[len(valid_pages) // 2]
    return getChapterForPage(midpoint_page, toc)

def summarizeChunkDistribution(chunks: list[dict], toc: list[dict]) -> list[dict]:
    summary = []
    for chapter in toc:
        chapter_chunks = [
            chunk for chunk in chunks
            if chunk.get("chapter") == chapter["title"]
        ]
        pages = [chunk.get("page_start") for chunk in chapter_chunks if isinstance(chunk.get("page_start"), int)]
        summary.append({
            "title": chapter["title"],
            "start_page": chapter["start_page"],
            "end_page": chapter["end_page"],
            "chunk_count": len(chapter_chunks),
            "min_chunk_page": min(pages) if pages else None,
            "max_chunk_page": max(pages) if pages else None,
        })
    return summary

# Pulls chapter ranges out of the PDF TOC.
def extract_toc(file: bytes) -> tuple[list[dict], int]:
    textbook = pymupdf.open(stream=file, filetype="pdf")
    toc = textbook.get_toc()
    total_pages = textbook.page_count

    try:
        if toc:
            level_toc = selectMainChapterEntries(toc)
            if len(level_toc) >= 2:
                level_toc = resolveTocStartPages(textbook, level_toc)
                chapters = buildChapterRanges(level_toc, total_pages)
                if len(chapters) >= 2:
                    return chapters, total_pages

        return [{"title": "Full Textbook", "start_page": 1, "end_page": total_pages}], total_pages
    finally:
        textbook.close()

# Chunks the book and tags each piece with page metadata.
def parse_and_chunk(file_bytes: bytes, user_id: str, textbook_id: str, toc: list[dict], *, page_offset: int = 0, start_index: int = 0) -> list[dict]:
    with tempfile.NamedTemporaryFile(suffix=".pdf", delete=False) as f:
        f.write(file_bytes)
        tmp_path = f.name

    try:
        result = converter.convert(tmp_path)
        textbook = result.document

        chunks: list[dict] = []
        chunk_index = start_index
        no_page = 0

        for chunk in chunker.chunk(textbook):
            meta = chunk.meta
            doc_items = meta.doc_items

            # IMPORTANT: guard None
            text = normalize_text(chunk.text or "")
            if not text:
                continue

            pages = sorted({
                item.prov[0].page_no
                for item in (doc_items or [])
                if getattr(item, "prov", None)
            })

            if not pages:
                no_page += 1

            # Normalize to 1-based if needed
            if pages and min(pages) == 0:
                pages = [p + 1 for p in pages]

            # Shift to global pages if this is a slice
            if pages and page_offset:
                pages = [p + page_offset for p in pages]

            page_start = pages[0] if pages else None
            page_end = pages[-1] if pages else None

            chapter_title = getChapterForPages(pages, toc) if pages else "Unknown"

            citation = None
            if page_start is not None:
                citation = f"Page {page_start}" if page_end in (None, page_start) else f"Pages {page_start}-{page_end}"

            chunks.append({
                "user_id": str(user_id),
                "textbook_id": str(textbook_id),
                "text": text,
                "chapter": chapter_title,
                "section": meta.headings[0] if getattr(meta, "headings", None) else None,
                "page_start": page_start,
                "page_end": page_end,
                "citation": citation,
                "chunk_index": chunk_index,
            })
            chunk_index += 1

        # print("chunks:", len(chunks), "chunks_missing_pages:", no_page)
        # ps = [c["page_start"] for c in chunks if c["page_start"] is not None]
        # if ps:
        #     print("page_start min/max:", min(ps), max(ps))
        # lens = [len(c["text"]) for c in chunks if c.get("text")]
        # if lens:
        #     print("avg_chars:", sum(lens)/len(lens), "min_chars:", min(lens), "max_chars:", max(lens))
        # if chunks:
        #     print("sample chunk 0:", chunks[0]["citation"], chunks[0]["text"][:300])
        #     print("sample chunk -1:", chunks[-1]["citation"], chunks[-1]["text"][:300])

        return chunks

    finally:
        try:
            os.unlink(tmp_path)
        except OSError:
            pass
