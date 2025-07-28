import fitz, os, json
from collections import defaultdict

def score_heading(span, base_size, prev_bottom, page_width):
    """Return (is_heading, level) for a text span."""
    text      = span["text"].strip()
    size      = span["size"]
    font_name = span["font"].lower()
    y0, y1    = span["bbox"][1], span["bbox"][3]
    line_height = y1 - y0

    w_size   = 3        # relative font size
    w_bold   = 2        # bold / heavy stroke
    w_caps   = 1        # upper-case ratio
    w_space  = 1        # extra leading before line
    w_family = 1        # different font family
    # -------------------------------------

    rel = size / base_size
    size_score = 2 if rel > 1.4 else (1 if rel > 1.15 else 0)

    # (2) bold / heavy
    is_bold_font = any(tag in font_name for tag in
                       ("bold", "black", "heavy", "demi"))
    is_stroked   = span.get("render_mode", 0) == 2   
    bold_score   = 1 if (is_bold_font or is_stroked) else 0

    # (3) capitals
    cap_ratio = sum(c.isupper() for c in text) / max(len(text), 1)
    caps_score = 1 if cap_ratio > 0.6 else 0

    # (4) whitespace above
    space_above = (y0 - prev_bottom) if prev_bottom else 0
    space_score = 1 if space_above > 1.2 * line_height else 0

    # (5) font family change
    family_score = 1 if ("bold" in font_name or
                         "italic" in font_name or
                         rel > 1.1 and not is_bold_font) else 0

    total = (w_size*size_score + w_bold*bold_score +
             w_caps*caps_score + w_space*space_score +
             w_family*family_score)

    is_heading = total >= 5
    if not is_heading:
        return False, None

    if rel > 1.6:
        level = "H1"
    elif rel > 1.35:
        level = "H2"
    elif rel > 1.2:
        level = "H3"
    else:
        level = "H4"
    return True, level


def extract_outline(pdf_path, max_level=6):
    doc      = fitz.open(pdf_path)
    outlines = []
    title    = ""

    sizes = [s["size"]
         for page in doc
         for b in page.get_text("dict")["blocks"]
         if b.get("type", 0) == 0          
         for l in b["lines"]
         for s in l["spans"]]

    body_size = sorted(sizes)[len(sizes)//2]

    prev_bottom = None
    for page_num, page in enumerate(doc):
        blocks = page.get_text("dict")["blocks"]
        for block in blocks:
            if block.get("type", 0) != 0:
                continue 
            for line in block["lines"]:
                span = line["spans"][0]              # 1st span = full line
                span["bbox"] = line["bbox"]
                span["render_mode"] = span.get("render_mode", 0)
                ok, lvl = score_heading(
                    span, base_size=body_size,
                    prev_bottom=prev_bottom,
                    page_width=page.rect.width)
                prev_bottom = span["bbox"][3]

                if ok:
                    text = span["text"].strip()
                    # first heading becomes document title
                    if not title:
                        title = text
                    outlines.append(
                        {"level": lvl, "text": text, "page": page_num+1})
    if not title:
        title = os.path.basename(pdf_path).replace(".pdf", "")

    return {"title": title, "outline": outlines}

def process_dir(inp="input", out="output"):
    os.makedirs(out, exist_ok=True)
    for f in os.listdir(inp):
        if f.lower().endswith(".pdf"):
            res = extract_outline(os.path.join(inp, f))
            with open(os.path.join(out, f.rsplit(".",1)[0]+".json"), "w",
                      encoding="utf8") as fp:
                json.dump(res, fp, indent=2, ensure_ascii=False)

if __name__ == "__main__":
    process_dir()

