from sentence_transformers import SentenceTransformer
from langchain_core.documents import Document
import chromadb
from chromadb.config import Settings
import os
import torch
import numpy as np

os.environ["PYDEVD_USE_CYTHON"] = "NO"
#max_threads = os.cpu_count()
#similarity = embeddings_1 @ embeddings_2.T
#print(similarity)

cn_punc_list = [
    "。",  #// Period
    "？",  #// Question mark
    "！",  #// Exclamation mark
    "；",  #// Semicolon
    "：",  #// Colon
    "……", #// Ellipsis
    "——", #// Em dash (sometimes used for segmentation)
    "，",   #// Comma
]

class Embedder:
    def __init__(self):
        self.model = SentenceTransformer('iampanda/zpoint_large_embedding_zh')

    def forward(self, sentence):
        embedding = self.model.encode(sentence, normalize_embeddings=True)
        return embedding

def get_all_descriptions(topic="Ave_Mujica"):
    srcs_path = f"{topic}/img_srcs.txt"
    with open(srcs_path, "r", encoding="utf-8") as f:
        urls = f.readlines()

    entries = []
    for url in urls:
        description, url = url.split(" | ")
        path = f"{topic}/{description}.jpg"
        entries.append({
            "path": path,
            "description": description.replace("[無詞]", "")
        })

    return entries

def softmax(input, temperature=0.01):
    expo = np.exp(np.array(input)/temperature)
    output = expo / sum(expo)
    return output

def create_db(collection, embedder, collection_names):

    documents = []
    embeddings = []
    metadatas = []
    ids = []
    for collection_name in collection_names:
        entries = get_all_descriptions(topic=collection_name)

        for idx, entry in enumerate(entries):
            #print(idx)
            # Generate embedding
            embedding = embedder.forward(entry["description"])  # Replace with your actual embedding logic
            # Create Document object
            document = Document(page_content=entry["description"], metadata={"path": entry["path"]})

            # Collect data for upsert
            documents.append(document.page_content)  # The document content
            embeddings.append(embedding.tolist())  # The corresponding embedding
            metadatas.append(document.metadata)  # Metadata
            ids.append(collection_name+str(idx))  # Unique ID for each document

    if True:
        for doc in documents:
            assert isinstance(doc, str), f"Document is not a string: {doc}"

        expected_dim = len(embeddings[0])
        for emb in embeddings:
            assert isinstance(emb, list), f"Embedding is not a list: {emb}"
            assert len(emb) == expected_dim, f"Inconsistent embedding dimensions: {len(emb)} != {expected_dim}"

        for meta in metadatas:
            assert isinstance(meta, dict), f"Metadata is not a dictionary: {meta}"

        assert len(ids) == len(set(ids)), "IDs are not unique!"
        for id_ in ids:
            assert isinstance(id_, str), f"ID is not a string: {id_}"

        collection_info = collection.get()
        if "embeddings" in collection_info and collection_info["embeddings"]:
            expected_dim = len(collection_info["embeddings"][0])
            print(f"Collection's expected embedding dimension: {expected_dim}")

        current_dim = len(embeddings[0])
        assert current_dim == expected_dim, f"Embedding dimension mismatch: {current_dim} != {expected_dim}"

    # Upsert into the ChromaDB collection (store documents, embeddings, and metadata)
    collection.upsert(
        documents=documents,  # List of document contents
        embeddings=embeddings,  # List of embeddings
        metadatas=metadatas,  # List of metadata dictionaries
        ids=ids  # List of unique IDs
    )

def select_from_result(results):
    #{'ids': [['Ave_Mujica1035', 'Ave_Mujica824', 'Ave_Mujica248', 'MyGo191']],
    # 'embeddings': None,
    # 'documents': [['傻瓜!', '我真是個傻瓜', '簡直蠢斃了', '做事笨拙總是徒勞']],
    # 'uris': None,
    # 'included': ['metadatas', 'documents', 'distances'], 'data': None,
    # 'metadatas': [[{'path': 'Ave_Mujica/傻瓜!.jpg'}, {'path': 'Ave_Mujica/我真是個傻瓜.jpg'}, {'path': 'Ave_Mujica/簡直蠢斃了.jpg'}, {'path': 'MyGo/做事笨拙總是徒勞.jpg'}]],
    # 'distances': [[0.23414282500743866, 0.2603228986263275, 0.2766856849193573, 0.29713261127471924]]}
    probs = softmax(results['distances'][0])

    #print(probs)
    choice = np.random.choice(list(range(len(probs))), 2, p=probs)[0]
    #print(choice)
    url = results['metadatas'][0][choice]["path"]
    text = results['documents'][0][choice]

    return url, text

def segmentation(sentence):
    #separators = cn_punc_list
    sep_token = "<sep>"
    for punc in cn_punc_list:
        sentence = sentence.replace(punc, sep_token)

    sep_list = sentence.split(sep_token)
    output = []
    for sep in sep_list:
        if sep != "":
            output.append(sep)

    return output



class ImageDB:
    def __init__(self, create=False):
    # Initialize Chroma client
        self.client = chromadb.PersistentClient(path='./chroma_db')  # Specify the path for persistent storage
        #client = chromadb.Client()
        collection_name = "BangDream"
        self.collection = self.client.get_or_create_collection(
            name=collection_name, 
            metadata={
                "hnsw:num_threads": 8,
                "hnsw:space": "cosine" 
            }
        )
        #collection = client.create_collection(name=collection_name)
        self.embedder = Embedder()
        if create:
            create_db(collection=self.collection, embedder=Embedder(), collection_names=["Ave_Mujica", "MyGo"])

    #create_db(collection, embedder, collection_names=["Ave_Mujica", "MyGo"])

    def find_matches(self, query):

        segment_l = [query]#segmentation(query)
        matches = []
        for segment in segment_l:
            match = self.find_match(segment)
            matches.append(match)
        return matches

    def find_match(self, segment):
        query_embedding = self.embedder.forward(segment)  # Get embedding for the query
        results = self.collection.query(
            query_embeddings=query_embedding.tolist(),
            n_results=1
        )  # Retrieve top similar documents
        url, text = select_from_result(results)
        return [url, text]


#{'ids': [['Ave_Mujica1035', 'Ave_Mujica824', 'Ave_Mujica248', 'MyGo191']],
    # 'embeddings': None, 'documents': [['傻瓜!', '我真是個傻瓜', '簡直蠢斃了', '做事笨拙總是徒勞']],
    # 'uris': None, 'included': ['metadatas', 'documents', 'distances'], 'data': None,
    # 'metadatas': [[{'path': 'Ave_Mujica/傻瓜!.jpg'}, {'path': 'Ave_Mujica/我真是個傻瓜.jpg'}, {'path': 'Ave_Mujica/簡直蠢斃了.jpg'}, {'path': 'MyGo/做事笨拙總是徒勞.jpg'}]],
    # 'distances': [[0.23414282500743866, 0.2603228986263275, 0.2766856849193573, 0.29713261127471924]]}

    # Display results
    #for result in results:
    #    print(f"entry Path: {result.metadata['path']}, Description: {result.page_content}")

def test():
    imDB = ImageDB()
    query = "直行再轉左"
    output = imDB.find_matches(query)
    print(output)

def main():
    test()
    #imDB = ImageDB(create=True)


if __name__ == "__main__":
    main()