from db_write import LinkDatabase

def view_links(db):
    links = db.get_all_links()
    print(f"\n=== LINKS ===")
    print(f"Total records: {len(links)}\n")
    for link in links:
        print(f"{link['id']:4} | {link['origin_url'][:50]:50} | {link['link']}")

def view_text(db):
    texts = db.get_all_text()
    print(f"\n=== TEXT ===")
    print(f"Total records: {len(texts)}\n")
    for text in texts:
        print(f"ID: {text['id']} | Origin: {text['origin_url']}")
        print(f"Length: {len(text['text_content'])} characters")
        print(f"\n{text['text_content']}\n")
        print("-" * 80)

if __name__ == "__main__":
    db = LinkDatabase()
    view_links(db)
    view_text(db)
    db.close()

