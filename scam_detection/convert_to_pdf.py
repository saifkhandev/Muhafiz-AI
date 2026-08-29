"""Convert REEVALUATION_PROPOSAL.md to a styled PDF using fpdf2."""
import re, sys, os
from fpdf import FPDF

PYTHON = sys.executable
MD_PATH = os.path.join(os.path.dirname(__file__), "REEVALUATION_PROPOSAL.md")
PDF_PATH = os.path.join(os.path.dirname(__file__), "REEVALUATION_PROPOSAL.pdf")


class ProposalPDF(FPDF):
    def header(self):
        if self.page_no() > 1:
            self.set_font("Helvetica", "I", 8)
            self.set_text_color(130, 130, 130)
            self.cell(0, 5, "Alibaba Cloud AI Hackathon Pakistan 2026 - Re-Evaluation Proposal", align="C")
            self.ln(8)

    def footer(self):
        self.set_y(-15)
        self.set_font("Helvetica", "I", 8)
        self.set_text_color(150, 150, 150)
        self.cell(0, 10, f"Page {self.page_no()}/{{nb}}", align="C")

    def chapter_title(self, title, level=1):
        if level == 1:
            self.set_font("Helvetica", "B", 18)
            self.set_text_color(15, 60, 130)
            self.ln(4)
            self.multi_cell(0, 10, title)
            self.set_draw_color(15, 60, 130)
            self.set_line_width(0.6)
            self.line(self.l_margin, self.get_y() + 1, self.w - self.r_margin, self.get_y() + 1)
            self.ln(6)
        elif level == 2:
            self.set_font("Helvetica", "B", 14)
            self.set_text_color(30, 80, 160)
            self.ln(3)
            self.multi_cell(0, 8, title)
            self.set_draw_color(180, 200, 230)
            self.set_line_width(0.3)
            self.line(self.l_margin, self.get_y() + 1, self.w - self.r_margin, self.get_y() + 1)
            self.ln(4)
        elif level == 3:
            self.set_font("Helvetica", "B", 12)
            self.set_text_color(50, 50, 50)
            self.ln(2)
            self.multi_cell(0, 7, title)
            self.ln(3)
        elif level == 4:
            self.set_font("Helvetica", "BI", 11)
            self.set_text_color(70, 70, 70)
            self.ln(1)
            self.multi_cell(0, 7, title)
            self.ln(2)

    def body_text(self, text):
        self.set_font("Helvetica", "", 10)
        self.set_text_color(40, 40, 40)
        # Handle bold markers **...**
        parts = re.split(r'(\*\*.*?\*\*)', text)
        for part in parts:
            if part.startswith('**') and part.endswith('**'):
                self.set_font("Helvetica", "B", 10)
                self.write(5, part[2:-2])
                self.set_font("Helvetica", "", 10)
            else:
                self.write(5, part)
        self.ln(5)

    def bullet_item(self, text, indent=0):
        x = self.l_margin + indent
        self.set_x(x)
        self.set_font("Helvetica", "", 10)
        self.set_text_color(40, 40, 40)
        bullet = "-  "
        self.write(5, bullet)
        parts = re.split(r'(\*\*.*?\*\*)', text)
        for part in parts:
            if part.startswith('**') and part.endswith('**'):
                self.set_font("Helvetica", "B", 10)
                self.write(5, part[2:-2])
                self.set_font("Helvetica", "", 10)
            else:
                self.write(5, part)
        self.ln(5)

    def checkbox_item(self, text, checked=True):
        self.set_x(self.l_margin)
        self.set_font("Helvetica", "", 10)
        self.set_text_color(40, 40, 40)
        mark = "[x] " if checked else "[ ] "
        self.write(5, mark)
        parts = re.split(r'(\*\*.*?\*\*)', text)
        for part in parts:
            if part.startswith('**') and part.endswith('**'):
                self.set_font("Helvetica", "B", 10)
                self.write(5, part[2:-2])
                self.set_font("Helvetica", "", 10)
            elif '`' in part:
                subparts = re.split(r'(`[^`]+`)', part)
                for sp in subparts:
                    if sp.startswith('`') and sp.endswith('`'):
                        self.set_font("Courier", "", 9)
                        self.set_text_color(180, 50, 50)
                        self.write(5, sp[1:-1])
                        self.set_font("Helvetica", "", 10)
                        self.set_text_color(40, 40, 40)
                    else:
                        self.write(5, sp)
            else:
                self.write(5, part)
        self.ln(5)

    def numbered_item(self, num, text):
        self.set_x(self.l_margin)
        self.set_font("Helvetica", "B", 10)
        self.set_text_color(15, 60, 130)
        self.write(5, f"{num}. ")
        self.set_font("Helvetica", "", 10)
        self.set_text_color(40, 40, 40)
        parts = re.split(r'(\*\*.*?\*\*)', text)
        for part in parts:
            if part.startswith('**') and part.endswith('**'):
                self.set_font("Helvetica", "B", 10)
                self.write(5, part[2:-2])
                self.set_font("Helvetica", "", 10)
            else:
                self.write(5, part)
        self.ln(5)

    def code_block(self, lines):
        self.set_fill_color(245, 245, 250)
        self.set_draw_color(200, 200, 210)
        self.set_font("Courier", "", 8)
        self.set_text_color(50, 50, 60)
        y_start = self.get_y()
        block_h = len(lines) * 4.2 + 6
        if y_start + block_h > self.h - 20:
            self.add_page()
            y_start = self.get_y()
        self.rect(self.l_margin, y_start, self.w - self.l_margin - self.r_margin, block_h, style="DF")
        self.set_y(y_start + 3)
        for line in lines:
            self.set_x(self.l_margin + 3)
            self.cell(0, 4.2, sanitize(line[:95]))
            self.ln(4.2)
        self.ln(5)

    def draw_table(self, headers, rows):
        col_count = len(headers)
        avail_w = self.w - self.l_margin - self.r_margin
        col_w = avail_w / col_count

        # Estimate row heights
        self.set_font("Helvetica", "", 8)
        row_height = 7

        # Check if table fits; if not, reduce font
        total_h = (len(rows) + 1) * row_height + 10
        if self.get_y() + total_h > self.h - 20:
            self.add_page()

        # Header
        self.set_fill_color(15, 60, 130)
        self.set_text_color(255, 255, 255)
        self.set_font("Helvetica", "B", 7.5)
        for h in headers:
            self.cell(col_w, row_height, h.strip()[:25], border=1, fill=True, align="C")
        self.ln()

        # Rows
        self.set_text_color(40, 40, 40)
        fill_toggle = False
        for row in rows:
            if fill_toggle:
                self.set_fill_color(240, 245, 255)
            else:
                self.set_fill_color(255, 255, 255)
            self.set_font("Helvetica", "", 7.5)
            for i, cell in enumerate(row):
                cell_text = sanitize(cell.strip().replace('**', '')[:30])
                align = "C" if i > 0 and len(cell_text) < 15 else "L"
                self.cell(col_w, row_height, cell_text, border=1, fill=True, align=align)
            self.ln()
            fill_toggle = not fill_toggle
        self.ln(4)


def sanitize(text):
    """Replace unicode chars outside latin-1 with ASCII equivalents."""
    replacements = {
        '\u2014': '--',   # em dash
        '\u2013': '-',    # en dash
        '\u2018': "'",    # left single quote
        '\u2019': "'",    # right single quote
        '\u201c': '"',    # left double quote
        '\u201d': '"',    # right double quote
        '\u2026': '...',  # ellipsis
        '\u2022': '-',    # bullet
        '\u2192': '->',   # right arrow
        '\u2190': '<-',   # left arrow
        '\u2265': '>=',   # >=
        '\u2264': '<=',   # <=
        '\u00d7': 'x',    # multiplication sign
        '\u2010': '-',    # hyphen
        '\u2011': '-',    # non-breaking hyphen
        '\u2012': '-',    # figure dash
        '\u00b2': '^2',   # superscript 2
        '\u2212': '-',    # minus sign
        '\u2500': '-',    # box drawing horizontal
        '\u2502': '|',    # box drawing vertical
        '\u250c': '+',    # box drawing top-left
        '\u2510': '+',    # box drawing top-right
        '\u2514': '+',    # box drawing bottom-left
        '\u2518': '+',    # box drawing bottom-right
        '\u251c': '+',    # box drawing tee right
        '\u2524': '+',    # box drawing tee left
        '\u252c': '+',    # box drawing tee down
        '\u2534': '+',    # box drawing tee up
        '\u253c': '+',    # box drawing cross
        '\u25ba': '>',    # right pointer
        '\u25bc': 'v',    # down pointer
    }
    for old, new in replacements.items():
        text = text.replace(old, new)
    # Drop any remaining non-latin-1 chars
    result = []
    for ch in text:
        try:
            ch.encode('latin-1')
            result.append(ch)
        except UnicodeEncodeError:
            result.append('?')
    return ''.join(result)


def parse_and_render(pdf, md_text):
    lines = md_text.split('\n')
    i = 0
    in_code_block = False
    code_lines = []

    while i < len(lines):
        line = lines[i]
        line = sanitize(line)

        # Horizontal rule
        if line.strip() == '---':
            i += 1
            continue

        # Code block start/end
        if line.strip().startswith('```'):
            if in_code_block:
                pdf.code_block(code_lines)
                code_lines = []
                in_code_block = False
            else:
                in_code_block = True
            i += 1
            continue

        if in_code_block:
            code_lines.append(line)
            i += 1
            continue

        # Headings
        m = re.match(r'^(#{1,4})\s+(.*)', line)
        if m:
            level = len(m.group(1))
            title = m.group(2).replace('**', '')
            pdf.chapter_title(title, level)
            i += 1
            continue

        # Checkbox items
        m = re.match(r'^- \[([ x])\] (.*)', line)
        if m:
            pdf.checkbox_item(m.group(2), m.group(1) == 'x')
            i += 1
            continue

        # Bullet items
        m = re.match(r'^(\s*)- (.*)', line)
        if m:
            indent = len(m.group(1)) * 2
            pdf.bullet_item(m.group(2), indent)
            i += 1
            continue

        # Numbered items
        m = re.match(r'^(\d+)\.\s+(.*)', line)
        if m:
            pdf.numbered_item(int(m.group(1)), m.group(2))
            i += 1
            continue

        # Table detection
        if '|' in line and i + 1 < len(lines) and re.match(r'^[\|\-\s:]+$', lines[i + 1].strip()):
            headers = [c.strip() for c in line.split('|') if c.strip()]
            i += 2  # skip header + separator
            rows = []
            while i < len(lines) and '|' in lines[i]:
                cells = [c.strip() for c in lines[i].split('|') if c.strip()]
                rows.append(cells)
                i += 1
            pdf.draw_table(headers, rows)
            continue

        # Empty line
        if line.strip() == '':
            pdf.ln(2)
            i += 1
            continue

        # Regular paragraph
        pdf.body_text(line.strip())
        i += 1


def main():
    with open(MD_PATH, 'r', encoding='utf-8') as f:
        md_text = f.read()

    pdf = ProposalPDF(orientation='P', unit='mm', format='A4')
    pdf.alias_nb_pages()
    pdf.set_auto_page_break(auto=True, margin=20)
    pdf.set_margins(18, 15, 18)
    pdf.add_page()

    # Title page
    pdf.set_font("Helvetica", "B", 26)
    pdf.set_text_color(15, 60, 130)
    pdf.ln(30)
    pdf.multi_cell(0, 14, "Alibaba Cloud\nAI Hackathon\nPakistan 2026", align="C")
    pdf.ln(8)
    pdf.set_font("Helvetica", "", 16)
    pdf.set_text_color(80, 80, 80)
    pdf.cell(0, 10, "Project Re-Evaluation Proposal", align="C")
    pdf.ln(15)
    pdf.set_draw_color(15, 60, 130)
    pdf.set_line_width(0.8)
    mid = pdf.w / 2
    pdf.line(mid - 40, pdf.get_y(), mid + 40, pdf.get_y())
    pdf.ln(15)
    pdf.set_font("Helvetica", "", 12)
    pdf.set_text_color(60, 60, 60)
    pdf.cell(0, 8, "Grade 2A to Grade 1 Re-Evaluation", align="C")
    pdf.ln(8)
    pdf.cell(0, 8, "Scam Detection ML System", align="C")
    pdf.ln(8)
    pdf.cell(0, 8, "Multilingual SMS Fraud Classification", align="C")
    pdf.ln(20)
    pdf.set_font("Helvetica", "I", 10)
    pdf.set_text_color(120, 120, 120)
    pdf.cell(0, 6, "Submitted: 28 August 2026", align="C")
    pdf.ln(6)
    pdf.cell(0, 6, "Build Phase Deadline: 4 September 2026", align="C")

    # Content pages
    pdf.add_page()
    parse_and_render(pdf, md_text)

    pdf.output(PDF_PATH)
    print(f"PDF generated: {PDF_PATH}")


if __name__ == "__main__":
    main()
