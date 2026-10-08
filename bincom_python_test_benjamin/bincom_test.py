import os
import re
import random
import statistics
import sys
from collections import Counter
from urllib.request import urlopen
from html.parser import HTMLParser


def load_html(source):
    if source.startswith("http://") or source.startswith("https://"):
        return urlopen(source).read().decode("utf-8", errors="ignore")
    with open(source, encoding="utf-8", errors="ignore") as f:
        return f.read()


class ColourTableParser(HTMLParser):
    def __init__(self):
        super().__init__()
        self.rows = []
        self.in_cell = False

    def handle_starttag(self, tag, attrs):
        if tag == "tr":
            self.rows.append([])
        elif tag == "td":
            self.in_cell = True
            self.rows[-1].append("")

    def handle_endtag(self, tag):
        if tag == "td":
            self.in_cell = False

    def handle_data(self, data):
        if self.in_cell:
            self.rows[-1][-1] += data


def extract_colors(html):
    """Each table row looks like: <tr><td>MONDAY</td><td>GREEN, BLUE, ...</td></tr>"""
    parser = ColourTableParser()
    parser.feed(html)

    days = {"MONDAY", "TUESDAY", "WEDNESDAY", "THURSDAY", "FRIDAY"}
    colors = []
    for cells in parser.rows:
        if len(cells) < 2 or cells[0].strip().upper() not in days:
            continue
        for c in cells[1].split(","):
            c = c.strip().upper()
            if c:
                colors.append(c)
    return colors



def analyse(colors):
    freq = Counter(colors)
    total = len(colors)
    counts = list(freq.values())

    mean_freq = sum(counts) / len(counts)
    mean_color = min(freq, key=lambda c: abs(freq[c] - mean_freq))
    print(f"1. Mean frequency = {mean_freq:.2f}; mean colour = {mean_color}")

    mode_color, mode_count = freq.most_common(1)[0]
    print(f"2. Most worn colour = {mode_color} ({mode_count} times)")

    ordered = sorted(freq.items(), key=lambda kv: (kv[1], kv[0]))
    median_color = ordered[len(ordered) // 2][0]
    print(f"3. Median frequency = {statistics.median(counts)}; "
          f"median colour = {median_color}")

    print(f"4. Variance of colour frequencies = {statistics.pvariance(counts):.4f}")

    p_red = freq.get("RED", 0) / total
    print(f"5. P(red) = {freq.get('RED', 0)}/{total} = {p_red:.4f}")
    return freq




def save_to_postgres(freq):
    import psycopg2
    conn = psycopg2.connect(
        host=os.getenv("PGHOST", "localhost"),
        port=os.getenv("PGPORT", "5432"),
        dbname=os.getenv("PGDATABASE", "postgres"),
        user=os.getenv("PGUSER", "postgres"),
        password=os.getenv("PGPASSWORD", ""),
    )
    with conn, conn.cursor() as cur:
        cur.execute(
            """CREATE TABLE IF NOT EXISTS colour_frequency (
                   colour TEXT PRIMARY KEY,
                   frequency INTEGER NOT NULL)"""
        )
        for colour, n in freq.items():
            cur.execute(
                """INSERT INTO colour_frequency (colour, frequency)
                   VALUES (%s, %s)
                   ON CONFLICT (colour) DO UPDATE SET frequency = EXCLUDED.frequency""",
                (colour, n),
            )
    conn.close()
    print("6. Colours and frequencies saved to table 'colour_frequency'.")



def recursive_search(numbers, target, index=0):
    """Return the index of target in numbers, or -1 if not found."""
    if index >= len(numbers):
        return -1
    if numbers[index] == target:
        return index
    return recursive_search(numbers, target, index + 1)


def q7():
    nums = [4, 8, 15, 16, 23, 42, 7, 19]
    print("7. List:", nums)
    try:
        target = int(input("   Enter a number to search for: "))
    except ValueError:
        print("   Please enter a valid integer.")
        return
    pos = recursive_search(nums, target)
    print(f"   Found at index {pos}" if pos != -1 else "   Not found in the list")


def q8():
    binary = "".join(random.choice("01") for _ in range(4))
    print(f"8. Random binary number: {binary} -> base 10: {int(binary, 2)}")



def q9():
    a, b, total = 0, 1, 0
    for _ in range(50):
        total += a
        a, b = b, a + b
    print(f"9. Sum of the first 50 Fibonacci numbers (0, 1, 1, 2, ...) = {total}")



def detect_triple_ones(bits):
    """Output 1 at the position where the third consecutive 1 appears, else 0."""
    out = []
    run = 0
    for b in bits:
        run = run + 1 if b == "1" else 0
        out.append("1" if run == 3 else "0")
    return "".join(out)


def q10():
    sample_in = "0101101011101011011101101000111"
    expected = "0000000000100000000100000000001"
    result = detect_triple_ones(sample_in)
    print("Extra: binary sequence from the page")
    print("   Input   :", sample_in)
    print("   Output  :", result)
    print("   Expected:", expected)
    print("   Matches expected output:", result == expected)


if __name__ == "__main__":
    if len(sys.argv) < 2:
        sys.exit("Usage: python bincom_test.py <url-or-path-to-html>")

    colors = extract_colors(load_html(sys.argv[1]))
    print(f"Parsed {len(colors)} colour entries, {len(set(colors))} distinct colours\n")
    freq = analyse(colors)
    for c, n in sorted(freq.items(), key=lambda kv: -kv[1]):
        print(f"   {c:<10} {n}")

    try:
        save_to_postgres(freq)
    except Exception as e:
        print("6. Could not save to PostgreSQL:", e)

    q7()
    q8()
    q9()
    q10()