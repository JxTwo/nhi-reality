import requests
from bs4 import BeautifulSoup
from django.core.management.base import BaseCommand


class Command(BaseCommand):
    help = "Inspect <a> tags on Liberation Times homepage for debugging selectors"

    def handle(self, *args, **kwargs):
        url = "https://liberationtimes.com"
        self.stdout.write(f"Fetching: {url}")
        resp = requests.get(url)

        if resp.status_code != 200:
            self.stderr.write(f"Failed to fetch page: {resp.status_code}")
            return

        soup = BeautifulSoup(resp.text, "html.parser")
        anchors = soup.find_all("a", href=True)

        self.stdout.write(f"Found {len(anchors)} <a> tags. Printing href + class:\n")

        for tag in anchors:
            href = tag.get("href")
            class_attr = tag.get("class")
            text = tag.get_text(strip=True)
            self.stdout.write(f"Link: {href}\n  Text: {text}\n  Class: {class_attr}\n")
