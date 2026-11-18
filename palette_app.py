"""Pixel Pop: color palette extractor (tkinter desktop app)."""
import os
import tkinter as tk
from tkinter import ttk, filedialog, messagebox
from PIL import Image, ImageTk, ImageDraw
from sklearn.cluster import KMeans
import matplotlib.pyplot as plt

RESIZE_TO, PREVIEW_SIZE = (100, 100), (340, 240)
STRIP_W, STRIP_H, BOARD_W, CELL_H = 600, 60, 900, 240
MIN_C, MAX_C, DEFAULT_C, SIMILAR = 3, 8, 5, 40
FILE_TYPES = [("Images", "*.jpg *.jpeg *.png"), ("All files", "*.*")]

BG = "#F7F4DC"
CARD = "#949088"
CARD_TEXT = "white"
CARD_ALT = "#949088"
INK, MUTED, BORDER = "#2E2A3A", "#5E5A68", "#B8BCCB"
ACCENT, ACCENT_HOVER = "#949088", "#7D7870"
FONT, FONT_BOLD = ("Century Gothic", 10), ("Century Gothic", 10, "bold")
HEADING, TITLE = ("Century Gothic", 12, "bold"), ("Century Gothic", 18, "bold")
TAB_ON = ("Century Gothic", 14, "bold")   # selected tab: bigger
TAB_OFF = ("Century Gothic", 10)          # unselected tab: smaller
TAB_OFF_BG = "#E9E4C8"                    # unselected tab background
MONO = ("Consolas", 10)


# ---------- Analysis ----------

def load_image(path):
    try:
        return Image.open(path).convert("RGB")
    except OSError:
        raise ValueError(f"'{os.path.basename(path)}' is not a valid image.")


def shrink(img):
    small = img.copy()
    small.thumbnail(RESIZE_TO)
    return small


def describe(c):
    r, g, b = c
    avg = (r + g + b) / 3
    if avg < 50:
        return "Dark"
    if avg > 200:
        return "Light"
    if r >= g and r >= b:
        return "Warm (red-ish)"
    return "Green-ish" if g >= b else "Cool (blue-ish)"


def dist(c1, c2):
    return sum((a - b) ** 2 for a, b in zip(c1, c2)) ** 0.5


def find_palette(pixels, n):
    model = KMeans(n_clusters=n, n_init=10, random_state=0).fit(pixels)
    counts = [list(model.labels_).count(i) for i in range(n)]
    palette = []
    for center, count in zip(model.cluster_centers_, counts):
        c = tuple(int(v) for v in center)
        palette.append({"color": c, "hex": "#{:02X}{:02X}{:02X}".format(*c),
                        "share": count / len(pixels) * 100, "name": describe(c)})
    return sorted(palette, key=lambda e: e["share"], reverse=True)


def compare(pa, pb):
    matches = []
    for a in pa:
        b = min(pb, key=lambda x: dist(a["color"], x["color"]))
        d = dist(a["color"], b["color"])
        if d <= SIMILAR:
            matches.append((a, b, d))
    return matches


def build_mood_board(images, n):
    pixels = [p for img in images for p in shrink(img).getdata()]
    palette = find_palette(pixels, n)
    cols = min(3, len(images))
    rows = -(-len(images) // cols)
    cell_w = BOARD_W // cols
    board = Image.new("RGB", (cell_w * cols, CELL_H * rows + STRIP_H), "white")
    for i, pic in enumerate(images):
        tile = pic.copy()
        tile.thumbnail((cell_w - 10, CELL_H - 10))
        board.paste(tile, ((i % cols) * cell_w + (cell_w - tile.width) // 2,
                           (i // cols) * CELL_H + (CELL_H - tile.height) // 2))
    board.paste(swatch_strip(palette, board.width, STRIP_H), (0, board.height - STRIP_H))
    return board, palette


# ---------- Output ----------

def swatch_strip(palette, width, height):
    strip = Image.new("RGB", (width, height), "white")
    draw, x = ImageDraw.Draw(strip), 0
    for i, e in enumerate(palette):
        end = width if i == len(palette) - 1 else min(width, x + round(width * e["share"] / 100))
        if end > x:
            draw.rectangle([x, 0, end - 1, height - 1], fill=e["color"])
        x = end
    return strip


def save_text(palette, path):
    with open(path, "w") as f:
        f.writelines(f"{e['hex']}  {e['share']:.1f}%  {e['name']}\n" for e in palette)


def show_chart(img, palette, title):
    fig, (ax1, ax2) = plt.subplots(1, 2, figsize=(10, 4.5))
    ax1.imshow(img)
    ax1.set_title("Image (resized)")
    ax1.axis("off")
    ax2.bar([e["hex"] for e in palette], [e["share"] for e in palette],
            color=[tuple(v / 255 for v in e["color"]) for e in palette], edgecolor="#555555")
    ax2.set_title(title)
    ax2.set_ylabel("Share of pixels (%)")
    fig.tight_layout()
    plt.show()
    plt.close(fig)


# ---------- GUI helpers ----------

class RoundButton(tk.Canvas):
    def __init__(self, master, text, command, width=130, height=32):
        super().__init__(master, width=width, height=height, bg=BG,
                         highlightthickness=0, cursor="hand2")
        self.command = command
        self.box = self._round(2, 2, width - 2, height - 2, 10,
                               fill=ACCENT, outline=BORDER, width=2)
        self.create_text(width / 2, height / 2, text=text, fill=CARD_TEXT, font=FONT_BOLD)
        self.bind("<Enter>", lambda e: self.itemconfig(self.box, fill=ACCENT_HOVER))
        self.bind("<Leave>", lambda e: self.itemconfig(self.box, fill=ACCENT))
        self.bind("<Button-1>", lambda e: self.command())

    def _round(self, x1, y1, x2, y2, r, **kw):
        pts = [x1 + r, y1, x2 - r, y1, x2, y1, x2, y1 + r, x2, y2 - r, x2, y2,
               x2 - r, y2, x1 + r, y2, x1, y2, x1, y2 - r, x1, y1 + r, x1, y1]
        return self.create_polygon(pts, smooth=True, **kw)


def read_count(var):
    try:
        n = int(var.get())
    except ValueError:
        return None
    return n if MIN_C <= n <= MAX_C else None


def show_image(label, img):
    label.photo = ImageTk.PhotoImage(img)  # keep a reference so it isn't deleted
    label.configure(image=label.photo, text="", width=0, height=0)


def build_cards(parent, palette, on_copy):
    for child in parent.winfo_children():
        child.destroy()
    for e in palette:
        card = tk.Frame(parent, bg=CARD, highlightthickness=2,
                        highlightbackground=BORDER, cursor="hand2")
        card.pack(side="left", padx=(0, 12), pady=4)
        block = tk.Frame(card, bg=e["hex"], width=130, height=64)
        block.pack_propagate(False)
        block.pack(fill="x")
        text = tk.Label(card, text=f"{e['hex']}\n{e['share']:.1f}%\n{e['name']}",
                        bg=CARD, fg=CARD_TEXT, font=MONO, justify="left", anchor="w")
        text.pack(fill="x", padx=8, pady=6)
        for w in (card, block, text):
            w.bind("<Button-1>", lambda _, h=e["hex"]: on_copy(h))


def header(parent, text):
    tk.Label(parent, text=text, bg=BG, fg=INK, font=HEADING).pack(anchor="w", pady=(14, 4))


def buttons(bar, items):
    for text, cmd, pad in items:
        RoundButton(bar, text, cmd, width=max(90, 9 * len(text))).pack(side="left", padx=pad)


def colors_box(bar, var):
    tk.Label(bar, text="Colors", bg=BG, fg=INK, font=FONT).pack(side="left", padx=(16, 4))
    ttk.Spinbox(bar, from_=MIN_C, to=MAX_C, width=4, textvariable=var).pack(side="left")


# ---------- Tab 1: compare ----------

class CompareTab(tk.Frame):
    def __init__(self, master, app):
        super().__init__(master, bg=BG, padx=16, pady=12)
        self.app = app
        self.paths, self.images, self.palettes = [None, None], [None, None], [None, None]
        self.count = tk.StringVar(value=str(DEFAULT_C))

        bar = tk.Frame(self, bg=BG)
        bar.pack(fill="x")
        buttons(bar, [("Choose photo 1", lambda: self.choose(0), 0),
                      ("Choose photo 2 (optional)", lambda: self.choose(1), 8)])
        colors_box(bar, self.count)
        buttons(bar, [("Extract", self.extract, 8),
                      ("Show chart", self.chart, 0),
                      ("Save", self.save, 8)])

        previews = tk.Frame(self, bg=BG)
        previews.pack(pady=12)
        self.preview_labels = [tk.Label(previews, text=f"No photo {i + 1}", bg=CARD, fg=CARD_TEXT,
                                        font=FONT, width=44, height=12,
                                        highlightthickness=2, highlightbackground=BORDER)
                               for i in range(2)]
        for label in self.preview_labels:
            label.pack(side="left", padx=8)

        self.strip_label = tk.Label(self, bg=BG)
        self.strip_label.pack()
        header(self, "Dominant colors (click a card to copy its hex code)")
        self.cards = tk.Frame(self, bg=BG)
        self.cards.pack(anchor="w")
        header(self, "Comparison")
        self.summary = tk.Label(self, bg=CARD, fg=CARD_TEXT, font=MONO, justify="left",
                                anchor="w", padx=10, pady=8, highlightthickness=2,
                                highlightbackground=BORDER)
        self.summary.pack(fill="x")

    def choose(self, i):
        path = filedialog.askopenfilename(filetypes=FILE_TYPES)
        if not path:
            return
        try:
            img = load_image(path)
        except ValueError as error:
            messagebox.showerror("Not an image", str(error))
            return
        self.paths[i], self.images[i], self.palettes[i] = path, img, None
        preview = img.copy()
        preview.thumbnail(PREVIEW_SIZE)
        show_image(self.preview_labels[i], preview)
        self.app.set_status(f"Loaded {os.path.basename(path)}")

    def extract(self):
        if self.images[0] is None:
            messagebox.showwarning("No photo", "Choose photo 1 first.")
            return
        n = read_count(self.count)
        if n is None:
            messagebox.showwarning("Colors", f"Enter a whole number from {MIN_C} to {MAX_C}.")
            return
        self.palettes = [find_palette(list(shrink(img).getdata()), n) if img else None
                         for img in self.images]

        show_image(self.strip_label, swatch_strip(self.palettes[0], STRIP_W, STRIP_H))
        build_cards(self.cards, self.palettes[0], self.app.copy_to_clipboard)

        p1, p2 = self.palettes
        lines = [f"Photo 1 tones: {', '.join(sorted({e['name'] for e in p1}))}"]
        if p2:
            lines.append(f"Photo 2 tones: {', '.join(sorted({e['name'] for e in p2}))}")
            matches = compare(p1, p2)
            lines.append("Close matches:" if matches else "No close color matches.")
            lines += [f"   {a['hex']} (photo 1)  ~  {b['hex']} (photo 2)   distance {d:.0f}"
                      for a, b, d in matches]
            shared = {e["name"] for e in p1} & {e["name"] for e in p2}
            lines.append("Shared tones: " + (", ".join(sorted(shared)) or "none"))
        else:
            lines.append("Choose photo 2 to see a comparison.")
        self.summary.configure(text="\n".join(lines))
        self.app.set_status("Palette extracted")

    def chart(self):
        if self.palettes[0] is None:
            messagebox.showwarning("Nothing to chart", "Extract a palette first.")
            return
        for img, pal, name in zip(self.images, self.palettes, ["Photo 1", "Photo 2"]):
            if pal:
                show_chart(img, pal, f"{name} colors")

    def save(self):
        if self.palettes[0] is None:
            messagebox.showwarning("Nothing to save", "Extract a palette first.")
            return
        for path, pal in zip(self.paths, self.palettes):
            if path and pal:
                base = os.path.splitext(path)[0]
                save_text(pal, base + "_palette.txt")
                swatch_strip(pal, STRIP_W, STRIP_H).save(base + "_palette.png")
        messagebox.showinfo("Saved", "Palette files were saved next to your photos.")


# ---------- Tab 2: mood board ----------

class MoodBoardTab(tk.Frame):
    def __init__(self, master, app):
        super().__init__(master, bg=BG, padx=16, pady=12)
        self.app = app
        self.paths, self.board, self.palette = [], None, None
        self.count = tk.StringVar(value=str(DEFAULT_C))

        bar = tk.Frame(self, bg=BG)
        bar.pack(fill="x")
        buttons(bar, [("Add photos", self.add_photos, 0), ("Clear", self.clear, 8)])
        colors_box(bar, self.count)
        buttons(bar, [("Build board", self.build, 8),
                      ("Show chart", self.chart, 0),
                      ("Save", self.save, 8)])

        self.listbox = tk.Listbox(self, height=4, font=FONT, relief="flat", bg=CARD, fg=CARD_TEXT,
                                  highlightthickness=2, highlightbackground=BORDER)
        self.listbox.pack(fill="x", pady=10)
        self.board_label = tk.Label(self, text="Add 2 or more photos, then build your board.",
                                    bg=CARD, fg=CARD_TEXT, font=FONT, width=100, height=12,
                                    highlightthickness=2, highlightbackground=BORDER)
        self.board_label.pack(pady=4)
        header(self, "Shared palette (click a card to copy its hex code)")
        self.cards = tk.Frame(self, bg=BG)
        self.cards.pack(anchor="w")

    def add_photos(self):
        for path in filedialog.askopenfilenames(filetypes=FILE_TYPES):
            if path not in self.paths:
                self.paths.append(path)
                self.listbox.insert("end", os.path.basename(path))

    def clear(self):
        self.paths, self.board, self.palette = [], None, None
        self.listbox.delete(0, "end")
        self.board_label.configure(image="", text="Add 2 or more photos, then build your board.")
        build_cards(self.cards, [], self.app.copy_to_clipboard)

    def build(self):
        if len(self.paths) < 2:
            messagebox.showwarning("Add more photos", "A mood board needs at least 2 photos.")
            return
        n = read_count(self.count)
        if n is None:
            messagebox.showwarning("Colors", f"Enter a whole number from {MIN_C} to {MAX_C}.")
            return
        images = []
        for path in self.paths:
            try:
                images.append(load_image(path))
            except ValueError:
                pass
        if len(images) < 2:
            messagebox.showerror("Error", "Need at least 2 valid photos.")
            return

        self.board, self.palette = build_mood_board(images, n)
        preview = self.board.copy()
        preview.thumbnail((860, 420))
        show_image(self.board_label, preview)
        build_cards(self.cards, self.palette, self.app.copy_to_clipboard)
        self.app.set_status("Mood board built")

    def chart(self):
        if self.board is None:
            messagebox.showwarning("Nothing to chart", "Build a mood board first.")
            return
        show_chart(self.board, self.palette, "Mood board palette")

    def save(self):
        if self.board is None:
            messagebox.showwarning("Nothing to save", "Build a mood board first.")
            return
        path = filedialog.asksaveasfilename(defaultextension=".png",
                                            filetypes=[("PNG image", "*.png")],
                                            initialfile="mood_board.png")
        if path:
            self.board.save(path)
            save_text(self.palette, os.path.splitext(path)[0] + "_palette.txt")
            messagebox.showinfo("Saved", f"Saved {os.path.basename(path)} and its palette text file.")


# ---------- Main window ----------

class PaletteApp(tk.Tk):
    def __init__(self):
        super().__init__()
        self.title("Pixel Pop")
        self.geometry("1000x820")
        self.configure(bg=BG)

        style = ttk.Style(self)
        style.theme_use("clam")
        style.configure("TSpinbox", font=FONT)

        tk.Label(self, text="Pixel Pop", bg=BG, fg=INK, font=TITLE).pack(anchor="w", padx=24, pady=(16, 0))
        tk.Label(self, text="Find the main colors in your photos.", bg=BG, fg=MUTED,
                 font=FONT).pack(anchor="w", padx=24)

        bar = tk.Frame(self, bg=BG)
        bar.pack(fill="x", padx=16, pady=(12, 0))
        body = tk.Frame(self, bg=BG)
        body.pack(fill="both", expand=True, padx=16, pady=(0, 12))

        self.pages, self.tabs = {}, {}
        for name, page in [("Compare photos", CompareTab), ("Mood board", MoodBoardTab)]:
            self.pages[name] = page(body, self)
            label = tk.Label(bar, text=name, cursor="hand2", bd=0)
            label.pack(side="left", padx=(0, 6), anchor="s")
            label.bind("<Button-1>", lambda e, n=name: self.select(n))
            self.tabs[name] = label

        self.status = tk.StringVar(value="Ready")
        tk.Label(self, textvariable=self.status, bg=BG, fg=MUTED, font=FONT,
                 anchor="w").pack(fill="x", padx=24, pady=(0, 8))

        self.select("Compare photos")

    def select(self, name):
        for tab_name, label in self.tabs.items():
            active = tab_name == name
            label.configure(
                text=tab_name,
                font=TAB_ON if active else TAB_OFF,
                bg=CARD if active else TAB_OFF_BG,
                fg=CARD_TEXT if active else INK,
                padx=22 if active else 12,
                pady=10 if active else 5,
            )
        for page in self.pages.values():
            page.pack_forget()
        self.pages[name].pack(fill="both", expand=True)

    def set_status(self, text):
        self.status.set(text)

    def copy_to_clipboard(self, hex_code):
        self.clipboard_clear()
        self.clipboard_append(hex_code)
        self.set_status(f"Copied {hex_code} to clipboard")


if __name__ == "__main__":
    PaletteApp().mainloop()
