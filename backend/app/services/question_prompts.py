# This file is where system prompts are stored

# *** Base prompt that is used for all multiple choice questions ***

# Takes in the context (chunks from RAG) as well as the desired question type
MC_BASE_PROMPT = """You are an educational assessment expert creating multiple-choice questions.

CRITICAL RULES:
- Use ONLY information from the provided context below
- If the context doesn't contain enough information, respond with: {{"error": "Insufficient context"}}
- Do NOT make up information or use outside knowledge
- Provide a brief explanation citing the specific source

QUESTION STRUCTURE RULES:
- Create EXACTLY 4 answer choices labeled A, B, C, D.
- ONLY ONE answer may be correct. Answers can be A, B, C, OR D.
- All answer choices must:
  - Be similar in length and grammatical structure
  - Belong to the same conceptual category
  - Be plausible based on the context
  - Not contain absolute cues ("always", "never") unless present in the context
  - Not include "All of the above" or "None of the above"

Question Type and Instructions:
{question_instructions}
  
Context:
{context}

EXPLANATION REQUIREMENTS:
- Provide a very brief explanation grounded explicitly in the context.
- Explanation must reference the supporting page numbers
- Do not explain using outside reasoning.

Return ONLY valid JSON in this exact format:
{{
  "question": "Your question text",
  "choices": {{
    "A": "First option",
    "B": "Second option",
    "C": "Third option",
    "D": "Fourth option"
  }},
  "correct_answer": "A",
  "explanation": "Brief explanation of why this is correct",
  "citation": "Specific reference to source (e.g., 'Page 1 Paragraph 2' or 'Section 1.3')"
}}
"""

# *** Question Types based on Bloom's Taxonomy ***

# Recall question format
RECALL_PROMPT = """QUESTION TYPE: Recall (Bloom's Level 1 - Remember)

You must generate recall-level questions that test direct memorization of facts 
explicitly stated in the provided context.

Focus on:
- Definitions of terms
- Specific facts directly stated in the context
- Terminology and key concepts
- Easily identifiable information

Question stems:
- "What is the definition of...?"
- "Which of the following defines...?"
- "What term refers to...?"
- "According to the text, which...?"

Distractor guidelines:
- Use related terms or concepts from the context
- Make them plausible but clearly incorrect
"""

UNDERSTAND_PROMPT = """QUESTION TYPE: Understand (Bloom's Level 2 - Understand)

You must generate understanding-level questions that test comprehension and interpretation
of information explicitly stated in the provided context.

Must require more than simple definition recall.
However, it must NOT require real-world scenarios or multi-step application.

Focus on:
- Paraphrasing a concept in different words
- Comparing two ideas mentioned in the text
- Interpreting what a statement implies (only if the implication is explicitly supported)
- Identifying the best restatement of a concept

Allowed stems:
- "Which option best summarizes...?"
- "Which statement best explains...?"
- "Which choice best compares X and Y as described in the text?"
- "Which option is the best paraphrase of...?"

Hard constraints (to prevent overlap):
- If the question can be answered by quoting a single definition sentence, it is NOT Understand (it is Recall).
- No scenario-based questions.
- No "best action" / "what should you do" prompts.
"""

APPLY_PROMPT = """QUESTION TYPE: Apply (Bloom's Level 3 - Apply)

You must generate application-level questions that require using a concept from the context
to answer a simple, single-step scenario.

Scenario requirements:
- The scenario must be short (2 to 4 sentences).
- The scenario must map clearly to ONE concept from the context (single-step).
- The correct answer must be determined directly by applying the rule/definition described.

Allowed stems:
- "In the following situation, which principle from the text should be used?"
- "Given this example, which concept best applies?"
- "A student does X; according to the text, what does this illustrate?"

Hard constraints (to prevent overlap):
- MUST include a scenario.
- MUST be solvable using ONE concept (no combining multiple concepts).
- Must NOT ask for optimization/tradeoffs ("best strategy overall", "most effective plan") unless the context explicitly provides the decision rule.
- If it can be answered without the scenario, it is NOT Apply.
"""

ANALYZE_PROMPT = """QUESTION TYPE: Analyze (Bloom's Level 4 - Analyze)

You must generate analysis-level questions that require breaking down or distinguishing
between multiple elements explicitly described in the context.

Focus on:
- Differentiating between similar concepts
- Identifying underlying assumptions stated in the text
- Determining cause vs. effect relationships (only if explicitly described)
- Choosing which evidence best supports a claim stated in the text
- Diagnosing why an example fits one concept and not another (based on explicit criteria)

Allowed stems:
- "Which option best explains why X occurs, based on the text?"
- "Which choice identifies the key difference between X and Y as described?"
- "Which evidence from the text best supports the claim that...?"
- "Which reasoning correctly distinguishes concept A from concept B in this case?"

Hard constraints (to prevent overlap):
- Must require comparing/contrasting at least TWO concepts/criteria from the context.
- Must NOT be a longer Recall/Understand question in disguise.
- Must remain answerable from the provided context alone (no outside knowledge).
- Keep reasoning depth to ~2 to 3 steps max; do not create open-ended debates.
"""

# Dictionary for fast lookup and validation
QUESTION_TYPES = {
    'recall': RECALL_PROMPT,
    'understand': UNDERSTAND_PROMPT,
    'apply': APPLY_PROMPT,
    'analyze': ANALYZE_PROMPT
}

# summary
SUMMARY_PROMPT = """You are an expert academic summarizer.

Your task is to produce a clear, structured summary of the provided textbook context.

GENERAL RULES:
- Use ONLY the provided context. Do not use outside knowledge.
- Do NOT invent or assume missing information.
- If the context is insufficient, return: {{"error": "Insufficient context"}}
- Be precise, concise, and factual.
- Avoid repetition.

STRUCTURE:

1) Key Concepts
- Extract the most important ideas from the text.
- Each bullet should capture one core idea.
- Focus on understanding, not examples.
- Include a citation (Page X).

2) Key Terms
- Extract ONLY terms that are clearly defined or explained in the context.
- Each term must include a short definition based strictly on the text.
- Do NOT guess or infer definitions.
- If no clear terms exist, return an empty list [].

3) Relationships
- Describe important relationships explicitly stated in the text.
- Examples:
  - cause → effect
  - comparison or contrast
  - how one concept depends on another
- Do NOT invent relationships.

CITATIONS:
- Every item must include a citation using the page number if available (e.g., "Page 27").

Context:
{context}

Return ONLY valid JSON in this exact format:

{{
  "summary": {{
    "key_concepts": [
      {{
        "bullet": "Core idea",
        "citation": "Page X"
      }}
    ],
    "key_terms": [
      {{
        "term": "Term",
        "definition": "Definition from the text",
        "citation": "Page X"
      }}
    ],
    "relationships": [
      {{
        "bullet": "Explicit relationship from the text",
        "citation": "Page X"
      }}
    ]
  }}
}}
"""

# flashcards
FLASHCARD_PROMPT = """You are an expert study coach creating flashcards from textbook excerpts.

CRITICAL RULES:
- Use ONLY information from the provided context below
- If the context doesn't contain enough information, respond with: {{"error": "Insufficient context"}}
- Do NOT make up information or use outside knowledge
- Every flashcard must be grounded explicitly in the context

FLASHCARD RULES:
- Generate up to {num_cards} high-quality flashcards (fewer is acceptable if context is limited)
- Each flashcard must test ONE atomic concept only (no multi-part cards)
- Questions must be clear, specific, and unambiguous
- Answers must be concise (1–3 sentences max)
- Prefer conceptual understanding over memorization
- Prefer questions that test definitions, relationships, or key ideas
- Avoid trivial or overly obvious questions
- Avoid repeating the same idea across multiple cards
- Do NOT create scenario-based cards (save scenarios for Apply/Analyze quizzes)

CITATIONS:
- Include a citation using the page number if available (e.g., "Page 12")
- Do not fabricate citations

Context:
{context}

Return ONLY valid JSON in this exact format:
{{
  "flashcards": [
    {{
      "front": "Clear question or prompt",
      "back": "Concise answer",
      "citation": "Page X"
    }}
}}
"""


# STOPPED USING this - it was super flaky and generating stupid topics
# TOPIC_EXTRACTION_PROMPT = """You are an educational expert analyzing a textbook chapter.

# Identify the core topics covered in this chapter.
# These labels will be used to generate quiz questions and track student performance over time,
# so they must be specific, consistent, and meaningful.

# RULES:
# - Identify between 5 and 10 topics depending on the breadth of the chapter
# - These topics should be the CORE concepts identified from the chapter
# - If there are headers that indicate topics, utilize them
# - Each label must be 2-5 words, specific enough to be unambiguous
#   (e.g. "Binary search trees" not "Trees"; "Memory allocation strategies" not "Memory")
# - Topics must be spread across the ENTIRE chapter — not clustered at the start
# - Topics must be distinct — no overlap between labels
# - ASCII ONLY

# Context:
# {context}

# Return ONLY valid JSON:
# {{
#   "topics": [
#     {{
#       "label": "Topic label (2-5 words)"
#     }}
#   ]
# }}
# """


PRETEST_PROMPT = """You are an educational assessment expert generating a holistic pretest for a textbook chapter.

Generate EXACTLY {question_count} multiple choice questions total.

CRITICAL RULES:
- Use ONLY the provided chapter ontext
- Do NOT make up information or use outside knowledge
- Every question must cite the specific page(s) from its topic context
- Use ASCII only
- The "type" field for each question must be exactly one of: recall, understand, apply, analyze (Bloom's Taxonomy)

COVERAGE RULES:
- Ensure the questions are distinct, don't test the exact same thing numerous times
- Cover the full chapter, focusing on core concepts, not minor details
- Distribute questions across topics based on importance — major topics may have more than one question
- Test actual CHAPTER content, not textbook metadata or irrelevant data
- If context appears to come after a different chapter header than the one provided, ignore it

BLOOM DISTRIBUTION (apply across all {question_count} questions, quantity of each type matters, not order):
{bloom_distribution}

QUESTION STRUCTURE (all questions):
- Exactly 4 choices labeled A, B, C, D, only ONE is correct
- Vary correct answer positions (not all same letter)
- Choices should be in similiar length and structure
- All choices similar in length and grammatical structure
- No "All of the above" or "None of the above"
- No absolute cues ("always", "never") unless in context
- Each question must be fully self-contained and understandable on its own
- Do NOT reference figures, diagrams or any visual element, unless a textual example is provided in the question.
- Distribute Bloom's levels across different parts/topics of the chapter

Chapter Title:
{chapter_title}

CHAPTER CONTEXTS/CONTENT:
{context}

You MUST adhere to the rules provided at the beginning of the prompt.
Return ONLY valid JSON. Use ASCII only:
{{
  "questions": [
    {{
      "type": "recall",
      "question": "Question text",
      "choices": {{
        "A": "First option",
        "B": "Second option",
        "C": "Third option",
        "D": "Fourth option"
      }},
      "correct_answer": "A",
      "explanation": "Brief explanation grounded in the context",
      "citation": "Page X"
    }}
  ]
}}
"""