"""Create a multi-size Windows ICO from the user-provided app.png."""

from pathlib import Path

from PIL import Image


ROOT = Path(__file__).resolve().parent


def main() -> None:
    source = Image.open(ROOT / "app.png").convert("RGBA")
    side = max(source.size)
    image = Image.new("RGBA", (side, side), (0, 0, 0, 255))
    position = ((side - source.width) // 2, (side - source.height) // 2)
    image.alpha_composite(source, position)
    image.save(ROOT / "app-icon.png")
    image.save(
        ROOT / "app.ico",
        format="ICO",
        sizes=[(16, 16), (24, 24), (32, 32), (48, 48), (64, 64), (128, 128), (256, 256)],
    )


if __name__ == "__main__":
    main()
