import argparse
from datetime import datetime
from bs4 import BeautifulSoup
from requests_html import HTMLSession

MAIN_URL = "https://hibid.com"
URL = "https://hibid.com/catalog/554957/public-auction-reno-316-06-16-2024--sunday-"
PAGE = "?apage="


def fetch_page_content(session: HTMLSession, url: str, headers: dict | None = None) -> str:
    """
    Fetch page content using requests_html WITHOUT forcing JS rendering.

    Rationale:
    - In practice, the HiBid catalog pages return all required lot data in the initial HTML.
    - JS rendering via pyppeteer is fragile and not needed for this target.
    - We keep a short network timeout so each page loads quickly.
    """
    r = session.get(url, headers=headers, timeout=8)
    return r.html.html


def read_pages(url: str = URL, max_pages: int | None = None):
    """
    Read catalog pages and extract lot data from static HTML.

    Behavior:
    - If max_pages is None: read until no tiles or 'More Lots Will Be' marker (all pages).
    - If max_pages is an int: limit to that many pages (e.g. for testing).
    - No JS rendering; avoids pyppeteer/Chromium issues entirely.
    - Stops early if:
        - No tiles on a page, or
        - A tile title contains 'More Lots Will Be'.
    """
    data: list[dict] = []
    running = True
    total_tiles = 0
    page_num = 1

    session = HTMLSession()
    headers = {
        "User-Agent": (
            "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 "
            "(KHTML, like Gecko) Chrome/119.0.0.0 Safari/537.36"
        ),
        "Cache-Control": "no-cache",
    }

    try:
        while running:
            if max_pages is not None and page_num > max_pages:
                break

            page_url = f"{url}{PAGE}{page_num}"
            print(f"Reading: {page_url}")
            page_num += 1

            content = fetch_page_content(session, page_url, headers=headers)
            if not content:
                print(f"[INFO] Empty content for {page_url}, stopping.")
                break

            soup = BeautifulSoup(content, "lxml")
            tiles = soup.find_all("app-lot-tile")
            print(f"Found {len(tiles)} tiles on this page.")
            total_tiles += len(tiles)

            if not tiles:
                # No tiles likely indicates end of catalog.
                break

            for tile in tiles:
                title_el = tile.find("h2", class_="lot-title")
                if not title_el:
                    continue

                title = title_el.get_text(strip=True)

                # Stop condition when HiBid shows placeholder tiles.
                if "More Lots Will Be" in title:
                    running = False
                    break

                lot_el = tile.find("span", class_="text-primary")
                lot = lot_el.get_text(strip=True) if lot_el else ""

                link_el = tile.find("a", class_="lot-link")
                if not link_el or not link_el.get("href"):
                    continue
                link_url = MAIN_URL + link_el.get("href")

                img_el = tile.find("img", class_="lot-thumbnail")
                image_src = img_el.get("src") if img_el else ""

                bid_el = tile.find("span", class_="d-sm-inline")
                bid = bid_el.get_text(strip=True) if bid_el else ""

                data.append(
                    {
                        "lot": lot,
                        "title": title,
                        "url": link_url,
                        "image": image_src,
                        "bid": bid,
                    }
                )

        print(f"Total tiles across processed pages: {total_tiles}")
        return data
    finally:
        session.close()


def generate_html(data):
    rows = []
    dt_string = datetime.now().strftime("%Y/%m/%d %H:%M:%S")
    with open("template.html", "r") as file:
        html = file.read()
    with open("table.txt", "r") as file:
        table_template = file.read()
    for item in data:
        row = table_template.format(
            lot=item["lot"],
            title=item["title"],
            image=item["image"],
            bid=item["bid"],
            url=item["url"],
        )
        rows.append(row)

    output = html.format(date=dt_string, insert="\n".join(rows))

    with open("final.html", "w") as file:
        file.write(output)


if __name__ == "__main__":
    parser = argparse.ArgumentParser()
    parser.add_argument(
        "-u",
        "--url",
        help="URL of Bid Website",
        type=str,
        default=URL,
    )
    parser.add_argument(
        "-p",
        "--pages",
        help=(
            "Max number of pages to scrape. "
            "If omitted, all pages are processed until no more lots are found."
        ),
        type=int,
        default=None,
    )
    args = parser.parse_args()

    data = read_pages(args.url, max_pages=args.pages)
    print(f"Found {len(data)} items")
    generate_html(data)
