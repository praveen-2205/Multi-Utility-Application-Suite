import google.generativeai as genai
import os
import re
import logging
from flask import Flask, render_template, request, redirect, url_for, flash, send_file, send_from_directory
from text_to_image import text_to_handwritten_image
from watermark import apply_text_watermark
import shutil
from werkzeug.utils import secure_filename
from pikepdf import Pdf, PdfImage
from PyPDF2 import PdfWriter, PdfReader
from pdf2image import convert_from_path
from moviepy.editor import VideoFileClip
import qrcode
from datetime import datetime
import cv2
from pdf2docx import Converter
import tempfile
from gtts import gTTS
from io import BytesIO
import docx
import pyttsx3

app = Flask(__name__)
app.secret_key = 'your_secret_key'  # Required for flash messages

# Directory Configurations
UPLOAD_FOLDER = 'static/uploads'
ENCRYPTED_FOLDER = 'static/encrypted'
OUTPUT_FOLDER = 'static/converted_images'
EXTRACTED_IMAGES_FOLDER = 'static/extracted_images'
ZIP_FOLDER = 'static/zips'
os.makedirs(UPLOAD_FOLDER, exist_ok=True)
os.makedirs(OUTPUT_FOLDER, exist_ok=True)
app.config.update({
    'UPLOAD_FOLDER': UPLOAD_FOLDER,
    'ENCRYPTED_FOLDER': ENCRYPTED_FOLDER,
    'OUTPUT_FOLDER': OUTPUT_FOLDER,
    'EXTRACTED_IMAGES_FOLDER': EXTRACTED_IMAGES_FOLDER,
    'ZIP_FOLDER': ZIP_FOLDER
})

for folder in [UPLOAD_FOLDER, ENCRYPTED_FOLDER, OUTPUT_FOLDER, EXTRACTED_IMAGES_FOLDER, ZIP_FOLDER]:
    os.makedirs(folder, exist_ok=True)

# Configure logging
logging.basicConfig(level=logging.INFO)

@app.route('/')
def home():
    return render_template('home.html')

# Text to Image Routes
@app.route('/text-to-image-form')
def text_to_image_form():
    return render_template('text_to_image.html')

@app.route('/text-to-image', methods=['POST'])
def text_to_image():
    if 'file' not in request.files:
        flash("No file part")
        return redirect(request.url)

    file = request.files['file']

    if file.filename == '' or not file.filename.endswith('.txt'):
        flash("Invalid file type. Please upload a .txt file.")
        return redirect(request.url)

    try:
        text = file.read().decode('utf-8')
        img_path = text_to_handwritten_image(text, app.config['UPLOAD_FOLDER'])
        img_filename = os.path.basename(img_path)
        return render_template('text_to_image_download.html', img_path=f'uploads/{img_filename}')
    except Exception as e:
        logging.error(f"Error generating image: {e}")
        return "An error occurred while processing the file."

# PDF Watermark Routes
@app.route('/upload-form')
def upload_form():
    return render_template('upload.html')

@app.route('/upload', methods=['POST'])
def upload_file():
    if 'pdf_file' not in request.files or 'watermark_text' not in request.form:
        flash("Missing file or watermark text!")
        return redirect(request.url)

    pdf_file = request.files['pdf_file']
    watermark_text = request.form['watermark_text']

    if pdf_file.filename == '':
        flash("No file selected")
        return redirect(request.url)

    try:
        output_pdf = apply_text_watermark(pdf_file, watermark_text)
        return send_file(output_pdf, download_name=f"watermarked_{pdf_file.filename}", as_attachment=True, mimetype='application/pdf')
    except Exception as e:
        logging.error(f"Error applying watermark: {e}")
        return "An error occurred while processing the file."
    
# PDF Encryption Routes
@app.route('/encrypt-form')
def encrypt_form():
    return render_template('encrypt_upload.html')

@app.route('/encrypt', methods=['POST'])
def encrypt_file():
    uploaded_file = request.files['pdf_file']
    password = request.form['password']

    if uploaded_file.filename == '':
        flash("No file selected")
        return redirect(request.url)

    file_path = os.path.join(app.config['UPLOAD_FOLDER'], secure_filename(uploaded_file.filename))
    uploaded_file.save(file_path)
    encrypted_file_path = os.path.join(app.config['ENCRYPTED_FOLDER'], f"encrypted_{uploaded_file.filename}")

    try:
        pdf_writer = PdfWriter()
        with open(file_path, "rb") as file:
            pdf_reader = PdfReader(file)
            for page in pdf_reader.pages:
                pdf_writer.add_page(page)
            pdf_writer.encrypt(password)
            with open(encrypted_file_path, "wb") as encrypted_file:
                pdf_writer.write(encrypted_file)
        return redirect(url_for('download_file', filename=f"encrypted_{uploaded_file.filename}"))
    except Exception as e:
        logging.error(f"Error encrypting PDF: {e}")
        flash("An error occurred while encrypting the file.")
        return redirect(request.url)

@app.route('/download/<filename>')
def download_file(filename):
    return render_template('encrypted_download.html', filename=filename)

@app.route('/download_file/<filename>')
def download(filename):
    file_path = os.path.join(app.config['ENCRYPTED_FOLDER'], filename)
    return send_file(file_path, as_attachment=True)

# PDF Image Extraction Routes
@app.route('/uploadkarthik-form')
def uploadkarthik_form():
    return render_template('uploadkarthik.html')

@app.route('/uploadkarthik', methods=['POST'])
def uploadkarthik():
    file = request.files['file']
    filename = secure_filename(file.filename)
    filepath = os.path.join(app.config['UPLOAD_FOLDER'], filename)
    file.save(filepath)

    pdf = Pdf.open(filepath)
    page_numbers = request.form['page'].split(',')
    pdf_name = os.path.splitext(filename)[0]
    image_dir = os.path.join(app.config['EXTRACTED_IMAGES_FOLDER'], pdf_name)
    os.makedirs(image_dir, exist_ok=True)

    try:
        # Iterate through each specified page
        for page_number_str in page_numbers:
            page_number = int(page_number_str.strip()) - 1  # Convert to 0-based index
            if 0 <= page_number < len(pdf.pages):
                page = pdf.pages[page_number]
                for image_key in page.images.keys():
                    raw_image = page.images[image_key]
                    pdf_image = PdfImage(raw_image)
                    image_filename = f"{image_key[1:]}.png"
                    pdf_image.extract_to(fileprefix=os.path.join(image_dir, image_filename.replace('.png', '')))
            else:
                logging.error(f"Page number {page_number + 1} is out of range.")
        
        zip_filepath = os.path.join(app.config['ZIP_FOLDER'], f"{pdf_name}_images.zip")
        shutil.make_archive(zip_filepath.replace('.zip', ''), 'zip', image_dir)
        return send_file(zip_filepath, as_attachment=True)
    except Exception as e:
        logging.error(f"Error extracting images: {e}")
        return "An error occurred while extracting images."
    
# PDF Processing Routes
@app.route('/process-form')
def process_form():
    return render_template('process.html')

@app.route('/process', methods=['POST'])
def process():
    action = request.form.get('action')
    pages = request.form.get('pages')
    pdf_file = request.files['fileInput']

    if pdf_file and action:
        pdf = Pdf.open(pdf_file)
        try:
            if action == "reverse":
                pdf.pages.reverse()
                new_pdf_path = os.path.join(app.config['UPLOAD_FOLDER'], "reversed.pdf")
            elif action == "delete":
                for page in sorted([int(p) - 1 for p in pages.split(",")], reverse=True):
                    del pdf.pages[page]
                new_pdf_path = os.path.join(app.config['UPLOAD_FOLDER'], "deleted.pdf")
            elif action == "copy":
                new_pdf = Pdf.new()
                for page in [int(p) - 1 for p in pages.split(",")]:
                    new_pdf.pages.append(pdf.pages[page])
                new_pdf_path = os.path.join(app.config['UPLOAD_FOLDER'], "copied.pdf")
                new_pdf.save(new_pdf_path)
            pdf.save(new_pdf_path)
            return send_file(new_pdf_path, as_attachment=True)
        except Exception as e:
            logging.error(f"Error processing PDF: {e}")
            return "An error occurred while processing the PDF."

# Convert PDF Pages to Images
@app.route('/uploadmani')
def uploadmani():
    return render_template('uploadmani.html')

@app.route('/uploadpdf', methods=['POST'])
def uploadpdf():
    if 'pdf_file' not in request.files:
        return redirect(request.url)

    pdf_file = request.files['pdf_file']
    if pdf_file.filename == '':
        return redirect(request.url)

    if pdf_file:
        # Save uploaded PDF
        pdf_filename = secure_filename(pdf_file.filename)
        pdf_path = os.path.join(app.config['UPLOAD_FOLDER'], pdf_filename)
        pdf_file.save(pdf_path)

        # Convert PDF to images
        pages = convert_from_path(pdf_path,poppler_path=r"Library/bin")
        image_paths = []
        for i, page in enumerate(pages, start=1):
            image_filename = f"page{i}.jpg"
            image_path = os.path.join(app.config['OUTPUT_FOLDER'], image_filename)
            page.save(image_path, 'JPEG')
            image_paths.append(image_filename)

        # Render template with image paths
        return render_template('uploadmani.html', image_paths=image_paths)

@app.route('/audio-form')
def audio_form():
    return render_template('audio.html')

@app.route('/convert-video-to-audio', methods=['POST'])
def convert_video_to_audio():
    if 'video_file' not in request.files:
        flash("No video file part")
        return redirect(request.url)

    video_file = request.files['video_file']

    if video_file.filename == '':
        flash("No file selected")
        return redirect(request.url)

    try:
        video_path = os.path.join(app.config['UPLOAD_FOLDER'], secure_filename(video_file.filename))
        video_file.save(video_path)

        # Convert video to audio
        audio_path = video_path.rsplit('.', 1)[0] + '.mp3'  # Save as MP3
        with VideoFileClip(video_path) as video:
            video.audio.write_audiofile(audio_path)

        return send_file(audio_path, as_attachment=True)
    except Exception as e:
        logging.error(f"Error converting video to audio: {e}")
        return "An error occurred while converting the video."

@app.route('/qr', methods=['GET', 'POST'])
def qr():
    if request.method == 'POST':
        url = request.form['url']
        # Generate QR code
        qr_img = qrcode.make(url)
        
        # Save the QR code as a file
        qr_code_path = 'static/qr_code.png'
        qr_img.save(qr_code_path)

        # Serve the file for download
        return send_file(qr_code_path, as_attachment=True, download_name='qr_code.png')

    return render_template('qr.html')
        
@app.route('/display_image/<filename>')
def display_image(filename):
    return send_from_directory(app.config['OUTPUT_FOLDER'], filename)

@app.route('/download_image/<filename>')
def download_image(filename):
    return send_from_directory(app.config['OUTPUT_FOLDER'], filename, as_attachment=True)

# Configure Google Generative AI with an environment variable for security
GOOGLE_API_KEY = os.getenv('AIzaSyDuU3IIsxYEXSFymaoHL5xW5eR9S8JFiJg')
genai.configure(api_key=GOOGLE_API_KEY)

# Define a logging configuration for debugging
logging.basicConfig(level=logging.DEBUG)

def detect_language(code):
    """Detect programming language based on code syntax and patterns"""
    patterns = {
        'assembly': r'(\s*section\s+\w+|\s*global\s+\w+|\s*extern\s+\w+|\s*mov\s+\w+\s*,\s*\w+)',
        'python': r'(def |import |from .* import|class .*:)',
        'javascript': r'(function |const |let |var |=>)',
        'java': r'(public class|private class|protected class|class .*{)',
        'cpp': r'(#include|using namespace|int main\()',
        'ruby': r'(def |require |module |class .*end)',
        'go': r'(package |func |import \()',
        'csharp': r'(public class|private class|protected class|class .*|using |namespace)',
        'php': r'(\$[a-zA-Z_][a-zA-Z0-9_]*|class |function |echo |include |require)',
        'swift': r'(func |import |class |let |var)',
        'kotlin': r'(fun |class |val |var |import)',
    }
    
    for lang, pattern in patterns.items():
        if re.search(pattern, code):
            return lang
    return 'unknown'

@app.route('/translate_code')
def translate_code_form():
    return render_template('translate_code.html')

@app.route('/translate_code', methods=['POST'])
def translate_code():
    try:
        source_code = request.form.get('source_code')
        target_language = request.form.get('target_language')
        
        if not source_code or not target_language:
            flash("Please provide both source code and target language")
            return redirect(url_for('translate_code'))
        
        # Detect source language
        source_language = detect_language(source_code)
        
        if source_language == 'unknown':
            flash("Could not detect source language")
            return redirect(url_for('translate_code'))

        # Configure Gemini model
        model = genai.GenerativeModel('gemini-pro')
        
        # Create prompt for Gemini
        prompt = f"""
        Act as a code translator. Translate the following {source_language} code to {target_language}.
        Maintain the same functionality and logic.
        Only respond with the translated code, no explanations.
        
        Source code:
        ```{source_language}
        {source_code}
        ```
        
        Translate to {target_language} code:
        """
        
        # Get translation from Gemini
        response = model.generate_content(prompt)
        
        # Extract code from response
        translated_code = response.text
        
        # Clean up the response to extract just the code
        # Remove markdown code blocks if present
        translated_code = re.sub(r'```.*?\n', '', translated_code)
        translated_code = translated_code.replace('```', '').strip()
        
        return render_template(
            'translate_code_result.html',
            source_code=source_code,
            translated_code=translated_code,
            source_language=source_language,
            target_language=target_language
        )
        
    except Exception as e:
        logging.error(f"Translation error: {e}")
        flash(f"An error occurred during translation: {str(e)}")
        return redirect(url_for('translate_code'))
    
    
    
# pdf to video using poppler
@app.route('/uploadkarthik1-form')
def uploadkarthik1_form():
    return render_template('uploadkarthik1.html')


@app.route('/uploadkarthik1', methods=['POST'])
def uploadkarthik1():
    # Step 1: Create uploads directory if it doesn't exist
    uploads_dir = 'uploads'
    os.makedirs(uploads_dir, exist_ok=True)

    # Step 2: Retrieve uploaded PDF file
    pdf_file = request.files['pdf']
    pdf_path = os.path.join(uploads_dir, pdf_file.filename)
    pdf_file.save(pdf_path)

    # Step 3: Convert PDF pages to images
    images = convert_from_path(pdf_path)
    image_files = []
    for i, image in enumerate(images):
        img_path = f"frame_{i}.jpg"
        image.save(img_path, 'JPEG')
        image_files.append(img_path)

    # Step 4: Combine images into a video
    frame = cv2.imread(image_files[0])
    height, width, _ = frame.shape
    video_path = 'output_video.avi'
    video = cv2.VideoWriter(video_path, cv2.VideoWriter_fourcc(*'DIVX'), 0.03, (width, height))

    for img_file in image_files:
        frame = cv2.imread(img_file)
        video.write(frame)

    video.release()

    # Clean up image files
    for img_file in image_files:
        os.remove(img_file)
    os.remove(pdf_path)

    # Step 5: Send the video file as a response
    return send_file(video_path, as_attachment=True)


@app.route('/uploadsumith')
def uploadsumith():
    return render_template('uploadsumith.html')

@app.route('/convertsum', methods=['POST'])
def convertsum():
    if 'pdf_file' not in request.files:
        return "No file part"
    
    pdf_file = request.files['pdf_file']
    if pdf_file.filename == '':
        return "No selected file"
    
    filename = secure_filename(pdf_file.filename)
    pdf_path = os.path.join(app.config['UPLOAD_FOLDER'], filename)
    pdf_file.save(pdf_path)
    
    # Convert PDF to DOCX
    word_path = pdf_path.replace('.pdf', '.docx')
    cv = Converter(pdf_path)
    cv.convert(word_path, start=0, end=None)
    cv.close()
    
    return send_file(word_path, as_attachment=True)




app.config['UPLOAD_FOLDER'] = 'static/uploads'
app.config['UNLOCKED_FOLDER'] = 'static/unlocked'

os.makedirs(app.config['UPLOAD_FOLDER'], exist_ok=True)
os.makedirs(app.config['UNLOCKED_FOLDER'], exist_ok=True)

# Route to display the unlock form
@app.route('/unlock')
def unlock_page():
    return render_template('unlock.html')

# Route to handle PDF unlocking
@app.route('/unlock-pdf', methods=['POST'])
def unlock_pdf():
    if 'pdf_file' not in request.files:
        flash("No file uploaded.")
        return redirect(request.url)

    pdf_file = request.files['pdf_file']
    password = request.form.get('password', '')

    if pdf_file.filename == '':
        flash("No file selected.")
        return redirect(request.url)

    # Save the uploaded PDF to a temporary file
    with tempfile.NamedTemporaryFile(delete=False, suffix='.pdf') as temp_file:
        pdf_file.save(temp_file.name)
        temp_file_path = temp_file.name

    # Try to remove the password
    unlocked_pdf_path = remove_pdf_password(temp_file_path, password)

    if unlocked_pdf_path:
        return render_template('unlocked_download.html', filename=os.path.basename(unlocked_pdf_path))
    else:
        flash("Incorrect password or failed to unlock PDF.")
        return redirect(url_for('unlock_page'))

# Function to remove the password from a PDF
def remove_pdf_password(input_path, password):
    try:
        pdf_reader = PdfReader(input_path)
        if pdf_reader.is_encrypted:
            pdf_reader.decrypt(password)
        
        # Save an unlocked version
        output_path = os.path.join(app.config['UNLOCKED_FOLDER'], f"unlocked_{os.path.basename(input_path)}")
        pdf_writer = PdfWriter()

        for page in pdf_reader.pages:
            pdf_writer.add_page(page)

        with open(output_path, "wb") as output_file:
            pdf_writer.write(output_file)
        
        return output_path

    except Exception as e:
        print(f"Error unlocking PDF: {e}")
        return None

# Route to download the unlocked PDF
@app.route('/download_unlocked/<filename>')
def download_unlocked(filename):
    return send_file(os.path.join(app.config['UNLOCKED_FOLDER'], filename), as_attachment=True)





@app.route('/uploadmani2')
def uploadmani2():
    return render_template('uploadmani2.html')

# Route to handle file upload and conversion to audio
@app.route('/upload_file2', methods=['POST'])
def upload_file2():
    if 'file' not in request.files:
        return 'No file part'
    
    file = request.files['file']
    
    if file.filename == '':
        return 'No selected file'
    
    if file and file.filename.endswith('.txt'):
        # Save the uploaded .txt file
        filepath = os.path.join(app.config['UPLOAD_FOLDER'], file.filename)
        file.save(filepath)

        # Read the text content from the file
        with open(filepath, 'r') as f:
            text = f.read()

        # Convert the text to audio using pyttsx3
        engine = pyttsx3.init()
        audio_file = os.path.join(app.config['UPLOAD_FOLDER'], 'output.mp3')

        engine.save_to_file(text, audio_file)
        engine.runAndWait()

        # Provide the download link for the generated audio file
        return send_from_directory(app.config['UPLOAD_FOLDER'], 'output.mp3', as_attachment=True)

    return 'Invalid file type. Please upload a .txt file.'

if __name__ == '__main__':
    app.run(debug=True)