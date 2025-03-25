import os
from flask import Flask, render_template, request, send_file, redirect, url_for, flash, jsonify
from generate_pdf import parse_markdown, PDF, process_text_formatting, format_bullet_text, render_formatted_text
import uuid
import re
from flask_cors import CORS
import requests
import time
from dotenv import load_dotenv
from apscheduler.schedulers.background import BackgroundScheduler

load_dotenv()

app = Flask(__name__)
app.secret_key = os.environ.get('SECRET_KEY', 'development-key')

CORS(app)
UPLOAD_FOLDER = 'uploads'
OUTPUT_FOLDER = 'output'
ALLOWED_EXTENSIONS = {'md', 'markdown', 'txt'}

# Create necessary directories
os.makedirs(os.path.join(os.path.dirname(__file__), UPLOAD_FOLDER), exist_ok=True)
os.makedirs(os.path.join(os.path.dirname(__file__), OUTPUT_FOLDER), exist_ok=True)

def allowed_file(filename):
    return '.' in filename and filename.rsplit('.', 1)[1].lower() in ALLOWED_EXTENSIONS

@app.route('/')
def index():
    return render_template('index.html')

def clean_text(text):
    """Remove invisible or unsupported characters from the text."""
    import unicodedata
    cleaned_text = ''.join(
        c for c in text if unicodedata.category(c)[0] != 'C'  # Remove control characters
    )
    return cleaned_text

def generate_pdf_from_content(content):
    """Helper function to generate PDF from markdown content"""
    unique_id = str(uuid.uuid4())
    pdf_filename = unique_id + '.pdf'
    
    # Parse markdown content
    sections = parse_markdown(content)
    
    # Create PDF with better styling
    pdf = PDF()
    pdf.set_auto_page_break(auto=True, margin=15)
    
    # Add a Unicode-compatible font
    font_path = "NotoSans-Regular.ttf"
    possible_paths = [
        os.path.join(os.path.dirname(__file__), font_path),  # Current project directory
        os.path.join(os.getcwd(), font_path),               # Current working directory
        font_path                                           # Direct path
    ]
    
    font_full_path = next((path for path in possible_paths if os.path.exists(path)), None)
    if not font_full_path:
        app.logger.error(f"Font file not found in any of the following locations: {possible_paths}")
        raise FileNotFoundError(f"Font file not found in any of the following locations: {possible_paths}")
    
    pdf.add_font("NotoSans", "", font_full_path, uni=True)
    pdf.add_font("NotoSans", "B", font_full_path, uni=True)
    pdf.add_font("NotoSans", "I", font_full_path, uni=True)
    
    pdf.add_page()
    
    # Process each section
    try:
        for section in sections:
            if section["title"]:
                title = clean_text(section["title"])
                formatted_title = process_text_formatting(title)
                title = ''.join(part[1] for part in formatted_title)
                pdf.chapter_title(title, section["level"])
            if section["type"] == "code":
                code_content = "\n".join(section["content"])
                cleaned_code = clean_text(code_content)
                pdf.add_code_block(cleaned_code)
            elif section["type"] == "hr":
                pdf.add_horizontal_line()
            elif section["type"] == "table":
                pdf.add_table(section["content"])
            else:
                for line in section["content"]:
                    try:
                        # Clean the line of text
                        line = clean_text(line)
                        line = line.replace('***', '**')
                        
                        # Check if line is a bullet point
                        bullet_match = None
                        numbered_match = None
                        table_match = None
                        heading_match = None
                        link_match = None
                        image_match = None
                        bold_match = None
                        italic_match = None
                        strikethrough_match = None
                        code_match = None
                        quote_match = None
                        hr_match = None
                        
                        if isinstance(line, str):
                            # Check if line is a bullet point
                            bullet_match = re.match(r'^__BULLET__(\d+)__(.+)$', line)
                            # Check if line is a numbered item
                            numbered_match = re.match(r'^__NUMBERED__(\d+)__(\d+)__(.+)$', line)
                            # Check if line is a table
                            table_match = re.match(r'^__TABLE__(.+)$', line)
                            # Check if line is a heading
                            heading_match = re.match(r'^__HEADING__(\d+)__(.+)$', line)
                            # Check if line is a link
                            link_match = re.match(r'^__LINK__(.+)$', line)
                            # Check if line is an image
                            image_match = re.match(r'^__IMAGE__(.+)$', line)
                            # Check if line is a bold text
                            bold_match = re.match(r'^__BOLD__(.+)$', line)
                            # Check if line is an italic text
                            italic_match = re.match(r'^__ITALIC__(.+)$', line)
                            # Check if line is a strikethrough text
                            strikethrough_match = re.match(r'^__STRIKETHROUGH__(.+)$', line)
                            # Check if line is a code block
                            code_match = re.match(r'^__CODE__(.+)$', line)
                            # Check if line is a quote
                            quote_match = re.match(r'^__QUOTE__(.+)$', line)
                            # Check if line is a horizontal line
                            hr_match = re.match(r'^__HR__$', line)
                        
                        if bullet_match:
                            indent_level = int(bullet_match.group(1))
                            bullet_text = bullet_match.group(2)
                            
                            # Format the bullet text without HTML tags
                            bullet_text = format_bullet_text(bullet_text)
                            pdf.add_bullet_point(bullet_text, indent_level)
                            continue
                        
                        elif numbered_match:
                            indent_level = int(numbered_match.group(1))
                            number = numbered_match.group(2)
                            numbered_text = numbered_match.group(3)
                            
                            # Format the numbered text without HTML tags
                            numbered_text = format_bullet_text(numbered_text)
                            pdf.add_bullet_point(numbered_text, indent_level, number)
                            continue
                        
                        elif table_match:
                            table_data = table_match.group(1)
                            pdf.add_table(table_data)
                            continue
                        
                        elif heading_match:
                            level = int(heading_match.group(1))
                            heading_text = heading_match.group(2)
                            
                            heading_text = process_text_formatting(heading_text)
                            pdf.add_heading(heading_text, level)
                            continue
                        
                        elif link_match:
                            link_text = link_match.group(1)
                            
                            link_text = process_text_formatting(link_text)
                            pdf.add_link(link_text)
                            continue
                        
                        elif image_match:
                            image_path = image_match.group(1)
                            pdf.add_image(image_path)
                            continue
                            
                        elif bold_match:
                            bold_text = bold_match.group(1)
                            pdf.add_bold_text(bold_text)
                            continue
                        
                        elif italic_match:
                            italic_text = italic_match.group(1)
                            pdf.add_italic_text(italic_text)
                            continue
                            
                        elif strikethrough_match:
                            strikethrough_text = strikethrough_match.group(1)
                            pdf.add_strikethrough_text(strikethrough_text)
                            continue
                            
                        elif code_match:
                            code_text = code_match.group(1)
                            pdf.add_code_text(code_text)
                            continue
                        
                        elif quote_match:
                            quote_text = quote_match.group(1)
                            pdf.add_quote(quote_text)
                            continue
                            
                        elif hr_match:
                            pdf.add_horizontal_line()
                            continue
                            
                        elif "*" in line or "**" in line or "***" in line:
                            # Only process non-empty lines
                            if isinstance(line, str) and line.strip():
                                # Get the parts with style information
                                formatted_parts = process_text_formatting(line)
                                # Render the text with proper formatting
                                render_formatted_text(pdf, formatted_parts)
                            continue
                        
                        else:
                            # Only process non-empty lines
                            if isinstance(line, str) and line.strip():
                                # Get the parts with style information
                                formatted_parts = process_text_formatting(line)
                                # Render the text with proper formatting
                                render_formatted_text(pdf, formatted_parts)
                            continue
                    except Exception as e:
                        app.logger.error(f"Error processing line '{line}': {str(e)}")
                        raise
    except Exception as e:
        app.logger.error(f'Error processing section: {str(e)}')
        raise Exception(f'Error processing section: {str(e)}')
        
    # Save PDF
    pdf_path = os.path.join(os.path.dirname(__file__), OUTPUT_FOLDER, pdf_filename)
    pdf.output(pdf_path)
    
    return pdf_path

@app.route('/convert', methods=['POST'])
def convert_file():
    app.logger.info('Received request at /convert')
    # Check if request is AJAX
    is_ajax = request.headers.get('X-Requested-With') == 'XMLHttpRequest' or request.content_type.startswith('multipart/form-data')
    
    # Check if a file was uploaded
    if 'file' not in request.files or request.files['file'].filename == '':
        # If no file, check if markdown text was provided
        markdown_text = request.form.get('markdown-text', '')
        if markdown_text.strip():
            return convert_text()
        else:
            if is_ajax:
                return jsonify({'error': 'No file or markdown text provided'}), 400
            flash('No file or markdown text provided')
            return redirect(url_for('index'))
    
    file = request.files['file']
        
    if file and allowed_file(file.filename):
        # Generate unique filename to avoid collisions
        unique_id = str(uuid.uuid4())
        md_filename = unique_id + '.md'
        
        # Save uploaded markdown file
        md_path = os.path.join(os.path.dirname(__file__), UPLOAD_FOLDER, md_filename)
        file.save(md_path)
        
        # Convert to PDF
        try:
            content = ''
            with open(md_path, 'r', encoding='utf-8') as f:
                content = f.read()
            
            pdf_path = generate_pdf_from_content(content)
            
            # Return the PDF file
            return send_file(pdf_path, 
                            mimetype='application/pdf',
                            as_attachment=True, 
                            download_name=file.filename.rsplit('.', 1)[0] + '.pdf')
        
        except Exception as e:
            if is_ajax:
                return jsonify({'error': f'Error converting file: {str(e)}'}), 500
            flash(f'Error converting file: {str(e)}')
            return redirect(url_for('index'))
        finally:
            # Clean up temporary files
            try:
                if os.path.exists(md_path):
                    os.remove(md_path)
                # We'll leave the PDF for the download and clean up later
            except:
                pass
    
    if is_ajax:
        return jsonify({'error': 'Invalid file format. Please upload a markdown file (.md, .markdown, .txt)'}), 400
    flash('Invalid file format. Please upload a markdown file (.md, .markdown, .txt)')
    return redirect(url_for('index'))

@app.route('/convert_text', methods=['POST'])
def convert_text():
    try:
        # Check if request is AJAX
        is_ajax = request.headers.get('X-Requested-With') == 'XMLHttpRequest'

        # Get markdown text from the form
        markdown_text = request.form.get('markdown-text', '')

        if not markdown_text or not markdown_text.strip():
            app.logger.warning('No markdown text provided in the request')
            if is_ajax:
                return jsonify({'error': 'No markdown text provided'}), 400
            flash('No markdown text provided')
            return redirect(url_for('index'))

        # Generate PDF from the text
        pdf_path = generate_pdf_from_content(markdown_text)

        # Return the PDF file with a default name
        return send_file(
            pdf_path,
            mimetype='application/pdf',
            as_attachment=True,
            download_name='markdown-document.pdf'
        )

    except KeyError as ke:
        app.logger.error(f'Missing form data: {str(ke)}')
        if is_ajax:
            return jsonify({'error': f'Missing form data: {str(ke)}'}), 400
        flash(f'Missing form data: {str(ke)}')
        return redirect(url_for('index'))

    except Exception as e:
        app.logger.error(f'Error converting markdown: {str(e)}')
        if is_ajax:
            return jsonify({'error': f'Error converting markdown: {str(e)}'}), 500
        flash(f'Error converting markdown: {str(e)}')
        return redirect(url_for('index'))

@app.route('/health')
def health_check():
    return {'status': 'healthy'}, 200

# Cleanup task to remove old PDF files
@app.route('/cleanup', methods=['POST'])
def cleanup():
    if request.headers.get('X-Admin-Key') != os.environ.get('ADMIN_KEY'):
        return {'status': 'unauthorized'}, 403
    
    try:
        output_dir = os.path.join(os.path.dirname(__file__), OUTPUT_FOLDER)
        upload_dir = os.path.join(os.path.dirname(__file__), UPLOAD_FOLDER)
        
        # Remove files older than 1 hour
        import time
        current_time = time.time()
        one_hour = 3600
        
        # Clean output folder
        files_removed = 0
        for filename in os.listdir(output_dir):
            file_path = os.path.join(output_dir, filename)
            if os.path.isfile(file_path) and (current_time - os.path.getmtime(file_path)) > one_hour:
                os.remove(file_path)
                files_removed += 1
        
        # Clean upload folder
        for filename in os.listdir(upload_dir):
            file_path = os.path.join(upload_dir, filename)
            if os.path.isfile(file_path) and (current_time - os.path.getmtime(file_path)) > one_hour:
                os.remove(file_path)
                files_removed += 1
        
        return {'status': 'success', 'files_removed': files_removed}, 200
    
    except Exception as e:
        return {'status': 'error', 'message': str(e)}, 500

def keep_alive_scheduler():
    """Ping the website to keep it alive."""
    url = os.environ.get('PING_URL', 'http://localhost:5000/health')
    try:
        requests.get(url)
        print(f"Pinged {url} to keep the site alive.")
        app.logger.info(f"Pinged {url} to keep the site alive.")
    except Exception as e:
        app.logger.error(f"Error pinging {url}: {str(e)}")

def scheduled_cleanup():
    """Scheduled cleanup task to remove old files."""
    try:
        output_dir = os.path.join(os.path.dirname(__file__), OUTPUT_FOLDER)
        upload_dir = os.path.join(os.path.dirname(__file__), UPLOAD_FOLDER)
        
        current_time = time.time()
        one_hour = 3600
        
        # Clean output folder
        for filename in os.listdir(output_dir):
            file_path = os.path.join(output_dir, filename)
            if os.path.isfile(file_path) and (current_time - os.path.getmtime(file_path)) > one_hour:
                os.remove(file_path)
        
        # Clean upload folder
        for filename in os.listdir(upload_dir):
            file_path = os.path.join(upload_dir, filename)
            if os.path.isfile(file_path) and (current_time - os.path.getmtime(file_path)) > one_hour:
                os.remove(file_path)
        
        app.logger.info("Scheduled cleanup completed successfully.")
    except Exception as e:
        app.logger.error(f"Error during scheduled cleanup: {str(e)}")

scheduler = BackgroundScheduler()
scheduler.add_job(keep_alive_scheduler, 'interval', minutes=10)
scheduler.add_job(scheduled_cleanup, 'cron', hour=0, minute=0)
scheduler.start()

if __name__ == '__main__':
    app.run()
