from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel
import subprocess, json, sys, os, tempfile

app = FastAPI()
app.add_middleware(CORSMiddleware, allow_origins=["*"], allow_methods=["*"], allow_headers=["*"])

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
            return {"status": "ERROR", "error": stderr[:500],
                    "contradictions": [], "soft_violations": [], "model": {}}

        if not stdout:
            return {"status": "NO_OUTPUT", "contradictions": [], "soft_violations": [], "model": {}}

        # Find the JSON line — Z3 output may have extra lines before the JSON
        json_output = None
        for line in reversed(stdout.split('\n')):
            line = line.strip()
            if line.startswith('{'):
                try:
                    json_output = json.loads(line)
                    break
                except:
                    continue

        if json_output:
            return json_output

        return {"status": "PARSE_ERROR", "error": "No JSON found in output",
                "raw_output": stdout[:300], "contradictions": [], "soft_violations": [], "model": {}}

    except subprocess.TimeoutExpired:
        return {"status": "TIMEOUT", "contradictions": [], "soft_violations": [], "model": {}}
    except Exception as e:
        return {"status": "EXCEPTION", "error": str(e), "contradictions": [], "soft_violations": [], "model": {}}
    finally:
        os.unlink(tmp_path)

@app.get("/health")
def health():
    return {"status": "ok"}
