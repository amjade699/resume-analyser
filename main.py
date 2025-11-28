from groq import Groq
from fastapi import FastAPI,UploadFile,File
from pdfminer.high_level import extract_text
from fastapi.responses import FileResponse
from dotenv import load_dotenv

import os


app=FastAPI()



@app.get("/")
def home():
    return FileResponse("index.html",media_type="text/html")


@app.post("/upload")
async def upload(resume: UploadFile = File(...), jd: UploadFile = File(...)):
    -u 

   
    resume_text=extract_text(resume.file)
    jd_text=extract_text(jd.file)

    

    return {
        "jd_text":jd_text[:200],
        "resume_text":resume_text[:200],
        "message":"file uploaded and extracted"
    }



@app.post("/model")
async def llm(resume: UploadFile = File(...), jd: UploadFile = File(...)):
   
   
    resume_text = extract_text(resume.file)
    jd_text = extract_text(jd.file)
    load_dotenv()
    APIKEY=os.getenv("API")
    client = Groq(api_key=APIKEY)
    prompt=f"""
    resume_text:{resume_text}
    job description:{jd_text}

    Give:
    - ATS Score
    - Missing Skills
    - Matching Skills
    - Summary Improvement Suggestions    

"""


    completion = client.chat.completions.create(
    model="llama-3.3-70b-versatile",
    messages=[
      {
        "role": "system",
        "content": f"You are an ATS scoring expert and resume evaluator"
      },
      {
          "role":"user",
          "content":prompt
      }
    ],
    temperature=1,
    max_completion_tokens=1024,
    top_p=1,
    stream=True,
  
)
    fullanswer=""
    for chunk in completion:fullanswer+=chunk.choices[0].delta.content or ""
    return {"response":fullanswer}

