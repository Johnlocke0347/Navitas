"""Generates a clearly-labelled SYNTHETIC sample tariff sheet for the vision demo (not a real bill)."""
import pathlib
from PIL import Image, ImageDraw, ImageFont
out = pathlib.Path(__file__).resolve().parent.parent / "app" / "static" / "sample_bill.png"
img = Image.new("RGB", (900, 620), "white"); d = ImageDraw.Draw(img)
try: f = ImageFont.truetype("DejaVuSans.ttf", 26); fb = ImageFont.truetype("DejaVuSans-Bold.ttf", 32); fs = ImageFont.truetype("DejaVuSans.ttf", 20)
except Exception: f = fb = fs = ImageFont.load_default()
d.rectangle([20, 20, 880, 600], outline="black", width=3)
d.text((50, 40), "SAMPLE ELECTRICITY TARIFF SHEET", font=fb, fill="black")
d.text((50, 90), "(synthetic image made for the Navitas demo, not a real bill)", font=fs, fill=(180, 0, 0))
rows = [("Category", "B2 industrial (25-500 kW)"), ("Peak rate (18:30 - 22:30)", "Rs 35.68 / kWh"), ("Off-peak rate", "Rs 22.83 / kWh"),
        ("Fixed charge", "Rs 1,250 / kW / month"), ("Billing period", "30 days")]
y = 160
for a, b in rows:
    d.text((50, y), a, font=f, fill="black"); d.text((470, y), b, font=f, fill="black"); d.line([50, y + 42, 850, y + 42], fill="gray"); y += 70
img.save(out); print("wrote", out)
