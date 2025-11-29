
from groq import Groq
from fastapi import FastAPI, UploadFile, File
from pdfminer.high_level import extract_text
from fastapi.responses import FileResponse
from dotenv import load_dotenv
import os, json, difflib, re

app = FastAPI()


@app.get("/")
def home():
    return FileResponse("index.html", media_type="text/html")


# CLEANING HELPERS
def clean(t: str):
    return re.sub(r"\s+", " ", t.lower()).strip()


def similarity(a: str, b: str):
    return difflib.SequenceMatcher(None, a, b).ratio()


def keyword_overlap(resume_text, jd_text):
    r = set(clean(resume_text).split())
    j = set(clean(jd_text).split())
    if not j:
        return 0
    return len(r.intersection(j)) / len(j)


@app.post("/upload")
async def upload(resume: UploadFile = File(...), jd: UploadFile = File(...)):
    resume_text = extract_text(resume.file)
    jd_text = extract_text(jd.file)

    return {
        "resume_preview": resume_text[:200],
        "jd_preview": jd_text[:200],
        "message": "Files uploaded and extracted successfully"
    }


@app.post("/model")
async def model(resume: UploadFile = File(...), jd: UploadFile = File(...)):

    resume_text = extract_text(resume.file)
    jd_text = extract_text(jd.file)

    resume_clean = clean(resume_text)
    jd_clean = clean(jd_text)

    sim = similarity(resume_clean, jd_clean)
    key_match = keyword_overlap(resume_clean, jd_clean)

    perfect_match_flag = (sim >= 0.85 or key_match >= 0.85)

    print("Similarity Score:", sim)
    print("Keyword Match Score:", key_match)
    print("Perfect Match Flag:", perfect_match_flag)

    load_dotenv()
    APIKEY = os.getenv("API")
    client = Groq(api_key=APIKEY)

  
    system_prompt = f"""
You are a strict JSON generator.

You must obey these rules EXACTLY:

100% MATCH RULE:
If perfect_match_flag = true:
- overall_score = 100
- ALL category scores = 100
- ALL category status = "excellent"
- ALL improvements = ""
- matched_keywords = all possible keywords extracted from resume/jd
- missing_keywords = []
- suggestions = []

If perfect_match_flag = false:
- Evaluate normally.

HARD RULES:
- Output ONLY valid JSON.
- No markdown.
- No code blocks.
- No text outside JSON.
"""

  
    user_prompt = f"""
perfect_match_flag = {str(perfect_match_flag).lower()}

RESUME TEXT:
{resume_text}

JOB DESCRIPTION TEXT:
{jd_text}

Your job:

1. If perfect_match_flag = true:
   - You MUST follow the 100% scoring rule from the system prompt.
   - DO NOT evaluate normally.

2. If perfect_match_flag = false:
   - Score normally based on resume vs JD.

Analyze the resume and job description and return an ATS evaluation.

Your task:

For each category:
- summary (1–2 sentences)
- detailed improvements:
    - MUST contain 3–8 content 
    - MUST NOT use any Unicode or special bullet characters
    - MUST be specific, actionable, and deeply detailed
    - MUST include ATS optimization tips
    
    - MUST include missing elements the candidate should 
    - MUST avoid generic phrases
    - MUST be useful and professional
add
Return output ONLY in this exact JSON:

{{
  "overall_score": 0,
  "categories": {{
    "education": {{ "score": 0, "status": "", "summary": "", "improvements": "" }},
    "formatting": {{ "score": 0, "status": "", "summary": "", "improvements": "" }},
    "contact_information": {{ "score": 0, "status": "", "summary": "", "improvements": "" }},
    "skills": {{ "score": 0, "status": "", "summary": "", "improvements": "" }},
    "work_experience": {{ "score": 0, "status": "", "summary": "", "improvements": "" }},
    "ats_compatibility": {{ "score": 0, "status": "", "summary": "", "improvements": "" }},
    "keywords": {{ "score": 0, "status": "", "summary": "", "improvements": "" }},
    "summary": {{ "score": 0, "status": "", "summary": "", "improvements": "" }}
  }},
  "matched_keywords": [],
  "missing_keywords": [],
  "suggestions": []
}}
"""

    # -----------------------------------------------------------
    # CALL LLM
    # -----------------------------------------------------------
    completion = client.chat.completions.create(
        model="llama-3.3-70b-versatile",
        messages=[
            {"role": "system", "content": system_prompt},
            {"role": "user", "content": user_prompt}
        ],
        max_completion_tokens=1500,
        temperature=0.0
    )

    raw_output = completion.choices[0].message.content.strip()

    cleaned = raw_output.replace("```json", "").replace("```", "").replace("`", "").strip()

    first = cleaned.find("{")
    last = cleaned.rfind("}")

    if first == -1 or last == -1:
        return {"error": "Invalid JSON returned", "raw": raw_output}

    cleaned_json = cleaned[first:last + 1]

    try:
        parsed = json.loads(cleaned_json)
    except json.JSONDecodeError:
        return {"error": "JSON parsing failed", "raw": raw_output, "cleaned": cleaned_json}

    return parsed
