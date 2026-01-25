from jinja2 import Environment, FileSystemLoader
from xhtml2pdf import pisa
from io import BytesIO
import os
from typing import Dict, Any

import qrcode
from io import BytesIO
import base64

class ReportRenderer:
    def __init__(self, template_dir: str = "app/templates"):
        self.env = Environment(loader=FileSystemLoader(template_dir))

    def render_pdf(self, data: Dict[str, Any]) -> bytes:
        """
        Renders the canonical JSON into a PDF byte stream using xhtml2pdf.
        """
        # Generate QR Code
        qr_data = f"Report No: {data.get('meta', {}).get('report_no', 'N/A')}"
        # If we had a view URL, we'd use that, but for now use Report No or some identifier
        if 'id' in data:
             qr_data = f"https://smrtlab-report-app.vercel.app/view/{data['id']}" # Placeholder URL base
        
        qr = qrcode.QRCode(box_size=4, border=1)
        qr.add_data(qr_data)
        qr.make(fit=True)
        img = qr.make_image(fill_color="black", back_color="white")
        
        buffered = BytesIO()
        img.save(buffered, format="PNG")
        qr_base64 = base64.b64encode(buffered.getvalue()).decode("utf-8")
        
        # Inject QR into data for template
        data['qr_code'] = qr_base64

        template = self.env.get_template("base.html")
        html_content = template.render(report=data)
        
        pdf_buffer = BytesIO()
        pisa_status = pisa.CreatePDF(html_content, dest=pdf_buffer)
        
        if pisa_status.err:
            raise Exception("PDF generation failed")
            
        return pdf_buffer.getvalue()
