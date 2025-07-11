"""
Web application for PDF Enrichment Platform

FastAPI-based HTTP interface for PDF form analysis and field modification.
"""

import logging
from pathlib import Path
from typing import Dict, List, Optional

from fastapi import FastAPI, File, Form, HTTPException, UploadFile
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import FileResponse, HTMLResponse
from pydantic import BaseModel

from ..pdf_enrichment import FieldAnalyzer, PDFModifier, PreviewGenerator
from ..pdf_enrichment.field_types import FormAnalysis, FieldModificationResult


logger = logging.getLogger(__name__)

app = FastAPI(
    title="PDF Enrichment Platform",
    description="Transform PDF forms into structured APIs with BEM-style field naming",
    version="0.1.0",
)

# Enable CORS for development
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Initialize services
field_analyzer = FieldAnalyzer()
pdf_modifier = PDFModifier()
preview_generator = PreviewGenerator()


class AnalysisRequest(BaseModel):
    """Request model for PDF analysis."""
    analysis_mode: str = "comprehensive"
    custom_sections: Optional[List[str]] = None


class ModificationRequest(BaseModel):
    """Request model for field modification."""
    field_mappings: Dict[str, str]
    preserve_original: bool = True
    validate_mappings: bool = True


@app.get("/")
async def root() -> Dict[str, str]:
    """Root endpoint with API information."""
    return {
        "name": "PDF Enrichment Platform",
        "version": "0.1.0",
        "description": "Transform PDF forms into structured APIs",
        "endpoints": {
            "analyze": "/analyze",
            "modify": "/modify", 
            "health": "/health",
            "docs": "/docs",
        }
    }


@app.get("/health")
async def health_check() -> Dict[str, str]:
    """Health check endpoint."""
    return {"status": "healthy", "service": "pdf-enrichment-platform"}


@app.post("/analyze")
async def analyze_pdf(
    file: UploadFile = File(...),
    analysis_mode: str = Form("comprehensive"),
    custom_sections: Optional[str] = Form(None),
) -> Dict:
    """Analyze PDF form and generate BEM field names."""
    try:
        # Validate file
        if not file.filename or not file.filename.endswith('.pdf'):
            raise HTTPException(status_code=400, detail="File must be a PDF")
        
        # Save uploaded file temporarily
        temp_path = Path(f"/tmp/{file.filename}")
        with temp_path.open("wb") as buffer:
            content = await file.read()
            buffer.write(content)
        
        # Parse custom sections
        sections = None
        if custom_sections:
            sections = [s.strip() for s in custom_sections.split(",") if s.strip()]
        
        # Run analysis
        analysis = await field_analyzer.analyze_form(
            pdf_path=temp_path,
            analysis_mode=analysis_mode,
            custom_sections=sections
        )
        
        # Clean up temp file
        temp_path.unlink(missing_ok=True)
        
        return analysis.model_dump(mode="json")
        
    except Exception as e:
        logger.exception("Error analyzing PDF")
        raise HTTPException(status_code=500, detail=f"Analysis failed: {str(e)}")


@app.post("/analyze/preview")
async def analyze_pdf_with_preview(
    file: UploadFile = File(...),
    analysis_mode: str = Form("comprehensive"),
    custom_sections: Optional[str] = Form(None),
) -> HTMLResponse:
    """Analyze PDF and return HTML preview."""
    try:
        # Validate file
        if not file.filename or not file.filename.endswith('.pdf'):
            raise HTTPException(status_code=400, detail="File must be a PDF")
        
        # Save uploaded file temporarily
        temp_path = Path(f"/tmp/{file.filename}")
        with temp_path.open("wb") as buffer:
            content = await file.read()
            buffer.write(content)
        
        # Parse custom sections
        sections = None
        if custom_sections:
            sections = [s.strip() for s in custom_sections.split(",") if s.strip()]
        
        # Run analysis
        analysis = await field_analyzer.analyze_form(
            pdf_path=temp_path,
            analysis_mode=analysis_mode,
            custom_sections=sections
        )
        
        # Generate HTML preview
        html_content = preview_generator.generate_field_review_html(analysis)
        
        # Clean up temp file
        temp_path.unlink(missing_ok=True)
        
        return HTMLResponse(content=html_content)
        
    except Exception as e:
        logger.exception("Error analyzing PDF with preview")
        raise HTTPException(status_code=500, detail=f"Analysis failed: {str(e)}")


@app.post("/modify")
async def modify_pdf(
    file: UploadFile = File(...),
    field_mappings: str = Form(...),
    preserve_original: bool = Form(True),
    validate_mappings: bool = Form(True),
) -> FileResponse:
    """Modify PDF form fields using BEM name mappings."""
    try:
        # Validate file
        if not file.filename or not file.filename.endswith('.pdf'):
            raise HTTPException(status_code=400, detail="File must be a PDF")
        
        # Parse field mappings
        import json
        try:
            mappings = json.loads(field_mappings)
        except json.JSONDecodeError:
            raise HTTPException(status_code=400, detail="Invalid field mappings JSON")
        
        # Save uploaded file temporarily
        temp_input_path = Path(f"/tmp/input_{file.filename}")
        temp_output_path = Path(f"/tmp/output_{file.filename}")
        
        with temp_input_path.open("wb") as buffer:
            content = await file.read()
            buffer.write(content)
        
        # Run modification
        result = await pdf_modifier.modify_fields(
            pdf_path=temp_input_path,
            field_mappings=mappings,
            output_path=temp_output_path,
            preserve_original=preserve_original,
            validate_mappings=validate_mappings,
        )
        
        if not result.success:
            # Clean up temp files
            temp_input_path.unlink(missing_ok=True)
            temp_output_path.unlink(missing_ok=True)
            raise HTTPException(
                status_code=400, 
                detail=f"Modification failed: {'; '.join(result.errors)}"
            )
        
        # Clean up input file
        temp_input_path.unlink(missing_ok=True)
        
        # Return modified PDF
        return FileResponse(
            path=temp_output_path,
            filename=f"modified_{file.filename}",
            media_type="application/pdf",
            background=None,  # Don't delete file immediately
        )
        
    except HTTPException:
        raise
    except Exception as e:
        logger.exception("Error modifying PDF")
        raise HTTPException(status_code=500, detail=f"Modification failed: {str(e)}")


@app.post("/batch/analyze")
async def batch_analyze_pdfs(
    files: List[UploadFile] = File(...),
    consistency_check: bool = Form(True),
) -> Dict:
    """Analyze multiple PDF forms in batch."""
    try:
        if not files:
            raise HTTPException(status_code=400, detail="No files provided")
        
        # Validate all files
        temp_paths = []
        for file in files:
            if not file.filename or not file.filename.endswith('.pdf'):
                raise HTTPException(status_code=400, detail=f"File {file.filename} must be a PDF")
            
            # Save uploaded file temporarily
            temp_path = Path(f"/tmp/batch_{file.filename}")
            with temp_path.open("wb") as buffer:
                content = await file.read()
                buffer.write(content)
            temp_paths.append(temp_path)
        
        # Run batch analysis
        batch_analysis = await field_analyzer.batch_analyze_forms(
            pdf_paths=temp_paths,
            consistency_check=consistency_check
        )
        
        # Clean up temp files
        for temp_path in temp_paths:
            temp_path.unlink(missing_ok=True)
        
        return batch_analysis.model_dump(mode="json")
        
    except HTTPException:
        raise
    except Exception as e:
        logger.exception("Error in batch analysis")
        raise HTTPException(status_code=500, detail=f"Batch analysis failed: {str(e)}")


@app.post("/validate/bem")
async def validate_bem_name(bem_name: str = Form(...)) -> Dict[str, any]:
    """Validate a BEM field name format."""
    from ..pdf_enrichment.utils import validate_bem_name_format
    
    is_valid, message = validate_bem_name_format(bem_name)
    
    return {
        "bem_name": bem_name,
        "is_valid": is_valid,
        "message": message,
    }


@app.get("/templates/upload")
async def upload_template() -> HTMLResponse:
    """Serve HTML upload template."""
    html_content = """
    <!DOCTYPE html>
    <html>
    <head>
        <title>PDF Enrichment Platform</title>
        <style>
            body { font-family: Arial, sans-serif; max-width: 800px; margin: 0 auto; padding: 20px; }
            .upload-form { border: 2px dashed #ccc; padding: 20px; margin: 20px 0; }
            .form-group { margin: 15px 0; }
            label { display: block; margin-bottom: 5px; font-weight: bold; }
            input, select, textarea { width: 100%; padding: 8px; margin-bottom: 10px; }
            button { background: #007bff; color: white; padding: 10px 20px; border: none; cursor: pointer; }
            button:hover { background: #0056b3; }
            .result { margin-top: 20px; padding: 15px; background: #f8f9fa; border-radius: 5px; }
        </style>
    </head>
    <body>
        <h1>🚀 PDF Enrichment Platform</h1>
        <p>Transform PDF forms into structured APIs with BEM-style field naming.</p>
        
        <div class="upload-form">
            <h2>📋 Analyze PDF Form</h2>
            <form id="analyzeForm" enctype="multipart/form-data">
                <div class="form-group">
                    <label for="file">Select PDF File:</label>
                    <input type="file" id="file" name="file" accept=".pdf" required>
                </div>
                
                <div class="form-group">
                    <label for="analysis_mode">Analysis Mode:</label>
                    <select id="analysis_mode" name="analysis_mode">
                        <option value="comprehensive">Comprehensive</option>
                        <option value="quick">Quick</option>
                    </select>
                </div>
                
                <div class="form-group">
                    <label for="custom_sections">Custom Sections (comma-separated):</label>
                    <input type="text" id="custom_sections" name="custom_sections" 
                           placeholder="owner-information, payment-details, signatures">
                </div>
                
                <button type="submit">🔍 Analyze PDF</button>
                <button type="button" onclick="analyzeWithPreview()">👁️ Analyze with Preview</button>
            </form>
        </div>
        
        <div class="upload-form">
            <h2>🔧 Modify PDF Fields</h2>
            <form id="modifyForm" enctype="multipart/form-data">
                <div class="form-group">
                    <label for="modifyFile">Select PDF File:</label>
                    <input type="file" id="modifyFile" name="file" accept=".pdf" required>
                </div>
                
                <div class="form-group">
                    <label for="field_mappings">Field Mappings (JSON):</label>
                    <textarea id="field_mappings" name="field_mappings" rows="6" 
                              placeholder='{"oldFieldName": "new-bem-name", ...}'></textarea>
                </div>
                
                <div class="form-group">
                    <label>
                        <input type="checkbox" id="preserve_original" name="preserve_original" checked>
                        Preserve Original File
                    </label>
                </div>
                
                <div class="form-group">
                    <label>
                        <input type="checkbox" id="validate_mappings" name="validate_mappings" checked>
                        Validate BEM Names
                    </label>
                </div>
                
                <button type="submit">🔧 Modify PDF</button>
            </form>
        </div>
        
        <div id="result" class="result" style="display: none;">
            <h3>📊 Results</h3>
            <div id="resultContent"></div>
        </div>
        
        <script>
            document.getElementById('analyzeForm').addEventListener('submit', async (e) => {
                e.preventDefault();
                const formData = new FormData(e.target);
                
                try {
                    const response = await fetch('/analyze', {
                        method: 'POST',
                        body: formData
                    });
                    
                    const result = await response.json();
                    document.getElementById('resultContent').innerHTML = 
                        '<pre>' + JSON.stringify(result, null, 2) + '</pre>';
                    document.getElementById('result').style.display = 'block';
                } catch (error) {
                    document.getElementById('resultContent').innerHTML = 
                        '<p style="color: red;">Error: ' + error.message + '</p>';
                    document.getElementById('result').style.display = 'block';
                }
            });
            
            async function analyzeWithPreview() {
                const form = document.getElementById('analyzeForm');
                const formData = new FormData(form);
                
                try {
                    const response = await fetch('/analyze/preview', {
                        method: 'POST',
                        body: formData
                    });
                    
                    const html = await response.text();
                    document.getElementById('resultContent').innerHTML = html;
                    document.getElementById('result').style.display = 'block';
                } catch (error) {
                    document.getElementById('resultContent').innerHTML = 
                        '<p style="color: red;">Error: ' + error.message + '</p>';
                    document.getElementById('result').style.display = 'block';
                }
            }
            
            document.getElementById('modifyForm').addEventListener('submit', async (e) => {
                e.preventDefault();
                const formData = new FormData(e.target);
                
                try {
                    const response = await fetch('/modify', {
                        method: 'POST',
                        body: formData
                    });
                    
                    if (response.ok) {
                        const blob = await response.blob();
                        const url = window.URL.createObjectURL(blob);
                        const a = document.createElement('a');
                        a.href = url;
                        a.download = 'modified_form.pdf';
                        a.click();
                        window.URL.revokeObjectURL(url);
                        
                        document.getElementById('resultContent').innerHTML = 
                            '<p style="color: green;">✅ PDF modified successfully! Download started.</p>';
                    } else {
                        const error = await response.json();
                        document.getElementById('resultContent').innerHTML = 
                            '<p style="color: red;">❌ ' + error.detail + '</p>';
                    }
                    document.getElementById('result').style.display = 'block';
                } catch (error) {
                    document.getElementById('resultContent').innerHTML = 
                        '<p style="color: red;">Error: ' + error.message + '</p>';
                    document.getElementById('result').style.display = 'block';
                }
            });
        </script>
    </body>
    </html>
    """
    return HTMLResponse(content=html_content)


# Error handlers
@app.exception_handler(404)
async def not_found_handler(request, exc):
    """Handle 404 errors."""
    return {"error": "Not found", "detail": "The requested resource was not found"}


@app.exception_handler(500)
async def internal_error_handler(request, exc):
    """Handle 500 errors."""
    logger.exception("Internal server error")
    return {"error": "Internal server error", "detail": "An unexpected error occurred"}


if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=8000)
