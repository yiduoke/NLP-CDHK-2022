import spacy
nlp = spacy.load('en_core_web_sm')


def find_persons(text):
     # Create Doc object
     doc2 = nlp(text)

     # Identify the persons
     persons = [ent.text for ent in doc2.ents if ent.label_ == 'PERSON']

     # Return persons
     return persons

print(find_persons("I passed a ball to Donna Hooshmand during the Golden Globes award Sunday night. The Oscar for Best Musical Piece in a Film goes to Adele"))