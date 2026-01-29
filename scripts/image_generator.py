"""
Image Generation Module
Uses Firefly Card API to convert Markdown content into beautiful images.
"""
import os
import base64
import requests
from typing import Dict, Any, Optional, Tuple
from dataclasses import dataclass
from pathlib import Path
from config import (
    FIREFLY_API_URL,
    FIREFLY_API_KEY,
    FIREFLY_DEFAULT_CONFIG,
    ENABLE_IMAGE_GENERATION,
    OUTPUT_DIR
)

@dataclass
class TextMetrics:
    """Quantitative analysis of markdown content"""
    line_count: int
    char_count: int
    max_width: int
    heading_count: int
    list_count: int

class CardMaker:
    """Generates visual cards from text using external API"""
    
    def __init__(self, url: str = None, key: str = None):
        """
        Initialize the card maker
        Args:
            url: API endpoint
            key: API key
        """
        self.endpoint = url or FIREFLY_API_URL
        self.token = key or FIREFLY_API_KEY
        self.settings = FIREFLY_DEFAULT_CONFIG.copy()
        self.is_active = ENABLE_IMAGE_GENERATION

    def _profile_text(self, text: str) -> TextMetrics:
        """Analyze text structure to guide styling"""
        lines = [l.strip() for l in text.split('\n') if l.strip()]
        return TextMetrics(
            line_count=len(lines),
            char_count=sum(len(l) for l in lines),
            max_width=max((len(l) for l in lines), default=0),
            heading_count=sum(1 for l in lines if l.startswith('#')),
            list_count=sum(1 for l in lines if l.startswith(('- ', '* ')))
        )

    def _tune_layout(self, metrics: TextMetrics) -> Dict[str, Any]:
        """Determine optimal dimensions based on text profile"""
        if metrics.line_count < 15:
            w, p, s = 520, 18, 1.0
        elif metrics.line_count < 30:
            w, p, s = 600, 20, 1.1
        else:
            w, p, s = 680, 24, 1.2
            
        # Adjust width for long lines
        w = max(w, min(metrics.max_width * 14, 750))
        
        return {"width": w, "padding": p, "scale": s}

    def create_card(self, md_text: str, save_path: str = None) -> Optional[str]:
        """Generate and save card image"""
        if not self.is_active or not md_text.strip():
            return None
            
        metrics = self._profile_text(md_text)
        layout = self._tune_layout(metrics)
        
        # Estimate height
        est_h = 200 + (metrics.line_count * 35)
        est_h = max(600, min(est_h, 2800))
        
        payload = self.settings.copy()
        payload.update({
            "content": md_text,
            "width": layout["width"],
            "height": est_h,
            "padding": layout["padding"],
            "fontScale": layout["scale"]
        })
        
        headers = {"Content-Type": "application/json"}
        if self.token:
            headers["Authorization"] = f"Bearer {self.token}"
            
        try:
            print(f"🎨 Generating visual card...")
            resp = requests.post(self.endpoint, json=payload, headers=headers, timeout=45)
            resp.raise_for_status()
            
            if 'image/' in resp.headers.get('Content-Type', ''):
                return self._save_binary(resp.content, save_path)
            
            data = resp.json()
            img_ref = data.get("data") or data.get("imageUrl") or data.get("url")
            
            if isinstance(img_ref, str) and img_ref.startswith("http"):
                return img_ref
            elif isinstance(img_ref, str):
                return self._save_base64(img_ref, save_path)
                
            return None
        except Exception as e:
            print(f"⚠️ Card generation failed: {e}")
            return None

    def _save_binary(self, raw: bytes, path: str) -> str:
        """Save raw image bytes to disk"""
        final_path = path or str(Path(OUTPUT_DIR) / "images" / "daily.png")
        p = Path(final_path)
        p.parent.mkdir(parents=True, exist_ok=True)
        p.write_bytes(raw)
        return str(p)

    def _save_base64(self, encoded: str, path: str) -> str:
        """Decode and save base64 image"""
        if "," in encoded:
            encoded = encoded.split(",", 1)[1]
        return self._save_binary(base64.b64decode(encoded), path)

    def from_analysis(self, result: Dict[str, Any], path: str = None) -> Optional[str]:
        """Helper to build card from analysis object"""
        md = self._to_markdown(result)
        return self.create_card(md, path)

    def _to_markdown(self, res: Dict[str, Any]) -> str:
        """Convert analysis result to card-friendly markdown"""
        day = res.get("date", "Today")
        blocks = [f"# AI Daily\n## {day}\n"]
        
        if res.get("summary"):
            blocks.append("### Highlights")
            blocks.extend([f"- {s}" for s in res["summary"][:4]])
            blocks.append("")
            
        for c in res.get("categories", []):
            if c.get("items"):
                blocks.append(f"### {c['name']}")
                blocks.extend([f"**{i['title']}**" for i in c["items"][:2]])
                blocks.append("")
                
        if res.get("keywords"):
            blocks.append(" ".join([f"#{k}" for k in res["keywords"][:6]]))
            
        return "\n".join(blocks)

# Compatibility aliases
class ImageGenerator(CardMaker):
    def generate(self, md, path=None): return self.create_card(md, path)
    def generate_from_analysis_result(self, res, path=None): return self.from_analysis(res, path)

def generate_card_image(md, path=None): return CardMaker().create_card(md, path)
def generate_card_from_analysis(res, path=None): return CardMaker().from_analysis(res, path)
