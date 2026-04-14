import re


CHAPTER_NUMBER_WORDS = {
    "one": 1,
    "two": 2,
    "three": 3,
    "four": 4,
    "five": 5,
    "six": 6,
    "seven": 7,
    "eight": 8,
    "nine": 9,
    "ten": 10,
    "eleven": 11,
    "twelve": 12,
    "thirteen": 13,
    "fourteen": 14,
    "fifteen": 15,
    "sixteen": 16,
    "seventeen": 17,
    "eighteen": 18,
    "nineteen": 19,
}

CHAPTER_TENS_WORDS = {
    "twenty": 20,
    "thirty": 30,
    "forty": 40,
    "fifty": 50,
}

CHAPTER_WORD_PATTERN = (
    r"one|two|three|four|five|six|seven|eight|nine|ten|eleven|twelve|thirteen|fourteen|"
    r"fifteen|sixteen|seventeen|eighteen|nineteen|"
    r"twenty(?:[\s-]+(?:one|two|three|four|five|six|seven|eight|nine))?|"
    r"thirty(?:[\s-]+(?:one|two|three|four|five|six|seven|eight|nine))?|"
    r"forty(?:[\s-]+(?:one|two|three|four|five|six|seven|eight|nine))?|"
    r"fifty(?:[\s-]+(?:one|two|three|four|five|six|seven|eight|nine))?"
)

CHAPTER_REFERENCE_REGEX = re.compile(
    rf"\b(?:chapter|chpater|chapetr|chaptr|chater|capter|hcpater|ch\.?)\s+(\d+|{CHAPTER_WORD_PATTERN}|[ivxlcdm]+)\b",
    re.IGNORECASE,
)

LEADING_CHAPTER_REFERENCE_REGEX = re.compile(
    rf"^\s*(?:(?:chapter|chpater|chapetr|chaptr|chater|capter|hcpater)\s+)?(\d+|{CHAPTER_WORD_PATTERN}|[ivxlcdm]+)\b",
    re.IGNORECASE,
)


# Cleans chapter titles so matching is less brittle.
def normalize_chapter_title(title: str) -> str:
    title = (title or "").strip().lower()
    title = re.sub(
        r"^(?:chapter\s+)?(?:\d+(?:\.\d+)*|[ivxlcdm]+|one|two|three|four|five|six|seven|eight|nine|ten|"
        r"eleven|twelve|thirteen|fourteen|fifteen|sixteen|seventeen|eighteen|nineteen|"
        r"twenty(?:[\s-]+(?:one|two|three|four|five|six|seven|eight|nine))?|"
        r"thirty(?:[\s-]+(?:one|two|three|four|five|six|seven|eight|nine))?|"
        r"forty(?:[\s-]+(?:one|two|three|four|five|six|seven|eight|nine))?|"
        r"fifty(?:[\s-]+(?:one|two|three|four|five|six|seven|eight|nine))?)\b"
        r"[\s.:_-]*",
        "",
        title,
        flags=re.IGNORECASE,
    )
    title = re.sub(r"\s+", " ", title)
    return title


# Turns chapter words like "one" into digits.
def chapter_word_to_number(raw_word: str) -> int | None:
    normalized = re.sub(r"[-]+", " ", (raw_word or "").strip().lower())
    if not normalized:
        return None

    if normalized in CHAPTER_NUMBER_WORDS:
        return CHAPTER_NUMBER_WORDS[normalized]

    parts = normalized.split()
    total = 0

    for part in parts:
        if part in CHAPTER_TENS_WORDS:
            total += CHAPTER_TENS_WORDS[part]
            continue
        if part in CHAPTER_NUMBER_WORDS:
            total += CHAPTER_NUMBER_WORDS[part]
            continue
        return None

    return total or None


# Turns roman numerals into digits when a book uses them.
def roman_to_number(raw_roman: str) -> int | None:
    normalized = (raw_roman or "").strip().lower()
    if not normalized or not re.fullmatch(r"[ivxlcdm]+", normalized):
        return None

    values = {"i": 1, "v": 5, "x": 10, "l": 50, "c": 100, "d": 500, "m": 1000}
    total = 0
    previous = 0

    for char in reversed(normalized):
        value = values[char]
        if value < previous:
            total -= value
        else:
            total += value
            previous = value

    return total or None


# Normalizes chapter numbers so we compare them the same way.
def normalize_chapter_identifier(raw_identifier: str) -> str | None:
    normalized = (raw_identifier or "").strip().lower()
    if not normalized:
        return None

    if normalized.isdigit():
        return str(int(normalized))

    word_value = chapter_word_to_number(normalized)
    if word_value is not None:
        return str(word_value)

    roman_value = roman_to_number(normalized)
    if roman_value is not None:
        return str(roman_value)

    return None


# Pulls the chapter number off a TOC title.
def chapter_identifier_from_title(title: str) -> str | None:
    match = LEADING_CHAPTER_REFERENCE_REGEX.match((title or "").strip())
    if not match:
        return None

    return normalize_chapter_identifier(match.group(1))


# Finds the chapter the user is probably talking about.
def find_referenced_chapter(message: str, chapters: list[dict]) -> dict | None:
    normalized_message = (message or "").strip().lower()
    if not normalized_message or not chapters:
        return None

    chapter_number_match = CHAPTER_REFERENCE_REGEX.search(normalized_message)
    if chapter_number_match:
        chapter_number = normalize_chapter_identifier(chapter_number_match.group(1))
        for chapter in chapters:
            if chapter_number and chapter_identifier_from_title(chapter.get("title") or "") == chapter_number:
                return chapter

    for chapter in chapters:
        normalized_title = normalize_chapter_title(chapter.get("title") or "")
        if normalized_title and normalized_title in normalized_message:
            return chapter

    return None


# Matches a saved chapter title back to the TOC.
def find_chapter_by_title(chapter_title: str, chapters: list[dict]) -> dict | None:
    normalized_target = normalize_chapter_title(chapter_title or "")
    if not normalized_target:
        return None

    for chapter in chapters:
        normalized_title = normalize_chapter_title(chapter.get("title") or "")
        if normalized_title == normalized_target:
            return chapter

    return None


# Turns small page numbers into roman numerals for front matter.
def int_to_roman(value: int) -> str:
    numerals = [
        (1000, "m"),
        (900, "cm"),
        (500, "d"),
        (400, "cd"),
        (100, "c"),
        (90, "xc"),
        (50, "l"),
        (40, "xl"),
        (10, "x"),
        (9, "ix"),
        (5, "v"),
        (4, "iv"),
        (1, "i"),
    ]

    remaining = max(1, int(value))
    result = []
    for numeral_value, numeral_text in numerals:
        while remaining >= numeral_value:
            result.append(numeral_text)
            remaining -= numeral_value
    return "".join(result)


# Builds our best guess for the book's shown page labels.
def build_page_label_config(chapters: list[dict]) -> dict:
    chapter_one = next(
        (
            chapter
            for chapter in chapters
            if chapter_identifier_from_title(chapter.get("title") or "") == "1"
        ),
        None,
    )

    chapter_one_start = chapter_one.get("start_page") if chapter_one else None
    if isinstance(chapter_one_start, int) and chapter_one_start > 1:
        return {
            "content_start_page": chapter_one_start,
            "front_matter_end_page": chapter_one_start - 1,
        }

    return {
        "content_start_page": 1,
        "front_matter_end_page": 0,
    }


# Maps a stored PDF page to the page number the book shows.
def physical_page_to_display_label(page_number: int | None, chapters: list[dict]) -> str | None:
    if not isinstance(page_number, int) or page_number < 1:
        return None

    config = build_page_label_config(chapters)
    content_start = config.get("content_start_page") or 1
    front_matter_end = config.get("front_matter_end_page") or 0

    if page_number >= content_start:
        return str(page_number - content_start + 1)

    if 1 <= page_number <= front_matter_end:
        return int_to_roman(page_number)

    return str(page_number)


# Maps a shown book page back to the stored PDF page.
def display_page_to_physical_page(page_number: int | None, chapters: list[dict]) -> int | None:
    if not isinstance(page_number, int) or page_number < 1:
        return None

    config = build_page_label_config(chapters)
    content_start = config.get("content_start_page") or 1
    return page_number + content_start - 1


# Formats page chips using the book's shown numbers.
def build_display_citation(page_start: int | None, page_end: int | None, chapters: list[dict]) -> str | None:
    start_label = physical_page_to_display_label(page_start, chapters)
    end_label = physical_page_to_display_label(page_end, chapters)

    if not start_label:
        return None

    if not end_label or end_label == start_label:
        return f"Page {start_label}"

    return f"Pages {start_label}-{end_label}"


# Checks whether a shown page label is still front matter.
def is_roman_page_label(page_label: str | None) -> bool:
    normalized = (page_label or "").strip().lower()
    return bool(normalized) and bool(re.fullmatch(r"[ivxlcdm]+", normalized))


# Swaps stored PDF page numbers for the book's shown ones.
def apply_display_page_labels(rows: list[dict], chapters: list[dict]) -> list[dict]:
    normalized_rows = []

    for row in rows:
        page_number = row.get("page_number")
        page_end = row.get("page_end")
        display_page_label = physical_page_to_display_label(page_number, chapters)
        display_citation = build_display_citation(page_number, page_end, chapters)

        normalized_rows.append({
            **row,
            "display_page_label": display_page_label,
            "citation": display_citation or row.get("citation"),
        })

    return normalized_rows


# Drops front-matter rows when the user is asking about a real chapter.
def filter_rows_for_chapter_content(rows: list[dict]) -> list[dict]:
    filtered_rows = [
        row for row in rows
        if not is_roman_page_label(row.get("display_page_label"))
    ]
    return filtered_rows or rows


# Builds the quick chapter-range reply without repeating the chip text.
def build_chapter_range_response(chapter: dict, chapters: list[dict]) -> tuple[str, list[str]]:
    title = (chapter.get("title") or "").strip()
    start_page = chapter.get("start_page")
    end_page = chapter.get("end_page")

    if start_page is None:
        return (f"I found {title}, but its page range is not available.", [])

    citation = build_display_citation(start_page, end_page, chapters)
    if not citation:
        return (f"I found {title}, but its page range is not available.", [])

    if end_page in (None, start_page):
        return (f'{title} starts on this page in the textbook.', [citation])

    return (f'{title} spans this page range in the textbook.', [citation])
