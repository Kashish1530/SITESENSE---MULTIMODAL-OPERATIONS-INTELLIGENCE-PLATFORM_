import sys
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parents[2]
if str(REPO_ROOT) not in sys.path:
    sys.path.insert(0, str(REPO_ROOT))
src_path = REPO_ROOT / "src"
if str(src_path) not in sys.path:
    sys.path.insert(0, str(src_path))

from ocr_module.ocr_engine import OCREngine
from deep_translator import GoogleTranslator
import requests

def translate_text(text: str) -> str:
    try:
        translator = GoogleTranslator(source='auto', target='en')
        return translator.translate_batch([text])[0]
    except Exception as e:
        print('Google translation failed, trying LibreTranslate:', e)
        try:
            payload = {'q': text, 'source': 'auto', 'target': 'en', 'format': 'text'}
            resp = requests.post('https://libretranslate.de/translate', json=payload, timeout=30)
            resp.raise_for_status()
            return resp.json().get('translatedText', '')
        except Exception as ee:
            print('LibreTranslate also failed:', ee)
            return 'Translation failed.'

def main():
    img_path = pathlib.Path(r'C:/Users/Desktop/.gemini/antigravity/brain/229d84d3-97ae-4d94-9110-e7f42d967221/.user_uploaded/media_1795438074584_841479b3.jpg')
    engine = OCREngine()
    response = engine.process_image(img_path, save_outputs=False)
    if not response.success:
        print('OCR failed:', response.error)
        return
    hindi = response.full_text
    print('--- Extracted Text (Hindi) ---')
    print(hindi)
    english = translate_text(hindi)
    print('\n--- Translated Text (English) ---')
    print(english)

if __name__ == '__main__':
    main()
