import os
from flask import Flask, request, jsonify, render_template
import assemblyai as aai
from google.oauth2 import service_account
from googleapiclient.discovery import build

app = Flask(__name__)

# Configurazione IA
aai.settings.api_key = "2ca31980bc7f4df89e07a7246385f8ba"

# Configurazione Google Docs
GOOGLE_DOC_ID = "1ncr0N2W-TMbp-r_DefthoVhd_FIAQlVNJXxBa_y-ZU0"
SERVICE_ACCOUNT_FILE = 'credentials.json'
SCOPES = ['https://www.googleapis.com/auth/documents']

def scrivi_su_google_doc(testo_da_aggiungere):
    """Funzione per appendere il testo in fondo al Google Doc"""
    creds = service_account.Credentials.from_service_account_file(
        SERVICE_ACCOUNT_FILE, scopes=SCOPES)
    service = build('docs', 'v1', credentials=creds)
    
    # Recupera il documento per vedere quant'è lungo (serve l'indice di fine)
    doc = service.documents().get(documentId=GOOGLE_DOC_ID).execute()
    end_index = doc.get('body').get('content')[-1].get('endIndex') - 1
    
    requests = [
        {
            'insertText': {
                'location': {'index': end_index},
                'text': testo_da_aggiungere
            }
        }
    ]
    service.documents().batchUpdate(documentId=GOOGLE_DOC_ID, body={'requests': requests}).execute()

@app.route('/')
def index():
    return render_template('index.html')

@app.route('/upload', methods=['POST'])
def upload_audio():
    if 'audio' not in request.files:
        return jsonify({"error": "Nessun file"}), 400
    
    audio_file = request.files['audio']
    
    # 1. SALVATAGGIO AUDIO (Qui puoi reindirizzarlo verso la cartella del tuo gestionale/banca dati)
    audio_path = "banca_dati_audio/registrazione_odierna.wav" 
    os.makedirs("banca_dati_audio", exist_ok=True)
    audio_file.save(audio_path)

    # 2. ELABORAZIONE TRASCRIZIONE E TONO
    config = aai.TranscriptionConfig(speaker_labels=True, sentiment_analysis=True)
    transcriber = aai.Transcriber()
    
    try:
        transcript = transcriber.transcribe(audio_path, config=config)
        
        testo_completo_doc = "\n--- NUOVO DIALOGO REGISTRATO ---\n"
        
        for utterance in transcript.utterances:
            sentiments = [word.sentiment for word in utterance.words if word.sentiment]
            tono = max(set(sentiments), key=sentiments.count) if sentiments else "NEUTRAL"
            tono_it = "Arrabbiato" if tono == "NEGATIVE" else "Calmo" if tono == "POSITIVE" else "Neutro"
            
            # Sostituiamo i nomi dei parlanti con i numeri
            parlante_num = utterance.speaker.replace("A", "1").replace("B", "2").replace("C", "3")
            
            # Formattiamo la riga come vuoi che appaia sul foglio di scrittura
            riga = f"Persona {parlante_num} ({tono_it}): {utterance.text}\n"
            testo_completo_doc += riga

        # 3. SCRITTURA DIRETTA SUL FOGLIO MODIFICABILE
        scrivi_su_google_doc(testo_completo_doc)
        
        return jsonify({"status": "Successo! Trascrizione inviata al foglio modificabile e audio salvato."})

    except Exception as e:
        return jsonify({"error": str(e)}), 500

if __name__ == '__main__':
    port = int(os.environ.get("PORT", 5000))
    app.run(host='0.0.0.0', port=port)
