"""
setup_colab.py — One-click setup script for Google Colab
Run this cell first before launching app.py:

    !python setup_colab.py
"""

import subprocess
import sys


def run(cmd: str):
    print(f"▶ {cmd}")
    result = subprocess.run(cmd, shell=True, capture_output=False)
    if result.returncode != 0:
        print(f"  ⚠️  Command exited with code {result.returncode}")


print("=" * 60)
print("Resume-to-Job Match Scorer — Colab Setup")
print("=" * 60)

print("\n[1/3] Installing Python packages…")
run(f"{sys.executable} -m pip install -q "
    "gradio==4.44.1 "
    "pdfplumber==0.11.4 "
    "spacy==3.7.6 "
    "keybert==0.8.5 "
    "sentence-transformers==3.3.1 "
    "anthropic")

print("\n[2/3] Downloading spaCy language model…")
run(f"{sys.executable} -m spacy download en_core_web_sm")

print("\n[3/3] Pre-downloading Sentence-BERT model…")
run(f"{sys.executable} -c "
    "\"from sentence_transformers import SentenceTransformer; "
    "SentenceTransformer('all-MiniLM-L6-v2'); print('Model cached.')\"")

print("\n✅ Setup complete! Now run:  !python app.py")
print("=" * 60)
