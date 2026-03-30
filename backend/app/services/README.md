## Textbook Processing & Pretest Flow

1. **Upload**
   - User uploads a PDF → stored in Supabase
   - TOC is extracted and chapters are saved

2. **Processing**
   - PDF is split into batches
   - Text is chunked + labeled (chapter, pages, citation)
   - Embeddings are generated and stored in Qdrant

3. **Topic Extraction**
   - Sample chunks across the full chapter
   - LLM extracts 5–10 core topic labels
   - Topics are stored on the chapter

4. **Context Retrieval**
   - For each topic, retrieve relevant chunks (same chapter)
   - Ensures each topic has grounded context + citations
   - Context is retrieved using semantic (embedding-based) search to find the most relevant chunks for each topic within the chapter.

5. **Pretest Generation**
   - All topic contexts sent in one call
   - Generates 12 questions across topics
   - Each question includes type, topic, explanation, citation

6. **Storage**
   - Pretest is saved in Supabase
   - Topics enable tracking performance per topic