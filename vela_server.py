"""Vela: local text-to-image generation, served over HTTP for chat.html to call.

Uses SD-Turbo (single-step, fast, ~6GB VRAM) - the image-gen equivalent of
picking a small/cheap model, same reasoning as Koda/Soi being 1.5B.

Usage: python vela_server.py   (serves on http://localhost:7860)
"""
import base64
import io
import json
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer

import torch
from diffusers import AutoPipelineForText2Image

MODEL_ID = "stabilityai/sd-turbo"
PORT = 7860

print("Loading Vela (sd-turbo)...")
pipe = AutoPipelineForText2Image.from_pretrained(MODEL_ID, torch_dtype=torch.float16, variant="fp16")
pipe = pipe.to("cuda")
print("Vela ready.")


def generate(prompt: str) -> bytes:
    image = pipe(prompt=prompt, num_inference_steps=2, guidance_scale=0.0).images[0]
    buf = io.BytesIO()
    image.save(buf, format="PNG")
    return buf.getvalue()


class Handler(BaseHTTPRequestHandler):
    def _cors(self):
        origin = self.headers.get("Origin", "*")
        self.send_header("Access-Control-Allow-Origin", origin)
        self.send_header("Access-Control-Allow-Methods", "POST, OPTIONS")
        self.send_header("Access-Control-Allow-Headers", "Content-Type")

    def do_OPTIONS(self):
        self.send_response(204)
        self._cors()
        self.end_headers()

    def do_POST(self):
        if self.path != "/generate":
            self.send_response(404)
            self.end_headers()
            return
        length = int(self.headers.get("Content-Length", 0))
        body = json.loads(self.rfile.read(length) or b"{}")
        prompt = (body.get("prompt") or "").strip()
        if not prompt:
            self.send_response(400)
            self._cors()
            self.end_headers()
            self.wfile.write(b'{"error":"prompt required"}')
            return
        try:
            png_bytes = generate(prompt)
            b64 = base64.b64encode(png_bytes).decode("ascii")
            self.send_response(200)
            self._cors()
            self.send_header("Content-Type", "application/json")
            self.end_headers()
            self.wfile.write(json.dumps({"image": f"data:image/png;base64,{b64}"}).encode())
        except Exception as e:
            self.send_response(500)
            self._cors()
            self.send_header("Content-Type", "application/json")
            self.end_headers()
            self.wfile.write(json.dumps({"error": str(e)}).encode())

    def log_message(self, format, *args):
        pass  # quiet


if __name__ == "__main__":
    server = ThreadingHTTPServer(("0.0.0.0", PORT), Handler)
    print(f"Vela serving on http://localhost:{PORT}")
    server.serve_forever()
