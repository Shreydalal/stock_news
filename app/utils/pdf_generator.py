import logging
from pathlib import Path
from reportlab.lib.pagesizes import letter
from reportlab.lib import colors
from reportlab.platypus import SimpleDocTemplate, Paragraph, Spacer, Table, TableStyle
from reportlab.lib.styles import getSampleStyleSheet, ParagraphStyle
from reportlab.lib.enums import TA_CENTER, TA_LEFT

logger = logging.getLogger(__name__)

def generate_pdf_from_markdown(markdown_content: str, output_path: Path) -> Path:
    """
    Parses simple markdown syntax (headers, lists, paragraphs) and creates
    a beautifully formatted PDF report at the output_path using ReportLab.
    """
    try:
        # Create PDF document
        doc = SimpleDocTemplate(
            str(output_path),
            pagesize=letter,
            rightMargin=54, leftMargin=54, topMargin=54, bottomMargin=54
        )
        
        story = []
        
        # Styles
        styles = getSampleStyleSheet()
        
        # Custom styles for premium look
        title_style = ParagraphStyle(
            name='PDFTitle',
            parent=styles['Normal'],
            fontName='Helvetica-Bold',
            fontSize=22,
            leading=26,
            textColor=colors.HexColor('#0F172A'), # Navy Slate
            alignment=TA_LEFT,
            spaceAfter=20
        )
        
        h1_style = ParagraphStyle(
            name='PDFH1',
            parent=styles['Normal'],
            fontName='Helvetica-Bold',
            fontSize=15,
            leading=19,
            textColor=colors.HexColor('#1E3A8A'), # Deep Blue
            spaceBefore=14,
            spaceAfter=8,
            keepWithNext=True
        )

        h2_style = ParagraphStyle(
            name='PDFH2',
            parent=styles['Normal'],
            fontName='Helvetica-Bold',
            fontSize=12,
            leading=16,
            textColor=colors.HexColor('#0D9488'), # Teal
            spaceBefore=10,
            spaceAfter=6,
            keepWithNext=True
        )

        body_style = ParagraphStyle(
            name='PDFBody',
            parent=styles['Normal'],
            fontName='Helvetica',
            fontSize=10,
            leading=14,
            textColor=colors.HexColor('#334155'), # Slate Gray
            spaceAfter=8
        )

        bullet_style = ParagraphStyle(
            name='PDFBullet',
            parent=styles['Normal'],
            fontName='Helvetica',
            fontSize=10,
            leading=14,
            textColor=colors.HexColor('#334155'),
            leftIndent=15,
            firstLineIndent=-10,
            spaceAfter=4
        )

        # Parse markdown lines
        lines = markdown_content.split('\n')
        in_list = False
        
        for line in lines:
            stripped = line.strip()
            
            if not stripped:
                continue
                
            # Headers
            if stripped.startswith('# '):
                story.append(Paragraph(stripped[2:], title_style))
                story.append(Spacer(1, 10))
            elif stripped.startswith('## '):
                story.append(Paragraph(stripped[3:], h1_style))
            elif stripped.startswith('### '):
                story.append(Paragraph(stripped[4:], h2_style))
            # Bullet points
            elif stripped.startswith('- ') or stripped.startswith('* '):
                bullet_text = f"&bull; {stripped[2:]}"
                # Clean simple Markdown bold markers inside bullets
                bullet_text = bullet_text.replace('**', '<b>', 1).replace('**', '</b>', 1)
                # Keep replacing any remaining bold markers
                while '**' in bullet_text:
                    bullet_text = bullet_text.replace('**', '<b>', 1).replace('**', '</b>', 1)
                story.append(Paragraph(bullet_text, bullet_style))
            # Standard paragraphs
            else:
                p_text = stripped
                # Clean simple Markdown bold markers
                while '**' in p_text:
                    p_text = p_text.replace('**', '<b>', 1).replace('**', '</b>', 1)
                story.append(Paragraph(p_text, body_style))
                
        # Build PDF
        doc.build(story)
        logger.info(f"Successfully compiled PDF report at {output_path}")
        return output_path
        
    except Exception as e:
        logger.error(f"Failed to generate PDF from markdown: {e}", exc_info=True)
        raise e
