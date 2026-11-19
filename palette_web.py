"""
Pixel Pop - color palette extractor (Streamlit web app)
Run with: & "C:\\Users\\User\\Downloads\\Programs\\python.exe" -m streamlit run palette_web.py
"""
import io
import streamlit as st
from PIL import Image, ImageDraw
from sklearn.cluster import KMeans
import matplotlib.pyplot as plt

RESIZE_TO = (100, 100)
STRIP_W, STRIP_H = 600, 80
BOARD_W, CELL_H = 900, 240
SIMILAR_THRESHOLD = 40
FILE_TYPES = ["jpg", "jpeg", "png"]
INK = "#222222"

st.set_page_config(page_title="Pixel Pop", layout="wide")

# ---------- Styling ----------
st.markdown("""
<style>
    header[data-testid="stHeader"], [data-testid="stToolbar"],
    [data-testid="stDecoration"], [data-testid="stStatusWidget"],
    #MainMenu, footer { display: none !important; }

    .block-container { padding-top: 2rem; max-width: 1100px; }
    h1 { font-weight: 700; color: #1F2A44; }
    h2, h3 { font-weight: 600; color: #1F2A44; }
    .stTabs [aria-selected="true"] { color: #4A6FA5 !important; }
    .stTabs [data-baseweb="tab-highlight"] { background-color: #4A6FA5; }
    img { border-radius: 10px; }

    .card {
        background: #F5F7FA; border: 1px solid #E3E8EF; border-radius: 12px;
        padding: 18px 20px; margin-bottom: 14px;
        box-shadow: 0 1px 3px rgba(0, 0, 0, 0.06);
    }
    .swatch-row { display: flex; gap: 12px; flex-wrap: wrap; }
    .swatch {
        width: 120px; border-radius: 10px; overflow: hidden;
        border: 1px solid #E3E8EF; background: #FFFFFF;
    }
    .swatch-color { height: 70px; }
    .swatch-text {
        padding: 8px 10px; font-size: 13px; color: #1F2A44;
        font-family: Consolas, monospace; line-height: 1.5;
    }
</style>
""", unsafe_allow_html=True)


# ---------- Analysis ----------

def open_image(file):
    """Open an uploaded photo as RGB. Returns None if it isn't an image."""
    try:
        return Image.open(io.BytesIO(file.getvalue())).convert("RGB")
    except OSError:
        return None


def describe_color(color):
    """A rough name based on brightness and the strongest channel."""
    r, g, b = color
    brightness = (r + g + b) / 3
    if brightness < 50:
        return "Dark"
    if brightness > 200:
        return "Light"
    if r >= g and r >= b:
        return "Warm (red-ish)"
    if g >= r and g >= b:
        return "Green-ish"
    return "Cool (blue-ish)"


def color_distance(c1, c2):
    """Straight-line distance between two colors in RGB space."""
    return sum((a - b) ** 2 for a, b in zip(c1, c2)) ** 0.5


def palette_from_pixels(pixels, num_colors):
    """Group pixels with k-means and return the colors, most common first."""
    model = KMeans(n_clusters=num_colors, n_init=10, random_state=0).fit(pixels)
    counts = [0] * num_colors
    for label in model.labels_:
        counts[label] += 1
    palette = []
    for center, count in zip(model.cluster_centers_, counts):
        color = tuple(int(v) for v in center)
        palette.append({
            "color": color,
            "hex": "#{:02X}{:02X}{:02X}".format(*color),
            "share": count / len(pixels) * 100,
            "name": describe_color(color),
        })
    return sorted(palette, key=lambda e: e["share"], reverse=True)


def find_palette(img, num_colors):
    """Shrink a photo and return its palette."""
    small = img.copy()
    small.thumbnail(RESIZE_TO)
    return palette_from_pixels(list(small.getdata()), num_colors)


def compare_palettes(pa, pb):
    """Pair each color in palette A with its closest color in palette B."""
    matches = []
    for a in pa:
        b = min(pb, key=lambda x: color_distance(a["color"], x["color"]))
        d = color_distance(a["color"], b["color"])
        if d <= SIMILAR_THRESHOLD:
            matches.append((a, b, d))
    return matches


def build_mood_board(images, num_colors):
    """Combine photos into one collage with one shared palette underneath."""
    pixels = []
    for img in images:
        small = img.copy()
        small.thumbnail(RESIZE_TO)
        pixels.extend(small.getdata())
    palette = palette_from_pixels(pixels, num_colors)

    cols = min(3, len(images))
    rows = -(-len(images) // cols)
    cell_w = BOARD_W // cols
    board = Image.new("RGB", (cell_w * cols, CELL_H * rows + STRIP_H), "white")
    for i, pic in enumerate(images):
        tile = pic.copy()
        tile.thumbnail((cell_w - 10, CELL_H - 10))
        x = (i % cols) * cell_w + (cell_w - tile.width) // 2
        y = (i // cols) * CELL_H + (CELL_H - tile.height) // 2
        board.paste(tile, (x, y))
    board.paste(swatch_strip(palette, board.width, STRIP_H), (0, board.height - STRIP_H))
    return board, palette


# ---------- Output ----------

def swatch_strip(palette, width, height):
    """One bar of colors, each block as wide as its share of the photo."""
    strip = Image.new("RGB", (width, height), "white")
    draw = ImageDraw.Draw(strip)
    x = 0
    for i, e in enumerate(palette):
        end = width if i == len(palette) - 1 else min(width, x + round(width * e["share"] / 100))
        if end > x:
            draw.rectangle([x, 0, end - 1, height - 1], fill=e["color"])
        x = end
    return strip


def format_palette(palette):
    """Text lines for one palette, with its tones at the end."""
    lines = [f"{i}. {e['hex']}  {e['share']:.1f}%  ({e['name']})"
             for i, e in enumerate(palette, start=1)]
    lines.append("Tones: " + ", ".join(sorted({e["name"] for e in palette})))
    return "\n".join(lines)


def palette_cards(palette):
    """Show each color as a swatch card with its hex code, share, and name."""
    items = ""
    for e in palette:
        items += (
            f'<div class="swatch">'
            f'<div class="swatch-color" style="background:{e["hex"]};"></div>'
            f'<div class="swatch-text">{e["hex"]}<br>{e["share"]:.1f}%<br>{e["name"]}</div>'
            f'</div>'
        )
    return f'<div class="card"><div class="swatch-row">{items}</div></div>'


def to_png(img):
    """An image as PNG bytes for a download button."""
    buf = io.BytesIO()
    img.save(buf, format="PNG")
    return buf.getvalue()


def to_txt(palette):
    """The palette as text bytes for a download button."""
    return "\n".join(f"{e['hex']}  {e['share']:.1f}%  {e['name']}" for e in palette).encode()


def make_chart(img, palette, title):
    """The photo next to a bar chart of its colors."""
    fig, (ax1, ax2) = plt.subplots(1, 2, figsize=(10, 4.5))
    ax1.imshow(img)
    ax1.set_title("Image (resized)", color=INK)
    ax1.axis("off")
    ax2.bar([e["hex"] for e in palette], [e["share"] for e in palette],
            color=[tuple(v / 255 for v in e["color"]) for e in palette],
            edgecolor="#555555")
    ax2.set_title(title, color=INK)
    ax2.set_ylabel("Share of pixels (%)")
    fig.tight_layout()
    return fig


# ---------- Pages ----------

def compare_page():
    col1, col2 = st.columns(2)
    file1 = col1.file_uploader("Photo 1", type=FILE_TYPES, key="file1")
    file2 = col2.file_uploader("Photo 2 (optional)", type=FILE_TYPES, key="file2")
    num = st.slider("Number of colors", 3, 8, 5, key="num1")

    if file1 is None:
        st.info("Upload photo 1 to get started.")
        return

    files = [f for f in (file1, file2) if f is not None]
    imgs = [open_image(f) for f in files]
    for f, img in zip(files, imgs):
        if img is None:
            st.error(f"'{f.name}' is not a valid image.")
            return
    palettes = [find_palette(img, num) for img in imgs]

    for f, img, pal, label in zip(files, imgs, palettes, ["Photo 1", "Photo 2"]):
        key = label.lower().replace(" ", "")
        st.subheader(label)
        st.image(img, caption=f.name)
        st.image(swatch_strip(pal, STRIP_W, STRIP_H))
        st.markdown(palette_cards(pal), unsafe_allow_html=True)
        st.pyplot(make_chart(img, pal, f"{label} colors"))
        st.download_button(f"Download {label.lower()} palette (.txt)", to_txt(pal),
                           file_name=f"{key}_palette.txt")
        st.download_button(f"Download {label.lower()} swatch (.png)",
                           to_png(swatch_strip(pal, STRIP_W, STRIP_H)),
                           file_name=f"{key}_palette.png", mime="image/png")

    if len(palettes) == 2:
        st.subheader("Comparison")
        matches = compare_palettes(palettes[0], palettes[1])
        if matches:
            for a, b, d in matches:
                st.write(f"{a['hex']} (photo 1) ~ {b['hex']} (photo 2), distance {d:.0f}")
        else:
            st.write("No close color matches.")
        shared = {e["name"] for e in palettes[0]} & {e["name"] for e in palettes[1]}
        st.write("Shared tones: " + (", ".join(sorted(shared)) or "none"))


def mood_board_page():
    files = st.file_uploader("Add 2 or more photos", type=FILE_TYPES,
                             accept_multiple_files=True, key="mood_files")
    num = st.slider("Number of colors", 3, 8, 5, key="num2")

    if len(files) < 2:
        st.info("Upload at least 2 photos to build a mood board.")
        return

    images = []
    for f in files:
        img = open_image(f)
        if img is None:
            st.warning(f"Skipped '{f.name}' because it is not a valid image.")
        else:
            images.append(img)
    if len(images) < 2:
        st.error("Need at least 2 valid photos.")
        return

    board, palette = build_mood_board(images, num)
    st.image(board, caption="Mood board")
    st.markdown(palette_cards(palette), unsafe_allow_html=True)
    st.pyplot(make_chart(board, palette, "Mood board palette"))
    st.download_button("Download mood board (.png)", to_png(board),
                       file_name="mood_board.png", mime="image/png")
    st.download_button("Download palette (.txt)", to_txt(palette),
                       file_name="mood_board_palette.txt")


# ---------- Main page ----------

st.title("Pixel Pop")
st.caption("Find the main colors in your photos.")
tab1, tab2 = st.tabs(["Compare photos", "Mood board"])
with tab1:
    compare_page()
with tab2:
    mood_board_page()