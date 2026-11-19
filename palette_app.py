"""Pixel Pop: color palette extractor (tkinter desktop app).
if-else: describe_color, read_count | loop: palette_of, build_mood_board
list: paths, palettes | tuple/set/dict: Swatch, shared tones, tabs dict
string: rgb_to_hex, compare_text | libraries: scikit-learn, Pillow, matplotlib, tkinter
"""
import os
import tkinter as tk
from collections import Counter
from dataclasses import dataclass
from tkinter import filedialog, messagebox, ttk

from matplotlib.backends.backend_tkagg import FigureCanvasTkAgg
from matplotlib.figure import Figure
from PIL import Image, ImageDraw, ImageOps, ImageTk
from sklearn.cluster import KMeans

LOGO = os.path.join(os.path.dirname(os.path.abspath(__file__)), "logo.png")
FILE_TYPES = [("Images", "*.jpg *.jpeg *.png"), ("All files", "*.*")]
RESIZE, PREVIEW, BOARD_PREVIEW, LOGO_SIZE = (100, 100), (340, 240), (860, 420), (360, 200)
BAR_W, BAR_H, BOARD_W, CELL_H = 600, 60, 900, 240
MIN_C, MAX_C, DEFAULT_C, SIMILAR = 3, 8, 5, 40
PAGE, BOX, PHOTO, TAB_BG = "#FCF8FF", "#CAC3E7", "#FCF6F9", "#E6E1F5"
BORDER, HOVER, TEXT = "#A9A1CC", "#B3AADB", "black"
FONT, BOLD = ("Century Gothic", 10), ("Century Gothic", 10, "bold")
HEAD, TITLE = ("Century Gothic", 12, "bold"), ("Century Gothic", 18, "bold")
TAB_FONT_ON, TAB_FONT_OFF = ("Century Gothic", 14, "bold"), ("Century Gothic", 10)
MONO = ("Consolas", 10)


@dataclass(frozen=True)
class Swatch:
    rgb: tuple
    hex_code: str
    share: float
    name: str


# ---------- Analysis ----------

def load_image(path):
    """Open a photo as RGB, turned upright. Returns None if it isn't an image."""
    try:
        return ImageOps.exif_transpose(Image.open(path)).convert("RGB")
    except OSError:
        return None


def describe_color(rgb):
    r, g, b = rgb
    brightness = sum(rgb) / 3
    if brightness < 50:
        return "Dark"
    if brightness > 200:
        return "Light"
    if r >= g and r >= b:
        return "Warm (red-ish)"
    return "Green-ish" if g >= b else "Cool (blue-ish)"


def distance(a, b):
    return sum((x - y) ** 2 for x, y in zip(a, b)) ** 0.5


def palette_of(images, n):
    """Group the pixels of one or more photos into n colors, most common first."""
    pixels = []
    for img in images:
        small = img.copy()
        small.thumbnail(RESIZE)
        pixels.extend(small.getdata())
    model = KMeans(n_clusters=n, n_init=10, random_state=0).fit(pixels)
    counts = Counter(model.labels_.tolist())
    swatches = []
    for k, center in enumerate(model.cluster_centers_):
        rgb = tuple(int(v) for v in center)
        share = counts[k] / len(pixels) * 100
        hex_code = "#{:02X}{:02X}{:02X}".format(*rgb)
        swatches.append(Swatch(rgb, hex_code, share, describe_color(rgb)))
    return sorted(swatches, key=lambda s: s.share, reverse=True)


def compare_text(p1, p2):
    """The comparison summary: tones, close color pairs, and shared tones."""
    tones1 = sorted({s.name for s in p1})
    if p2 is None:
        return f"Photo 1 tones: {', '.join(tones1)}\nChoose photo 2 to see a comparison."
    tones2 = sorted({s.name for s in p2})
    lines = [f"Photo 1 tones: {', '.join(tones1)}", f"Photo 2 tones: {', '.join(tones2)}"]
    pairs = []
    for a in p1:
        b = min(p2, key=lambda s: distance(a.rgb, s.rgb))
        d = distance(a.rgb, b.rgb)
        if d <= SIMILAR:
            pairs.append(f"   {a.hex_code} (photo 1)  ~  {b.hex_code} (photo 2)   distance {d:.0f}")
    lines.append("Close matches:" if pairs else "No close color matches.")
    lines += pairs
    shared = sorted(set(tones1) & set(tones2))
    lines.append("Shared tones: " + (", ".join(shared) or "none"))
    return "\n".join(lines)


def build_mood_board(images, palette):
    """All photos in one collage, with the shared color bar along the bottom."""
    cols = min(3, len(images))
    rows = -(-len(images) // cols)
    cell_w = BOARD_W // cols
    board = Image.new("RGB", (cell_w * cols, CELL_H * rows + BAR_H), "white")
    for i, img in enumerate(images):
        tile = img.copy()
        tile.thumbnail((cell_w - 10, CELL_H - 10))
        x = (i % cols) * cell_w + (cell_w - tile.width) // 2
        y = (i // cols) * CELL_H + (CELL_H - tile.height) // 2
        board.paste(tile, (x, y))
    board.paste(color_bar(palette, board.width, BAR_H), (0, board.height - BAR_H))
    return board


# ---------- Output ----------

def color_bar(palette, width, height):
    """Each block is as wide as its share of the photo."""
    bar = Image.new("RGB", (width, height), "white")
    draw, x = ImageDraw.Draw(bar), 0
    for i, s in enumerate(palette):
        end = width if i == len(palette) - 1 else min(width, x + round(width * s.share / 100))
        if end > x:
            draw.rectangle([x, 0, end - 1, height - 1], fill=s.rgb)
        x = end
    return bar


def save_text(palette, path):
    with open(path, "w") as f:
        for s in palette:
            f.write(f"{s.hex_code}  {s.share:.1f}%  {s.name}\n")


def to_unit(rgb):
    return tuple(v / 255 for v in rgb)


# ---------- Charts ----------

def pie_chart(img, palette, title):
    """The photo beside a pie of its colors. Percentages sit in a legend."""
    fig = Figure(figsize=(10, 5), layout="tight")
    photo = fig.add_subplot(1, 2, 1)
    photo.imshow(img)
    photo.set_title("Image")
    photo.axis("off")
    ax = fig.add_subplot(1, 2, 2)
    wedges, _ = ax.pie([s.share for s in palette], colors=[to_unit(s.rgb) for s in palette],
                       startangle=90, counterclock=False, wedgeprops={"edgecolor": "white"})
    ax.legend(wedges, [f"{s.hex_code}   {s.share:.1f}%" for s in palette],
              loc="center left", bbox_to_anchor=(1.0, 0.5), frameon=False, fontsize=9)
    ax.set_title(title)
    ax.axis("equal")
    return fig


def shift_chart(names, palettes):
    """One stacked bar per photo. Each bar shows that photo's own palette."""
    fig = Figure(figsize=(10, 5), layout="tight")
    ax = fig.add_subplot(1, 1, 1)
    bottoms = [0.0] * len(palettes)
    for layer in range(max(len(p) for p in palettes)):
        for i, palette in enumerate(palettes):
            if layer < len(palette):
                s = palette[layer]
                ax.bar(i, s.share, bottom=bottoms[i], color=to_unit(s.rgb), edgecolor="white")
                bottoms[i] += s.share
    ax.set_xticks(range(len(names)))
    ax.set_xticklabels(names, rotation=20, ha="right")
    ax.set_ylabel("Share of pixels (%)")
    ax.set_title("How the palette changes across photos")
    return fig


def open_chart_window(figures, title):
    """A window about 45% of the screen. Buttons are packed first so they stay visible."""
    win = tk.Toplevel()
    win.title(title)
    win.configure(bg=PAGE)
    sw, sh = win.winfo_screenwidth(), win.winfo_screenheight()
    w, h = int(sw / 2.2), int(sh / 2.2)
    win.geometry(f"{w}x{h}+{(sw - w) // 2}+{(sh - h) // 2}")
    win.minsize(600, 420)

    buttons = tk.Frame(win, bg=PAGE)
    buttons.pack(side="bottom", fill="x", padx=12, pady=8)
    area = tk.Frame(win, bg=PAGE)
    area.pack(fill="both", expand=True, padx=12, pady=(12, 8))
    canvases = [FigureCanvasTkAgg(f, master=area) for f in figures]
    current = [0]
    counter = tk.Label(buttons, bg=PAGE, fg=TEXT, font=FONT)

    def show(index):
        current[0] = index % len(figures)
        for c in canvases:
            c.get_tk_widget().pack_forget()
        canvases[current[0]].get_tk_widget().pack(fill="both", expand=True)
        canvases[current[0]].draw_idle()
        counter.configure(text=f"Chart {current[0] + 1} of {len(figures)}")

    def save_image():
        path = filedialog.asksaveasfilename(parent=win, defaultextension=".png",
                                            filetypes=[("PNG image", "*.png")])
        if path:
            figures[current[0]].savefig(path, dpi=150, facecolor="white")

    RoundButton(buttons, "Previous", lambda: show(current[0] - 1), 120).pack(side="left", padx=(0, 8))
    RoundButton(buttons, "Next", lambda: show(current[0] + 1), 120).pack(side="left", padx=(0, 8))
    RoundButton(buttons, "Save image", save_image, 140).pack(side="left", padx=(0, 16))
    counter.pack(side="left")
    show(0)


# ---------- GUI helpers ----------

def warn(message):
    messagebox.showwarning("Pixel Pop", message)


def read_count(var):
    text = var.get().strip()
    if text.isdigit() and MIN_C <= int(text) <= MAX_C:
        return int(text)
    warn(f"Enter a whole number from {MIN_C} to {MAX_C}.")
    return None


def boxed(parent, **options):
    style = {"bg": BOX, "fg": TEXT, "font": FONT,
             "highlightthickness": 2, "highlightbackground": BORDER}
    style.update(options)
    return tk.Label(parent, **style)


def show_image(label, pil_image):
    label.photo = ImageTk.PhotoImage(pil_image)  # keep a reference or Tk erases it
    label.configure(image=label.photo, text="", width=0, height=0)


class RoundButton(tk.Canvas):
    """A rounded button that darkens while the mouse is over it."""

    def __init__(self, master, text, command, width, height=32, r=10):
        super().__init__(master, width=width, height=height, bg=PAGE,
                         highlightthickness=0, cursor="hand2")
        x2, y2 = width - 2, height - 2
        pts = [2 + r, 2, x2 - r, 2, x2, 2, x2, 2 + r, x2, y2 - r, x2, y2,
               x2 - r, y2, 2 + r, y2, 2, y2, 2, y2 - r, 2, 2 + r, 2, 2]
        self.shape = self.create_polygon(pts, smooth=True, fill=BOX, outline=BORDER, width=2)
        self.create_text(width / 2, height / 2, text=text, fill=TEXT, font=BOLD)
        self.bind("<Enter>", lambda e: self.itemconfig(self.shape, fill=HOVER))
        self.bind("<Leave>", lambda e: self.itemconfig(self.shape, fill=BOX))
        self.bind("<Button-1>", lambda e: command())


class SwatchCards(tk.Frame):
    """A row of color cards. Clicking one copies its hex code."""

    def __init__(self, master, on_copy):
        super().__init__(master, bg=PAGE)
        self.on_copy = on_copy

    def show(self, palette):
        for child in self.winfo_children():
            child.destroy()
        for s in palette:
            card = tk.Frame(self, bg=BOX, highlightthickness=2,
                            highlightbackground=BORDER, cursor="hand2")
            card.pack(side="left", padx=(0, 12), pady=4)
            block = tk.Frame(card, bg=s.hex_code, width=130, height=64)
            block.pack_propagate(False)
            block.pack(fill="x")
            text = tk.Label(card, text=f"{s.hex_code}\n{s.share:.1f}%\n{s.name}", bg=BOX,
                            fg=TEXT, font=MONO, justify="left", anchor="w")
            text.pack(fill="x", padx=8, pady=6)
            for widget in (card, block, text):
                widget.bind("<Button-1>", lambda e, code=s.hex_code: self.on_copy(code))


class ScrollArea(tk.Frame):
    """A frame that scrolls vertically. Put page content in .inner."""

    def __init__(self, master):
        super().__init__(master, bg=PAGE)
        self.canvas = tk.Canvas(self, bg=PAGE, highlightthickness=0)
        bar = ttk.Scrollbar(self, orient="vertical", command=self.canvas.yview)
        self.canvas.configure(yscrollcommand=bar.set)
        bar.pack(side="right", fill="y")
        self.canvas.pack(side="left", fill="both", expand=True)
        self.inner = tk.Frame(self.canvas, bg=PAGE)
        win = self.canvas.create_window((0, 0), window=self.inner, anchor="nw")
        self.inner.bind("<Configure>",
                        lambda e: self.canvas.configure(scrollregion=self.canvas.bbox("all")))
        self.canvas.bind("<Configure>", lambda e: self.canvas.itemconfig(win, width=e.width))


# ---------- Tabs ----------

class BaseTab(tk.Frame):
    """Shared layout: button rows, the color count box, and headings."""

    def __init__(self, master, app):
        super().__init__(master, bg=PAGE, padx=16, pady=12)
        self.app = app
        self.count = tk.StringVar(value=str(DEFAULT_C))
        self.build_ui()

    def row(self, items):
        """One straight row of buttons. None marks the Colors box."""
        bar = tk.Frame(self, bg=PAGE)
        bar.pack(anchor="w", pady=(0, 6))
        for item in items:
            if item is None:
                tk.Label(bar, text="Colors", bg=PAGE, fg=TEXT, font=FONT).pack(side="left", padx=(8, 4))
                ttk.Spinbox(bar, from_=MIN_C, to=MAX_C, width=4,
                            textvariable=self.count).pack(side="left", padx=(0, 8))
            else:
                text, command = item
                RoundButton(bar, text, command, max(90, 9 * len(text))).pack(side="left", padx=(0, 8))

    def heading(self, text):
        tk.Label(self, text=text, bg=PAGE, fg=TEXT, font=HEAD).pack(anchor="w", pady=(14, 4))


class CompareTab(BaseTab):
    """Compare one or two photos: palettes, a comparison, pie charts, and saved files."""

    def build_ui(self):
        self.paths = [None, None]
        self.images = [None, None]
        self.palettes = [None, None]
        self.row([("Choose photo 1", lambda: self.choose(0)),
                  ("Choose photo 2 (optional)", lambda: self.choose(1)),
                  ("Clear", self.clear), None,
                  ("Extract", self.extract), ("Pie chart", self.show_pies),
                  ("Save", self.save)])

        previews = tk.Frame(self, bg=PAGE)
        previews.pack(pady=12)
        self.previews = [boxed(previews, text=f"No photo {i + 1}", bg=PHOTO, width=44, height=12)
                         for i in range(2)]
        for label in self.previews:
            label.pack(side="left", padx=8)

        self.bars, self.cards = [], []
        for i in range(2):
            self.heading(f"Dominant colors, photo {i + 1} (click a card to copy its hex code)")
            bar = tk.Label(self, bg=PAGE)
            bar.pack(anchor="w")
            cards = SwatchCards(self, self.app.copy_to_clipboard)
            cards.pack(anchor="w")
            self.bars.append(bar)
            self.cards.append(cards)

        self.heading("Comparison")
        self.summary = boxed(self, font=MONO, justify="left", anchor="w", padx=10, pady=8)
        self.summary.pack(fill="x")

    def choose(self, i):
        path = filedialog.askopenfilename(filetypes=FILE_TYPES)
        if not path:
            return
        img = load_image(path)
        if img is None:
            return messagebox.showerror("Not an image", f"'{os.path.basename(path)}' could not be opened.")
        self.paths[i], self.images[i], self.palettes[i] = path, img, None
        preview = img.copy()
        preview.thumbnail(PREVIEW)
        show_image(self.previews[i], preview)
        self.app.set_status(f"Loaded {os.path.basename(path)}")

    def clear(self):
        self.paths = [None, None]
        self.images = [None, None]
        self.palettes = [None, None]
        for i, label in enumerate(self.previews):
            label.configure(image="", text=f"No photo {i + 1}", width=44, height=12)
        for bar, cards in zip(self.bars, self.cards):
            bar.configure(image="")
            cards.show([])
        self.summary.configure(text="")
        self.app.set_status("Cleared")

    def extract(self):
        if self.images[0] is None:
            return warn("Choose photo 1 first.")
        n = read_count(self.count)
        if n is None:
            return
        self.palettes = [palette_of([img], n) if img is not None else None for img in self.images]
        for palette, bar, cards in zip(self.palettes, self.bars, self.cards):
            if palette is None:
                bar.configure(image="")
                cards.show([])
            else:
                show_image(bar, color_bar(palette, BAR_W, BAR_H))
                cards.show(palette)
        self.summary.configure(text=compare_text(*self.palettes))
        self.app.set_status("Palette extracted")

    def show_pies(self):
        if self.palettes[0] is None:
            return warn("Extract a palette first.")
        figures = [pie_chart(self.images[i], pal, f"Photo {i + 1} color shares")
                   for i, pal in enumerate(self.palettes) if pal is not None]
        open_chart_window(figures, "Color shares")

    def save(self):
        if self.palettes[0] is None:
            return warn("Extract a palette first.")
        for path, palette in zip(self.paths, self.palettes):
            if path is not None and palette is not None:
                base = os.path.splitext(path)[0]
                save_text(palette, base + "_palette.txt")
                color_bar(palette, BAR_W, BAR_H).save(base + "_palette.png")
        messagebox.showinfo("Saved", "Palette files were saved next to your photos.")


class MoodBoardTab(BaseTab):
    """Combine several photos into one collage that shares a single palette."""

    EMPTY = "Add 2 or more photos, then build your board."

    def build_ui(self):
        self.paths, self.names, self.per_photo = [], [], []
        self.board, self.palette = None, None
        self.row([("Add photos", self.add_photos), ("Clear", self.clear), None,
                  ("Build board", self.build), ("Pie chart", self.show_pie),
                  ("Palette shift", self.show_shift), ("Save", self.save)])
        self.listbox = tk.Listbox(self, height=4, font=FONT, relief="flat", bg=PHOTO,
                                  fg=TEXT, highlightthickness=2, highlightbackground=BORDER)
        self.listbox.pack(fill="x", pady=10)
        self.board_label = boxed(self, text=self.EMPTY, bg=PHOTO, width=100, height=12)
        self.board_label.pack(pady=4)
        self.heading("Shared palette (click a card to copy its hex code)")
        self.cards = SwatchCards(self, self.app.copy_to_clipboard)
        self.cards.pack(anchor="w")

    def add_photos(self):
        for path in filedialog.askopenfilenames(filetypes=FILE_TYPES):
            if path not in self.paths:
                self.paths.append(path)
                self.listbox.insert("end", os.path.basename(path))

    def clear(self):
        self.paths, self.names, self.per_photo = [], [], []
        self.board, self.palette = None, None
        self.listbox.delete(0, "end")
        self.board_label.configure(image="", text=self.EMPTY)
        self.cards.show([])

    def build(self):
        if len(self.paths) < 2:
            return warn("A mood board needs at least 2 photos.")
        n = read_count(self.count)
        if n is None:
            return
        loaded = [(os.path.basename(p), load_image(p)) for p in self.paths]
        loaded = [(name, img) for name, img in loaded if img is not None]
        if len(loaded) < 2:
            return warn("Need at least 2 valid photos.")
        self.names = [name for name, _ in loaded]
        images = [img for _, img in loaded]
        self.palette = palette_of(images, n)
        self.per_photo = [palette_of([img], n) for img in images]
        self.board = build_mood_board(images, self.palette)
        preview = self.board.copy()
        preview.thumbnail(BOARD_PREVIEW)
        show_image(self.board_label, preview)
        self.cards.show(self.palette)
        self.app.set_status("Mood board built")

    def show_pie(self):
        if self.board is None:
            return warn("Build a mood board first.")
        open_chart_window([pie_chart(self.board, self.palette, "Shared palette color shares")],
                          "Color shares")

    def show_shift(self):
        if self.board is None:
            return warn("Build a mood board first.")
        names = ["All photos"] + self.names
        open_chart_window([shift_chart(names, [self.palette] + self.per_photo)], "Palette shift")

    def save(self):
        if self.board is None:
            return warn("Build a mood board first.")
        path = filedialog.asksaveasfilename(defaultextension=".png",
                                            filetypes=[("PNG image", "*.png")],
                                            initialfile="mood_board.png")
        if path:
            self.board.save(path)
            save_text(self.palette, os.path.splitext(path)[0] + "_palette.txt")
            messagebox.showinfo("Saved", f"Saved {os.path.basename(path)} and its palette file.")


# ---------- Main window ----------

class PaletteApp(tk.Tk):
    def __init__(self):
        super().__init__()
        self.title("Pixel Pop")
        self.geometry("1200x900")
        self.configure(bg=PAGE)
        ttk.Style(self).theme_use("clam")
        self.status = tk.StringVar(value="Ready")

        self.page = ScrollArea(self)
        self.page.pack(fill="both", expand=True)
        root = self.page.inner

        logo = load_image(LOGO)
        if logo is not None:
            logo.thumbnail(LOGO_SIZE)
            label = tk.Label(root, bg=PAGE, bd=0)
            show_image(label, logo)
            label.pack(pady=(10, 0))
        else:
            tk.Label(root, text="Pixel Pop", bg=PAGE, fg=TEXT, font=TITLE).pack(pady=(16, 0))
        tk.Label(root, text="Find the main colors in your photos.", bg=PAGE, fg=TEXT,
                 font=FONT).pack(pady=(4, 0))

        tab_bar = tk.Frame(root, bg=PAGE)
        tab_bar.pack(fill="x", padx=16, pady=(12, 0))
        body = tk.Frame(root, bg=PAGE)
        body.pack(fill="x", padx=16, pady=(0, 12))

        self.pages, self.tabs = {}, {}
        for name, page_class in [("Compare photos", CompareTab), ("Mood board", MoodBoardTab)]:
            self.pages[name] = page_class(body, self)
            tab = tk.Label(tab_bar, text=name, cursor="hand2", bd=0,
                           highlightthickness=2, highlightbackground=BORDER)
            tab.pack(side="left", padx=(0, 4), anchor="s")
            tab.bind("<Button-1>", lambda e, n=name: self.select(n))
            self.tabs[name] = tab

        tk.Label(root, textvariable=self.status, bg=PAGE, fg=TEXT, font=FONT,
                 anchor="w").pack(fill="x", padx=24, pady=(0, 8))
        self.bind("<MouseWheel>", lambda e: self.page.canvas.yview_scroll(int(-e.delta / 120), "units"))
        self.select("Compare photos")

    def select(self, name):
        for tab_name, tab in self.tabs.items():
            active = tab_name == name
            tab.configure(font=TAB_FONT_ON if active else TAB_FONT_OFF,
                          bg=BOX if active else TAB_BG, fg=TEXT,
                          padx=22 if active else 12, pady=10 if active else 5)
        for page in self.pages.values():
            page.pack_forget()
        self.pages[name].pack(fill="x")

    def copy_to_clipboard(self, hex_code):
        self.clipboard_clear()
        self.clipboard_append(hex_code)
        self.status.set(f"Copied {hex_code} to clipboard")


if __name__ == "__main__":
    PaletteApp().mainloop()