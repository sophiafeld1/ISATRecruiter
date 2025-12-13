# ISAT RAG Chatbot - LangGraph Workflow

```mermaid
flowchart TD
    Start([User Question]) --> Classify[Classify Question<br/>LLM: Determine if RAG needed]
    
    Classify --> Decision{Requires RAG?}
    
    Decision -->|Yes<br/>On-topic| Retrieve[Retrieve Chunks<br/>Generate embedding<br/>Query database<br/>Top 8 similar chunks]
    
    Decision -->|No<br/>Off-topic| Generic[Answer Generic<br/>LLM: Friendly off-topic response]
    
    Retrieve --> RAG[Answer with RAG<br/>LLM: Generate answer<br/>using retrieved chunks<br/>+ conversation history]
    
    RAG --> End1([Return Answer])
    Generic --> End2([Return Answer])
    
    style Start fill:#e1f5ff,stroke:#01579b,stroke-width:2px
    style Classify fill:#fff3e0,stroke:#e65100,stroke-width:2px
    style Decision fill:#f3e5f5,stroke:#4a148c,stroke-width:2px
    style Retrieve fill:#e8f5e9,stroke:#1b5e20,stroke-width:2px
    style RAG fill:#e8f5e9,stroke:#1b5e20,stroke-width:2px
    style Generic fill:#fce4ec,stroke:#880e4f,stroke-width:2px
    style End1 fill:#e1f5ff,stroke:#01579b,stroke-width:2px
    style End2 fill:#e1f5ff,stroke:#01579b,stroke-width:2px
```

## Workflow Description

### 1. **Classify Question**
- Uses GPT-4o-mini to determine if the question requires RAG
- On-topic: ISAT program, courses, curriculum, labs, careers, concentrations
- Off-topic: Unrelated topics or questions not requiring JMU/ISAT knowledge

### 2. **Retrieve Chunks** (RAG Path)
- Generates embedding for user question using `text-embedding-3-small`
- Queries database for top 8 most similar chunks
- Includes course information and similarity scores

### 3. **Answer with RAG**
- Builds context from retrieved chunks
- Uses GPT-4o-mini to generate answer based on retrieved context
- Includes conversation history (last 10 exchanges)
- Cites sources and provides links when possible

### 4. **Answer Generic** (Off-topic Path)
- Uses GPT-4o-mini for friendly generic response
- Mentions focus on ISAT-related questions
- Includes conversation history for context

## State Management

The workflow maintains state through `GraphState`:
- `question`: User's input question
- `requires_rag`: Boolean flag from classification
- `chunks`: Retrieved chunks from database (RAG path)
- `answer`: Final generated answer
- `conversation_history`: Previous Q&A pairs for context

