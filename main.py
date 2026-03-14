# BridgeM Z3 Backend
# Receives compiled Z3 Python code, executes it, returns results

from fastapi import FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel
import subprocess
import json
import sys
import os
import tempfile

app = FastAPI()

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_methods=["POST", "OPTIONS"],
    allow_headers=["*"],
)

class Z3Request(BaseModel):
    z3_code: str
    timeout: int = 30

@app.post("/run_z3")
async def run_z3(req: Z3Request):
    # Write Z3 code to temp file
    with tempfile.NamedTemporaryFile(mode='w', suffix='.py', delete=False) as f:
        f.write(req.z3_code)
        tmp_path = f.name

    try:
        # Execute with timeout
        result = subprocess.run(
            [sys.executable, tmp_path],
            capture_output=True,
            text=True,
            timeout=req.timeout
        )

        if result.returncode != 0:
            # Z3 error — parse what went wrong
            return {
                "status": "ERROR",
                "error": result.stderr[:500],
                "contradictions": [],
                "soft_violations": [],
                "model": {}
            }

        # Parse JSON output from Z3 script
        output_text = result.stdout.strip()
        if not output_text:
            return {
                "status": "NO_OUTPUT",
                "contradictions": [],
                "soft_violations": [],
                "model": {}
            }

        parsed = json.loads(output_text)
        return parsed

    except subprocess.TimeoutExpired:
        return {
            "status": "TIMEOUT",
            "contradictions": [],
            "soft_violations": [],
            "model": {}
        }
    except json.JSONDecodeError as e:
        return {
            "status": "PARSE_ERROR",
            "error": str(e),
            "raw_output": result.stdout[:300] if result else "",
            "contradictions": [],
            "soft_violations": [],
            "model": {}
        }
    finally:
        os.unlink(tmp_path)

@app.get("/health")
def health():
    return {"status": "ok"}
