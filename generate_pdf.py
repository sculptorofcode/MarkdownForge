from fpdf import FPDF
import re
import os

class PDF(FPDF):
    def header(self):
        # Add a header with better styling
        self.set_font("NotoSans", "B", 16)
        self.set_text_color(0, 51, 102)  # Dark blue color
        self.set_line_width(0.5)
        self.line(10, self.get_y(), self.w - 10, self.get_y())
        self.ln(10)

    def footer(self):
        # Add a footer with page numbers
        self.set_y(-15)
        self.set_font("NotoSans", "I", 8)
        self.set_text_color(128, 128, 128)  # Gray color
        self.cell(0, 10, f"Page {self.page_no()}", align="C")

    def chapter_title(self, title, level=1):
        # Format titles based on heading level
        if level == 1:
            self.set_font("NotoSans", "B", 14)
            self.set_text_color(0, 51, 102)  # Dark blue
            self.cell(0, 10, title, ln=True)
            self.line(10, self.get_y(), self.w - 10, self.get_y())
        elif level == 2:
            self.set_font("NotoSans", "B", 12)
            self.set_text_color(51, 51, 51)  # Dark gray
            self.cell(0, 10, title, ln=True)
        else:
            self.set_font("NotoSans", "B", 11)
            self.set_text_color(51, 51, 51)  # Dark gray
            self.cell(0, 10, title, ln=True)
        self.ln(5)

    def chapter_body(self, body):
        self.set_font("NotoSans", "", 10)
        self.set_text_color(0, 0, 0)  # Black text
        self.multi_cell(0, 6, body)
        self.ln()
    
    def add_code_block(self, code):
        self.set_font("Courier", "", 9)
        self.set_fill_color(240, 240, 240)  # Light gray background
        self.multi_cell(0, 6, code, fill=True)
        self.ln(5)
        self.set_font("NotoSans", "", 10)  # Reset font

    def add_bullet_point(self, text, indent_level=0, number=None):
        """Add a bullet point or numbered item with proper indentation"""
        indent = 5 + (indent_level * 5)  # 5mm per indent level
        self.set_font("NotoSans", "", 10)
        self.set_text_color(0, 0, 0)
        
        # Save current x position
        x_pos = self.get_x()
        
        # Move to indent position and add bullet symbol or number
        self.set_x(x_pos + indent)
        
        if number:
            # This is a numbered item
            bullet_width = self.get_string_width(f"{number}. ")
            self.cell(bullet_width, 6, f"{number}. ", 0, 0)
            bullet_offset = bullet_width
        else:
            # This is a regular bullet point
            self.cell(5, 6, "•", 0, 0)
            bullet_offset = 5
        
        # Add the text with proper wrapping
        self.set_x(x_pos + indent + bullet_offset)  # Add space after bullet/number
        self.multi_cell(self.w - (x_pos + indent + bullet_offset) - 10, 6, text)  # -10 for right margin

    def add_horizontal_line(self):
        """Add a horizontal line across the page"""
        self.ln(2)  # Add some space above the line
        self.set_line_width(0.3)
        self.set_draw_color(200, 200, 200)  # Light gray color
        self.line(10, self.get_y(), self.w - 10, self.get_y())
        self.ln(5)  # Add some space below the line

# Helper function to process text formatting
def process_text_formatting(text):
    # We'll store formatting instructions instead of inserting HTML tags
    result = []
    i = 0
    while i < len(text):
        # Check for bold text
        if text[i:i+2] == '**' and i+2 < len(text):
            # Find closing **
            end = text.find('**', i+2)
            if end != -1:
                result.append(('B', text[i+2:end]))
                i = end + 2
                continue
        
        # Check for italic text
        elif (text[i] == '_' or text[i] == '*') and i+1 < len(text):
            marker = text[i]
            # Find closing marker
            end = text.find(marker, i+1)
            if end != -1 and text[i:i+2] != '**':  # Avoid confusing with bold
                result.append(('I', text[i+1:end]))
                i = end + 1
                continue
        
        # Regular text
        if i < len(text):
            # Collect regular text until next formatting marker
            start = i
            while i < len(text):
                if ((text[i:i+2] == '**') or 
                    (text[i] == '_' and i+1 < len(text)) or 
                    (text[i] == '*' and i+1 < len(text) and text[i:i+2] != '**')):
                    break
                i += 1
            if start < i:
                result.append(('', text[start:i]))
            continue
        
        i += 1
    
    # Encode each part to handle unsupported characters
    return [(style, text.encode('utf-8', 'replace').decode('utf-8')) for style, text in result]

# Modified version of chapter_body to handle formatted text
def render_formatted_text(pdf, formatted_parts):
    x_position = pdf.get_x()
    y_position = pdf.get_y()
    
    for style, text in formatted_parts:
        if not text:  # Skip empty text
            continue
            
        # Set the appropriate font style
        if style == 'B':
            pdf.set_font("NotoSans", "B", 10)
        elif style == 'I':
            pdf.set_font("NotoSans", "I", 10)
        elif style == 'BI':  # Handle bold and italic
            pdf.set_font("NotoSans", "BI", 10)
        else:
            pdf.set_font("NotoSans", "", 10)
        
        width = pdf.get_string_width(text)
        
        # Check if we need to wrap to next line
        if x_position + width > pdf.w - 20:
            pdf.ln()
            x_position = pdf.get_x()
            y_position = pdf.get_y()
        
        # Render the text segment with the appropriate style
        pdf.set_xy(x_position, y_position)
        pdf.cell(width, 6, text, 0, 0)
        x_position += width
    
    pdf.ln()  # Move to next line after processing all parts

# Process text with proper formatting for bullet points
def format_bullet_text(text):
    # Process the text and combine regular text segments
    parts = process_text_formatting(text)
    formatted_text = ""
    for style, part in parts:
        formatted_text += part
    return formatted_text

# Parse markdown content
def parse_markdown(content):
    sections = []
    lines = content.split("\n")
    
    current_section = {"title": "", "level": 0, "content": [], "type": "text"}
    in_code_block = False
    code_content = []
    
    for line in lines:
        # Check for horizontal rule
        if re.match(r'^-{3,}$|^\*{3,}$|^_{3,}$', line.strip()):
            # Add current section if it has content
            if current_section["content"]:
                sections.append(current_section)
                current_section = {"title": "", "level": 0, "content": [], "type": "text"}
            
            # Add a horizontal rule section
            sections.append({"title": "", "level": 0, "content": [], "type": "hr"})
            continue
        
        # Check for headings
        heading_match = re.match(r'^(#{1,6})\s+(.+)$', line)
        
        if in_code_block:
            if line.strip() == "```":
                current_section = {"title": "", "level": 0, "content": code_content, "type": "code"}
                sections.append(current_section)
                code_content = []
                in_code_block = False
                current_section = {"title": "", "level": 0, "content": [], "type": "text"}
            else:
                code_content.append(line)
        elif line.strip() == "```" or line.strip().startswith("```"):
            in_code_block = True
        elif heading_match:
            # If we have content in the current section, add it to sections
            if current_section["content"]:
                sections.append(current_section)
            
            # Create a new section with this heading
            level = len(heading_match.group(1))
            title = heading_match.group(2)
            current_section = {"title": title, "level": level, "content": [], "type": "text"}
        else:
            # Check if the line is a bullet point
            bullet_match = re.match(r'^(\s*[-*+])\s+(.+)$', line)
            # Check if the line is a numbered list item
            numbered_match = re.match(r'^(\s*)(\d+)\.\s+(.+)$', line)
            
            if bullet_match:
                # Mark bullet points with a special prefix that we'll process later
                indent_level = len(bullet_match.group(1)) - 1  # -1 accounts for the bullet character
                bullet_text = bullet_match.group(2)
                current_section["content"].append(f"__BULLET__{indent_level}__" + bullet_text)
            elif numbered_match:
                # Mark numbered items with a special prefix
                indent_level = len(numbered_match.group(1))
                number = numbered_match.group(2)
                numbered_text = numbered_match.group(3)
                current_section["content"].append(f"__NUMBERED__{indent_level}__{number}__" + numbered_text)
            else:
                current_section["content"].append(line)
    
    # Add the last section
    if current_section["content"]:
        sections.append(current_section)
    
    return sections