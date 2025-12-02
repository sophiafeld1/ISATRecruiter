"""
Generate embeddings for chunks using OpenAI text-embedding-3-small model.
"""
import sys
import os

# Add project root to path
project_root = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
if project_root not in sys.path:
    sys.path.insert(0, project_root)

from langchain_openai import OpenAIEmbeddings
from database.db_write import LinkDatabase
from psycopg2.extras import RealDictCursor


def generate_embeddings_for_chunks():
    """
    Generate embeddings for all chunks that don't have embeddings yet.
    Uses OpenAI text-embedding-3-small model.
    """
    db = LinkDatabase()
    cursor = db.conn.cursor(cursor_factory=RealDictCursor)
    
    # Get all chunks without embeddings
    cursor.execute("SELECT id, chunk_text FROM chunks WHERE embedding IS NULL ORDER BY id")
    chunks = cursor.fetchall()
    
    print(f"Found {len(chunks)} chunks without embeddings\n")
    
    if len(chunks) == 0:
        print("All chunks already have embeddings.")
        cursor.close()
        db.close()
        return
    
    # Initialize embeddings model (requires OPENAI_API_KEY in .env)
    # Using text-embedding-3-small model
    embeddings_model = OpenAIEmbeddings(model="text-embedding-3-small")
    
    total_embedded = 0
    
    # Process in batches for efficiency
    batch_size = 100
    for i in range(0, len(chunks), batch_size):
        batch = chunks[i:i + batch_size]
        chunk_ids = [chunk['id'] for chunk in batch]
        chunk_texts = [chunk['chunk_text'] for chunk in batch]
        
        print(f"Processing batch {i//batch_size + 1}/{(len(chunks)-1)//batch_size + 1} ({len(batch)} chunks)...")
        
        try:
            # Generate embeddings for batch
            embeddings = embeddings_model.embed_documents(chunk_texts)
            
            # Update each chunk with its embedding
            for j, chunk_id in enumerate(chunk_ids):
                embedding = embeddings[j]
                
                # Convert embedding list to string format for pgvector
                embedding_str = '[' + ','.join(map(str, embedding)) + ']'
                
                cursor.execute("""
                    UPDATE chunks 
                    SET embedding = %s::vector 
                    WHERE id = %s
                """, (embedding_str, chunk_id))
                
                total_embedded += 1
            
            db.conn.commit()
            print(f"  ✓ Embedded {len(batch)} chunks\n")
            
        except Exception as e:
            print(f"  ✗ Error processing batch: {e}\n")
            db.conn.rollback()
            continue
    
    cursor.close()
    db.close()
    
    print(f"Complete! Generated embeddings for {total_embedded} chunks.")


def regenerate_all_embeddings():
    """
    Regenerate embeddings for ALL chunks (even if they already have embeddings).
    Uses OpenAI text-embedding-3-small model.
    """
    db = LinkDatabase()
    cursor = db.conn.cursor(cursor_factory=RealDictCursor)
    
    # Get all chunks
    cursor.execute("SELECT id, chunk_text FROM chunks ORDER BY id")
    chunks = cursor.fetchall()
    
    print(f"Found {len(chunks)} chunks to regenerate embeddings for\n")
    
    if len(chunks) == 0:
        print("No chunks found. Run chunking first.")
        cursor.close()
        db.close()
        return
    
    # Initialize embeddings model (requires OPENAI_API_KEY in .env)
    # Using text-embedding-3-small model
    embeddings_model = OpenAIEmbeddings(model="text-embedding-3-small")
    
    total_embedded = 0
    
    # Process in batches for efficiency
    batch_size = 100
    for i in range(0, len(chunks), batch_size):
        batch = chunks[i:i + batch_size]
        chunk_ids = [chunk['id'] for chunk in batch]
        chunk_texts = [chunk['chunk_text'] for chunk in batch]
        
        print(f"Processing batch {i//batch_size + 1}/{(len(chunks)-1)//batch_size + 1} ({len(batch)} chunks)...")
        
        try:
            # Generate embeddings for batch
            embeddings = embeddings_model.embed_documents(chunk_texts)
            
            # Update each chunk with its embedding
            for j, chunk_id in enumerate(chunk_ids):
                embedding = embeddings[j]
                
                # Convert embedding list to string format for pgvector
                embedding_str = '[' + ','.join(map(str, embedding)) + ']'
                
                cursor.execute("""
                    UPDATE chunks 
                    SET embedding = %s::vector 
                    WHERE id = %s
                """, (embedding_str, chunk_id))
                
                total_embedded += 1
            
            db.conn.commit()
            print(f"  ✓ Embedded {len(batch)} chunks\n")
            
        except Exception as e:
            print(f"  ✗ Error processing batch: {e}\n")
            db.conn.rollback()
            continue
    
    cursor.close()
    db.close()
    
    print(f"Complete! Generated embeddings for {total_embedded} chunks.")


if __name__ == "__main__":
    import sys
    
    # Check for command-line argument
    if len(sys.argv) > 1:
        if sys.argv[1] == "all":
            regenerate_all_embeddings()
        elif sys.argv[1] in ["-h", "--help", "help"]:
            print("Usage:")
            print("  python chunking/embeddings.py          # Generate embeddings for chunks without embeddings")
            print("  python chunking/embeddings.py all      # Regenerate ALL embeddings")
        else:
            print(f"Unknown argument: {sys.argv[1]}")
            print("Use 'all' to regenerate all embeddings, or no argument for missing embeddings only.")
    else:
        # Interactive menu
        print("\n" + "=" * 60)
        print("EMBEDDINGS GENERATOR")
        print("=" * 60)
        print("\nWhat would you like to do?")
        print("1. Generate embeddings for chunks without embeddings (default)")
        print("2. Regenerate ALL embeddings")
        print("0. exit")
        
        choice = input("\nEnter your choice (0-2): ").strip()
        
        if choice == "1" or choice == "":
            generate_embeddings_for_chunks()
        elif choice == "2":
            regenerate_all_embeddings()
        elif choice == "0":
            print("Exiting...")
        else:
            print("Invalid choice. Please run again and select 0-2.")

