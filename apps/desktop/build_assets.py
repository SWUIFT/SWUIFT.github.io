"""Generate deterministic platform icons for local and CI packaging."""

from pathlib import Path

from PIL import Image, ImageDraw, ImageFont


ROOT = Path(__file__).resolve().parent
SIZE = 1024


def main() -> None:
    source = next((path for path in (ROOT / "SWUIFT.icns", ROOT / "SWUIFT.ico") if path.is_file()), None)
    if source is not None:
        image = Image.open(source).convert("RGBA").resize((SIZE, SIZE), Image.Resampling.LANCZOS)
    else:
        image = Image.new("RGBA", (SIZE, SIZE), "#162b24")
        draw = ImageDraw.Draw(image)
        draw.rounded_rectangle((70, 70, 954, 954), radius=190, fill="#246b49")
        draw.polygon(
            [(512, 125), (745, 485), (620, 465), (790, 805), (512, 695), (234, 805), (404, 465), (279, 485)],
            fill="#f28c28",
        )
        try:
            font = ImageFont.truetype("DejaVuSans-Bold.ttf", 165)
        except OSError:
            font = ImageFont.load_default()
        draw.text((512, 825), "SWUIFT", anchor="mm", fill="white", font=font)
    image.save(ROOT / "SWUIFT.png")
    if not (ROOT / "SWUIFT.ico").is_file():
        image.save(
            ROOT / "SWUIFT.ico",
            sizes=[(16, 16), (32, 32), (48, 48), (64, 64), (128, 128), (256, 256)],
        )
    if not (ROOT / "SWUIFT.icns").is_file():
        image.save(ROOT / "SWUIFT.icns")


if __name__ == "__main__":
    main()
