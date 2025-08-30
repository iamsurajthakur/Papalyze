from transformers import pipeline

# Load summarization pipeline (only once at startup)
summarizer = pipeline("summarization", model="facebook/bart-large-cnn")

def generate_summary(text):
    """
    text: str -> notes or extracted PDF text
    returns: str -> summary
    """
    # Split long text into chunks of ~500-1000 words if necessary
    max_chunk = 1000
    chunks = [text[i:i+max_chunk] for i in range(0, len(text), max_chunk)]

    summaries = []
    for chunk in chunks:
        summary = summarizer(chunk, max_length=150, min_length=50, do_sample=False)
        summaries.append(summary[0]['summary_text'])
    
    # Combine all chunks
    return " ".join(summaries)
