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


smolvlm_picture_description = PictureDescriptionVlmOptions(
    repo_id="HuggingFaceTB/SmolVLM-256M-Instruct",
    prompt="Describe this image in the context of a textbook. Focus on any data, labels, or concepts shown."
)

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
    generate_picture_images=True,
    images_scale=0.5,
    do_ocr=False,
    do_table_structure=False,
    do_picture_description=True,
    picture_description_options=smolvlm_picture_description
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

# ANNACHEN vv 
def normalize_text(s: str) -> str:
    s = s.replace("\u00a0", " ")
    s = re.sub(r"[ \t]{2,}", " ", s)
    s = re.sub(r"\n{3,}", "\n\n", s)
    return s.strip()

def pdf_page_range(pdf_bytes: bytes, start_page: int, end_page: int) -> bytes:
    src = pymupdf.open(stream=pdf_bytes, filetype="pdf")
    out = pymupdf.open()
    out.insert_pdf(src, from_page=start_page-1, to_page=end_page-1)
    b = out.tobytes()
    src.close()
    out.close()
    return b
# ANNACHEN ^^

def extract_toc(file: bytes) -> tuple[list[dict], int]:
    """
    Table of Contents extraction with PyMuPDF, returns chapters with their page ranges
    """
    textbook = pymupdf.open(stream=file, filetype="pdf")
    toc = textbook.get_toc()
    total_pages = textbook.page_count
    textbook.close()

    if not toc:
        return [{"title": "Full Textbook", "start_page": 1, "end_page": total_pages}], total_pages

    chapters = []
    for i, (level, title, start_page) in enumerate(toc):
        # if i + 1 < len(toc):
        #     end_page = toc[i + 1][2] - 1
        # else:
        #     end_page = total_pages
        end_page = total_pages
        for j in range(i + 1, len(toc)):
            next_level, _, next_start = toc[j]
            if next_level <= level:
                end_page = next_start - 1
                break 
            # ANNACHEN
        end_page = max(start_page, end_page)

        chapters.append({
            "title": title,
            "start_page": start_page,
            "end_page": end_page
        })

    return chapters, total_pages

def _get_chapter_for_page(page: int, toc: list[dict]) -> str:
    """
    Return the chapter title for a given page number using the TOC
    """
    if not page or not toc:
        return "Unknown"

    # chapter_title = toc[0]["title"]
    # for chapter in toc:
    #     if page >= chapter["start_page"]:
    #         chapter_title = chapter["title"]
    #     else:
    #         break

    # return chapter_title  

    for ch in toc:
        if ch["start_page"] <= page <= ch["end_page"]:
            return ch["title"]

    previous = [c for c in toc if c["start_page"] <= page] # nearest previous chapter
    return previous[-1]["title"] if previous else toc[0]["title"]

def parse_and_chunk(file_bytes: bytes, user_id: str, textbook_id: str, toc: list[dict], *, page_offset: int = 0, start_index: int = 0) -> list[dict]:
    """ 
    Docling -> HybridChunker -> list of chunk dicts.

    Use page_offset when you're processing a sliced PDF batch:
      global_page = local_page + page_offset

    Use start_index so chunk_index stays unique across batches.
    """
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

            chapter_title = _get_chapter_for_page(page_start, toc) if page_start is not None else "Unknown"

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

        print("chunks:", len(chunks), "chunks_missing_pages:", no_page)
        ps = [c["page_start"] for c in chunks if c["page_start"] is not None]
        if ps:
            print("page_start min/max:", min(ps), max(ps))
        lens = [len(c["text"]) for c in chunks if c.get("text")]
        if lens:
            print("avg_chars:", sum(lens)/len(lens), "min_chars:", min(lens), "max_chars:", max(lens))
        if chunks:
            print("sample chunk 0:", chunks[0]["citation"], chunks[0]["text"][:300])
            print("sample chunk -1:", chunks[-1]["citation"], chunks[-1]["text"][:300])

        return chunks

    finally:
        try:
            os.unlink(tmp_path)
        except OSError:
            pass

# def parse_and_chunk(file: bytes, user_id: str, textbook_id: str, toc: list[dict], page_offset: int = 0) -> list[dict]:
#     """
#     Runs Docling on the full textbook and return structured chunks
#     """
#     with tempfile.NamedTemporaryFile(suffix=".pdf", delete=False) as f:
#         f.write(file)
#         tmp_path = f.name

#     try:
#         no_page = 0
#         result = converter.convert(tmp_path)
#         textbook = result.document

#         chunks = []
#         for chunk in chunker.chunk(textbook):
#             meta = chunk.meta
#             doc_items = meta.doc_items
#             text = normalize_text(chunk.text or "")
#             if not text:
#                 continue
            
#             pages = sorted({item.prov[0].page_no for item in doc_items if item.prov})
#             if not pages:
#                 no_page += 1
#             # If Docling gives 0-based pages in your run, normalize here:
#             # pages = [p + 1 for p in pages] OK
#             if pages and min(pages) == 0:
#                 pages = [p + 1 for p in pages]
#             pages = [p + page_offset for p in pages]

#             page_start = pages[0] if pages else None
#             page_end = pages[-1] if pages else None
#             chapter_title = _get_chapter_for_page(page_start, toc) if page_start is not None else "Unknown"

#             citation = None
#             if page_start is not None:
#                 citation = f"Page {page_start}" if page_start == page_end else f"Pages {page_start}-{page_end}"

#             chunks.append({
#                 "user_id": user_id,
#                 "textbook_id": textbook_id,
#                 "text": text,
#                 "chapter": chapter_title,
#                 "section": meta.headings[0] if meta.headings else None,
#                 "page_start": page_start,
#                 "page_end": page_end,
#                 "citation": citation,
#                 "chunk_index": len(chunks)
#             }) # ANNACHEN
#         print("chunks:", len(chunks), "chunks_missing_pages:", no_page)
#         pages = [c["page_start"] for c in chunks if c["page_start"] is not None]
#         print("page_start min/max:", min(pages), max(pages))
#         lens = [len(c["text"]) for c in chunks]
#         print("avg_chars:", sum(lens)/len(lens), "min_chars:", min(lens), "max_chars:", max(lens))
#         print("sample chunk 0:", chunks[0]["citation"], chunks[0]["text"][:300])
#         print("sample chunk -1:", chunks[-1]["citation"], chunks[-1]["text"][:300]) 

#         return chunks

#     finally:
#         os.unlink(tmp_path)
    
# def parse_and_chunk(file_bytes: bytes, user_id: str, textbook_id: str, toc: list[dict], max_chars: int = 1800, overlap_chars: int = 200):
#     doc = pymupdf.open(stream=file_bytes, filetype="pdf")
#     chunks = []
#     chunk_index = 0

#     for page_idx in range(doc.page_count):
#         page_no = page_idx + 1
#         raw = doc.load_page(page_idx).get_text("text")
#         text = normalize_text(raw)
#         if not text:
#             continue

#         # simple sliding window chunking by chars (good enough; you can token-chunk later)
#         start = 0
#         while start < len(text):
#             end = min(len(text), start + max_chars)
#             piece = text[start:end].strip()
#             if piece:
#                 chapter_title = _get_chapter_for_page(page_no, toc)
#                 citation = f"Page {page_no}"
#                 chunks.append({
#                     "user_id": user_id,
#                     "textbook_id": textbook_id,
#                     "text": piece,
#                     "chapter": chapter_title,
#                     "section": None,
#                     "page_start": page_no,
#                     "page_end": page_no,
#                     "citation": citation,
#                     "chunk_index": chunk_index
#                 })
#                 chunk_index += 1
#             if end == len(text):
#                 break
#             start = max(0, end - overlap_chars)
#     print("chunks:", len(chunks))
#     pages = [c["page_start"] for c in chunks if c.get("page_start") is not None]
#     print("page_start min/max:", min(pages) if pages else None, max(pages) if pages else None)
#     lens = [len(c["text"]) for c in chunks if c.get("text")]
#     print("avg_chars:", (sum(lens)/len(lens)) if lens else 0, "min_chars:", min(lens) if lens else 0, "max_chars:", max(lens) if lens else 0)
#     print("sample chunk 0:", chunks[0]["citation"], chunks[0]["text"][:300] if chunks else "")
#     print("sample chunk -1:", chunks[-1]["citation"], chunks[-1]["text"][:300] if chunks else "")

#     doc.close()
#     return chunks
