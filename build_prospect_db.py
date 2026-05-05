from __future__ import annotations

import argparse
import csv
import hashlib
import html
import math
import re
import ssl
import sys
import time
from collections import Counter, defaultdict
from concurrent.futures import ThreadPoolExecutor, as_completed
from dataclasses import dataclass, field
from html.parser import HTMLParser
from pathlib import Path
from typing import Iterable
from urllib.parse import parse_qs, quote_plus, urlencode, urljoin, urlparse
from urllib.request import Request, urlopen

import pandas as pd


BASE_DIR = Path(__file__).resolve().parent
CACHE_DIR = BASE_DIR / "cache"
OUTPUT_DIR = BASE_DIR / "outputs"

SEARCH_URL = (
    "https://www.texasbar.com/AM/Template.cfm"
    "?Section=Find_A_Lawyer&Template=/CustomSource/MemberDirectory/Result_form_client.cfm"
)
DETAIL_URL = "https://www.texasbar.com/attorneys/member.cfm?id={contact_id}"
DEFAULT_HEADERS = {
    "User-Agent": (
        "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) "
        "AppleWebKit/537.36 (KHTML, like Gecko) Chrome/122.0.0.0 Safari/537.36"
    )
}
SSL_CONTEXT = ssl._create_unverified_context()
TIMEOUT = 40
RESULTS_PER_PAGE = 25

PRIORITY_CITIES = ["Houston", "Dallas", "Austin", "San Antonio"]
TITLE_ORDER = {
    "Founder": 0,
    "Owner": 1,
    "Managing Attorney": 2,
    "Principal Attorney": 3,
    "Partner": 4,
    "Attorney at Law": 5,
}
GENERIC_EMAIL_PREFIXES = (
    "info",
    "contact",
    "hello",
    "intake",
    "office",
    "admin",
    "consult",
    "consultation",
    "appointments",
    "legal",
    "mail",
)
DISALLOWED_EMAIL_DOMAINS = {
    "example.com",
    "findanimmigrationattorney.com",
    "godaddy.com",
    "latofonts.com",
    "sentry-next.wixpress.com",
    "sentry.wixpress.com",
    "tbls.org",
    "wixpress.com",
}
DISALLOWED_EMAIL_LOCALS = {"demo", "example", "filler", "sample", "test", "you"}
CONSUMER_EMAIL_DOMAINS = {
    "aol.com",
    "att.net",
    "gmail.com",
    "hotmail.com",
    "icloud.com",
    "live.com",
    "me.com",
    "msn.com",
    "outlook.com",
    "protonmail.com",
    "sbcglobal.net",
    "verizon.net",
    "yahoo.com",
    "ymail.com",
}
HIGH_VOLUME_SUBPRACTICES = (
    "asylum",
    "deport",
    "removal",
    "naturalization",
    "citizenship",
    "uscis",
    "family immigration",
    "green card",
    "visa",
    "humanitarian",
    "waiver",
)
LOW_FIT_DOMAINS = {
    "justice.gov",
    "uscis.gov",
    "state.gov",
    "texasbar.com",
}
CONTACT_PAGE_KEYWORDS = (
    "contact",
    "consulta",
    "consultation",
    "book",
    "schedule",
    "team",
    "attorney",
    "lawyer",
    "about",
    "our-firm",
    "our-team",
)
CITY_FIXUPS = {
    "Mcallen": "McAllen",
}
BRAND_TOKEN_STOPWORDS = {
    "abogado",
    "abogados",
    "and",
    "associates",
    "attorney",
    "attorneys",
    "firm",
    "group",
    "immigration",
    "law",
    "legal",
    "office",
    "offices",
    "pc",
    "pllc",
    "the",
}


def ensure_dirs() -> None:
    CACHE_DIR.mkdir(parents=True, exist_ok=True)
    OUTPUT_DIR.mkdir(parents=True, exist_ok=True)


def slugify(value: str) -> str:
    value = html.unescape(value or "")
    value = value.lower()
    value = re.sub(r"[^a-z0-9]+", " ", value)
    return re.sub(r"\s+", " ", value).strip()


def collapse_ws(value: str) -> str:
    return re.sub(r"\s+", " ", value or "").strip()


def normalize_city(value: str) -> str:
    cleaned = collapse_ws(value)
    if not cleaned:
        return ""
    titled = cleaned.title()
    return CITY_FIXUPS.get(titled, titled)


def strip_tags(value: str) -> str:
    value = re.sub(r"(?is)<script.*?>.*?</script>", " ", value or "")
    value = re.sub(r"(?is)<style.*?>.*?</style>", " ", value)
    value = re.sub(r"(?i)<br\s*/?>", "\n", value)
    value = re.sub(r"(?is)<[^>]+>", " ", value)
    value = html.unescape(value)
    return collapse_ws(value.replace("\xa0", " "))


def clean_html_text(value: str) -> str:
    return collapse_ws(html.unescape(value or "").replace("\xa0", " "))


def strip_url(url: str) -> str:
    if not url:
        return ""
    parsed = urlparse(url.strip())
    if not parsed.scheme:
        url = "https://" + url.lstrip("/")
        parsed = urlparse(url)
    path = parsed.path or "/"
    if path != "/":
        path = path.rstrip("/")
    return parsed._replace(fragment="", query="", path=path).geturl()


def get_domain(url: str) -> str:
    if not url:
        return ""
    parsed = urlparse(strip_url(url))
    netloc = parsed.netloc.lower()
    if netloc.startswith("www."):
        netloc = netloc[4:]
    return netloc


def same_domain(url: str, root_url: str) -> bool:
    return get_domain(url) == get_domain(root_url)


def parse_name(full_name: str) -> tuple[str, str]:
    tokens = [t for t in re.split(r"\s+", full_name.strip()) if t]
    suffixes = {"jr", "jr.", "sr", "sr.", "ii", "iii", "iv"}
    while tokens and tokens[-1].lower().rstrip(".") in suffixes:
        tokens.pop()
    if not tokens:
        return "", ""
    first = tokens[0]
    last = tokens[-1]
    return first, re.sub(r"[^A-Za-z'-]", "", last)


def domain_from_email(email: str) -> str:
    parts = email.split("@", 1)
    return parts[1].lower() if len(parts) == 2 else ""


def domain_root(value: str) -> str:
    domain = value.lower().strip()
    if domain.startswith("www."):
        domain = domain[4:]
    return domain.split(".", 1)[0]


def extract_brand_tokens(*values: str) -> set[str]:
    tokens: set[str] = set()
    for value in values:
        for token in slugify(value).split():
            if len(token) >= 4 and token not in BRAND_TOKEN_STOPWORDS:
                tokens.add(token)
    return tokens


def is_usable_business_email(email: str, source_url: str, site_domain: str) -> bool:
    normalized = email.strip().lower()
    if "@" not in normalized:
        return False
    local, raw_domain = normalized.split("@", 1)
    email_domain = raw_domain[4:] if raw_domain.startswith("www.") else raw_domain
    if email_domain.endswith((".gif", ".jpeg", ".jpg", ".png", ".svg", ".webp")):
        return False
    if local in DISALLOWED_EMAIL_LOCALS:
        return False
    if re.fullmatch(r"[0-9a-f]{24,}", local):
        return False
    if email_domain in DISALLOWED_EMAIL_DOMAINS:
        return False
    if any(token in email_domain for token in ("example.", "wixpress", "godaddy", "latofonts")):
        return False
    if local.startswith("sentry") or "sentry" in email_domain:
        return False
    if source_url and get_domain(source_url) not in {site_domain, ""}:
        return False
    return True


def is_confident_ready_email(email: str, site_domain: str, firm_name: str, decision_maker_name: str) -> bool:
    email_domain = domain_from_email(email)
    if not email_domain:
        return False
    normalized_email_domain = email_domain[4:] if email_domain.startswith("www.") else email_domain
    normalized_site_domain = site_domain[4:] if site_domain.startswith("www.") else site_domain
    if normalized_email_domain == normalized_site_domain:
        return True
    if normalized_email_domain in CONSUMER_EMAIL_DOMAINS:
        return True

    email_root = domain_root(normalized_email_domain)
    site_root = domain_root(normalized_site_domain)
    if email_root and site_root and min(len(email_root), len(site_root)) >= 5:
        if email_root in site_root or site_root in email_root:
            return True

    brand_tokens = extract_brand_tokens(firm_name, decision_maker_name)
    return any(token in email_root for token in brand_tokens)


def choose_best_email(email_hits: list[tuple[str, str]], site_domain: str) -> tuple[str, str, str]:
    if not email_hits:
        return "", "", ""

    ranked = []
    seen = set()
    for email, source_url in email_hits:
        key = email.lower()
        if key in seen:
            continue
        seen.add(key)
        if not is_usable_business_email(email, source_url, site_domain):
            continue
        local = email.split("@", 1)[0].lower()
        email_domain = domain_from_email(email)
        generic = any(local.startswith(prefix) for prefix in GENERIC_EMAIL_PREFIXES)
        same = email_domain == site_domain
        contact_bonus = int("contact" in source_url.lower())
        score = (
            100 * int(same),
            20 * int(generic),
            10 * contact_bonus,
            -len(local),
            email.lower(),
        )
        ranked.append((score, email, source_url))
    ranked.sort(reverse=True)
    if not ranked:
        return "", "", ""
    primary = ranked[0]
    secondary = ranked[1] if len(ranked) > 1 else ("", "", "")
    return primary[1], secondary[1] if secondary else "", primary[2]


def candidate_names_for_site(entries: list[ResultEntry], best_entry: ResultEntry, detail: DetailRecord) -> list[str]:
    target_firm = slugify(detail.firm_name or best_entry.firm_name)
    names: list[str] = []
    for entry in entries:
        entry_firm = slugify(entry.firm_name)
        if target_firm and entry_firm and entry_firm != target_firm:
            continue
        if entry.attorney_name and entry.attorney_name not in names:
            names.append(entry.attorney_name)
    for fallback_name in [detail.attorney_name, best_entry.attorney_name]:
        if fallback_name and fallback_name not in names:
            names.insert(0, fallback_name)
    return names


class SimplePageParser(HTMLParser):
    def __init__(self) -> None:
        super().__init__()
        self.links: list[tuple[str, str]] = []
        self.text_chunks: list[str] = []
        self.title_parts: list[str] = []
        self.meta_description = ""
        self.current_href = ""
        self.current_link_text: list[str] = []
        self.in_title = False

    def handle_starttag(self, tag: str, attrs: list[tuple[str, str | None]]) -> None:
        attr_map = {k.lower(): (v or "") for k, v in attrs}
        if tag.lower() == "a":
            self.current_href = attr_map.get("href", "")
            self.current_link_text = []
        elif tag.lower() == "title":
            self.in_title = True
        elif tag.lower() == "meta":
            name = attr_map.get("name", "").lower()
            prop = attr_map.get("property", "").lower()
            if name == "description" or prop == "og:description":
                content = clean_html_text(attr_map.get("content", ""))
                if content and not self.meta_description:
                    self.meta_description = content

    def handle_endtag(self, tag: str) -> None:
        if tag.lower() == "a":
            text = collapse_ws(" ".join(self.current_link_text))
            self.links.append((self.current_href, text))
            self.current_href = ""
            self.current_link_text = []
        elif tag.lower() == "title":
            self.in_title = False

    def handle_data(self, data: str) -> None:
        if not data or not data.strip():
            return
        cleaned = clean_html_text(data)
        if cleaned:
            self.text_chunks.append(cleaned)
            if self.current_href:
                self.current_link_text.append(cleaned)
            if self.in_title:
                self.title_parts.append(cleaned)

    @property
    def title(self) -> str:
        return collapse_ws(" ".join(self.title_parts))

    @property
    def text(self) -> str:
        return collapse_ws(" ".join(self.text_chunks))


def cache_key(method: str, url: str, data: dict[str, str] | None) -> str:
    payload = urlencode(sorted((data or {}).items()), doseq=True)
    return hashlib.sha1(f"{method}|{url}|{payload}".encode("utf-8")).hexdigest()


def fetch_html(url: str, data: dict[str, str] | None = None, force: bool = False) -> str:
    method = "POST" if data else "GET"
    key = cache_key(method, url, data)
    path = CACHE_DIR / f"{key}.html"
    if path.exists() and not force:
        return path.read_text(encoding="utf-8")

    payload = urlencode(data or {}, doseq=True).encode("utf-8") if data else None
    request = Request(url, data=payload, headers=DEFAULT_HEADERS, method=method)
    for attempt in range(3):
        try:
            with urlopen(request, timeout=TIMEOUT, context=SSL_CONTEXT) as response:
                raw = response.read()
                charset = response.headers.get_content_charset() or "utf-8"
            text = raw.decode(charset, errors="ignore")
            path.write_text(text, encoding="utf-8")
            return text
        except Exception:
            if attempt == 2:
                raise
            time.sleep(1 + attempt)
    raise RuntimeError(f"Failed to fetch {url}")


def fetch_result_page(offset: int = 0) -> str:
    data = {"Submitted": "1", "ShowPrinter": "1", "Find": "1", "PracticeArea": "44"}
    if offset:
        data["ButtonName"] = "Page"
        data["Page"] = str(offset)
    return fetch_html(SEARCH_URL, data=data)


@dataclass
class ResultEntry:
    contact_id: str
    attorney_name: str
    firm_name: str
    city: str
    state: str
    address: str
    practice_areas: str
    website_hint: str
    phone_hint: str


@dataclass
class DetailRecord:
    contact_id: str
    attorney_name: str
    website: str
    phone: str
    city: str
    state: str
    practice_areas: str
    firm_name: str
    firm_size_raw: str
    occupation: str
    linkedin_urls: list[str] = field(default_factory=list)
    board_certified: bool = False
    board_certification: str = ""
    address: str = ""
    foreign_languages: list[str] = field(default_factory=list)
    language_translation: bool = False
    payment_options: list[str] = field(default_factory=list)
    statutory_certified_on: str = ""


@dataclass
class SiteSignals:
    website: str
    contact_page_url: str
    emails: list[tuple[str, str]]
    phone_numbers: list[str]
    firm_linkedin_url: str
    decision_maker_linkedin_url: str
    text_blob: str
    title: str
    meta_description: str
    explicit_name: str
    explicit_title: str
    cta_signals: list[str]
    subpractice_signals: list[str]
    bilingual: bool
    pages_fetched: list[str]


def parse_result_entries(html_text: str) -> list[ResultEntry]:
    blocks = re.findall(r'<div class="results">\s*<article class="lawyer">(.*?)</article>', html_text, re.S | re.I)
    entries: list[ResultEntry] = []
    for block in blocks:
        cid_match = re.search(r"ContactID=(\d+)", block)
        if not cid_match:
            continue
        name_parts = re.findall(
            r'<span class="(?:honorific-prefix|given-name|family-name|honorific-suffix)">(.*?)</span>',
            block,
            re.S | re.I,
        )
        name = collapse_ws(" ".join(strip_tags(part) for part in name_parts))
        firm_match = re.search(r"<h5>(.*?)</h5>", block, re.S | re.I)
        firm_name = strip_tags(firm_match.group(1)) if firm_match else ""
        city_match = re.search(r"Primary Practice Location:</strong>\s*([^,<]+),&nbsp;TX", block, re.S | re.I)
        city = clean_html_text(city_match.group(1)) if city_match else ""
        address_match = re.search(r'<p class="address">(.*?)</p>', block, re.S | re.I)
        address = strip_tags(address_match.group(1)).replace(" ,", ",") if address_match else ""
        practice_match = re.search(r"<strong>Practice Areas:</strong>\s*(.*?)\s*</p>", block, re.S | re.I)
        practice_areas = strip_tags(practice_match.group(1)) if practice_match else ""
        website_match = re.search(r'<a href="([^"]+)" target="_blank">VISIT WEBSITE', block, re.S | re.I)
        phone_match = re.search(r'href="tel:([^"]+)"', block, re.I)
        entries.append(
            ResultEntry(
                contact_id=cid_match.group(1),
                attorney_name=name,
                firm_name=firm_name,
                city=city,
                state="Texas" if city else "",
                address=address,
                practice_areas=practice_areas,
                website_hint=website_match.group(1).strip() if website_match else "",
                phone_hint=phone_match.group(1).strip() if phone_match else "",
            )
        )
    return entries


def get_total_pages(html_text: str) -> int:
    match = re.search(r"Page 1 of (\d+)", html_text)
    return int(match.group(1)) if match else 1


def parse_detail_page(contact_id: str) -> DetailRecord:
    html_text = fetch_html(DETAIL_URL.format(contact_id=contact_id))

    def m(pattern: str) -> str:
        match = re.search(pattern, html_text, re.S | re.I)
        if not match:
            return ""
        return strip_tags(match.group(1))

    title_match = re.search(r"<title>.*?\|\s*&nbsp;([^<]+)</title>", html_text, re.S | re.I)
    attorney_name = clean_html_text(title_match.group(1)) if title_match else ""
    website_match = re.search(r'<a class="no_print" href="([^"]+)" target="_blank">VISIT WEBSITE', html_text, re.I)
    phone_match = re.search(r'<a href="tel:([^"]+)">', html_text, re.I)
    linkedin_urls = sorted(
        {
            url.strip()
            for url in re.findall(r'href="(https?://[^"]*linkedin\.com/[^"]+)"', html_text, re.I)
        }
    )
    board_match = re.search(r"<figcaption><a [^>]*>(.*?)</a></figcaption>", html_text, re.S | re.I)
    board_label = strip_tags(board_match.group(1)) if board_match else ""
    map_match = re.search(r"maps/embed/v1/place\?[^\"']*q=([^\"'>]+)", html_text, re.I)
    address = clean_html_text(map_match.group(1).replace("+", " ")) if map_match else ""
    languages_raw = m(r"<strong>Foreign Language Assistance:\s*</strong>\s*<br/>\s*(.*?)\s*</p>")
    if languages_raw.lower() == "none reported by attorney":
        foreign_languages: list[str] = []
    else:
        foreign_languages = [collapse_ws(part) for part in re.split(r"[,/]", languages_raw) if collapse_ws(part)]
    services_match = re.search(r"<strong>Services Provided:\s*</strong><br/>(.*?)</p>", html_text, re.S | re.I)
    services_block = strip_tags(services_match.group(1)) if services_match else ""
    payment_options: list[str] = []
    payment_match = re.search(r"<strong>Fee Options Provided:\s*</strong>.*?<br/>(.*?)<br/>\s*<br/>", html_text, re.S | re.I)
    if payment_match:
        payment_block = strip_tags(payment_match.group(1))
        for item in ["Flat Fees", "Hourly Rate", "Payment Plans", "Sliding Scale Fees", "Contingency Fees"]:
            if item.lower() in payment_block.lower():
                payment_options.append(item)

    return DetailRecord(
        contact_id=contact_id,
        attorney_name=attorney_name,
        website=strip_url(website_match.group(1)) if website_match else "",
        phone=phone_match.group(1).strip() if phone_match else "",
        city=m(r"<strong>Primary Practice Location:</strong>\s*([^,<]+)\s*,\s*Texas"),
        state="Texas",
        practice_areas=m(r'<strong>Practice Areas: </strong>\s*([^<]+)'),
        firm_name=m(r"<p><strong>Firm: </strong>(.*?)</p>"),
        firm_size_raw=m(r"<p><strong>Firm Size: </strong>(.*?)</p>"),
        occupation=m(r"<p><strong>Occupation: </strong>(.*?)</p>"),
        linkedin_urls=linkedin_urls,
        board_certified=bool(board_label),
        board_certification=board_label,
        address=address,
        foreign_languages=foreign_languages,
        language_translation="Language translation: Yes" in services_block,
        payment_options=payment_options,
        statutory_certified_on=m(r"Statutory Profile Last Certified On:\s*</span></strong>\s*([^<]+)"),
    )


def map_firm_size(raw: str) -> str:
    text = (raw or "").strip().lower()
    if text == "solo":
        return "1"
    if text == "2 to 5":
        return "2-5"
    if text == "6 to 10":
        return "6-10"
    if "11" in text or "24" in text or "25" in text or "50" in text or "100" in text:
        return "11+"
    return "unknown"


def is_private_law_practice(detail: DetailRecord) -> bool:
    return detail.occupation.lower() == "private law practice"


def is_crawlable_website(url: str) -> bool:
    cleaned = (url or "").strip()
    if not cleaned or re.search(r"[\s\x00-\x1f]", cleaned):
        return False
    domain = get_domain(cleaned)
    return bool(domain and "." in domain)


def should_crawl_site(detail: DetailRecord, website: str) -> bool:
    if not detail.city or detail.state != "Texas":
        return False
    if not is_private_law_practice(detail):
        return False
    if map_firm_size(detail.firm_size_raw) == "11+":
        return False
    if not is_crawlable_website(website):
        return False
    site_domain = get_domain(website)
    if site_domain in LOW_FIT_DOMAINS or site_domain.endswith(".gov"):
        return False
    return True


def decode_cf_email(hex_value: str) -> str:
    try:
        key = int(hex_value[:2], 16)
        chars = [chr(int(hex_value[i : i + 2], 16) ^ key) for i in range(2, len(hex_value), 2)]
        return "".join(chars)
    except Exception:
        return ""


def extract_emails_from_html(html_text: str) -> set[str]:
    emails: set[str] = set()
    for email in re.findall(r"[A-Z0-9._%+-]+@[A-Z0-9.-]+\.[A-Z]{2,}", html_text, re.I):
        emails.add(email.strip(" .;,").lower())
    for href in re.findall(r'mailto:([^"\'?]+)', html_text, re.I):
        emails.add(html.unescape(href).strip().lower())
    for cf_hex in re.findall(r'data-cfemail="([0-9a-f]+)"', html_text, re.I):
        decoded = decode_cf_email(cf_hex)
        if decoded:
            emails.add(decoded.lower())
    text = strip_tags(html_text)
    for email in re.findall(
        r"([A-Z0-9._%+-]+)\s*(?:@|\(at\)|\[at\]|\sat\s)\s*([A-Z0-9.-]+\.[A-Z]{2,})",
        text,
        re.I,
    ):
        emails.add(f"{email[0]}@{email[1]}".lower())
    return {e for e in emails if "@" in e and not e.endswith((".png", ".jpg", ".jpeg", ".gif", ".svg"))}


def extract_phone_numbers(text: str) -> list[str]:
    raw_numbers = re.findall(r"(?:\+?1[\s\-.]?)?(?:\(?\d{3}\)?[\s\-.]?)\d{3}[\s\-.]?\d{4}", text)
    cleaned = []
    seen = set()
    for raw in raw_numbers:
        digits = re.sub(r"\D", "", raw)
        if len(digits) == 11 and digits.startswith("1"):
            digits = digits[1:]
        if len(digits) != 10:
            continue
        formatted = f"{digits[:3]}-{digits[3:6]}-{digits[6:]}"
        if formatted not in seen:
            seen.add(formatted)
            cleaned.append(formatted)
    return cleaned


def extract_site_pages(root_url: str) -> list[str]:
    root_url = strip_url(root_url)
    homepage_html = fetch_html(root_url)
    parser = SimplePageParser()
    parser.feed(homepage_html)
    candidates = [root_url]
    for href, text in parser.links:
        if not href:
            continue
        absolute = strip_url(urljoin(root_url + "/", href))
        if not same_domain(absolute, root_url):
            continue
        haystack = f"{href} {text}".lower()
        if any(keyword in haystack for keyword in CONTACT_PAGE_KEYWORDS):
            candidates.append(absolute)
    deduped = []
    seen = set()
    for url in candidates:
        key = strip_url(url)
        if key and key not in seen:
            seen.add(key)
            deduped.append(key)
        if len(deduped) >= 6:
            break
    return deduped


def find_explicit_decision_maker(
    pages: list[tuple[str, str]],
    candidate_names: list[str],
) -> tuple[str, str]:
    title_regex = r"(founding attorney|founder|owner|managing attorney|principal attorney|partner|attorney at law)"
    for name in candidate_names:
        simple_name = collapse_ws(name)
        if not simple_name:
            continue
        for _, text in pages:
            pattern_a = re.search(
                rf"{re.escape(simple_name)}.{{0,120}}?{title_regex}",
                text,
                re.I,
            )
            if pattern_a:
                return simple_name, normalize_title(pattern_a.group(1))
            pattern_b = re.search(
                rf"{title_regex}.{{0,120}}?{re.escape(simple_name)}",
                text,
                re.I,
            )
            if pattern_b:
                return simple_name, normalize_title(pattern_b.group(1))
    return "", ""


def normalize_title(raw: str) -> str:
    value = raw.lower().strip()
    if "found" in value:
        return "Founder"
    if "owner" in value:
        return "Owner"
    if "managing" in value:
        return "Managing Attorney"
    if "principal" in value:
        return "Principal Attorney"
    if "partner" in value:
        return "Partner"
    return "Attorney at Law"


def derive_title_from_firm_name(detail: DetailRecord, attorney_name: str) -> str:
    normalized_firm = slugify(detail.firm_name)
    _, last_name = parse_name(attorney_name)
    last_slug = slugify(last_name)
    if not last_slug:
        return "Attorney at Law"
    if map_firm_size(detail.firm_size_raw) == "1":
        return "Owner"
    if last_slug and last_slug in normalized_firm:
        if " and " in normalized_firm or "&" in detail.firm_name:
            return "Partner"
        if "law office of" in normalized_firm or "law offices of" in normalized_firm or "law group" in normalized_firm:
            return "Principal Attorney"
        return "Principal Attorney"
    return "Attorney at Law"


def extract_site_signals(root_url: str, candidate_names: list[str], detail: DetailRecord) -> SiteSignals:
    pages = []
    emails: list[tuple[str, str]] = []
    phone_numbers: list[str] = []
    firm_linkedin_url = ""
    decision_maker_linkedin_url = detail.linkedin_urls[0] if detail.linkedin_urls else ""
    cta_signals: list[str] = []
    subpractice_signals: list[str] = []
    bilingual = bool(detail.foreign_languages)

    for url in extract_site_pages(root_url):
        try:
            html_text = fetch_html(url)
        except Exception:
            continue
        parser = SimplePageParser()
        parser.feed(html_text)
        page_text = " ".join(filter(None, [parser.title, parser.meta_description, parser.text]))
        pages.append((url, page_text))

        found_emails = extract_emails_from_html(html_text)
        for email in found_emails:
            emails.append((email, url))
        phone_numbers.extend(extract_phone_numbers(page_text))

        for href, _ in parser.links:
            absolute = urljoin(url, href)
            if "linkedin.com/company/" in absolute.lower() and not firm_linkedin_url:
                firm_linkedin_url = absolute
            if "linkedin.com/in/" in absolute.lower() and not decision_maker_linkedin_url:
                decision_maker_linkedin_url = absolute

        lowered = page_text.lower()
        signal_map = {
            "schedule a consultation": "schedule consultation",
            "book a consultation": "book consultation",
            "free consultation": "free consultation",
            "call now": "call now",
            "available 24/7": "available 24/7",
            "serving families": "serving families",
            "personalized immigration": "personalized immigration help",
            "bilingual": "bilingual positioning",
            "spanish": "spanish-language positioning",
            "consultation": "consultation CTA",
        }
        for needle, label in signal_map.items():
            if needle in lowered and label not in cta_signals:
                cta_signals.append(label)
        for needle in HIGH_VOLUME_SUBPRACTICES:
            if needle in lowered and needle not in subpractice_signals:
                subpractice_signals.append(needle)
        if "bilingual" in lowered or "spanish" in lowered:
            bilingual = True

    explicit_name, explicit_title = find_explicit_decision_maker(pages, candidate_names)
    contact_page_url = root_url
    for page_url, _ in pages:
        lower = page_url.lower()
        if "contact" in lower or "consult" in lower or "schedule" in lower:
            contact_page_url = page_url
            break

    if not cta_signals and detail.language_translation:
        cta_signals.append("language translation")
    if not bilingual and detail.foreign_languages:
        bilingual = True
    if not subpractice_signals:
        lowered_practice = detail.practice_areas.lower()
        for needle in HIGH_VOLUME_SUBPRACTICES:
            if needle in lowered_practice:
                subpractice_signals.append(needle)

    pages_fetched = [page_url for page_url, _ in pages]
    text_blob = " ".join(page_text for _, page_text in pages)
    title = pages[0][1].split(" ", 20)[0] if pages else ""
    meta_description = ""
    if pages:
        try:
            homepage = fetch_html(root_url)
            p = SimplePageParser()
            p.feed(homepage)
            meta_description = p.meta_description
            title = p.title
        except Exception:
            pass

    return SiteSignals(
        website=root_url,
        contact_page_url=contact_page_url,
        emails=emails,
        phone_numbers=sorted(set(phone_numbers)),
        firm_linkedin_url=firm_linkedin_url,
        decision_maker_linkedin_url=decision_maker_linkedin_url,
        text_blob=text_blob,
        title=title,
        meta_description=meta_description,
        explicit_name=explicit_name,
        explicit_title=explicit_title,
        cta_signals=cta_signals,
        subpractice_signals=subpractice_signals,
        bilingual=bilingual,
        pages_fetched=pages_fetched,
    )


def likely_immigration_focused(detail: DetailRecord, site: SiteSignals) -> bool:
    combined = " ".join([detail.practice_areas, site.title, site.meta_description, site.text_blob]).lower()
    if "immigration" not in combined:
        return False
    score = 0
    if "immigration" in (detail.practice_areas or "").lower():
        score += 2
    if "immigration" in (site.title or "").lower() or "immigration" in (site.meta_description or "").lower():
        score += 2
    score += sum(1 for term in HIGH_VOLUME_SUBPRACTICES if term in combined)
    return score >= 2


def choose_main_pain_signal(detail: DetailRecord, site: SiteSignals, founder_led_signal: str, firm_size: str) -> tuple[str, str]:
    text = " ".join([detail.practice_areas, site.text_blob, " ".join(site.cta_signals)]).lower()
    if site.bilingual or detail.foreign_languages:
        return "bilingual service delivery pressure", "bilingual service delivery pressure"
    if "free consultation" in text or "book consultation" in text or "schedule consultation" in text:
        if any(term in text for term in ["family", "asylum", "deport", "removal", "naturalization", "citizenship"]):
            return "consultation-to-client conversion", "consultation-to-client conversion"
        return "intake overload", "intake overload"
    if any(term in text for term in ["asylum", "deport", "removal", "humanitarian", "waiver"]):
        return "case-status communication burden", "case-status communication burden"
    if any(term in text for term in ["green card", "citizenship", "naturalization", "visa", "uscis", "family immigration"]):
        return "document collection friction", "document collection friction"
    if founder_led_signal == "yes" and firm_size == "1":
        return "founder bottleneck", "founder bottleneck"
    return "repetitive client communication", "repetitive client communication"


def score_authority(title: str) -> int:
    if title in {"Founder", "Owner", "Managing Attorney", "Principal Attorney"}:
        return 3
    if title == "Partner":
        return 2
    return 1


def score_pain(detail: DetailRecord, site: SiteSignals, founder_led_signal: str) -> int:
    text = " ".join([detail.practice_areas, site.text_blob, " ".join(site.cta_signals)]).lower()
    score = 1
    if site.bilingual or detail.language_translation:
        score += 1
    if any(term in text for term in ["consultation", "call now", "serving families"]):
        score += 1
    if any(term in text for term in HIGH_VOLUME_SUBPRACTICES):
        score += 1
    if founder_led_signal == "yes" and map_firm_size(detail.firm_size_raw) == "1":
        score = max(score, 3)
    return min(score, 3)


def score_payment_capacity(detail: DetailRecord, site: SiteSignals) -> int:
    score = 1
    firm_size = map_firm_size(detail.firm_size_raw)
    professional_signals = 0
    if detail.board_certified:
        professional_signals += 1
    if site.website and len(site.pages_fetched) >= 2:
        professional_signals += 1
    if site.meta_description or site.firm_linkedin_url:
        professional_signals += 1
    if firm_size in {"2-5", "6-10"}:
        score += 1
    if professional_signals >= 2:
        score += 1
    return min(score, 3)


def score_ease_of_entry(primary_email: str, site: SiteSignals, founder_led_signal: str) -> int:
    score = 1
    if primary_email:
        score += 1
    if site.contact_page_url and site.contact_page_url != site.website:
        score += 1
    elif site.website and any(signal in site.cta_signals for signal in ["consultation CTA", "book consultation", "schedule consultation"]):
        score += 1
    if founder_led_signal == "yes" and primary_email:
        score = 3
    return min(score, 3)


def determine_tier(total_score: int) -> str:
    if total_score >= 10:
        return "Tier A"
    if total_score >= 7:
        return "Tier B"
    return "Tier C"


def determine_status(
    tier: str,
    has_primary_email: bool,
    site_domain: str,
    qualifying: bool,
    is_strong_no_email: bool,
    ambiguous_decision_maker: bool,
) -> str:
    if not qualifying:
        return "exclude"
    if has_primary_email:
        return "ready_outreach" if tier in {"Tier A", "Tier B"} else "low_priority"
    if is_strong_no_email or ambiguous_decision_maker:
        return "review_needed"
    return "low_priority" if tier == "Tier C" else "review_needed"


def generate_personalization_observation(
    city: str,
    detail: DetailRecord,
    founder_led_signal: str,
    main_pain_signal: str,
    site: SiteSignals,
) -> str:
    pieces = []
    if founder_led_signal == "yes":
        pieces.append(f"Founder-led {city} immigration firm")
    elif founder_led_signal == "likely":
        pieces.append(f"Small {city} immigration firm")
    else:
        pieces.append(f"{city} immigration practice")
    if site.bilingual or detail.foreign_languages:
        pieces.append("with bilingual positioning")
    elif any(signal in site.cta_signals for signal in ["consultation CTA", "book consultation", "schedule consultation", "free consultation"]):
        pieces.append("with heavy consultation CTA")
    elif detail.board_certified:
        pieces.append("with board-certified immigration branding")
    if main_pain_signal:
        pieces.append(f"likely {main_pain_signal}")
    sentence = " ".join(pieces)
    return sentence[:1].upper() + sentence[1:] + "."


def rank_priority(city: str) -> int:
    try:
        return PRIORITY_CITIES.index(city)
    except ValueError:
        return len(PRIORITY_CITIES)


def firm_group_key(entry: ResultEntry) -> str:
    domain = get_domain(entry.website_hint)
    if domain and domain not in LOW_FIT_DOMAINS:
        return f"domain::{domain}"
    firm = slugify(entry.firm_name)
    if firm:
        return f"firm::{firm}::{slugify(entry.city)}"
    name = slugify(entry.attorney_name)
    return f"person::{name}::{slugify(entry.city)}"


def dedupe_rows(rows: list[dict[str, object]]) -> list[dict[str, object]]:
    final_rows = []
    seen = set()
    for row in rows:
        domain = get_domain(str(row.get("Website", "")))
        name = slugify(str(row.get("Decision Maker Name", "")))
        email = str(row.get("Public Business Email", "")).lower()
        key = (domain, name) if domain and name else None
        alt_key = (domain, email) if domain and email else None
        if key and key in seen:
            continue
        if alt_key and alt_key in seen:
            continue
        if key:
            seen.add(key)
        if alt_key:
            seen.add(alt_key)
        final_rows.append(row)
    return final_rows


def build_summary(df: pd.DataFrame) -> str:
    valid_df = df[df["Status"] != "exclude"].copy()
    active_df = valid_df[valid_df["Tier"].isin(["Tier A", "Tier B"])]
    ready_df = valid_df[valid_df["Status"] == "ready_outreach"]

    top_cities = (
        valid_df[valid_df["City"].astype(str) != ""]
        .groupby("City")
        .size()
        .sort_values(ascending=False)
        .head(10)
    )
    cluster_map = {
        "family immigration": ["family immigration", "family"],
        "asylum": ["asylum"],
        "deportation/removal defense": ["deport", "removal"],
        "visa services": ["visa", "nonimmigrant", "h-1b", "l-1", "e-2", "e-1", "tn"],
        "green cards": ["green card", "permanent residency", "permanent resident"],
        "citizenship/naturalization": ["citizenship", "naturalization"],
        "humanitarian immigration": ["humanitarian", "waiver", "u visa", "t visa", "vawa"],
        "business immigration": ["business", "employment", "investor", "international"],
    }
    subpractice_counter = Counter()
    for practice in valid_df["Practice Area"].fillna(""):
        lowered = practice.lower()
        for label, needles in cluster_map.items():
            if any(needle in lowered for needle in needles):
                subpractice_counter[label] += 1

    pain_counts = valid_df["Main Pain Signal"].replace("", pd.NA).dropna().value_counts().head(10)
    angle_counts = valid_df["Outreach Angle"].replace("", pd.NA).dropna().value_counts().head(10)

    lines = [
        "# Commercial Summary",
        "",
        f"- Valid prospects found: {len(valid_df)}",
        f"- Tier A: {int((valid_df['Tier'] == 'Tier A').sum())}",
        f"- Tier B: {int((valid_df['Tier'] == 'Tier B').sum())}",
        f"- Ready for outreach: {len(ready_df)}",
        f"- Review needed: {int((valid_df['Status'] == 'review_needed').sum())}",
        "",
        "## Top Cities",
    ]
    for city, count in top_cities.items():
        lines.append(f"- {city}: {int(count)}")

    lines.extend(["", "## Top Sub-Practice Clusters"])
    for label, count in subpractice_counter.most_common(10):
        lines.append(f"- {label}: {count}")

    lines.extend(["", "## Most Common Pain Signals"])
    for label, count in pain_counts.items():
        lines.append(f"- {label}: {int(count)}")

    lines.extend(["", "## Most Common Outreach Angles"])
    for label, count in angle_counts.items():
        lines.append(f"- {label}: {int(count)}")

    density = (
        active_df.groupby(["City", "Estimated Firm Size"])
        .size()
        .sort_values(ascending=False)
        .head(10)
    )
    lines.extend(["", "## Best Commercial Density"])
    for (city, size), count in density.items():
        lines.append(f"- {city} / {size}: {int(count)}")

    if len(valid_df) < 1000:
        lines.extend(
            [
                "",
                "## Ceiling Note",
                f"- The current Texas-only run produced {len(valid_df)} non-excluded records, below the 1,000 target.",
                "- Bottleneck: many Texas Bar immigration profiles belong to larger firms, government roles, non-immigration-led practices, or sites without public website email exposure.",
                "- Narrowest next expansion path: keep Texas-only but widen into adjacent immigration-heavy sub-niches that still fit intake-heavy, small-firm criteria before touching adjacent practice areas.",
            ]
        )
    return "\n".join(lines) + "\n"


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser()
    parser.add_argument("--max-pages", type=int, default=0)
    parser.add_argument("--max-firms", type=int, default=0)
    parser.add_argument("--workers", type=int, default=8)
    return parser.parse_args()


def empty_site_signals(website: str, detail: DetailRecord) -> SiteSignals:
    return SiteSignals(
        website=website,
        contact_page_url=website,
        emails=[],
        phone_numbers=[],
        firm_linkedin_url="",
        decision_maker_linkedin_url=detail.linkedin_urls[0] if detail.linkedin_urls else "",
        text_blob="",
        title="",
        meta_description="",
        explicit_name="",
        explicit_title="",
        cta_signals=[],
        subpractice_signals=[],
        bilingual=bool(detail.foreign_languages),
        pages_fetched=[],
    )


def main() -> int:
    ensure_dirs()
    args = parse_args()

    print("Fetching Texas Bar immigration result pages...", file=sys.stderr)
    first_page_html = fetch_result_page(0)
    total_pages = get_total_pages(first_page_html)
    if args.max_pages:
        total_pages = min(total_pages, args.max_pages)

    page_offsets = [0] + [((page - 1) * RESULTS_PER_PAGE) + 1 for page in range(2, total_pages + 1)]
    page_html_by_offset: dict[int, str] = {0: first_page_html}

    with ThreadPoolExecutor(max_workers=min(args.workers, 10)) as executor:
        future_map = {
            executor.submit(fetch_result_page, offset): offset
            for offset in page_offsets
            if offset != 0
        }
        for future in as_completed(future_map):
            offset = future_map[future]
            try:
                page_html_by_offset[offset] = future.result()
            except Exception as exc:
                print(f"Failed result page offset {offset}: {exc}", file=sys.stderr)

    result_entries: list[ResultEntry] = []
    for offset in sorted(page_html_by_offset):
        result_entries.extend(parse_result_entries(page_html_by_offset[offset]))
    print(f"Parsed {len(result_entries)} result entries.", file=sys.stderr)

    grouped: dict[str, list[ResultEntry]] = defaultdict(list)
    for entry in result_entries:
        grouped[firm_group_key(entry)].append(entry)

    grouped_items = sorted(
        grouped.items(),
        key=lambda item: (
            rank_priority(item[1][0].city),
            item[1][0].city or "ZZZ",
            slugify(item[1][0].firm_name or item[1][0].attorney_name),
        ),
    )
    if args.max_firms:
        grouped_items = grouped_items[: args.max_firms]
    print(f"Grouped into {len(grouped_items)} firm candidates.", file=sys.stderr)

    representative_details: dict[str, tuple[ResultEntry, DetailRecord]] = {}
    with ThreadPoolExecutor(max_workers=min(args.workers, 10)) as executor:
        futures = {}
        for key, entries in grouped_items:
            best_entry = sorted(
                entries,
                key=lambda e: (
                    -int(bool(e.website_hint)),
                    -int(bool(e.phone_hint)),
                    len(e.attorney_name),
                ),
            )[0]
            futures[executor.submit(parse_detail_page, best_entry.contact_id)] = (key, best_entry)
        completed = 0
        for future in as_completed(futures):
            key, best_entry = futures[future]
            try:
                representative_details[key] = (best_entry, future.result())
            except Exception as exc:
                print(f"Failed detail page {best_entry.contact_id}: {exc}", file=sys.stderr)
            completed += 1
            if completed % 100 == 0 or completed == len(futures):
                print(f"Fetched {completed}/{len(futures)} Texas Bar detail pages.", file=sys.stderr)

    rows: list[dict[str, object]] = []
    prospect_id = 1
    print("Crawling official sites and scoring prospects...", file=sys.stderr)

    candidate_records: list[tuple[str, list[ResultEntry], ResultEntry, DetailRecord]] = []
    crawl_inputs: list[tuple[str, list[ResultEntry], ResultEntry, DetailRecord, str]] = []
    skipped_site_crawls = 0
    for key, entries in grouped_items:
        best_entry, detail = representative_details.get(key, (None, None))
        if not best_entry or not detail:
            continue
        candidate_records.append((key, entries, best_entry, detail))
        website = detail.website or best_entry.website_hint
        if should_crawl_site(detail, website):
            crawl_inputs.append((key, entries, best_entry, detail, website))
        else:
            skipped_site_crawls += 1

    print(
        f"Scheduling {len(crawl_inputs)} official site crawls and bypassing {skipped_site_crawls} candidates pre-site.",
        file=sys.stderr,
    )

    site_results: dict[str, SiteSignals | None] = {}
    with ThreadPoolExecutor(max_workers=min(args.workers, 10)) as executor:
        site_futures = {}
        for key, entries, best_entry, detail, website in crawl_inputs:
            candidate_names = candidate_names_for_site(entries, best_entry, detail)
            site_futures[executor.submit(extract_site_signals, website, candidate_names, detail)] = (
                key,
                entries,
                best_entry,
                detail,
            )

        completed = 0
        for future in as_completed(site_futures):
            key, entries, best_entry, detail = site_futures[future]
            try:
                site_results[key] = future.result()
            except Exception as exc:
                site_results[key] = None
                print(f"Website crawl failed for {detail.firm_name or detail.attorney_name}: {exc}", file=sys.stderr)
            completed += 1
            if completed % 100 == 0 or completed == len(site_futures):
                print(f"Scored {completed}/{len(site_futures)} firm candidates.", file=sys.stderr)

    total_candidates = len(candidate_records)
    for completed, (key, entries, best_entry, detail) in enumerate(candidate_records, start=1):
        website_hint = detail.website or best_entry.website_hint
        site = site_results.get(key)
        if site is None:
            site = empty_site_signals(website_hint, detail)

        website = site.website or website_hint
        site_domain = get_domain(website)
        normalized_city = normalize_city(detail.city or best_entry.city)
        estimated_firm_size = map_firm_size(detail.firm_size_raw)
        qualifying = True
        evidence_notes = []

        if not detail.city or detail.state != "Texas":
            qualifying = False
            evidence_notes.append("Excluded: non-Texas or missing Texas location.")
        if not is_private_law_practice(detail):
            qualifying = False
            evidence_notes.append(f"Excluded: occupation is {detail.occupation or 'unknown'}.")
        if estimated_firm_size == "11+":
            qualifying = False
            evidence_notes.append(f"Excluded: firm size {detail.firm_size_raw}.")
        if website and (site_domain in LOW_FIT_DOMAINS or site_domain.endswith(".gov")):
            qualifying = False
            evidence_notes.append(f"Excluded: website domain {site_domain} is not a boutique law-firm domain.")
        if not likely_immigration_focused(detail, site):
            qualifying = False
            evidence_notes.append("Excluded: website and profile do not show immigration as a clear primary/major service line.")

        decision_maker_name = site.explicit_name or best_entry.attorney_name or detail.attorney_name
        decision_maker_title = site.explicit_title
        if not decision_maker_title:
            decision_maker_title = derive_title_from_firm_name(detail, decision_maker_name)
        elif estimated_firm_size == "1" and decision_maker_title not in {"Founder", "Owner"}:
            decision_maker_title = "Owner"
        founder_led_signal = "unclear"
        if decision_maker_title in {"Founder", "Owner", "Managing Attorney", "Principal Attorney"} or estimated_firm_size == "1":
            founder_led_signal = "yes"
        elif decision_maker_title == "Partner" or estimated_firm_size == "2-5":
            founder_led_signal = "likely"

        email_hits = [(email, source) for email, source in site.emails if domain_from_email(email)]
        primary_email, secondary_email, email_source_url = choose_best_email(email_hits, site_domain)
        confident_ready_email = is_confident_ready_email(
            primary_email,
            site_domain,
            detail.firm_name or best_entry.firm_name,
            decision_maker_name,
        ) if primary_email else False

        main_pain_signal, outreach_angle = choose_main_pain_signal(detail, site, founder_led_signal, estimated_firm_size)
        authority_score = score_authority(decision_maker_title)
        pain_score = score_pain(detail, site, founder_led_signal)
        payment_capacity_score = score_payment_capacity(detail, site)
        ease_score = score_ease_of_entry(primary_email, site, founder_led_signal)
        total_score = authority_score + pain_score + payment_capacity_score + ease_score
        tier = determine_tier(total_score)
        very_strong_no_email = total_score >= 10 and not primary_email and bool(site.contact_page_url or detail.phone or best_entry.phone_hint)
        ambiguous_decision_maker = decision_maker_title == "Attorney at Law" and founder_led_signal == "unclear"
        status = determine_status(
            tier=tier,
            has_primary_email=bool(primary_email),
            site_domain=site_domain,
            qualifying=qualifying,
            is_strong_no_email=very_strong_no_email,
            ambiguous_decision_maker=ambiguous_decision_maker,
        )

        if status == "ready_outreach" and (not email_source_url or not confident_ready_email):
            status = "review_needed"

        practice_area = detail.practice_areas or best_entry.practice_areas
        if detail.board_certified:
            evidence_notes.append(f"Texas Bar detail: board certified in {detail.board_certification}.")
        evidence_notes.append(
            f"Texas Bar detail: firm '{detail.firm_name}', size '{detail.firm_size_raw}', occupation '{detail.occupation}', city '{detail.city}'."
        )
        if not should_crawl_site(detail, website_hint):
            evidence_notes.append("Official site crawl skipped after Texas Bar pre-filter.")
        if site.cta_signals:
            evidence_notes.append(f"Website CTA signals: {', '.join(site.cta_signals[:4])}.")
        if site.subpractice_signals:
            evidence_notes.append(f"Website sub-practice signals: {', '.join(site.subpractice_signals[:4])}.")
        if primary_email:
            evidence_notes.append(f"Public website email found on {email_source_url}.")
            if not confident_ready_email:
                evidence_notes.append("Public email domain differs from firm branding; marked review_needed.")
        elif site.contact_page_url:
            evidence_notes.append(f"No public website email found; contact route available at {site.contact_page_url}.")
        elif detail.website:
            evidence_notes.append("No public website email found on crawled pages.")

        personalization = ""
        if tier in {"Tier A", "Tier B"} and status != "exclude":
            personalization = generate_personalization_observation(
                city=normalized_city,
                detail=detail,
                founder_led_signal=founder_led_signal,
                main_pain_signal=main_pain_signal,
                site=site,
            )

        firm_linkedin_url = site.firm_linkedin_url
        decision_maker_linkedin_url = site.decision_maker_linkedin_url or (detail.linkedin_urls[0] if detail.linkedin_urls else "")
        website_to_store = website
        contact_page_url = site.contact_page_url or website
        phone_number = detail.phone or best_entry.phone_hint
        if not phone_number and site.phone_numbers:
            phone_number = site.phone_numbers[0]

        row = {
            "Prospect ID": f"TX-IMM-{prospect_id:05d}",
            "Firm Name": detail.firm_name or best_entry.firm_name or decision_maker_name,
            "Website": website_to_store,
            "Contact Page URL": contact_page_url,
            "Public Business Email": primary_email,
            "Secondary Public Email": secondary_email,
            "Phone Number": phone_number,
            "City": normalized_city,
            "State": "Texas",
            "Practice Area": practice_area,
            "Decision Maker Name": decision_maker_name,
            "Decision Maker Title": decision_maker_title,
            "Decision Maker LinkedIn URL": decision_maker_linkedin_url,
            "Firm LinkedIn URL": firm_linkedin_url,
            "Estimated Firm Size": estimated_firm_size,
            "Founder-Led Signal": founder_led_signal,
            "Main Pain Signal": main_pain_signal,
            "Authority Score": authority_score,
            "Pain Score": pain_score,
            "Payment Capacity Score": payment_capacity_score,
            "Ease of Entry Score": ease_score,
            "Total Score": total_score,
            "Tier": tier,
            "Personalization Observation": personalization,
            "Outreach Angle": outreach_angle if tier in {"Tier A", "Tier B"} and status != "exclude" else "",
            "Evidence / Source Notes": " ".join(evidence_notes),
            "Public Source URL for Email": email_source_url,
            "Status": status,
            "_priority_rank": rank_priority(detail.city or best_entry.city),
            "_detail_contact_id": detail.contact_id,
            "_pages_fetched": " | ".join(site.pages_fetched),
            "_site_domain": site_domain,
        }
        rows.append(row)
        prospect_id += 1
        if completed % 100 == 0 or completed == total_candidates:
            print(f"Built {completed}/{total_candidates} prospect rows.", file=sys.stderr)

    rows = dedupe_rows(rows)
    df = pd.DataFrame(rows)
    if df.empty:
        print("No rows were generated.", file=sys.stderr)
        return 1

    df = df.sort_values(
        by=["_priority_rank", "Total Score", "Pain Score", "Ease of Entry Score", "Firm Name"],
        ascending=[True, False, False, False, True],
    ).reset_index(drop=True)

    df["Prospect ID"] = [f"TX-IMM-{i:05d}" for i in range(1, len(df) + 1)]

    public_columns = [
        "Prospect ID",
        "Firm Name",
        "Website",
        "Contact Page URL",
        "Public Business Email",
        "Secondary Public Email",
        "Phone Number",
        "City",
        "State",
        "Practice Area",
        "Decision Maker Name",
        "Decision Maker Title",
        "Decision Maker LinkedIn URL",
        "Firm LinkedIn URL",
        "Estimated Firm Size",
        "Founder-Led Signal",
        "Main Pain Signal",
        "Authority Score",
        "Pain Score",
        "Payment Capacity Score",
        "Ease of Entry Score",
        "Total Score",
        "Tier",
        "Personalization Observation",
        "Outreach Angle",
        "Evidence / Source Notes",
        "Public Source URL for Email",
        "Status",
    ]

    master_df = df[public_columns].copy()
    tier_a_df = master_df[(master_df["Tier"] == "Tier A") & (master_df["Status"] != "exclude")].copy()
    tier_b_df = master_df[(master_df["Tier"] == "Tier B") & (master_df["Status"] != "exclude")].copy()
    top25_df = master_df[master_df["Status"] == "ready_outreach"].copy()
    top25_df = top25_df.sort_values(
        by=["Total Score", "Pain Score", "Ease of Entry Score", "Founder-Led Signal"],
        ascending=[False, False, False, True],
    ).head(25)

    master_df.to_csv(OUTPUT_DIR / "master_prospects.csv", index=False, quoting=csv.QUOTE_MINIMAL)
    tier_a_df.to_csv(OUTPUT_DIR / "tier_a_prospects.csv", index=False, quoting=csv.QUOTE_MINIMAL)
    tier_b_df.to_csv(OUTPUT_DIR / "tier_b_prospects.csv", index=False, quoting=csv.QUOTE_MINIMAL)
    top25_df.to_csv(OUTPUT_DIR / "top25_first_outreach.csv", index=False, quoting=csv.QUOTE_MINIMAL)
    (OUTPUT_DIR / "commercial_summary.md").write_text(build_summary(master_df), encoding="utf-8")

    ready_count = int((master_df["Status"] == "ready_outreach").sum())
    valid_count = int((master_df["Status"] != "exclude").sum())
    print(
        f"Wrote {len(master_df)} master rows, {valid_count} non-excluded, {ready_count} ready_outreach.",
        file=sys.stderr,
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
