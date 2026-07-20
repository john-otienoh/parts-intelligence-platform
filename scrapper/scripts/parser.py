"""Pure functions that turn lxml trees into structured dicts."""

from __future__ import annotations

import re
from typing import Any, Dict, List, Optional
from urllib.parse import urljoin

from lxml import etree, html as lxml_html


def _text(el) -> Optional[str]:
    if el is None:
        return None
    if isinstance(el, list):
        if not el:
            return None
        el = el[0]
    raw = el if isinstance(el, str) else el.xpath("string()")
    cleaned = re.sub(r"\s+", " ", raw).strip()
    return cleaned or None


def parse_price_block(tree) -> Dict[str, Any]:
    """Extract price information from a listing page."""
    boxes = tree.xpath('//div[contains(@class,"price-box")]')
    if not boxes:
        return {}
    box = boxes[0]
    orig = _text(box.xpath('.//p[contains(@class,"item-original-price")]//del'))
    cur = _text(box.xpath('.//p[contains(@class,"item-price")]/b'))
    save = _text(
        box.xpath(
            './/p[contains(@class,"item-save-price")]//span[contains(@class,"save-text")]'
        )
    )

    def _extract_amount(text: Optional[str]) -> Optional[float]:
        if not text:
            return None
        m = re.search(r"[\d,]+(?:\.\d+)?", text)
        return float(m.group().replace(",", "")) if m else None

    def _extract_percent(text: Optional[str]) -> Optional[int]:
        if not text:
            return None
        m = re.search(r"\((\d+)\s*%\)", text)
        return int(m.group(1)) if m else None

    bargain = tree.xpath(
        '//div[contains(@class,"discount-price-wrap")]//div[contains(@class,"exa-icon-text")]/div'
    )
    return {
        "currency": "$",
        "original_price": _extract_amount(orig),
        "current_price": _extract_amount(cur),
        "you_save_amount": _extract_amount(save),
        "you_save_percent": _extract_percent(save),
        "is_bargain_price": bool(bargain),
    }


def parse_people_viewing(tree) -> Optional[int]:
    """Extract the number of people currently viewing the listing."""
    text = _text(
        tree.xpath(
            '//div[contains(@class,"promotion-text")]/span[contains(@class,"num-text")]'
        )
    )
    return int(text) if text and text.isdigit() else None


def parse_item_location(tree) -> Optional[str]:
    """Extract the item location from the listing page."""
    for row in tree.xpath('//table[contains(@class,"table-item")]//tr'):
        th, td = row.xpath("./th"), row.xpath("./td")
        if th and td and _text(th) and _text(th).lower() == "item location":
            return _text(td)
    return None


def parse_specifications(tree) -> Dict[str, Optional[str]]:
    """Extract the specification table from the listing page."""
    specs: Dict[str, Optional[str]] = {}
    tables = tree.xpath(
        '//table[contains(@class,"table-simple") and not(contains(@class,"table-item"))]'
    )
    if not tables:
        return specs
    for row in tables[0].xpath(".//tr"):
        th, td = row.xpath("./th"), row.xpath("./td")
        if th and td:
            key = _text(th)
            if key:
                specs[key] = _text(td)
    return specs


def parse_description(tree) -> Optional[str]:
    """Extract the description text from the listing page."""
    nodes = tree.xpath(
        '//div[contains(@class,"item-description")]//div[contains(@class,"description-text")]'
    )
    if not nodes:
        return None
    raw_html = etree.tostring(nodes[0], encoding="unicode", method="html")
    raw_html = re.sub(r"<br\s*/?>", "\n", raw_html)
    text = lxml_html.fromstring(raw_html).text_content()
    lines = [re.sub(r"[ \t\u3000]+", " ", line).strip() for line in text.split("\n")]
    lines = [line for line in lines if line]
    return "\n".join(lines) if lines else None


def parse_images(tree, base_url: str) -> list[str]:
    """Extract image URLs from the listing page."""
    images: List[str] = []
    seen = set()
    for a in tree.xpath(
        '//ul[contains(@class,"fn-thumbnails")]/li[contains(@class,"thumb")]/a[@data-lightbox="item-image"]'
    ):
        href = urljoin(base_url, a.get("href"))
        if href and href not in seen:
            seen.add(href)
            images.append(href)
    if not images:
        for img in tree.xpath(
            "//li[contains(@class,'thumb')]/img[@data-originalimage]"
        ):
            href = urljoin(base_url, img.get("data-originalimage"))
            if href and href not in seen:
                seen.add(href)
                images.append(href)
    return images


def parse_shipping(tree) -> Dict[str, Any]:
    """Extract shipping information from the listing page."""
    country = _text(
        tree.xpath('//select[@name="delivery_country_select"]/option[@selected]')
    )
    options = []
    for table in tree.xpath(
        '//div[contains(@class,"delivery-select-space")]//table[contains(@class,"table-shipping")]'
    ):
        etd = _text(table.xpath('.//div[b[contains(text(),"ETD")]]'))
        eta = _text(table.xpath('.//div[b[contains(text(),"ETA")]]'))
        est = _text(table.xpath('.//b[contains(text(),"Est. delivery")]'))
        price_text = _text(table.xpath('.//span[contains(@class,"text-price")]'))
        price = None
        if price_text:
            m = re.search(r"[\d,]+(?:\.\d+)?", price_text)
            price = float(m.group().replace(",", "")) if m else None
        options.append(
            {
                "destination_port": _text(
                    table.xpath('.//td[contains(@class,"calculator-title")]')
                ),
                "freight_method": _text(
                    table.xpath('.//span[contains(@class,"text-freight")]')
                ),
                "price": price,
                "currency": "$",
                "etd": re.sub(r"^ETD:\s*", "", etd) if etd else None,
                "eta": re.sub(r"^ETA:\s*", "", eta) if eta else None,
                "estimated_delivery": (
                    re.sub(r"^Est\.\s*delivery:\s*", "", est) if est else None
                ),
            }
        )
    return {"destination_country": country, "options": options}


def parse_similar_items(tree, base_url: str) -> List[Dict[str, Any]]:
    """Extract similar items from the listing page."""
    items = []
    seen = set()
    for container in tree.xpath(
        '//div[contains(@class,"item-similar-and-related-items")]'
    ):
        for entry in container.xpath(
            './/section[contains(@class,"entry") and not(contains(@class,"fn-dammy-entry"))]'
        ):
            link = entry.xpath('.//a[contains(@class,"fn-image-resize-image-wrapper")]')
            if not link:
                continue
            a = link[0]
            url = urljoin(base_url, a.get("href"))
            if not url or url in seen:
                continue
            seen.add(url)
            price_text = _text(a.xpath('.//span[contains(@class,"tile-price")]'))
            orig_text = _text(a.xpath('.//del[contains(@class,"is-off-price")]'))
            price = None
            orig = None
            if price_text:
                m = re.search(r"[\d,]+(?:\.\d+)?", price_text)
                price = float(m.group().replace(",", "")) if m else None
            if orig_text:
                m = re.search(r"[\d,]+(?:\.\d+)?", orig_text)
                orig = float(m.group().replace(",", "")) if m else None
            items.append(
                {
                    "ref_no": a.get("data-ref"),
                    "url": url,
                    "name": _text(a.xpath(".//h2")),
                    "image": urljoin(base_url, _text(a.xpath(".//img/@src")) or ""),
                    "condition": _text(
                        a.xpath('.//span[contains(@class,"text-used-gray")]')
                    ),
                    "price": price,
                    "original_price": orig,
                    "currency": "$",
                    "discount_label": _text(
                        a.xpath('.//span[contains(@class,"text-save")]')
                    ),
                    "tag": _text(
                        entry.xpath('.//div[contains(@class,"text-thumbnail")]')
                    ),
                }
            )
    return items


def parse_reviews(tree) -> Dict[str, Any]:
    """Extract reviews from the listing page."""

    sections = tree.xpath('//section[contains(@class,"customer-reviews")]')
    if not sections:
        return None
    root = sections[0]
    total_text = _text(root.xpath('.//a[contains(@class,"all-reviews")]'))
    total_match = re.search(r"(\d+)", total_text) if total_text else None
    avg = (
        len(
            root.xpath(
                './/div[contains(@class,"score-reviews")]//span[contains(@class,"score-star-total") and contains(@class,"full")]'
            )
        )
        or None
    )
    reviews = []
    for wrap in root.xpath('.//div[contains(@class,"review-item-wrap")]'):
        rid = (wrap.get("id") or "").replace("review-", "") or None
        rating = (
            len(
                wrap.xpath(
                    './/div[contains(@class,"review-score")]//span[contains(@class,"score-star-review") and contains(@class,"full")]'
                )
            )
            or None
        )
        name_block = wrap.xpath(
            './/div[contains(@class,"review-contents")]/div[contains(@class,"name")]'
        )
        reviewer_name = reviewer_country = review_date = None
        verified = False
        if name_block:
            nb = name_block[0]
            full = _text(nb)
            if full:
                m = re.match(r"^(.*?)\s*\(([^)]+)\)", full)
                if m:
                    reviewer_name, reviewer_country = (
                        m.group(1).strip(),
                        m.group(2).strip(),
                    )
            review_date = _text(nb.xpath('.//span[contains(@class,"date")]'))
            verified = (
                "verified"
                in (_text(nb.xpath('.//span[contains(@class,"type")]')) or "").lower()
            )
        reviews.append(
            {
                "review_id": rid,
                "rating": rating,
                "reviewer_name": reviewer_name,
                "reviewer_country": reviewer_country,
                "date": review_date,
                "verified_buyer": verified,
                "text": _text(wrap.xpath('.//p[contains(@class,"review-text")]')),
            }
        )
    return {
        "total_reviews_text": total_text,
        "total_reviews_count": int(total_match.group(1)) if total_match else None,
        "average_rating": avg,
        "reviews_scraped": len(reviews),
        "reviews": reviews,
    }
