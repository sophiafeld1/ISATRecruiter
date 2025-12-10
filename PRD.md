## ISAT Recruitment Tool – Product Requirements Document (PRD)

### 1) Overview
- **Goal**: Build an AI RAG chatbot that answers questions about the ISAT program using official ISAT documents, with cited sources and low hallucination risk.
- **Primary outcomes**: Faster, 24/7 answers for prospective students and parents; reduced load on staff; reusable ingestion and evaluation pipeline for ISAT content.

### 2) Problem Statement
Prospective students struggle to understand the ISAT program, since it does not exist at other schools. The visability of ISAT is also low. The main goal of this chatbot is to increase ISAT visibility and expand the major to attract more students. A chatbot is an engaging, innovative consolidated way to present the information that is disoraganized, scattered, and overwhelming for users.

### 3) Users and Use Cases
- **Prospective students/parents**: general about ISAT, curriculum, labs, careers, concentrations
- **JMU faculty/advisors**: consistent answers, quick linking to official sources.
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
  - Chat API: query encoding → retrieve top‑k chunks → prompt → generate answer with citations.
  - Web chat widget embedded on ISAT site.
  - Safety: source‑only answers, refusal for out‑of‑scope questions, refusal for prompt interjections
 - Reranker to make chunks match better


### 5) Functional Requirements
- **Ingestion pipeline**
  - Cleaning/normalization to plain text with metadata (title, section, URL, requirements).
  - Chunking strategy: semantic overlap 
  - Embeddings generation and storage in vector DB; record embedding model/version.
- **Retrieval and ranking**
  - Encode queries using the same embedding model (openai-emeddings-small).
  - Vector search top‑k (k=8)
- **Answer generation**
  - Compose prompt with system prompt, user query, and context chunks.
  - Include inline citations with source titles/URLs or PDF page numbers.
  - Return answer, citations, show on UI
  - Low‑confidence fallback: “I’m not sure—here are the best sources,” with links.
- **Frontend**
  - Responsive website (ISAT brand theme), copy link
- **Admin**
  - View query, top 8 chunks returned


### 6) Architecture 
- **Offline/Batch**: Documents → Clean/normalize → Chunk → Embedding → Vector DB 
- **Online/Runtime**: User query → Encode → Retrieve chunks → Build prompt → LLM generate → Return answer + citations.

### 7) Technology Choices 
- Backend:LangGraph, 
- Vector DB: PostGreSQL, maybe chroma
- Embeddings: openai-emeddings-small
- Generator: GPT‑4o‑mini 
- Frontend: Next.js / react
- Hosting: Vercel
- Testing


### 8) Deliverables
- Running chatbot on local machine
- DB with 3 tables: pages and courses
- Testing with set "sucess" (ex 70% testing passes)
- Github with ReadMe
