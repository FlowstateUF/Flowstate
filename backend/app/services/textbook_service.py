import os, tempfile
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

pipeline_options = PdfPipelineOptions(
    generate_page_images=True,
    generate_picture_images=True,
    images_scale=1.0,
    do_ocr=True,
    do_table_structure=True,
    do_picture_description=True,
    ocr_options=RapidOcrOptions(),
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
        if i + 1 < len(toc):
            end_page = toc[i + 1][2] - 1
        else:
            end_page = total_pages

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

    chapter_title = toc[0]["title"]
    for chapter in toc:
        if page >= chapter["start_page"]:
            chapter_title = chapter["title"]
        else:
            break

    return chapter_title  

def parse_and_chunk(file: bytes, user_id: str, textbook_id: str, toc: list[dict]) -> list[dict]:
    """
    Runs Docling on the full textbook and return structured chunks
    """
    with tempfile.NamedTemporaryFile(suffix=".pdf", delete=False) as f:
        f.write(file)
        tmp_path = f.name

    try:
        result = converter.convert(tmp_path)
        textbook = result.document

        chunks = []
        for chunk in chunker.chunk(textbook):
            meta = chunk.meta
            doc_items = meta.doc_items

            pages = sorted({item.prov[0].page_no for item in doc_items if item.prov})

            first_page = pages[0] if pages else None
            chapter_title = _get_chapter_for_page(first_page, toc)
            page = first_page if len(pages) == 1 else pages

            chunks.append({
                "user_id": user_id,
                "textbook_id": textbook_id,
                "text": chunk.text,
                "chapter": chapter_title,
                "section": meta.headings[0] if meta.headings else None,
                "page": page,
                "chunk_index": len(chunks)
            })

        return chunks

    finally:
        os.unlink(tmp_path)
    