## ISAT Recruitment Tool – Product Requirements Document (PRD)

### 1) Overview
- **Goal**: Build an AI RAG chatbot that answers questions about the ISAT program using official ISAT/SIS documents, with cited sources and low hallucination risk.
- **Primary outcomes**: Faster, 24/7 answers for prospective students and parents; reduced load on staff; reusable ingestion and evaluation pipeline for ISAT content.

### 2) Problem Statement
Prospective students and parents struggle to find up‑to‑date, trustworthy information across scattered PDFs, web pages, and forms. Staff spend time answering repetitive questions. A retrieval‑augmented chatbot consolidates knowledge and provides cited answers embedded on the SIS website.

### 3) Users and Use Cases
- **Prospective students/parents**: admissions steps, deadlines, curriculum, labs, careers, scholarships, transfer credits, contacts.
- **Recruitment staff/advisors**: consistent answers, quick linking to official sources.
- **Website admins**: upload/update documents, monitor usage and quality.

**Example queries**
- “What are ISAT admission requirements and deadlines?”
- “Compare the Energy and Environment concentrations.”
- “Which intro courses should I take as a transfer?”
- “Link me to the lab safety policy PDF.”
- “What scholarships are available for first‑years?”

### 4) Scope
- **In scope (MVP)**
  - Document ingestion (HTML/PDF) → clean → chunk → embed → vector DB.
  - Chat API: query encoding → retrieve top‑k chunks (optional rerank) → prompt → generate answer with citations.
  - Web chat widget embedded on SIS site (simple theme).
  - Admin: upload documents and trigger re‑index; view basic analytics; thumbs up/down feedback.
  - Safety: source‑only answers, refusal for out‑of‑scope questions, rate limiting.
- **Out of scope (MVP)**
  - Voice, multilingual, agents/browsing, fine‑tuning, personal data integrations, scheduling, email capture.


### 6) Functional Requirements
- **Ingestion pipeline**
  - Upload/sync sources: campus web pages (HTML), PDFs
  - Cleaning/normalization to plain text with metadata (title, section, URL, page, updated_at).
  - Chunking strategy: semantic or fixed with overlap (e.g., 512–1,000 tokens, 15–20% overlap).
  - Embeddings generation and storage in vector DB; record embedding model/version.
- **Retrieval and ranking**
  - Encode queries using the same embedding family.
  - Vector search top‑k (default k=8–12), optional Maximal Marginal Relevance (MMR).
- **Answer generation**
  - Compose prompt with system guardrails, user query, and context chunks.
  - Include inline citations with source titles/URLs or PDF page numbers.
  - Return answer, citations, confidence, and safety flags.
  - Low‑confidence fallback: “I’m not sure—here are the best sources,” with links.
- **Frontend**
  - Responsive web chat widget (ISAT brand theme), copy link
- **Admin**
  - View query analytics, popular/failed questions
- **Observability and Safety**
  - logs 


### 8) Data Model (key fields)
- **Document**: `doc_id`, `source_url`, `title`, `type`, `published_at`, `updated_at`, `checksum`.
- **Chunk**: `chunk_id`, `doc_id`, `section`, `page_number`, `text`, `token_count`, `embedding`, `tags`.
- **Query log**: `query_id`, `text`, `top_k_ids`, `reranked_ids`, `latency_ms`, `model`, `answer_id`, `feedback`.

### 9) Architecture (aligned to slide)
- **Offline/Batch**: Documents → Clean/normalize → Chunk → Embedding → Vector DB 
- **Online/Runtime**: User query → Encode → Retrieve chunks → Build prompt → LLM generate → Return answer + citations.

### 10) Technology Choices (proposed)
- Backend: Python FastAPI; orchestration with LangChain or LangGraph.
- Vector DB: PostGreSQL, maybe chroma
- Embeddings: tbd
- Generator: Llama 3.1 8B Instruct via TGI/vLLM; fallback to GPT‑4o‑mini if allowed.
- Frontend: React widget or plain JS embed; deploy on SIS site.
- Hosting: Vercel for prototype.
- Analytics: simple Postgres + dashboards; or Plausible/GA for page‑embed metrics.

### 11) Prompting and Guardrails
- System prompt mandates: answer only from provided context; cite each claim; refuse if not supported; neutral, student‑friendly tone.
- Truncation: token‑aware chunk selection; keep within model context window.
- Safety checks: detect injection (e.g., “ignore previous instructions”), external URLs, or personal advice requests; respond with refusal template. 


### 16) Deliverables
- Running chatbot widget embedded on SIS site (staging).
- Backend service with REST endpoints for chat, admin ingestion.
- Vector DB with documented schema and versioned corpus.
- Evaluation report with metrics and error analysis.
- Admin guide and maintenance runbook.

### 18) Open Questions
- Exact list of initial document sources and crawl scope?
- Hosting constraints on campus vs managed cloud?
- Branding requirements for widget theming?
- Policy for storing conversation transcripts for improvement (opt‑in)?
- Preferred analytics platform for stakeholders?

### 19) Assumptions
- Access is granted to crawl or export official ISAT resources.
- Staff can help curate the initial eval set and validate answers.
- A staging environment is available for the website embed.

