"""BOT USD parser 0.1.1 / selector 0.1.0. Strict finite layouts; no network I/O."""

PARSER_VERSION = '0.1.1'
SELECTOR_VERSION = '0.1.0'

from calendar import monthrange
from datetime import date
from decimal import Decimal
import re


class QuoteError(ValueError):
    pass


def iso_date(value):
    if not isinstance(value, str) or not re.fullmatch(r"[0-9]{4}-[0-9]{2}-[0-9]{2}", value):
        raise QuoteError("invalid_date")
    try:
        return date.fromisoformat(value)
    except ValueError:
        raise QuoteError("invalid_date") from None


def select_monthly_usd_quote(table, target_month):
    if not isinstance(target_month, str) or not re.fullmatch(r"[0-9]{4}-[0-9]{2}", target_month):
        raise QuoteError("invalid_month")
    try:
        year, month = map(int, target_month.split("-"))
        start = date(year, month, 15)
        last = date(year, month, monthrange(year, month)[1])
    except ValueError:
        raise QuoteError("invalid_month") from None
    columns = ["date", "currency", "cash_buy", "cash_sell", "spot_buy", "spot_sell"]
    if table.get("schema_version") != "0.1.0" or table.get("columns") != columns:
        raise QuoteError("schema_changed")
    as_of = iso_date(table["as_of"])
    if as_of < start:
        raise QuoteError("not_yet_available")
    coverage = table["coverage"]
    if (coverage.get("complete") is not True
            or iso_date(coverage["from"]) > start
            or iso_date(coverage["to"]) < min(as_of, last)):
        raise QuoteError("coverage_incomplete")
    candidates = []
    for row in table["rows"]:
        day = iso_date(row["date"])
        if day > as_of:
            raise QuoteError("future_row")
        if row["currency"] == "USD" and (day.year, day.month) == (year, month) and day >= start:
            candidates.append((day, row))
    if not candidates:
        raise QuoteError("no_available_date")
    selected = min(day for day, row in candidates)
    prices = set()
    for day, row in candidates:
        if day != selected:
            continue
        value = row["spot_sell"]
        if not isinstance(value, str) or len(value) > 32 or not re.fullmatch(r"[0-9]+(?:\.[0-9]+)?", value):
            raise QuoteError("invalid_rate")
        amount = Decimal(value)
        if not amount.is_finite() or amount <= 0:
            raise QuoteError("invalid_rate")
        prices.add(amount)
    if len(prices) != 1:
        raise QuoteError("ambiguous_rate")
    text = format(next(iter(prices)), "f")
    if "." in text:
        text = text.rstrip("0").rstrip(".")
    return {"target_month": target_month, "selected_date": selected.isoformat(),
            "currency": "USD", "rate_type": "spot", "direction": "bank_sell",
            "sell_rate": text}

from datetime import datetime
from html.parser import HTMLParser
from zoneinfo import ZoneInfo

COLUMNS = ['date', 'currency', 'cash_buy', 'cash_sell', 'spot_buy', 'spot_sell']


class _Table(HTMLParser):
    def __init__(self):
        super().__init__(convert_charrefs=True)
        self.depth = 0; self.count = 0; self.rows = []; self.row = None; self.cell = None; self.ignore = 0

    def handle_starttag(self, tag, attrs):
        if tag in ('script', 'style'):
            self.ignore += 1
        if tag == 'table':
            self.depth += 1; self.count += 1
            if self.depth != 1 or self.count != 1:
                raise QuoteError('schema_changed')
        if self.depth and tag == 'tr':
            if self.row is not None:
                raise QuoteError('schema_changed')
            self.row = []
        if self.depth and tag in ('td', 'th'):
            if self.row is None or self.cell is not None:
                raise QuoteError('schema_changed')
            attrs = dict(attrs)
            try:
                down, across = int(attrs.get('rowspan', '1')), int(attrs.get('colspan', '1'))
                if not 1 <= down <= 2 or not 1 <= across <= 6:
                    raise ValueError()
            except ValueError:
                raise QuoteError('schema_changed') from None
            self.cell = [tag, down, across, '', frozenset(attrs.get('class', '').split())]

    def handle_data(self, data):
        if self.cell is not None and not self.ignore:
            self.cell[3] += data

    def handle_endtag(self, tag):
        if tag in ('script', 'style'):
            self.ignore = max(0, self.ignore - 1)
        if tag in ('td', 'th') and self.cell is not None:
            self.row.append(self.cell); self.cell = None
        if tag == 'tr' and self.row is not None:
            if self.cell is not None:
                raise QuoteError('schema_changed')
            self.rows.append(self.row); self.row = None
        if tag == 'table':
            self.depth -= 1


def _header_rows(rows):
    """Normalize only BOT's observed seven-cell JavaScript header layout.

    Keep responsive cash/spot/currency cells. Never drop arbitrary hidden cells,
    nonempty spacer cells, data rows, or contradictory duplicate date headings.
    """
    first, second = rows[:2]
    if len(first) != 7:
        return first, second

    def date_cell(cell, classes):
        tag, down, across, text, actual = cell
        return (tag == 'th' and down == 2 and across == 1 and actual == classes
                and re.sub(r'\s+', '', text) in ('掛牌日期', '日期', 'Date'))

    def spacer(cell):
        tag, down, across, text, classes = cell
        return tag == 'th' and down == across == 1 and not text.strip() and classes == {'hidden'}

    if (not date_cell(first[0], {'noscript'})
            or not date_cell(first[1], {'rowSP_Ctrl_2_2_2', 'hasscript'})
            or re.sub(r'\s+', '', first[0][3]) != re.sub(r'\s+', '', first[1][3])
            or not spacer(first[4]) or not spacer(first[6])):
        raise QuoteError('schema_changed')
    return [first[index] for index in (1, 2, 3, 5)], second


def parse_bot_usd_table(snapshot):
    """Provider-attested completeness plus strict headers/date bounds; no guessed cells."""
    if snapshot.get('complete') is not True or snapshot.get('pagination_complete') is not True:
        raise QuoteError('coverage_incomplete')
    html = snapshot.get('table_html')
    if not isinstance(html, str) or not 0 < len(html) <= 1500000:
        raise QuoteError('schema_changed')
    parser = _Table()
    parser.feed(html); parser.close()
    if parser.depth or parser.row is not None or parser.cell is not None or parser.count != 1 or not 3 <= len(parser.rows) <= 1000:
        raise QuoteError('schema_changed')
    # Normalize the known alternate headers before checking the six-column grid.
    headers = _header_rows(parser.rows)
    grid = [[None] * 6 for _ in range(2)]
    for r in range(2):
        column = 0
        for tag, down, across, text, classes in headers[r]:
            while column < 6 and grid[r][column] is not None:
                column += 1
            if tag != 'th' or classes & {'hidden', 'noscript'} or r + down > 2 or column + across > 6:
                raise QuoteError('schema_changed')
            for rr in range(r, r + down):
                for cc in range(column, column + across):
                    if grid[rr][cc] is not None:
                        raise QuoteError('schema_changed')
                    grid[rr][cc] = re.sub(r'\s+', '', text)
            column += across
    if any(value is None for row in grid for value in row):
        raise QuoteError('schema_changed')
    chinese = [['掛牌日期', '幣別', '現金匯率', '現金匯率', '即期匯率', '即期匯率'],
               ['掛牌日期', '幣別', '本行買入', '本行賣出', '本行買入', '本行賣出']]
    english = [['Date', 'Currency', 'CashRate', 'CashRate', 'SpotRate', 'SpotRate'],
               ['Date', 'Currency', 'BankBuying', 'BankSelling', 'BankBuying', 'BankSelling']]
    # The bank has used both 日期 and 掛牌日期 in otherwise identical tables.
    if grid[0][0] == grid[1][0] == '日期':
        grid[0][0] = grid[1][0] = '掛牌日期'
    if grid not in (chinese, english):
        raise QuoteError('schema_changed')
    dates = re.findall(r'(?<![0-9])[0-9]{4}[-/][0-9]{2}[-/][0-9]{2}(?![0-9])', snapshot.get('range_text', ''))
    if len(dates) != 2:
        raise QuoteError('coverage_incomplete')
    first, last = [iso_date(value.replace('/', '-')) for value in dates]
    if first > last:
        raise QuoteError('coverage_incomplete')
    try:
        captured = datetime.fromisoformat(snapshot['captured_at'])
        if captured.tzinfo is None:
            raise ValueError()
        as_of = captured.astimezone(ZoneInfo('Asia/Taipei')).date()
    except (ValueError, TypeError, KeyError):
        raise QuoteError('invalid_date') from None
    rows = []
    for raw in parser.rows[2:]:
        if len(raw) != 6 or any(tag != 'td' or down != 1 or across != 1 for tag, down, across, text, classes in raw):
            raise QuoteError('schema_changed')
        cells = [text.strip() for tag, down, across, text, classes in raw]
        day = iso_date(cells[0].replace('/', '-'))
        if not first <= day <= last:
            raise QuoteError('coverage_incomplete')
        if re.sub(r'\s+', '', cells[1]) not in ('USD', '美金(USD)', '美元(USD)'):
            raise QuoteError('schema_changed')
        cells[0] = day.isoformat(); cells[1] = 'USD'
        rows.append(dict(zip(COLUMNS, cells)))
    return dict(schema_version='0.1.0', columns=COLUMNS, as_of=as_of.isoformat(),
                coverage={'from': first.isoformat(), 'to': last.isoformat(), 'complete': True}, rows=rows)
