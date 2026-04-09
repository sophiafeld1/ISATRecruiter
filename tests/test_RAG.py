from database.db_write import LinkDatabase

db = LinkDatabase()
cursor = db.conn.cursor()
cursor.execute("SELECT COUNT(*) FROM chunks WHERE embedding IS NOT NULL")
print(f"Chunks with embeddings: {cursor.fetchone()[0]}")
cursor.execute("SELECT COUNT(*) FROM chunks")
print(f"Total chunks: {cursor.fetchone()[0]}")