import os
import io
import uuid
import base64
from typing import List, Optional, Tuple

import cv2
import numpy as np
from PIL import Image

from fastapi import FastAPI, UploadFile, File, Form
from fastapi.responses import JSONResponse

import easyocr
import torch
from transformers import BlipForQuestionAnswering, BlipProcessor, AutoTokenizer, AutoModelForSeq2SeqLM
from sentence_transformers import SentenceTransformer
import faiss
import pandas as pd
from deep_translator import GoogleTranslator

# ---------- Config ----------
DEVICE = "cuda" if torch.cuda.is_available() else "cpu"
os.makedirs("storage", exist_ok=True)

# OCR (Vietnamese + English)
ocr_reader = easyocr.Reader(['vi', 'en'])

# VQA model (English). We'll auto-translate vi <-> en around it.
VQA_MODEL_NAME = "Salesforce/blip-vqa-base"
vqa_processor = BlipProcessor.from_pretrained(VQA_MODEL_NAME)
vqa_model = BlipForQuestionAnswering.from_pretrained(VQA_MODEL_NAME).to(DEVICE).eval()

# Small generator model to compose final answer from contexts (multi-lingual ready enough)
GEN_MODEL_NAME = "google/flan-t5-base"
gen_tokenizer = AutoTokenizer.from_pretrained(GEN_MODEL_NAME)
gen_model = AutoModelForSeq2SeqLM.from_pretrained(GEN_MODEL_NAME).to(DEVICE).eval()

# Embedding model for KG retrieval
EMB_MODEL_NAME = "sentence-transformers/all-MiniLM-L6-v2"
emb_model = SentenceTransformer(EMB_MODEL_NAME, device=DEVICE)

# ---------- Knowledge Base (FAISS) ----------
class KnowledgeBase:
    def __init__(self, csv_path: str):
        self.df = pd.read_csv(csv_path)
        self.texts = (
            self.df["title"].fillna("").astype(str) + " — " +
            self.df["content"].fillna("").astype(str)
        ).tolist()
        self.ids = self.df["id"].tolist()
        self.emb = emb_model.encode(self.texts, convert_to_numpy=True, normalize_embeddings=True, batch_size=64)
        dim = self.emb.shape[1]
        self.index = faiss.IndexFlatIP(dim)
        self.index.add(self.emb)

    def search(self, query: str, k: int = 5) -> List[Tuple[int, float, str]]:
        q = emb_model.encode([query], convert_to_numpy=True, normalize_embeddings=True)
        scores, idx = self.index.search(q, k)
        out = []
        for i, s in zip(idx[0], scores[0]):
            if i == -1: continue
            out.append((self.ids[i], float(s), self.texts[i]))
        return out

kb = KnowledgeBase("data/knowledge.csv")

# ---------- Utils ----------
def save_upload(file: UploadFile) -> str:
    ext = os.path.splitext(file.filename)[1].lower() or ".jpg"
    path = os.path.join("storage", f"{uuid.uuid4().hex}{ext}")
    with open(path, "wb") as f:
        f.write(file.file.read())
    return path

def load_image(path: str) -> Image.Image:
    return Image.open(path).convert("RGB")

def ocr_image(path: str) -> str:
    # Use EasyOCR on RGB numpy
    img = cv2.imread(path)
    if img is None:
        raise ValueError("Invalid image")
    img = cv2.cvtColor(img, cv2.COLOR_BGR2RGB)
    result = ocr_reader.readtext(img, detail=0)  # only text
    text = "\n".join(result).strip()
    return text

def translate_vi_en(text: str, source="vi", target="en") -> str:
    try:
        if not text.strip(): return text
        return GoogleTranslator(source=source, target=target).translate(text)
    except Exception:
        return text  # fallback

@torch.inference_mode()
def vqa_answer(path: str, question_vi: str) -> str:
    # Translate vi->en for BLIP VQA
    q_en = translate_vi_en(question_vi, source="vi", target="en")
    image = load_image(path)
    inputs = vqa_processor(image, q_en, return_tensors="pt").to(DEVICE)
    out = vqa_model.generate(**inputs, max_new_tokens=20)
    ans_en = vqa_processor.decode(out[0], skip_special_tokens=True)
    # Translate back to vi
    ans_vi = translate_vi_en(ans_en, source="en", target="vi")
    return ans_vi

@torch.inference_mode()
def generate_answer(context_vi: str, question_vi: str) -> str:
    prompt = (
        "Trả lời ngắn gọn và chính xác bằng tiếng Việt dựa trên ngữ cảnh.\n"
        f"Ngữ cảnh:\n{context_vi}\n\n"
        f"Câu hỏi: {question_vi}\n"
        "Trả lời:"
    )
    inputs = gen_tokenizer(prompt, return_tensors="pt").to(DEVICE)
    out = gen_model.generate(**inputs, max_new_tokens=128, temperature=0.2)
    return gen_tokenizer.decode(out[0], skip_special_tokens=True).strip()

def compose_final_answer(ocr_text: str, vqa: str, kg_hits: List[Tuple[int, float, str]], question_vi: str) -> dict:
    top_kg = "\n".join([f"- {txt}" for _, _, txt in kg_hits[:3]])
    context = (
        f"Thông tin từ OCR (ảnh sách):\n{ocr_text[:1500]}\n\n"
        f"Câu trả lời từ VQA (nhìn ảnh): {vqa}\n\n"
        f"Tri thức liên quan từ KG:\n{top_kg}"
    )
    final = generate_answer(context, question_vi)
    return {"vqa": vqa, "context_used": context, "answer": final}

# ---------- API ----------
app = FastAPI(title="Edu VQA + OCR + KG")

@app.post("/ocr")
def api_ocr(file: UploadFile = File(...)):
    path = save_upload(file)
    text = ocr_image(path)
    return {"text": text, "image_path": path}

@app.post("/vqa")
def api_vqa(file: UploadFile = File(...), question: str = Form(...)):
    path = save_upload(file)
    ans = vqa_answer(path, question)
    return {"answer": ans, "image_path": path}

@app.post("/ask")
def api_ask(
    file: UploadFile = File(...),
    question: str = Form(...),
    subject: Optional[str] = Form(None),
    grade: Optional[str] = Form(None),
    top_k: int = Form(5),
):
    path = save_upload(file)
    ocr_txt = ocr_image(path)
    vqa_ans = vqa_answer(path, question)

    # Build KG query string
    meta = []
    if subject: meta.append(f"môn {subject}")
    if grade: meta.append(f"lớp {grade}")
    meta_str = " ".join(meta)
    kg_query = f"{question} {ocr_txt[:400]} {meta_str}".strip()
    hits = kb.search(kg_query, k=top_k)

    result = compose_final_answer(ocr_txt, vqa_ans, hits, question)
    result.update({
        "image_path": path,
        "kg_top": [{"id": i, "score": s, "text": t} for i, s, t in hits]
    })
    return JSONResponse(result)