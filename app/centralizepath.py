# config.py - Create a centralized configuration file
from flask import render_template,abort,url_for, request, session, jsonify, current_app
from app.blueprints.main import bp
from werkzeug.utils import secure_filename
from app.utils.helpers import login_required
from datetime import datetime
import os
from pathlib import Path
from app.blueprints.analyzer import analyze_enhanced_topic_repetitions
from .config import config  # Import our config
import os
from pathlib import Path

ALLOWED_EXTENSIONS = {'png', 'jpg', 'jpeg', 'pdf'}

class Config:
    def __init__(self):
        self.is_production = bool(os.environ.get('RENDER'))
        self.base_dir = Path(__file__).parent.absolute()
        
        if self.is_production:
             self.base_storage = Path('/tmp/enhanced_repetition_analysis')
        else:
            self.base_storage = self.base_dir / 'enhanced_repetition_analysis'
        
        self.upload_folder = self.base_storage / 'uploads'
        self.temp_folder = self.base_storage / 'temp'
        self.reports_folder = self.base_storage / 'reports'
        
        # Ensure all directories exist
        self.ensure_directories()
    
    def ensure_directories(self):
        """Create all necessary directories"""
        for folder in [self.upload_folder, self.temp_folder, self.reports_folder]:
            folder.mkdir(parents=True, exist_ok=True)
            print(f"Ensured folder exists: {folder} (Exists: {folder.exists()})")
    
    def get_upload_path(self, filename=None):
        """Get upload path, optionally with filename"""
        if filename:
            return self.upload_folder / filename
        return self.upload_folder
    
    def get_temp_path(self, filename=None):
        """Get temp path, optionally with filename"""
        if filename:
            return self.temp_folder / filename
        return self.temp_folder
    
    def cleanup_temp_files(self):
        """Clean up temporary files (important for Render's ephemeral filesystem)"""
        import shutil
        if self.temp_folder.exists():
            shutil.rmtree(self.temp_folder)
            self.temp_folder.mkdir(parents=True, exist_ok=True)

# Create global config instance
config = Config()

def allowed_file(filename):
    return '.' in filename and filename.rsplit('.', 1)[1].lower() in ALLOWED_EXTENSIONS

@bp.route('/upload', methods=['POST'])
@login_required
def upload():
    files = request.files.getlist('paper_files')

    if not files or all(f.filename == '' for f in files):
        if request.is_json or request.accept_mimetypes['application/json'] > request.accept_mimetypes['text/html']:
            return jsonify({'status': 'error', 'message': 'No files provided'}), 400
        return render_template('report.html', error="No files provided")

    
    saved_filenames = []
    saved_file_paths = []

    for file in files:
        if file and file.filename != '':
            if not allowed_file(file.filename):
                return jsonify({'status': 'error', 'message': f'File type not allowed: {file.filename}'}), 400
            
            filename = secure_filename(file.filename)
            # Add timestamp to avoid conflicts
            timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
            unique_filename = f"{timestamp}_{filename}"
            
            file_path = config.get_upload_path(unique_filename)

            try:
                current_app.logger.info(f"Trying to save to {file_path}")
                file.save(str(file_path))  # Convert Path to string for save()
                current_app.logger.info(f"File saved to {file_path}")

                if not Path(file_path).exists():
                    current_app.logger.warning(f"File does NOT exist after save: {file_path}")
                else:
                    current_app.logger.info(f"Confirmed file exists after save: {file_path}")
                
                saved_filenames.append(unique_filename)
                saved_file_paths.append(str(file_path))
                current_app.logger.info(f"Saved file: {file_path}")

            except Exception as e:
                current_app.logger.error(f"Failed to save file {filename}: {e}")
                return jsonify({'status': 'error', 'message': 'File saving failed'}), 500

    # Verify files were actually saved
    existing_files = []
    for file_path in saved_file_paths:
        if Path(file_path).exists():
            existing_files.append(file_path)
        else:
            current_app.logger.warning(f"File not found after save: {file_path}")

    if not existing_files:
        return jsonify({'status': 'error', 'message': 'No files were successfully saved'}), 500

    current_app.logger.info(f"Processing {len(existing_files)} files: {existing_files}")

    try:
        # Pass the list of file paths directly to the analyzer
        result = analyze_enhanced_topic_repetitions(
            existing_files,  # Pass file list instead of folder
            debug=False,
            use_lemmatization=True,
            verbose=True  # Enable verbose for debugging
        )

        if not result:
            current_app.logger.error("Analysis returned no results")
            return jsonify({'status': 'error', 'message': 'Analysis failed or no valid files'}), 500

        # Store result in session for report page
        session['analysis_result'] = {
            'predictions': result.get('predictions', []),
            'summary': result.get('summary', {}),
            'analyzer_data': {
                'extracted_texts': [
                    {
                        'filename': data['filename'],
                        'confidence': data['confidence'],
                        'word_count': data['word_count'],
                        'date': data['date']
                    }
                    for data in result['analyzer'].extracted_texts
                ]
            }
        }

        return jsonify({
            'status': 'success',
            'message': f'Analysis complete! Processed {len(existing_files)} files.',
            'summary': result.get("summary", {}),
            'predictions': result.get("predictions", []),
            'redirect_url': '/report.html'
        }), 200

    except Exception as e:
        current_app.logger.error(f"Analysis error: {e}")
        return jsonify({'status': 'error', 'message': f'Analysis failed: {str(e)}'}), 500
    finally:
        config.cleanup_temp_files()
        try:
            for file_path in saved_file_paths:
                if Path(file_path).exists():
                    Path(file_path).unlink()
        except Exception as e:
            current_app.logger.warning(f"Could not clean up {file_path}: {e}")

@bp.route('/report.html')
def report():
    try:
        # Load analysis_result from session
        analysis_result = session.get('analysis_result')
        if not analysis_result:
            return render_template('error.html', message="No analysis data found. Please upload and analyze files first.")

        # Folder and files setup
        folder_name = 'enhanced_repetition_analysis'
        folder_path = os.path.join(current_app.root_path, folder_name)

        if not os.path.exists(folder_path):
            current_app.logger.error(f"Folder not found: {folder_path}")
            return abort(404, description="Report folder not found.")

        allowed_extensions = ('.png', '.jpg', '.jpeg', '.tiff', '.bmp', '.pdf', '.txt')
        files = [
            f for f in os.listdir(folder_path)
            if f.lower().endswith(allowed_extensions)
        ]

        # Generate URLs for files
        file_urls = [url_for('bp.enhanced_static', filename=f) for f in files]

        # Extract confidence stats and other summary data
        extracted_texts = analysis_result['analyzer_data']['extracted_texts']
        confidence_stats = {
            'high_confidence_count': len([f for f in extracted_texts if f['confidence'] >= 85]),
            'medium_confidence_count': len([f for f in extracted_texts if 70 <= f['confidence'] < 85]),
            'low_confidence_count': len([f for f in extracted_texts if f['confidence'] < 70])
        }
        total_words = sum(f['word_count'] for f in extracted_texts)
        avg_words_per_doc = total_words // len(extracted_texts) if extracted_texts else 0
        avg_ocr_confidence = sum(f['confidence'] for f in extracted_texts) / len(extracted_texts) if extracted_texts else 0

        # Pass all to template
        return render_template('report.html',
                               analysis_result=analysis_result,
                               generation_date=datetime.now().strftime("%B %d, %Y"),
                               confidence_stats=confidence_stats,
                               total_words=total_words,
                               avg_words_per_doc=avg_words_per_doc,
                               avg_ocr_confidence=avg_ocr_confidence,
                               files=file_urls)

    except Exception as e:
        current_app.logger.error(f"Error in /report: {e}")
        return abort(500, description="Internal Server Error")