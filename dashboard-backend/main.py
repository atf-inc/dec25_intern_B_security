from fastapi import FastAPI, HTTPException
from pydantic import BaseModel
from fastapi.middleware.cors import CORSMiddleware
from gmail_service import GmailService
import uvicorn

app = FastAPI()

# Configure CORS (allow frontend to connect)
app.add_middleware(
    CORSMiddleware,
    allow_origins=["http://localhost:3000"],  # Next.js frontend
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

class FetchEmailsRequest(BaseModel):
    access_token: str

@app.get("/")
def read_root():
    return {"message": "Hello from dashboard-backend!"}

@app.post("/api/v1/emails/fetch")
def fetch_emails(request: FetchEmailsRequest):
    if not request.access_token:
        raise HTTPException(status_code=400, detail="Access token is required")
    
    gmail = GmailService(request.access_token)
    emails = gmail.fetch_recent_emails()
    
    return {"status": "success", "count": len(emails), "emails": emails}

if __name__ == "__main__":
    uvicorn.run("main:app", host="0.0.0.0", port=8000, reload=True)
