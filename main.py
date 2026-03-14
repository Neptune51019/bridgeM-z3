import os
import sys
import json
import tempfile
import subprocess

from fastapi import FastAPI
from pydantic import BaseModel

app = FastAPI()


class Z3Request(BaseModel):
    z3_code: str
    timeout: int = 30


@app.post("/run_z3")
async def run_z3(req: Z3Request):
    with tempfile.NamedTemporaryFile(mode='w', suffix='.py', delete=False) as f:
        f.write(req.z3_code)
        tmp_path = f.name
    try:
        result = subprocess.run(
            [sys.executable, tmp_path],
            capture_output=True, text=True, timeout=req.timeout
        )
        stdout = result.stdout.strip()
        stderr = result.stderr.strip()

        if result.returncode != 0:
            return {
                "status": "ERROR",
                "error": stderr[:500],
                "contradictions": [], "soft_violations": [], "model": {}
            }

        if not stdout:
            return {
                "status": "NO_OUTPUT",
                "contradictions": [], "soft_violations": [], "model": {}
            }

        # Try every line looking for valid JSON with a status field
        json_output = None
        for line in stdout.split('\n'):
            line = line.strip()
            if line.startswith('{'):
                try:
                    parsed = json.loads(line)
                    if 'status' in parsed:
                        json_output = parsed
                        break
                except Exception:
                    continue

        if json_output:
            return json_output

        # Fallback: parse sat/unsat plain text
        last_line = stdout.split('\n')[-1].strip()
        if last_line == 'sat':
            return {"status": "CONSISTENT", "contradictions": [], "soft_violations": [], "model": {}}
        elif last_line == 'unsat':
            return {"status": "CONTRADICTION_DETECTED", "contradictions": ["Z3 found contradiction"], "soft_violations": [], "model": {}}

        return {
            "status": "PARSE_ERROR",
            "error": "No JSON found in output",
            "raw_output": stdout[:300],
            "contradictions": [], "soft_violations": [], "model": {}
        }

    except subprocess.TimeoutExpired:
        return {"status": "TIMEOUT", "contradictions": [], "soft_violations": [], "model": {}}
    except Exception as e:
        return {"status": "EXCEPTION", "error": str(e), "contradictions": [], "soft_violations": [], "model": {}}
    finally:
        try:
            os.unlink(tmp_path)
        except Exception:
            pass


@app.get("/health")
def health():
    return {"status": "ok"}
