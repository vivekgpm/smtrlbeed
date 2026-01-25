from fastapi import APIRouter, UploadFile, File, HTTPException
from fastapi.responses import JSONResponse, Response

router = APIRouter()

@router.post("/generate-report")
async def generate_report_endpoint(file: UploadFile = File(...)):
    if not file.filename.endswith(".xlsx"):
        raise HTTPException(status_code=400, detail="Invalid file type. Only .xlsx supported.")
    
    try:
        # 1. Parse Excel
        from app.engine.parser import ExcelParser
        from app.engine.detector import TestDetector
        from app.engine.normalizer import Normalizer
        from app.engine.renderer import ReportRenderer
        
        parser = ExcelParser(file.file)
        sheets_data = parser.get_all_sheets_data()
        
        # For this MVP, we just take the first sheet or iterate
        # Assuming single test per sheet for simplicity in MVP, but architecture allows multiple
        first_sheet = list(sheets_data.values())[0] if sheets_data else []
        
        if not first_sheet:
             raise HTTPException(status_code=400, detail="Excel file is empty")

        # 2. Detect & Normalize
        detector = TestDetector()
        detection = detector.detect_test_type(first_sheet)
        
        if not detection["test_type"]:
             # Fallback or error? MVP: Error
             raise HTTPException(status_code=400, detail="Could not identify test type" + str(detection))
             
        normalizer = Normalizer(first_sheet, detection["test_type"])
        canonical_json = normalizer.normalize()
        
        # 3. Render PDF
        renderer = ReportRenderer()
        pdf_bytes = renderer.render_pdf(canonical_json)
        
        return Response(content=pdf_bytes, media_type="application/pdf")
        
    except Exception as e:
        import traceback
        error_trace = traceback.format_exc()
        print("-------------- API ERROR --------------")
        print(f"Error processing file {file.filename}: {str(e)}")
        print(error_trace)
        print("---------------------------------------")
        return JSONResponse(status_code=500, content={"message": str(e), "trace": error_trace})
