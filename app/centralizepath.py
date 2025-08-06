from flask import render_template, abort, url_for, request, session, jsonify, current_app
from app.blueprints.main import bp
from werkzeug.utils import secure_filename
from app.utils.helpers import login_required
from datetime import datetime
import os
from pathlib import Path
from app.blueprints.analyzer import analyze_enhanced_topic_repetitions
import shutil
import logging
import json
import uuid 
import traceback

ALLOWED_EXTENSIONS = {'png', 'jpg', 'jpeg', 'pdf'}

# Use a simplified file config class specific to routes
class FileConfig:
    def __init__(self):
        self._initialized = False 
        self.is_production = os.environ.get('RENDER') == 'true' or os.environ.get('RENDER') == '1'
        
        # Use consistent base path
        if self.is_production:
            self.base_storage = Path('/tmp/enhanced_repetition_analysis')
        else:
            # Use absolute path from project root
            project_root = Path(__file__).resolve()
            while project_root.name != "Papalyze" and project_root != project_root.parent:
                project_root = project_root.parent # Adjust based on your structure
            self.base_storage = project_root / 'enhanced_repetition_analysis'
        
        self.upload_folder = self.base_storage / 'uploads'
        self.temp_folder = self.base_storage / 'temp'
        self.reports_folder = self.base_storage / 'reports'
        self.session_backup_folder = self.base_storage / 'session_backup'
    
    def _get_logger(self):
        """Get logger safely"""
        try:
            return current_app.logger
        except RuntimeError:
            return logging.getLogger(__name__)
    
    def ensure_directories(self):
        """Create all necessary directories with proper permissions"""
        if self._initialized:
            return
            
        logger = self._get_logger()
        
        try:
            for folder in [self.base_storage, self.upload_folder, self.temp_folder, 
                          self.reports_folder, self.session_backup_folder]:
                folder.mkdir(parents=True, exist_ok=True)
                # Set proper permissions for production
                if self.is_production:
                    os.chmod(str(folder), 0o755)
                logger.info(f"Created/verified directory: {folder}")
            
            self._initialized = True
            
        except Exception as e:
            logger.error(f"Failed to create directories: {e}")
            raise
    
    def get_upload_path(self, filename=None):
        self.ensure_directories()
        if filename:
            return self.upload_folder / filename
        return self.upload_folder
    
    def get_temp_path(self, filename=None):
        self.ensure_directories()
        if filename:
            return self.temp_folder / filename
        return self.temp_folder
    
    def get_session_backup_path(self, session_id):
        self.ensure_directories()
        return self.session_backup_folder / f"session_{session_id}.json"
    
    def cleanup_temp_files(self):
        """Clean up temporary files"""
        logger = self._get_logger()
        try:
            if self.temp_folder.exists():
                shutil.rmtree(str(self.temp_folder))
                self.temp_folder.mkdir(parents=True, exist_ok=True)
                logger.info("Cleaned up temp files")
        except Exception as e:
            logger.warning(f"Could not clean up temp files: {e}")
    
    def cleanup_upload_files(self):
        """Clean up upload files"""
        logger = self._get_logger()
        try:
            if self.upload_folder.exists():
                for file_path in self.upload_folder.iterdir():
                    if file_path.is_file():
                        file_path.unlink()
                logger.info("Cleaned up upload files")
        except Exception as e:
            logger.warning(f"Could not clean up upload files: {e}")

# Create config instance
file_config = FileConfig()

def allowed_file(filename):
    return '.' in filename and filename.rsplit('.', 1)[1].lower() in ALLOWED_EXTENSIONS

def save_analysis_result_backup(analysis_result, session_id=None):
    """Save analysis result to file as backup"""
    try:
        if not session_id:
            session_id = session.get('_permanent_id', 'default')
        
        backup_path = file_config.get_session_backup_path(session_id)
        
        with open(backup_path, 'w', encoding='utf-8') as f:
            json.dump(analysis_result, f, default=str, ensure_ascii=False, indent=2)
        
        current_app.logger.info(f"Saved analysis result backup to {backup_path}")
        return str(backup_path)
    except Exception as e:
        current_app.logger.error(f"Failed to save analysis result backup: {e}")
        return None

def load_analysis_result_backup(session_id=None):
    """Load analysis result from file backup"""
    try:
        if not session_id:
            session_id = session.get('_permanent_id', 'default')
        
        backup_path = file_config.get_session_backup_path(session_id)
        
        if backup_path.exists():
            with open(backup_path, 'r', encoding='utf-8') as f:
                analysis_result = json.load(f)
            current_app.logger.info(f"Loaded analysis result backup from {backup_path}")
            return analysis_result
    except Exception as e:
        current_app.logger.error(f"Failed to load analysis result backup: {e}")
    
    return None

@bp.route('/upload', methods=['POST'])
@login_required
def upload():
    saved_file_paths = []
    try:
        files = request.files.getlist('paper_files')

        if not files or all(f.filename == '' for f in files):
            return jsonify({'status': 'error', 'message': 'No files provided'}), 400

        current_app.logger.info(f"Received {len(files)} files for upload")
        
        # Ensure session is permanent
        session.permanent = True
        
        # Generate session ID
        if '_permanent_id' not in session:
            session['_permanent_id'] = datetime.now().strftime("%Y%m%d_%H%M%S") + "_" + str(uuid.uuid4())
        
        current_app.logger.info(f"Session ID: {session['_permanent_id']}")
        
        # Ensure directories exist
        file_config.ensure_directories()
        
        # Clean up existing files
        file_config.cleanup_temp_files()
        file_config.cleanup_upload_files()
        
        saved_filenames = []

        for i, file in enumerate(files):
            if file and file.filename != '':
                current_app.logger.info(f"Processing file {i+1}: {file.filename}")
                
                if not allowed_file(file.filename):
                    error_msg = f'File type not allowed: {file.filename}'
                    current_app.logger.error(error_msg)
                    return jsonify({'status': 'error', 'message': error_msg}), 400
                
                filename = secure_filename(file.filename)
                timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
                unique_filename = f"{timestamp}_{i}_{filename}"
                
                file_path = file_config.get_upload_path(unique_filename)
                
                current_app.logger.info(f"Saving file to: {file_path}")

                try:
                    # Save the file
                    file.save(str(file_path))
                    
                    # Verify file was saved
                    if file_path.exists() and file_path.stat().st_size > 0:
                        saved_filenames.append(unique_filename)
                        saved_file_paths.append(str(file_path))
                        current_app.logger.info(f"Successfully saved file: {file_path} (size: {file_path.stat().st_size} bytes)")
                    else:
                        current_app.logger.error(f"File was not saved properly: {file_path}")
                        
                except Exception as e:
                    current_app.logger.error(f"Failed to save file {filename}: {e}")
                    return jsonify({'status': 'error', 'message': f'File saving failed: {str(e)}'}), 500

        # Verify saved files
        existing_files = []
        for file_path in saved_file_paths:
            path_obj = Path(file_path)
            if path_obj.exists() and path_obj.stat().st_size > 0:
                existing_files.append(file_path)
                current_app.logger.info(f"Verified file exists: {file_path}")

        if not existing_files:
            current_app.logger.error("No files were successfully saved")
            return jsonify({'status': 'error', 'message': 'No files were successfully saved'}), 500

        current_app.logger.info(f"Processing {len(existing_files)} verified files for analysis")

        # Enhanced error handling for analysis
        try:
            result = analyze_enhanced_topic_repetitions(
                existing_files,
                debug=True,
                use_lemmatization=True,
                verbose=True
            )
        except Exception as analysis_error:
            current_app.logger.error(f"Analysis function failed: {analysis_error}")
            current_app.logger.error(traceback.format_exc())
            return jsonify({
                'status': 'error', 
                'message': f'Analysis failed: {str(analysis_error)}'
            }), 500

        if not result:
            current_app.logger.error("Analysis returned no results")
            
            # Check if it's a text extraction issue
            current_app.logger.info("Checking file formats and attempting manual inspection...")
            for file_path in existing_files:
                current_app.logger.info(f"File: {file_path}, Size: {Path(file_path).stat().st_size} bytes")
            
            return jsonify({
                'status': 'error', 
                'message': 'Analysis failed - no text could be extracted from files. Please ensure files are readable PDFs or images with clear text.'
            }), 500

        # Process successful result
        analysis_result = {
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
            },
            'timestamp': datetime.now().isoformat(),
            'file_count': len(existing_files)
        }

        # Store in session
        session['analysis_result'] = analysis_result
        session['analysis_timestamp'] = datetime.now().isoformat()
        
        # Save backup
        backup_path = save_analysis_result_backup(analysis_result, session.get('_permanent_id'))
        if backup_path:
            session['analysis_backup_path'] = backup_path

        session.modified = True
        
        current_app.logger.info("Analysis completed successfully")

        return jsonify({
            'status': 'success',
            'message': f'Analysis complete! Processed {len(existing_files)} files.',
            'summary': result.get("summary", {}),
            'predictions': result.get("predictions", []),
            'session_id': session.get('_permanent_id'),
            'redirect_url': '/report.html'
        }), 200

    except Exception as e:
        current_app.logger.error(f"Upload route error: {e}")
        current_app.logger.error(traceback.format_exc())
        return jsonify({'status': 'error', 'message': f'Upload failed: {str(e)}'}), 500
    
    finally:
        # Clean up uploaded files
        try:
            for file_path in saved_file_paths:
                path_obj = Path(file_path)
                if path_obj.exists():
                    path_obj.unlink()
                    current_app.logger.info(f"Cleaned up file: {file_path}")
        except Exception as e:
            current_app.logger.warning(f"Could not clean up files: {e}")

@bp.route('/report.html')
def report():
    try:
        current_app.logger.info("Report route accessed")
        current_app.logger.info(f"Session keys: {list(session.keys())}")
        
        # Try to load from session first
        analysis_result = session.get('analysis_result')
        
        # Try backup if session is empty
        if not analysis_result:
            current_app.logger.warning("No analysis data found in session, trying backup")
            analysis_result = load_analysis_result_backup(session.get('_permanent_id'))
            
            if analysis_result:
                session['analysis_result'] = analysis_result
                session.modified = True
                current_app.logger.info("Restored analysis data from backup")

        if not analysis_result:
            current_app.logger.error("No analysis data found in session or backup")
            return render_template('error.html', 
                                   message="No analysis data found. Please upload and analyze files first.",
                                   debug_info=f"Session ID: {session.get('_permanent_id', 'None')}")

        current_app.logger.info("Loading report with analysis results")

        # Process analysis results for template
        extracted_texts = analysis_result.get('analyzer_data', {}).get('extracted_texts', [])
        
        confidence_stats = {
            'high_confidence_count': len([f for f in extracted_texts if f.get('confidence', 0) >= 85]),
            'medium_confidence_count': len([f for f in extracted_texts if 70 <= f.get('confidence', 0) < 85]),
            'low_confidence_count': len([f for f in extracted_texts if f.get('confidence', 0) < 70])
        }
        
        total_words = sum(f.get('word_count', 0) for f in extracted_texts)
        avg_words_per_doc = total_words // len(extracted_texts) if extracted_texts else 0
        avg_ocr_confidence = sum(f.get('confidence', 0) for f in extracted_texts) / len(extracted_texts) if extracted_texts else 0

        return render_template('report.html',
                               analysis_result=analysis_result,
                               generation_date=datetime.now().strftime("%B %d, %Y"),
                               confidence_stats=confidence_stats,
                               total_words=total_words,
                               avg_words_per_doc=avg_words_per_doc,
                               avg_ocr_confidence=avg_ocr_confidence,
                               files=[])  # Empty for production

    except Exception as e:
        current_app.logger.error(f"Error in /report: {e}")
        current_app.logger.error(traceback.format_exc())
        return abort(500, description=f"Internal Server Error: {str(e)}")

@bp.route('/debug-session')
def debug_session():
    """Debug route to check session data"""
    return jsonify({
        'session_keys': list(session.keys()),
        'session_id': session.get('_permanent_id'),
        'has_analysis_result': 'analysis_result' in session,
        'analysis_timestamp': session.get('analysis_timestamp'),
        'backup_path': session.get('analysis_backup_path'),
        'session_permanent': session.permanent,
        'is_production': file_config.is_production,
        'base_storage': str(file_config.base_storage)
    })
config = FileConfig()