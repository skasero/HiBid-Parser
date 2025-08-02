import argparse
import time
from datetime import datetime
from bs4 import BeautifulSoup
from requests_html import HTMLSession
from requests.exceptions import RequestException


MAIN_URL = "https://hibid.com"
URL = "https://hibid.com/catalog/554957/public-auction-reno-316-06-16-2024--sunday-"
PAGE = "?apage="


def fetch_page_content(session, url, headers=None, max_retries=1):
    for attempt in range(max_retries):
        try:
            r = session.get(url, headers=headers, timeout=10)
            r.html.render(wait=4, sleep=3, timeout=10)
            content = r.html.html
            return content
        except Exception as e:
            print(f"Attempt {attempt + 1} failed: {e}")
            time.sleep(2)  # Wait before retrying
    return None


def read_pages(url=URL):
    data = []
    running = True
    total_tiles = 0
    count = 1
    session = HTMLSession()
    headers = {
        'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/119.0.0.0 Safari/537.36',
        'Cache-Control': 'no-cache'
    }

    while running:
        page_url = url + PAGE + str(count)
        count += 1
        print(f"Reading: {page_url}")
        try:
            content = fetch_page_content(session, page_url, headers=headers)
            if content is None:
                print(f"Failed to fetch {page_url}")
                session.close()
                exit(1)
            soup = BeautifulSoup(content, "lxml")
            tiles = soup.find_all("app-lot-tile")
            total_tiles += len(tiles)
            for tile in tiles:
                sub_data = {}
                title = tile.find("h2", class_="lot-title").text
                if "More Lots Will Be" in title:
                    running = False
                    break
                lot = tile.find("span", class_="text-primary")
                new_url = tile.find("a", class_="lot-link").get("href")
                link_url = MAIN_URL + new_url
                image_src = tile.find("img", class_="lot-thumbnail").get("src")
                bid = tile.find("span", class_="d-sm-inline").text
                sub_data["lot"] = lot
                sub_data["title"] = title
                sub_data["url"] = link_url
                sub_data["image"] = image_src
                sub_data["bid"] = bid
                data.append(sub_data)

            if (len(tiles) == 0):
                break
                try:
                    end = soup.find("div", class_="pt-3 mx-auto text-center fw-bold").text
                    if "Please check back soon" in end:
                        break
                except AttributeError:
                    print("Check if website is down")
                break
        except (RequestException, TimeoutError) as e:
            print(f"Failed to fetch {page_url}: {str(e)}")
            session.close()
            exit(1)

    session.close()
    return data


def generate_html(data):
    rows = []
    dt_string = datetime.now().strftime("%Y/%m/%d %H:%M:%S")
    with open('template.html', 'r') as file:
        html = file.read()
    with open('table.txt', 'r') as file:
        table_template = file.read()
    for item in data:
        row = table_template.format(lot=item["lot"],
                                    title=item["title"],
                                    image=item["image"],
                                    bid=item["bid"],
                                    url=item["url"])
        rows.append(row)

    output = html.format(date=dt_string,
                         insert="\n".join(rows))

    with open('final.html', 'w') as file:
        file.write(output)


if __name__ == "__main__":
    parser = argparse.ArgumentParser()
    parser.add_argument('-u', '--url', help='URL of Bid Website', type=str)
    args = parser.parse_args()
    data = read_pages(args.url)
    print(f"Found {len(data)} items")
    generate_html(data)
