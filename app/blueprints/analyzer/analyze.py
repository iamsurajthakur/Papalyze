import cv2
import pytesseract
from PIL import Image
import numpy as np
import os
import json
import pandas as pd
from datetime import datetime, timedelta
import re
from collections import Counter, defaultdict
import matplotlib.pyplot as plt
import seaborn as sns
from sklearn.feature_extraction.text import TfidfVectorizer, CountVectorizer
from sklearn.cluster import KMeans
from sklearn.metrics.pairwise import cosine_similarity
from wordcloud import WordCloud
import nltk
from nltk.corpus import stopwords
from pdf2image import convert_from_path
from nltk.tokenize import word_tokenize, sent_tokenize
from nltk.stem import WordNetLemmatizer
import warnings
warnings.filterwarnings('ignore')

# Download required NLTK data silently
nltk_downloads = ["punkt", "stopwords", "wordnet", "omw-1.4", "averaged_perceptron_tagger"]
for item in nltk_downloads:
    try:
        nltk.data.find(f'tokenizers/{item}' if item == 'punkt' else f'corpora/{item}')
    except LookupError:
        nltk.download(item, quiet=True)

def convert_pdf_to_images(pdf_path, output_folder="temp_images", dpi=300):
    if not os.path.exists(output_folder):
        os.makedirs(output_folder)
    images = convert_from_path(pdf_path, dpi=dpi)
    image_paths = []

    for i, img in enumerate(images):
        image_path = os.path.join(output_folder, f"page_{i+1}.png")
        img.save(image_path, "PNG")
        image_paths.append(image_path)
    
    return image_paths

class EnhancedTopicRepetitionAnalyzer:
    def __init__(self, output_dir="enhanced_repetition_analysis", use_lemmatization=True, verbose=False):
        self.output_dir = output_dir
        self.extracted_texts = []
        self.processed_files = []
        self.stop_words = set(stopwords.words('english'))
        self.use_lemmatization = use_lemmatization
        self.verbose = verbose  # Control logging level
        
        # Enhanced stopwords for academic content
        self.academic_stopwords = {
            'related to computer science', 'computer science and information technology',
            'information technology', 'related to', 'example related', 'page', 'question',
            'answer', 'following question', 'the following', 'as follows', 'marks',
            'explain briefly', 'short answer', 'long answer', 'unit', 'chapter',
            'section', 'part', 'what is', 'define', 'list', 'write short note',
            'write note', 'short note', 'give', 'state', 'mention', 'discuss'
        }
        
        # Expanded academic topic keywords for CSIT/Statistics
        self.academic_keywords = {
            # Statistics keywords
            'distribution', 'probability', 'hypothesis', 'regression', 'correlation',
            'variance', 'mean', 'median', 'standard deviation', 'confidence interval',
            'sampling', 'estimation', 'test', 'significance', 'parametric', 'non-parametric',
            'design', 'experiment', 'analysis', 'model', 'markov', 'chain', 'process',
            'stochastic', 'random', 'variable', 'function', 'chi-square', 'anova',
            'kruskal', 'wilcoxon', 'mann-whitney', 'friedman', 'spearman', 'kendall',
            'binomial', 'poisson', 'normal', 'exponential', 'gamma', 'beta',
            'randomized', 'factorial', 'block', 'latin square', 'nested',
            
            # Computer Science keywords
            'algorithm', 'data structure', 'database', 'network', 'security', 
            'software', 'programming', 'system', 'operating', 'compiler',
            'machine learning', 'artificial intelligence', 'neural network',
            'tree', 'graph', 'hash', 'sorting', 'searching', 'complexity',
            'big o', 'dynamic programming', 'greedy', 'divide conquer'
        }
        
        if self.use_lemmatization:
            self.lemmatizer = WordNetLemmatizer()
        
        # Create output directories
        os.makedirs(output_dir, exist_ok=True)
        for subdir in ['debug_images', 'extracted_texts', 'visualizations', 'reports']:
            os.makedirs(f"{output_dir}/{subdir}", exist_ok=True)
        
        if self.verbose:
            print(f"Enhanced analysis output directory: {output_dir}")

    def enhance_image_for_ocr(self, image_path, debug=False):
        """Enhanced OCR preprocessing with better noise reduction"""
        img = cv2.imread(image_path)
        if img is None:
            raise ValueError(f"Could not load image from {image_path}")
        
        gray = cv2.cvtColor(img, cv2.COLOR_BGR2GRAY)
        
        # Auto-resize for better OCR
        height, width = gray.shape
        if height < 800 or width < 600:
            scale_factor = max(800/height, 600/width, 1.5)
            new_width = int(width * scale_factor)
            new_height = int(height * scale_factor)
            gray = cv2.resize(gray, (new_width, new_height), interpolation=cv2.INTER_CUBIC)
        
        # Advanced preprocessing pipeline
        # 1. Noise reduction
        denoised = cv2.bilateralFilter(gray, 9, 75, 75)
        
        # 2. Contrast enhancement
        clahe = cv2.createCLAHE(clipLimit=2.0, tileGridSize=(8,8))
        enhanced = clahe.apply(denoised)
        
        # 3. Multiple thresholding approaches
        thresh_adaptive = cv2.adaptiveThreshold(enhanced, 255, cv2.ADAPTIVE_THRESH_GAUSSIAN_C, cv2.THRESH_BINARY, 11, 2)
        _, thresh_otsu = cv2.threshold(enhanced, 0, 255, cv2.THRESH_BINARY + cv2.THRESH_OTSU)
        
        # 4. Morphological operations for text enhancement
        kernel = cv2.getStructuringElement(cv2.MORPH_RECT, (1,1))
        processed_adaptive = cv2.morphologyEx(thresh_adaptive, cv2.MORPH_CLOSE, kernel)
        processed_otsu = cv2.morphologyEx(thresh_otsu, cv2.MORPH_CLOSE, kernel)
        
        methods = {
            'adaptive': processed_adaptive,
            'otsu': processed_otsu,
            'enhanced': enhanced  # Also try the enhanced grayscale
        }
        
        if debug:
            filename = os.path.basename(image_path).split('.')[0]
            for method_name, processed in methods.items():
                cv2.imwrite(f"{self.output_dir}/debug_images/{filename}_{method_name}.jpg", processed)
        
        return methods

    def extract_text_from_image(self, image_path, debug=False):
        """Improved text extraction with better confidence scoring"""
        try:
            processed_methods = self.enhance_image_for_ocr(image_path, debug)
            
            best_text = ""
            best_confidence = 0
            best_method = ""
            
            for method_name, processed in processed_methods.items():
                pil_img = Image.fromarray(processed)
                
                # Try different PSM modes with priority order
                psm_modes = [6, 8, 3, 7, 4, 11, 12]
                
                for psm in psm_modes:
                    try:
                        whitelist_chars = r'0123456789ABCDEFGHIJKLMNOPQRSTUVWXYZabcdefghijklmnopqrstuvwxyz.,:;?!()[]{}"-+=*/\\|@#$%^&_~ \n\t'
                        config = f'--oem 3 --psm {psm} -c tessedit_char_whitelist="{whitelist_chars}"'

                        
                        # Get detailed OCR data
                        data = pytesseract.image_to_data(pil_img, config=config, output_type=pytesseract.Output.DICT)
                        
                        # Calculate confidence more accurately
                        valid_confidences = [int(conf) for conf in data['conf'] if int(conf) > 30]
                        
                        if valid_confidences and len(valid_confidences) > 3:
                            avg_confidence = sum(valid_confidences) / len(valid_confidences)
                            text = pytesseract.image_to_string(pil_img, config=config).strip()
                            
                            # Quality scoring: length * confidence * word ratio
                            word_count = len([w for w in text.split() if len(w) > 1])
                            quality_score = word_count * (avg_confidence / 100) * min(word_count / 20, 1.0)
                            current_score = len(best_text.split()) * (best_confidence / 100)
                            
                            if quality_score > current_score and len(text.strip()) > 15:
                                best_confidence = avg_confidence
                                best_text = text
                                best_method = f"{method_name}_psm{psm}"
                    except Exception as e:
                        continue
            
            return best_text, best_confidence, best_method
            
        except Exception as e:
            if self.verbose:
                print(f"Error extracting from {image_path}: {e}")
            return "", 0, "failed"

    def extract_date_from_filename(self, filename):
        """Enhanced date extraction from filename patterns"""
        patterns = [
            r'(\d{4})-(\d{1,2})-(\d{1,2})',
            r'(\d{1,2})-(\d{1,2})-(\d{4})',
            r'(\d{4})(\d{2})(\d{2})',
            r'(\d{2})(\d{2})(\d{4})',
            r'(\d{4})_(\d{1,2})_(\d{1,2})',
            r'(\d{1,2})_(\d{1,2})_(\d{4})'
        ]
        
        for pattern in patterns:
            match = re.search(pattern, filename)
            if match:
                try:
                    groups = match.groups()
                    if len(groups[0]) == 4:
                        year, month, day = groups
                    else:
                        if int(groups[2]) > 31:  # Likely DDMMYYYY
                            day, month, year = groups  
                        else:  # Likely MMDDYYYY
                            month, day, year = groups
                    
                    return datetime(int(year), int(month), int(day))
                except:
                    continue
        
        return datetime.now()

    def process_multiple_files(self, file_paths, debug=False):
        """Enhanced file processing with better error handling"""
        if self.verbose:
            print(f"Processing {len(file_paths)} files...")
        
        successful_extractions = 0
        
        for i, file_path in enumerate(file_paths, 1):
            if self.verbose:
                print(f"Processing file {i}/{len(file_paths)}: {os.path.basename(file_path)}")
            
            text, confidence, method = self.extract_text_from_image(file_path, debug)
            
            if text.strip() and len(text.split()) >= 10:  # Minimum word requirement
                extracted_date = self.extract_date_from_filename(os.path.basename(file_path))
                
                file_data = {
                    'filename': os.path.basename(file_path),
                    'filepath': file_path,
                    'text': text,
                    'confidence': confidence,
                    'method': method,
                    'date': extracted_date.strftime('%Y-%m-%d'),
                    'word_count': len(text.split()),
                    'char_count': len(text)
                }
                
                self.extracted_texts.append(file_data)
                successful_extractions += 1
                
                # Save individual text file
                safe_filename = re.sub(r'[^\w\-_.]', '_', os.path.basename(file_path))
                text_filename = f"{self.output_dir}/extracted_texts/{safe_filename}.txt"
                
                with open(text_filename, 'w', encoding='utf-8') as f:
                    f.write(f"Source: {file_path}\n")
                    f.write(f"Date: {extracted_date.strftime('%Y-%m-%d')}\n")
                    f.write(f"Confidence: {confidence:.1f}%\n")
                    f.write(f"Method: {method}\n")
                    f.write("="*50 + "\n\n")
                    f.write(text)
                
                if self.verbose:
                    print(f"   Extracted {len(text.split())} words (confidence: {confidence:.1f}%)")
        
        if self.verbose:
            print(f"Successfully processed {successful_extractions}/{len(file_paths)} files")
        
        return self.extracted_texts

    def normalize_phrase(self, phrase):
        """Normalize phrases for better matching"""
        # Convert to lowercase and split into words
        words = phrase.lower().split()
        
        # Remove common stop words
        filtered_words = [w for w in words if w not in self.stop_words and len(w) > 2]
        
        # Sort words to handle different orderings (e.g., "sampling distribution" vs "distribution sampling")
        if len(filtered_words) <= 3:  # Only sort for short phrases
            filtered_words.sort()
        
        # Apply lemmatization if enabled
        if self.use_lemmatization and filtered_words:
            try:
                filtered_words = [self.lemmatizer.lemmatize(word) for word in filtered_words]
            except:
                pass
        
        return ' '.join(filtered_words)

    def clean_topic_phrase(self, phrase):
        """Enhanced phrase cleaning to remove question numbers and noise"""
        # Remove leading/trailing whitespace
        phrase = phrase.strip()
        
        # Skip if it's just a number or too short
        if re.match(r'^\d+$', phrase) or len(phrase) < 3:
            return None
            
        # Remove question number patterns at the start
        phrase = re.sub(r'^\d+\.?\s*', '', phrase)  # "1. " or "1 "
        phrase = re.sub(r'^Q\d+\.?\s*', '', phrase, flags=re.IGNORECASE)  # "Q1. "
        phrase = re.sub(r'^Question\s*\d+\.?\s*', '', phrase, flags=re.IGNORECASE)  # "Question 1: "
        phrase = re.sub(r'^\d+\s*[\)\]\}]\s*', '', phrase)  # "1) " or "1] "
        phrase = re.sub(r'^[a-z]\)\s*', '', phrase, flags=re.IGNORECASE)  # "a) "
        
        # Remove common prefixes and suffixes
        prefixes_to_remove = [
            r'^what\s+is\s+', r'^define\s+', r'^explain\s+', r'^describe\s+',
            r'^write\s+short\s+note\s+on\s+', r'^discuss\s+', r'^list\s+',
            r'^briefly\s+explain\s+', r'^give\s+', r'^state\s+', r'^mention\s+',
            r'^how\s+', r'^why\s+', r'^when\s+', r'^where\s+'
        ]
        
        for prefix in prefixes_to_remove:
            phrase = re.sub(prefix, '', phrase, flags=re.IGNORECASE)
        
        # Remove trailing marks/points references
        phrase = re.sub(r'\s*\(\d+\s*marks?\)', '', phrase, flags=re.IGNORECASE)
        phrase = re.sub(r'\s*\[\d+\s*marks?\]', '', phrase, flags=re.IGNORECASE)
        phrase = re.sub(r'\s*\d+\s*marks?$', '', phrase, flags=re.IGNORECASE)
        
        # Clean up whitespace and punctuation
        phrase = re.sub(r'[^\w\s-]', ' ', phrase)  # Replace punctuation with spaces
        phrase = ' '.join(phrase.split())  # Normalize whitespace
        
        # Skip if too short after cleaning
        if len(phrase.split()) < 2:
            return None
            
        # Skip if it's just common academic boilerplate
        if phrase.lower() in self.academic_stopwords:
            return None
        
        return phrase

    def extract_academic_topics(self, text):
        """Enhanced topic extraction with better patterns and normalization"""
        # Clean the text first
        text = re.sub(r'\n+', ' ', text)  # Replace newlines with spaces
        text = re.sub(r'\s+', ' ', text)  # Normalize whitespace
        
        topics = set()  # Use set to avoid duplicates
        
        # Pattern 1: Extract n-grams (2-4 words) that contain academic keywords
        words = text.lower().split()
        for i in range(len(words)):
            # Extract 2-grams, 3-grams, and 4-grams
            for n in [2, 3, 4]:
                if i + n <= len(words):
                    ngram = ' '.join(words[i:i+n])
                    
                    # Check if n-gram contains academic keywords
                    if any(keyword in ngram for keyword in self.academic_keywords):
                        cleaned = self.clean_topic_phrase(ngram)
                        if cleaned:
                            normalized = self.normalize_phrase(cleaned)
                            if normalized and len(normalized.split()) >= 2:
                                topics.add(normalized)
        
        # Pattern 2: Extract capitalized phrases (likely proper nouns/concepts)
        capitalized_patterns = re.findall(r'\b[A-Z][a-z]+(?:\s+[A-Z][a-z]+)*\b', text)
        for pattern in capitalized_patterns:
            if len(pattern.split()) >= 2:  # At least 2 words
                cleaned = self.clean_topic_phrase(pattern)
                if cleaned:
                    normalized = self.normalize_phrase(cleaned)
                    if normalized and len(normalized.split()) >= 2:
                        topics.add(normalized)
        
        # Pattern 3: Statistical/Mathematical terms with common suffixes
        stat_patterns = re.findall(
            r'\b(?:test|analysis|method|distribution|design|model|algorithm|theory|principle|technique|approach|procedure)\b[^.]*?(?:[.!?]|$)', 
            text, re.IGNORECASE
        )
        for pattern in stat_patterns:
            # Take first 5 words max to avoid overly long phrases
            words_in_pattern = pattern.strip('.,!?').split()[:5]
            if len(words_in_pattern) >= 2:
                cleaned = self.clean_topic_phrase(' '.join(words_in_pattern))
                if cleaned:
                    normalized = self.normalize_phrase(cleaned)
                    if normalized and len(normalized.split()) >= 2:
                        topics.add(normalized)
        
        # Pattern 4: Direct keyword matching with context
        for keyword in self.academic_keywords:
            if keyword in text.lower():
                # Find occurrences and extract surrounding context
                pattern = r'\b\w*\s*' + re.escape(keyword) + r'\s*\w*\b'
                matches = re.findall(pattern, text, re.IGNORECASE)
                for match in matches:
                    cleaned = self.clean_topic_phrase(match)
                    if cleaned:
                        normalized = self.normalize_phrase(cleaned)
                        if normalized and len(normalized.split()) >= 2:
                            topics.add(normalized)
        
        return list(topics)

    def analyze_enhanced_topic_frequency(self):
        """Enhanced topic frequency analysis with LOWERED thresholds"""
        if not self.extracted_texts:
            return None
        
        if self.verbose:
            print("Analyzing enhanced topic frequency patterns...")
        
        all_topics = []
        topic_sources = defaultdict(list)
        
        # Extract topics from each document
        for data in self.extracted_texts:
            topics = self.extract_academic_topics(data['text'])
            if self.verbose:
                print(f"   {data['filename']}: Found {len(topics)} topics")
            
            all_topics.extend(topics)
            
            for topic in topics:
                topic_sources[topic].append({
                    'filename': data['filename'],
                    'date': data['date']
                })
        
        if self.verbose:
            print(f"   Total topics extracted: {len(all_topics)}")
            print(f"   Unique topics: {len(set(all_topics))}")
        
        # Count topic frequencies
        topic_freq = Counter(all_topics)
        
        # LOWERED THRESHOLD: Include topics that appear even once but in academic context
        # OR appear multiple times
        repeated_topics = {}
        for topic, freq in topic_freq.items():
            if freq >= 2:  # Traditional repeated topics
                repeated_topics[topic] = freq
            elif freq == 1 and any(keyword in topic.lower() for keyword in self.academic_keywords):
                # Include single-occurrence academic topics
                repeated_topics[topic] = freq
        
        if self.verbose:
            print(f"   Topics meeting criteria: {len(repeated_topics)}")
        
        # Calculate document coverage for each topic
        topic_coverage = {}
        for topic, freq in repeated_topics.items():
            unique_docs = len(set(source['filename'] for source in topic_sources[topic]))
            coverage_percentage = (unique_docs / len(self.extracted_texts)) * 100
            topic_coverage[topic] = {
                'frequency': freq,
                'document_count': unique_docs,
                'coverage_percentage': coverage_percentage,
                'sources': topic_sources[topic]
            }
        
        # Sort by frequency and document coverage
        sorted_topics = sorted(topic_coverage.items(), 
                              key=lambda x: (x[1]['frequency'], x[1]['document_count']), 
                              reverse=True)
        
        return {
            'repeated_topics': sorted_topics,
            'total_unique_topics': len(set(all_topics)),
            'total_documents': len(self.extracted_texts),
            'topic_sources': dict(topic_sources),
            'all_topics_list': list(set(all_topics))  # Add this for fallback recommendations
        }

    def calculate_enhanced_predictions(self, topic_analysis):
        """Enhanced prediction system with ADJUSTED likelihood calculation"""
        if not topic_analysis or not topic_analysis['repeated_topics']:
            # Fallback: create basic predictions from all unique topics
            if topic_analysis and topic_analysis.get('all_topics_list'):
                fallback_predictions = []
                for topic in topic_analysis['all_topics_list'][:10]:  # Top 10 topics
                    fallback_predictions.append({
                        'topic': topic.title(),  # Capitalize for better readability
                        'frequency': 1,
                        'document_count': 1,
                        'coverage_percentage': 100.0 / topic_analysis['total_documents'],
                        'likelihood_score': 0.3,  # Medium score for single occurrences
                        'likelihood_category': "Medium",
                        'sources': ['Various sources']
                    })
                return fallback_predictions
            return []
        
        predictions = []
        total_docs = topic_analysis['total_documents']
        
        for topic, data in topic_analysis['repeated_topics']:
            frequency = data['frequency']
            doc_count = data['document_count']
            coverage_pct = data['coverage_percentage']
            
            # ADJUSTED likelihood calculation with lower thresholds
            frequency_score = min(frequency / max(total_docs, 2), 1.0)  # Prevent division issues
            spread_score = min(doc_count / total_docs, 1.0)
            consistency_score = frequency / doc_count if doc_count > 0 else 0
            
            # Check if it's an important academic topic
            academic_bonus = 0.2 if any(keyword in topic.lower() for keyword in self.academic_keywords) else 0
            
            # Weighted likelihood score with academic bonus
            likelihood_score = (frequency_score * 0.4) + (spread_score * 0.4) + (consistency_score * 0.2) + academic_bonus
            
            # LOWERED thresholds for likelihood categories
            if likelihood_score >= 0.6 or frequency >= 3:
                likelihood_category = "Very High"
            elif likelihood_score >= 0.4 or frequency >= 2:
                likelihood_category = "High" 
            elif likelihood_score >= 0.2 or doc_count >= 1:
                likelihood_category = "Medium"
            else:
                likelihood_category = "Low"
            
            prediction = {
                'topic': topic.title(),  # Capitalize for better readability
                'frequency': frequency,
                'document_count': doc_count,
                'coverage_percentage': coverage_pct,
                'likelihood_score': likelihood_score,
                'likelihood_category': likelihood_category,
                'sources': [source['filename'] for source in data['sources'][:3]]
            }
            
            predictions.append(prediction)
        
        # Sort by likelihood score
        return sorted(predictions, key=lambda x: x['likelihood_score'], reverse=True)

    def create_topic_heat_index(self, topic_analysis):
        """Create a Topic Heat Index for all found topics"""
        if not topic_analysis:
            return []
        
        heat_index = []
        all_topic_counts = Counter()
        
        # Count all topics (including single occurrences)
        for data in self.extracted_texts:
            topics = self.extract_academic_topics(data['text'])
            for topic in topics:
                all_topic_counts[topic] += 1
        
        # Create heat index
        for topic, count in all_topic_counts.most_common(15):  # Top 15
            heat_level = "🔥🔥🔥" if count >= 3 else "🔥🔥" if count >= 2 else "🔥"
            heat_index.append({
                'topic': topic.title(),
                'mentions': count,
                'heat': heat_level
            })
        
        return heat_index

    def create_enhanced_visualizations(self, predictions, topic_analysis):
        """Create enhanced visualizations with better design"""
        if self.verbose:
            print("Creating enhanced visualizations...")
        
        if not predictions and not topic_analysis:
            if self.verbose:
                print("No data to visualize")
            return
        
        plt.style.use('default')
        sns.set_palette("husl")
        
        # Create comprehensive visualization
        fig, axes = plt.subplots(2, 2, figsize=(18, 14))
        fig.suptitle('Enhanced Topic Repetition Analysis', fontsize=18, fontweight='bold')
        
        # 1. Top Topics by Likelihood Score or Frequency
        if predictions:
            top_predictions = predictions[:10]
            topics = [pred['topic'][:25] + "..." if len(pred['topic']) > 25 else pred['topic'] 
                     for pred in top_predictions]
            scores = [pred['likelihood_score'] for pred in top_predictions]
            colors = ['red' if score >= 0.6 else 'orange' if score >= 0.4 else 'gold' if score >= 0.2 else 'lightgreen' 
                     for score in scores]
            
            bars = axes[0, 0].barh(range(len(topics)), scores, color=colors)
            axes[0, 0].set_yticks(range(len(topics)))
            axes[0, 0].set_yticklabels(topics, fontsize=9)
            axes[0, 0].set_xlabel('Likelihood Score')
            axes[0, 0].set_title('Top Topics by Repetition Likelihood')
            axes[0, 0].invert_yaxis()
            
            # Add score labels on bars
            for i, bar in enumerate(bars):
                width = bar.get_width()
                axes[0, 0].text(width + 0.01, bar.get_y() + bar.get_height()/2, 
                               f'{scores[i]:.2f}', ha='left', va='center', fontsize=8)
        else:
            axes[0, 0].text(0.5, 0.5, 'No predictions available\nTry lowering thresholds', 
                           ha='center', va='center', transform=axes[0, 0].transAxes, fontsize=12)
            axes[0, 0].set_title('Top Topics by Repetition Likelihood')
        
        # 2. Topic Heat Index
        heat_index = self.create_topic_heat_index(topic_analysis)
        if heat_index:
            topics = [item['topic'][:20] + "..." if len(item['topic']) > 20 else item['topic'] 
                     for item in heat_index[:8]]
            mentions = [item['mentions'] for item in heat_index[:8]]
            
            bars = axes[0, 1].bar(range(len(topics)), mentions, color='skyblue')
            axes[0, 1].set_xticks(range(len(topics)))
            axes[0, 1].set_xticklabels(topics, rotation=45, ha='right', fontsize=8)
            axes[0, 1].set_ylabel('Mentions')
            axes[0, 1].set_title('Topic Heat Index')
            axes[0, 1].grid(True, alpha=0.3, axis='y')
            
            # Add mention count labels on bars
            for bar in bars:
                height = bar.get_height()
                axes[0, 1].text(bar.get_x() + bar.get_width()/2., height + 0.05,
                               f'{int(height)}', ha='center', va='bottom', fontsize=8)
        else:
            axes[0, 1].text(0.5, 0.5, 'No topics found', 
                           ha='center', va='center', transform=axes[0, 1].transAxes)
            axes[0, 1].set_title('Topic Heat Index')
        
        # 3. Likelihood Categories Distribution
        if predictions:
            categories = {}
            for pred in predictions:
                cat = pred['likelihood_category']
                categories[cat] = categories.get(cat, 0) + 1
            
            if categories:
                category_colors = {'Very High': 'red', 'High': 'orange', 'Medium': 'gold', 'Low': 'lightgreen'}
                colors = [category_colors.get(cat, 'gray') for cat in categories.keys()]
                
                axes[1, 0].pie(categories.values(), labels=categories.keys(), autopct='%1.1f%%', 
                              colors=colors, startangle=90)
                axes[1, 0].set_title('Distribution of Likelihood Categories')
        else:
            axes[1, 0].text(0.5, 0.5, 'No predictions for\ncategory distribution', 
                           ha='center', va='center', transform=axes[1, 0].transAxes)
            axes[1, 0].set_title('Distribution of Likelihood Categories')
        
        # 4. Document Processing Quality
        if self.extracted_texts:
            filenames = [data['filename'][:15] + "..." if len(data['filename']) > 15 else data['filename'] 
                        for data in self.extracted_texts]
            confidences = [data['confidence'] for data in self.extracted_texts]
            word_counts = [data['word_count'] for data in self.extracted_texts]
            
            # Create a dual-axis plot
            ax1 = axes[1, 1]
            ax2 = ax1.twinx()
            
            x = range(len(filenames))
            bars1 = ax1.bar([i - 0.2 for i in x], confidences, 0.4, label='OCR Confidence (%)', 
                           color='lightblue', alpha=0.7)
            bars2 = ax2.bar([i + 0.2 for i in x], word_counts, 0.4, label='Word Count', 
                           color='lightcoral', alpha=0.7)
            
            ax1.set_xlabel('Documents')
            ax1.set_ylabel('OCR Confidence (%)', color='blue')
            ax2.set_ylabel('Word Count', color='red')
            ax1.set_title('Document Processing Quality')
            ax1.set_xticks(x)
            ax1.set_xticklabels(filenames, rotation=45, ha='right', fontsize=8)
            
            # Add legends
            ax1.legend(loc='upper left')
            ax2.legend(loc='upper right')
            
            # Add value labels
            for i, bar in enumerate(bars1):
                height = bar.get_height()
                ax1.text(bar.get_x() + bar.get_width()/2., height + 1,
                        f'{confidences[i]:.0f}%', ha='center', va='bottom', fontsize=7)
            
            for i, bar in enumerate(bars2):
                height = bar.get_height()
                ax2.text(bar.get_x() + bar.get_width()/2., height + max(word_counts)*0.02,
                        f'{word_counts[i]}', ha='center', va='bottom', fontsize=7)
        else:
            axes[1, 1].text(0.5, 0.5, 'No document data', 
                           ha='center', va='center', transform=axes[1, 1].transAxes)
            axes[1, 1].set_title('Document Processing Quality')
        
        plt.tight_layout()
        plt.savefig(f"{self.output_dir}/visualizations/enhanced_analysis.png", 
                   dpi=300, bbox_inches='tight')
        plt.close()
        
        # Create a detailed topic word cloud if we have topics
        if topic_analysis and (topic_analysis.get('repeated_topics') or topic_analysis.get('all_topics_list')):
            self.create_topic_wordcloud(topic_analysis)
        
        if self.verbose:
            print(f"Enhanced visualizations saved to {self.output_dir}/visualizations/")

    def create_topic_wordcloud(self, topic_analysis):
        """Create a word cloud of repeated topics"""
        try:
            # Prepare text for word cloud
            topic_text = []
            
            # Use repeated topics if available
            if topic_analysis.get('repeated_topics'):
                for topic, data in topic_analysis['repeated_topics']:
                    # Repeat topic based on its frequency for word cloud weighting
                    topic_text.extend([topic] * data['frequency'])
            
            # Fallback to all topics if no repeated topics
            elif topic_analysis.get('all_topics_list'):
                topic_text = topic_analysis['all_topics_list']
            
            if topic_text:
                wordcloud_text = ' '.join(topic_text)
                
                wordcloud = WordCloud(width=1200, height=600, 
                                    background_color='white',
                                    colormap='viridis',
                                    max_words=50,
                                    relative_scaling=0.5).generate(wordcloud_text)
                
                plt.figure(figsize=(15, 8))
                plt.imshow(wordcloud, interpolation='bilinear')
                plt.axis('off')
                plt.title('Most Repeated Academic Topics', fontsize=16, fontweight='bold', pad=20)
                plt.tight_layout()
                plt.savefig(f"{self.output_dir}/visualizations/topic_wordcloud.png", 
                           dpi=300, bbox_inches='tight')
                plt.close()
                
        except Exception as e:
            if self.verbose:
                print(f"Warning: Could not create word cloud: {e}")

    def generate_enhanced_report(self, predictions, topic_analysis):
        """Generate comprehensive enhanced report with better fallback content"""
        report_path = f"{self.output_dir}/reports/enhanced_analysis_report.txt"
        
        # Create topic heat index for fallback recommendations
        heat_index = self.create_topic_heat_index(topic_analysis)
        
        with open(report_path, 'w', encoding='utf-8') as f:
            f.write("="*80 + "\n")
            f.write("ENHANCED TOPIC REPETITION & PREDICTION ANALYSIS REPORT\n")
            f.write("="*80 + "\n")
            f.write(f"Generated on: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}\n\n")
            
            # Executive Summary
            f.write("📋 EXECUTIVE SUMMARY\n")
            f.write("-"*40 + "\n")
            f.write(f"Documents Analyzed: {len(self.extracted_texts)}\n")
            f.write(f"Unique Topics Identified: {topic_analysis['total_unique_topics'] if topic_analysis else 0}\n")
            f.write(f"Repeated Topics Found: {len([p for p in predictions if p['frequency'] >= 2]) if predictions else 0}\n")
            f.write(f"Total Topics (including single mentions): {len(predictions) if predictions else len(heat_index)}\n")
            
            high_likelihood = len([p for p in predictions if p['likelihood_category'] in ['Very High', 'High']]) if predictions else 0
            f.write(f"High-Priority Topics: {high_likelihood}\n\n")
            
            # Document Quality Assessment
            f.write("📊 DOCUMENT QUALITY ASSESSMENT\n")
            f.write("-"*35 + "\n")
            if self.extracted_texts:
                avg_confidence = sum(data['confidence'] for data in self.extracted_texts) / len(self.extracted_texts)
                total_words = sum(data['word_count'] for data in self.extracted_texts)
                f.write(f"Average OCR Confidence: {avg_confidence:.1f}%\n")
                f.write(f"Total Words Processed: {total_words:,}\n")
                f.write(f"Average Words per Document: {total_words // len(self.extracted_texts)}\n\n")
            
            # Top Predictions or Heat Index
            if predictions:
                f.write("🎯 TOP TOPIC PREDICTIONS FOR UPCOMING EXAMS\n")
                f.write("="*50 + "\n")
                
                # Very High and High Likelihood
                priority_topics = [p for p in predictions if p['likelihood_category'] in ['Very High', 'High']]
                if priority_topics:
                    f.write("🔥 PRIORITY TOPICS (Focus Your Study Here!):\n")
                    f.write("-"*45 + "\n")
                    
                    for i, pred in enumerate(priority_topics, 1):
                        f.write(f"\n{i}. {pred['topic']}\n")
                        f.write(f"   ✅ Likelihood: {pred['likelihood_category']} ({pred['likelihood_score']:.2f})\n")
                        f.write(f"   📈 Appeared: {pred['frequency']} times across {pred['document_count']} documents\n")
                        f.write(f"   📊 Coverage: {pred['coverage_percentage']:.1f}% of all documents\n")
                        f.write(f"   📁 Sources: {', '.join(pred['sources'][:3])}\n")
                else:
                    f.write("🔥 PRIORITY TOPICS (Based on Analysis):\n")
                    f.write("-"*45 + "\n")
                    f.write("No topics met the high-priority threshold, but consider reviewing these:\n\n")
                    
                    for i, pred in enumerate(predictions[:5], 1):
                        f.write(f"{i}. {pred['topic']} (Score: {pred['likelihood_score']:.2f})\n")
                        f.write(f"   Appeared {pred['frequency']} times in {pred['document_count']} documents\n\n")
                
                # Medium Likelihood
                medium_topics = [p for p in predictions if p['likelihood_category'] == 'Medium']
                if medium_topics:
                    f.write(f"\n📚 SECONDARY TOPICS (Good to Review):\n")
                    f.write("-"*40 + "\n")
                    for i, pred in enumerate(medium_topics[:10], 1):
                        f.write(f"{i:2d}. {pred['topic']} (Score: {pred['likelihood_score']:.2f})\n")
                        f.write(f"     Appeared {pred['frequency']} times in {pred['document_count']} documents\n")
            
            elif heat_index:
                f.write("🌡️ TOPIC HEAT INDEX (All Identified Topics)\n")
                f.write("="*45 + "\n")
                f.write("Since no topics were repeated frequently, here are all identified academic topics:\n\n")
                
                for i, item in enumerate(heat_index, 1):
                    f.write(f"{i:2d}. {item['topic']} {item['heat']}\n")
                    f.write(f"     Mentioned {item['mentions']} time(s)\n\n")
                
                f.write("💡 RECOMMENDATION: Even single mentions are worth reviewing!\n")
                f.write("These topics appeared in your study materials, so they're likely relevant.\n\n")
            
            # Study Recommendations
            f.write(f"📚 PERSONALIZED STUDY RECOMMENDATIONS\n")
            f.write("="*45 + "\n")
            
            if predictions:
                very_high = len([p for p in predictions if p['likelihood_category'] == 'Very High'])
                high = len([p for p in predictions if p['likelihood_category'] == 'High'])
                medium = len([p for p in predictions if p['likelihood_category'] == 'Medium'])
                
                f.write(f"🎯 STUDY PRIORITY BREAKDOWN:\n")
                f.write(f"   • Very High Priority: {very_high} topics (Study First!)\n")
                f.write(f"   • High Priority: {high} topics (Study Second)\n")
                f.write(f"   • Medium Priority: {medium} topics (Time Permitting)\n\n")
                
                total_priority = very_high + high
                if total_priority > 0:
                    f.write(f"⏰ RECOMMENDED TIME ALLOCATION:\n")
                    f.write(f"   • Spend 70% of study time on {total_priority} high-priority topics\n")
                    f.write(f"   • Spend 30% of study time on medium-priority topics\n\n")
                else:
                    f.write(f"⏰ RECOMMENDED APPROACH:\n")
                    f.write(f"   • Since repetition is low, review all {len(predictions)} topics equally\n")
                    f.write(f"   • Focus on understanding fundamental concepts\n")
                    f.write(f"   • Create comprehensive notes for each topic\n\n")
            
            elif heat_index:
                f.write(f"🎯 STUDY STRATEGY FOR DIVERSE TOPICS:\n")
                f.write(f"   • Review all {len(heat_index)} identified topics\n")
                f.write(f"   • Focus on topics with 🔥🔥🔥 heat level first\n")
                f.write(f"   • Create summary notes for each topic\n")
                f.write(f"   • Look for connections between related concepts\n\n")
            
            f.write(f"💡 SMART STUDY STRATEGIES:\n")
            f.write(f"   • Create concept maps linking related topics\n")
            f.write(f"   • Practice problems from multiple sources\n")
            f.write(f"   • Form study groups to discuss complex concepts\n")
            f.write(f"   • Use active recall and spaced repetition\n")
            f.write(f"   • Solve past papers to identify question patterns\n\n")
            
            # Detailed Analysis Section
            f.write(f"📈 DETAILED STATISTICAL ANALYSIS\n")
            f.write("="*40 + "\n")
            
            if topic_analysis and topic_analysis.get('repeated_topics'):
                f.write("Top 15 Most Repeated Topics:\n")
                f.write("-"*30 + "\n")
                
                for i, (topic, data) in enumerate(topic_analysis['repeated_topics'][:15], 1):
                    f.write(f"{i:2d}. {topic}\n")
                    f.write(f"     Frequency: {data['frequency']} | Documents: {data['document_count']} | Coverage: {data['coverage_percentage']:.1f}%\n")
                    f.write(f"     Sources: {', '.join([s['filename'] for s in data['sources'][:3]])}\n\n")
            
            elif heat_index:
                f.write("All Identified Academic Topics:\n")
                f.write("-"*30 + "\n")
                
                for i, item in enumerate(heat_index, 1):
                    f.write(f"{i:2d}. {item['topic']} - {item['mentions']} mention(s) {item['heat']}\n")
            
            # Quality Metrics
            f.write(f"\n🔬 ANALYSIS QUALITY METRICS\n")
            f.write("-"*30 + "\n")
            
            if self.extracted_texts:
                confidence_levels = [data['confidence'] for data in self.extracted_texts]
                high_confidence_docs = len([c for c in confidence_levels if c >= 85])
                medium_confidence_docs = len([c for c in confidence_levels if 70 <= c < 85])
                low_confidence_docs = len([c for c in confidence_levels if c < 70])
                
                f.write(f"📋 OCR Quality Assessment:\n")
                f.write(f"   • High confidence (≥85%): {high_confidence_docs} documents\n")
                f.write(f"   • Medium confidence (70-84%): {medium_confidence_docs} documents\n")
                f.write(f"   • Low confidence (<70%): {low_confidence_docs} documents\n\n")
                
                if low_confidence_docs > 0:
                    f.write(f"⚠️  Note: {low_confidence_docs} documents had lower OCR confidence.\n")
                    f.write(f"   Consider re-scanning these for better accuracy.\n\n")
            
            # Files Processed
            f.write(f"📁 PROCESSED FILES DETAILS\n")
            f.write("-"*30 + "\n")
            if self.extracted_texts:
                for i, data in enumerate(self.extracted_texts, 1):
                    confidence_emoji = "🟢" if data['confidence'] >= 85 else "🟡" if data['confidence'] >= 70 else "🔴"
                    f.write(f"{i:2d}. {data['filename']}\n")
                    f.write(f"     {confidence_emoji} Confidence: {data['confidence']:.1f}% | Words: {data['word_count']} | Date: {data['date']}\n")
                    f.write(f"     Method: {data['method']}\n\n")
            
            # Footer
            f.write(f"\n" + "="*80 + "\n")
            f.write(f"📈 ANALYSIS POWERED BY ENHANCED TOPIC REPETITION ANALYZER\n")
            f.write(f"🎓 Designed for Academic Success - Focus Smart, Study Less!\n")
            if not predictions or len(predictions) == 0:
                f.write(f"💡 Tip: Try processing more documents to identify stronger patterns\n")
            else:
                f.write(f"💡 Tip: Regular analysis of new materials improves prediction accuracy\n")
            f.write("="*80 + "\n")
        
        if self.verbose:
            print(f"Enhanced comprehensive report saved to: {report_path}")

    def find_semantic_topic_groups(self, similarity_threshold=0.3):
        """Find semantically similar topics using advanced NLP with lowered threshold"""
        if not self.extracted_texts or len(self.extracted_texts) < 2:
            return []
        
        if self.verbose:
            print("Finding semantic topic groups...")
        
        # Extract all academic topics
        all_topics = []
        topic_sources = []
        
        for data in self.extracted_texts:
            topics = self.extract_academic_topics(data['text'])
            for topic in topics:
                all_topics.append(topic)
                topic_sources.append({
                    'topic': topic,
                    'filename': data['filename'],
                    'date': data['date']
                })
        
        if len(all_topics) < 2:
            return []
        
        try:
            # Use TF-IDF for semantic similarity
            vectorizer = TfidfVectorizer(
                max_features=500,
                ngram_range=(1, 2),
                stop_words='english',
                lowercase=True
            )
            
            tfidf_matrix = vectorizer.fit_transform(all_topics)
            similarity_matrix = cosine_similarity(tfidf_matrix)
            
            # Find semantic groups
            semantic_groups = []
            processed_indices = set()
            
            for i in range(len(all_topics)):
                if i in processed_indices:
                    continue
                
                similar_indices = [i]
                for j in range(i + 1, len(all_topics)):
                    if j in processed_indices:
                        continue
                    
                    if similarity_matrix[i][j] > similarity_threshold:
                        similar_indices.append(j)
                
                if len(similar_indices) > 1:  # Group has multiple topics
                    processed_indices.update(similar_indices)
                    
                    group = {
                        'group_size': len(similar_indices),
                        'avg_similarity': np.mean([similarity_matrix[i][j] for j in similar_indices[1:]]),
                        'topics': []
                    }
                    
                    for idx in similar_indices:
                        group['topics'].append({
                            'topic': all_topics[idx],
                            'source': topic_sources[idx]
                        })
                    
                    semantic_groups.append(group)
            
            # Sort by group size and similarity
            semantic_groups.sort(key=lambda x: (x['group_size'], x['avg_similarity']), reverse=True)
            return semantic_groups[:10]  # Top 10 groups
            
        except Exception as e:
            if self.verbose:
                print(f"Error in semantic grouping: {e}")
            return []

def analyze_enhanced_topic_repetitions(image_folder, debug=False, use_lemmatization=True, verbose=False):
    """Main enhanced function to analyze topic repetitions with better predictions"""
    
    from tempfile import TemporaryDirectory
    from pathlib import Path

    # Initialize enhanced analyzer
    analyzer = EnhancedTopicRepetitionAnalyzer(use_lemmatization=use_lemmatization, verbose=verbose)
    
    # File processing
    image_extensions = ['.jpg', '.jpeg', '.png', '.tiff', '.tif', '.bmp']
    pdf_extension = '.pdf'
    input_files = []

    if os.path.isdir(image_folder):
        for file in os.listdir(image_folder):
            file_path = os.path.join(image_folder, file)
            if any(file.lower().endswith(ext) for ext in image_extensions + [pdf_extension]):
                input_files.append(file_path)
    else:
        input_files = [image_folder]

    if not input_files:
        if verbose:
            print("No image or PDF files found!")
        return None

    if verbose:
        print(f"Found {len(input_files)} files to process")

    final_image_files = []

    with TemporaryDirectory() as temp_dir:
        # Convert PDFs to images if needed
        for file_path in input_files:
            ext = Path(file_path).suffix.lower()

            if ext == '.pdf':
                if verbose:
                    print(f"Converting PDF: {file_path}")
                try:
                    images = convert_from_path(file_path)
                    for i, img in enumerate(images):
                        image_path = os.path.join(temp_dir, f"{Path(file_path).stem}_page_{i}.png")
                        img.save(image_path, "PNG")
                        final_image_files.append(image_path)
                except Exception as e:
                    if verbose:
                        print(f"Failed to convert {file_path}: {e}")
            else:
                final_image_files.append(file_path)

        # Process all files with enhanced OCR
        extracted_data = analyzer.process_multiple_files(final_image_files, debug=debug)

        if not extracted_data:
            if verbose:
                print("No text was extracted from any files!")
            return None

        # Enhanced topic analysis
        topic_analysis = analyzer.analyze_enhanced_topic_frequency()
        
        if not topic_analysis:
            if verbose:
                print("No topics could be analyzed!")
            return None

        # Generate enhanced predictions
        predictions = analyzer.calculate_enhanced_predictions(topic_analysis)
        
        # Find semantic topic groups
        semantic_groups = analyzer.find_semantic_topic_groups()

        # Create enhanced visualizations
        analyzer.create_enhanced_visualizations(predictions, topic_analysis)

        # Generate comprehensive report
        analyzer.generate_enhanced_report(predictions, topic_analysis)

        # Return analysis results for backend use
        result = {
            'analyzer': analyzer,
            'predictions': predictions,
            'topic_analysis': topic_analysis,
            'semantic_groups': semantic_groups,
            'summary': {
                'total_files': len(final_image_files),
                'successful_extractions': len(extracted_data),
                'total_topics': len(predictions) if predictions else 0,
                'high_priority_topics': len([p for p in predictions if p['likelihood_category'] in ['Very High', 'High']]) if predictions else 0,
                'output_directory': analyzer.output_dir
            }
        }

        if verbose:
            print("Enhanced Topic Repetition Analysis Complete!")
            if predictions:
                very_high_count = len([p for p in predictions if p['likelihood_category'] == 'Very High'])
                high_count = len([p for p in predictions if p['likelihood_category'] == 'High'])
                medium_count = len([p for p in predictions if p['likelihood_category'] == 'Medium'])
                
                print(f"Prediction Summary:")
                print(f"   • Very High Priority: {very_high_count} topics")
                print(f"   • High Priority: {high_count} topics")
                print(f"   • Medium Priority: {medium_count} topics")
                print(f"   • Total Predictions: {len(predictions)} topics")
            
            print(f"Results saved to: {analyzer.output_dir}")

        return result


# Example usage for backend integration
if __name__ == "__main__":
    # Backend-friendly usage
    image_folder_path = "D:\\pytesseract\\images"  # Change this to your folder path
    
    # For backend use - set verbose=False to minimize console output
    result = analyze_enhanced_topic_repetitions(
        image_folder_path, 
        debug=False,  # Set to False for production
        use_lemmatization=True,
        verbose=False  # Set to False for backend use
    )
    
    if result:
        # Access results programmatically
        predictions = result['predictions']
        summary = result['summary']
        
        # You can now use these results in your Flask app
        print(f"Analysis completed. Found {summary['total_topics']} topics.")
    else:
        print("Analysis failed or no files processed.")