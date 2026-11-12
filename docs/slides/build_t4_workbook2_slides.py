"""Build T4-Workbook2.pptx from rendered slide images plus speaker notes.
Usage: python build_t4_workbook2_slides.py <dir with s00.png..> <notes.json> <out.pptx>
The images are screenshots of docs/presentation-wb2 (render.html?i=N at 1600x900)."""
import glob
import json
import sys

from pptx import Presentation
from pptx.util import Inches

shots, notes, out = sys.argv[1:4]
prs = Presentation()
prs.slide_width, prs.slide_height = Inches(13.333), Inches(7.5)
for img, n in zip(sorted(glob.glob(f"{shots}/s[0-9][0-9].png")), json.load(open(notes))):
    s = prs.slides.add_slide(prs.slide_layouts[6])
    s.shapes.add_picture(img, 0, 0, width=prs.slide_width, height=prs.slide_height)
    s.notes_slide.notes_text_frame.text = (
        f"{n['rubric']}\n\nSAY:\n" + "\n\n".join(n["say"]) + "\n\nIF ASKED:\n" + "\n\n".join(n["qa"])
    )
prs.save(out)
print("saved", out, len(prs.slides), "slides")
