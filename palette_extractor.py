"""
Color Palette Extractor
Input:  one or two photo files (JPG or PNG) and a number of colors (3-8)
Output: dominant colors as hex codes, text files, swatch images,
        and (optionally) the colors two photos have in common
"""
import os
from PIL import Image
from sklearn.cluster import KMeans
import matplotlib.pyplot as plt

RESIZE_TO = (100, 100)    # shrink photos so they run fast
MIN_COLORS = 3
MAX_COLORS = 8
DEFAULT_COLORS = 5
SIMILAR_THRESHOLD = 40    # colors this close (RGB distance) count as "shared"


def load_image(path):
    """Open an image, convert it to RGB, and shrink it. Returns None on error."""
    try:
        img = Image.open(path).convert("RGB")
    except FileNotFoundError:
        print(f"Error: '{path}' was not found.")
        return None
    except OSError:
        print("Error: that file is not a valid image.")
        return None
    img.thumbnail(RESIZE_TO)
    return img


def get_pixels(img):
    """Turn the image into a list of (red, green, blue) tuples."""
    return list(img.getdata())


def ask_num_colors():
    """Ask how many colors to find. Pressing Enter uses the default."""
    while True:
        answer = input(f"How many colors? ({MIN_COLORS}-{MAX_COLORS}, Enter for {DEFAULT_COLORS}): ").strip()
        if answer == "":
            return DEFAULT_COLORS
        if answer.isdigit() and MIN_COLORS <= int(answer) <= MAX_COLORS:
            return int(answer)
        print(f"Please enter a whole number from {MIN_COLORS} to {MAX_COLORS}.")


def rgb_to_hex(color):
    """Convert an (r, g, b) tuple into a hex string like '#1A2B3C'."""
    r, g, b = color
    return "#{:02X}{:02X}{:02X}".format(r, g, b)


def describe_color(color):
    """Give a rough name to a color based on brightness and its strongest channel."""
    r, g, b = color
    brightness = (r + g + b) / 3
    if brightness < 50:
        return "Dark"
    elif brightness > 200:
        return "Light"
    elif r >= g and r >= b:
        return "Warm (red-ish)"
    elif g >= r and g >= b:
        return "Green-ish"
    else:
        return "Cool (blue-ish)"


def color_distance(c1, c2):
    """Straight-line distance between two colors in RGB space."""
    return sum((a - b) ** 2 for a, b in zip(c1, c2)) ** 0.5


def find_palette(pixels, num_colors):
    """Group similar pixels with k-means and return a list of color dictionaries."""
    model = KMeans(n_clusters=num_colors, n_init=10, random_state=0)
    model.fit(pixels)

    # Count how many pixels fall into each group
    counts = {}
    for label in model.labels_:
        counts[label] = counts.get(label, 0) + 1

    total = len(pixels)
    palette = []
    for i, center in enumerate(model.cluster_centers_):
        color = tuple(int(v) for v in center)
        palette.append({
            "color": color,
            "hex": rgb_to_hex(color),
            "share": counts.get(i, 0) / total * 100,
            "name": describe_color(color),
        })

    # Show the most common color first
    palette.sort(key=lambda entry: entry["share"], reverse=True)
    return palette


def print_palette(palette):
    """Print the palette and the set of tones it contains."""
    print("\nDominant colors:")
    for number, entry in enumerate(palette, start=1):
        print(f"{number}. {entry['hex']}  {entry['share']:.1f}%  ({entry['name']})")

    tones = {entry["name"] for entry in palette}
    print("Tones in this photo:", ", ".join(sorted(tones)))
    return tones


def compare_palettes(palette_a, palette_b, threshold=SIMILAR_THRESHOLD):
    """For each color in palette A, find the closest color in palette B.
    Pairs closer than the threshold count as shared. Returns a list of matches."""
    matches = []
    for a in palette_a:
        closest = min(palette_b, key=lambda b: color_distance(a["color"], b["color"]))
        distance = color_distance(a["color"], closest["color"])
        if distance <= threshold:
            matches.append((a, closest, distance))
    return matches


def print_comparison(palette_a, palette_b, tones_a, tones_b):
    """Print the shared colors and shared tones between two photos."""
    print("\n=== Comparison ===")
    matches = compare_palettes(palette_a, palette_b)
    if matches:
        print("Shared colors (close matches):")
        for a, b, distance in matches:
            print(f"  {a['hex']} (photo 1)  ~  {b['hex']} (photo 2)  distance {distance:.0f}")
    else:
        print("No close color matches between the two photos.")

    common_tones = tones_a & tones_b
    if common_tones:
        print("Tones both photos share:", ", ".join(sorted(common_tones)))
    else:
        print("The two photos share no tones.")


def save_palette_text(palette, path):
    """Write the hex codes and percentages to a text file."""
    with open(path, "w") as f:
        for entry in palette:
            f.write(f"{entry['hex']}  {entry['share']:.1f}%  {entry['name']}\n")


def plot_palette(img, palette, out_path):
    """Show the original photo next to a bar chart of the colors, and save it."""
    fig, (ax1, ax2) = plt.subplots(1, 2, figsize=(10, 5))

    ax1.imshow(img)
    ax1.set_title("Original (resized)")
    ax1.axis("off")

    labels = [entry["hex"] for entry in palette]
    shares = [entry["share"] for entry in palette]
    # matplotlib wants colors as values from 0 to 1
    colors = [tuple(v / 255 for v in entry["color"]) for entry in palette]
    ax2.bar(labels, shares, color=colors, edgecolor="black")
    ax2.set_title("Dominant colors (% of photo)")
    ax2.set_ylabel("Share of pixels (%)")

    fig.tight_layout()
    fig.savefig(out_path)
    plt.show()
    plt.close(fig)


def analyze_image(path, num_colors):
    """Load a photo and build its palette. Returns (img, palette, tones) or None."""
    img = load_image(path)
    if img is None:
        return None
    palette = find_palette(get_pixels(img), num_colors)
    tones = print_palette(palette)
    return img, palette, tones


def save_results(img, palette, path):
    """Save the text and image outputs for one photo."""
    base = os.path.splitext(os.path.basename(path))[0]
    save_palette_text(palette, base + "_palette.txt")
    plot_palette(img, palette, base + "_palette.png")
    print(f"Saved {base}_palette.txt and {base}_palette.png")


def main():
    print("=== Color Palette Extractor ===")
    while True:
        path = input("\nImage path (or 'q' to quit): ").strip()
        if path.lower() == "q":
            print("Goodbye!")
            break

        num_colors = ask_num_colors()
        first = analyze_image(path, num_colors)
        if first is None:
            continue
        img, palette, tones = first
        save_results(img, palette, path)

        # Extension 3: optionally compare with a second photo
        second_path = input("\nSecond photo to compare (Enter to skip): ").strip()
        if second_path:
            second = analyze_image(second_path, num_colors)
            if second is not None:
                img2, palette2, tones2 = second
                save_results(img2, palette2, second_path)
                print_comparison(palette, palette2, tones, tones2)


if __name__ == "__main__":
    main()