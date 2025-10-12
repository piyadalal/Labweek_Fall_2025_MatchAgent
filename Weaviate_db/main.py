import client, schema, insert, query

if __name__ == "__main__":
    c = client.get_client_local()
    schema.create_document_class(c)
    insert.insert_documents(c)
    query.search_documents(c, concept="medicine")
