from transformers import AutoTokenizer, AutoModelForTokenClassification, pipeline

#Masked language modeling : guess the missing words model : bert-base-german-case ( case unsensitive)

model_name = "bert-base-german-cased"
nlp = pipeline("ner", model=model_name, tokenizer=model_name, device_map="auto")

text = "Reus schießt ein Tor für Dortmund nach einem Freistoß."
entities = nlp(text)
print(entities)
