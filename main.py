import argparse
from datetime import datetime
from bs4 import BeautifulSoup
from requests_html import HTMLSession


MAIN_URL = "https://publicauctionreno.hibid.com"
URL = "https://publicauctionreno.hibid.com/catalog/554957/public-auction-reno-316-06-16-2024--sunday-"
PAGE = "?apage="


def read_pages(url=URL):
    data = []
    running = True
    total_tiles = 0
    count = 1
    while running:
        page_url = url + PAGE + str(count)
        count += 1
        session = HTMLSession()
        print(f"Reading: {page_url}")
        r = session.get(page_url)
        r.html.render(sleep=2)
        content = r.html.html
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
            end = soup.find("div", class_="text-center fw-bold mx-auto ng-star-inserted").text
            if "Please check back soon" in end:
                break

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
