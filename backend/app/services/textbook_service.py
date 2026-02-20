from docling.datamodel.base_models import InputFormat
from docling.datamodel.pipeline_options import (
    PdfPipelineOptions,
    RapidOcrOptions,
    smolvlm_picture_description
)
from docling.document_converter import DocumentConverter, PdfFormatOption


def parse_textbook(file: bytes):
    pipeline_options = PdfPipelineOptions(
        generate_page_images=True,
        images_scale=1.00,
        do_ocr=True,
        do_picture_description=True,
        ocr_options=RapidOcrOptions(),
        picture_description_options=smolvlm_picture_description
    )

    converter = DocumentConverter(
        format_options={InputFormat.PDF: PdfFormatOption(pipeline_options=pipeline_options)}
    )

    result = converter.convert(file)
    textbook = result.document
    print(textbook.export_to_markdown())