"""Viper's respirator, dark armor, and green chemical effects."""
from PIL import Image, ImageDraw

from sprites import CLEAR, save, strip
from sprites_breach import export_agent
from sprites_figure_views import LOOKS, Look
from sprites_waylay import pose as base_pose

INK, SUIT, GREEN, LIME = "#101d21", "#294338", "#529b54", "#b6f176"


def pose(tag, frame):
    img = base_pose(tag, frame)
    palette = {"#ffd269": GREEN, "#bc783e": SUIT, "#303759": SUIT, "#62689a": GREEN}
    colors = {tuple(bytes.fromhex(a[1:])) + (255,): tuple(bytes.fromhex(b[1:])) + (255,) for a, b in palette.items()}
    px = img.load()
    for y in range(img.height):
        for x in range(img.width):
            px[x, y] = colors.get(px[x, y], px[x, y])
    d = ImageDraw.Draw(img)
    y = 3 if tag.startswith("crouch") or tag in ("land", "plant", "defuse") else int(tag == "flinch" and frame == 0)
    d.polygon([(4, 6+y), (7, 7+y), (9, 7+y), (12, 6+y), (11, 10+y), (8, 12+y), (5, 10+y)], fill=INK)
    d.line((5, 9+y, 11, 9+y), fill=GREEN)
    d.point((8, 10+y), fill=LIME)
    return img


def icon(slot):
    img = Image.new("RGBA", (32, 32), CLEAR)
    d = ImageDraw.Draw(img)
    if slot == "C":
        d.polygon([(5, 12), (16, 6), (27, 12), (24, 23), (16, 27), (8, 23)], fill=SUIT, outline=LIME, width=2)
        d.line((8, 12, 13, 19, 16, 14, 19, 19, 24, 12), fill=LIME, width=2)
    elif slot == "Q":
        d.ellipse((5, 6, 26, 26), fill=SUIT, outline=LIME, width=2)
        d.ellipse((9, 12, 16, 19), fill=GREEN)
        d.ellipse((16, 10, 23, 20), fill=GREEN)
    elif slot == "E":
        for x in (6, 13, 20):
            d.line((x, 26, x+5, 9, x+2, 5), fill=LIME, width=2)
    else:
        d.arc((3, 3, 28, 28), 0, 350, fill=LIME, width=3)
        d.arc((8, 8, 23, 23), 20, 330, fill=GREEN, width=2)
        d.ellipse((13, 13, 18, 18), fill=LIME)
    return img


if __name__ == "__main__":
    LOOKS["viper"] = Look(11, INK, SUIT, INK, SUIT, GREEN, SUIT, LIME, GREEN, INK,
                          ("..tt..", ".ssss.", ".s..s.", "..tt..", "......"))
    export_agent("viper", pose, icon)
    for slot, key in (("C", "canister"), ("Q", "emitter"), ("E", "screen")):
        save(icon(slot).resize((16, 16), Image.Resampling.NEAREST), f"fx/viper_{key}.png")
    for name in ("cloud", "acid", "pit"):
        frames = []
        for phase in range(3):
            art = Image.new("RGBA", (64, 64), CLEAR)
            d = ImageDraw.Draw(art)
            d.ellipse((0, 0, 63, 63), fill=(36, 80, 48, 235 if name != "acid" else 105), outline=LIME, width=2)
            for inset in (7, 14, 21):
                d.arc((inset, inset, 63-inset, 63-inset), phase*20, 240+phase*20, fill=GREEN, width=3)
            frames.append(art)
        save(strip(frames), f"fx/viper_{name}.png")
