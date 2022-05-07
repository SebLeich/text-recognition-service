import spacy
import json
from base64 import b64encode
import requests
from spacy.tokens import Doc, DocBin
import pyodbc
import logging

nlp = spacy.load("./output/model-last/")

class EvaluationResult:
    def __init__(self, text, ents, tokens):
        self.text = text
        self.ents = list(map(map_ents, ents))
        self.tokens = tokens

    def to_json(self):
        return json.dumps(self, default=lambda o: o.__dict__, sort_keys=True, indent=4)

def map_ents(ent):
    return {
        "label": ent.label_,
        "text": ent.text
    }

def map_tokens(token):
    return {
        "text": token.text,
        "tag": token.tag_,
        "isOov": token.is_oov,
        "isStop": token.is_stop,
        "isAlpha": token.is_alpha,
        "isDigit": token.is_digit,
        "likeNum": token.like_num,
        "likeEMail": token.like_email,
        "likeURL": token.like_url,
        "lemma": token.lemma_,
        "prefix": token.prefix_,
        "suffix": token.suffix_,
        "sentiment": token.sentiment,
        "entType": token.ent_type_
    }

def evaluate_text(text):

    doc = nlp(text)

    tokens = []
    for token in doc:
        tokens.append(map_tokens(token))

    return EvaluationResult(doc.text, doc.ents, tokens)

def introspect_token(token):
    with open('oidc.json') as json_file:
        data = json.load(json_file)

    payload = 'token=' + token
    auth = '%s:%s' % (data['api_resource'], data['api_secret'])
    headers = {
        'Authorization': 'Basic ' + b64encode(auth.encode()).decode("ascii"),
        'Content-Type': 'application/x-www-form-urlencoded'
    }

    res = requests.post(data['ids'] + data['token_introspection'], headers = headers, data = payload, verify = False)

    try:
        response = json.loads(res.content.decode('utf-8'))
        return response['active']

    except:
        logging.error(res.text)

def train_data():

    nlp = None

    conn = pyodbc.connect(
        'Driver={SQL Server};' 
        'Server=.\SQLEXPRESS;' 
        'Database=TRIZData;' 
        'Trusted_Connection=yes;'
    )

    cursor = conn.cursor()
    cursor.execute('SELECT DISTINCT TRIZData.dbo.TaggedWords.[Article] FROM TRIZData.dbo.TaggedWords')

    nlp = spacy.load('./output/model-last/')

    docbin = DocBin()

    counter = 0

    for row in cursor.fetchall():

        query = 'SELECT TRIZData.dbo.TaggedWords.[Text], TRIZData.dbo.TaggedWords.[Tag], TRIZData.dbo.TaggedWords.[SubsequentSpace], TRIZData.dbo.TaggedWords.[Guid] FROM TRIZData.dbo.TaggedWords WHERE TRIZData.dbo.TaggedWords.[Article]=\'' + row[0] + '\''

        docCursor = conn.cursor()
        docCursor.execute(query)
        
        words = []
        ents = []
        spaces = []
        lastB = None
        for entry in docCursor:
            words.append(entry[0])
            ents.append(entry[1])
            spaces.append(entry[2])
            counter+=1

            if entry[1][0] == 'B':
                lastB = entry

            elif entry[1][0] == 'I':

                if lastB == None:
                    print(entry[3])
                
            else:
                lastB = None

        doc = Doc(nlp.vocab, words=words, spaces=spaces, ents=ents)
        docbin.add(doc)

    docbin.to_disk("./train.spacy")
    return counter
