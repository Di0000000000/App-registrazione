import os
import time
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

@app.route('/upload_audio', methods=['POST'])
def upload_audio():
    if 'audio' not in request.files:
        return jsonify({"success": False, "error": "Nessun file"}), 400
    
    audio_file = request.files['audio']
    chosen_lang = request.form.get('lang', 'it')
    
    timestamp = int(time.time())
    # Usiamo un'estensione generica per non confondere l'IA sul formato di origine del telefono
    audio_path = f"banca_dati_audio/chunk_{timestamp}.raw" 
    os.makedirs("banca_dati_audio", exist_ok=True)
    audio_file.save(audio_path)

    if chosen_lang == 'auto':
        config = aai.TranscriptionConfig(language_detection=True)
    else:
        config = aai.TranscriptionConfig(language_code=chosen_lang)
        
    transcriber = aai.Transcriber()
    
    try:
        transcript = transcriber.transcribe(audio_path, config=config)
        
        if os.path.exists(audio_path):
            os.remove(audio_path)
            
        if transcript.text and transcript.text.strip():
            orario_blocco = time.strftime('%H:%M:%S', time.localtime(timestamp))
            testo_da_scrivere = f"\n[{orario_blocco}] {transcript.text}\n"
            scrivi_su_google_doc(testo_da_scrivere)
        
        return jsonify({"success": True})

    except Exception as e:
        return jsonify({"success": False, "error": str(e)}), 500

if __name__ == '__main__':
    port = int(os.environ.get("PORT", 5000))
    app.run(host='0.0.0.0', port=port)
