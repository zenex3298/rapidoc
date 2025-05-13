from fastapi import APIRouter, Request, HTTPException, Depends
from fastapi.responses import HTMLResponse, RedirectResponse
from fastapi.templating import Jinja2Templates
from fastapi.staticfiles import StaticFiles
import os
from pathlib import Path
from app.services.auth_service import get_current_admin_user
from app.models.user import User

# Create the router for frontend routes
frontend_router = APIRouter(prefix="", tags=["frontend"])

# Get the current directory
current_dir = Path(__file__).parent

# Set up Jinja2 templates
templates = Jinja2Templates(directory=str(current_dir / "templates"))

# Static files path (to be mounted in main.py)
static_path = current_dir / "static"

# Define routes
@frontend_router.get("/", response_class=HTMLResponse)
async def index(request: Request):
    """Render the homepage"""
    return templates.TemplateResponse("index.html", {"request": request, "current_user": None, "messages": []})

@frontend_router.get("/login", response_class=HTMLResponse)
async def login(request: Request):
    """Render the login page"""
    return templates.TemplateResponse("login.html", {"request": request, "current_user": None, "messages": []})

@frontend_router.get("/register", response_class=HTMLResponse)
async def register(request: Request):
    """Render the registration page"""
    return templates.TemplateResponse("register.html", {"request": request, "current_user": None, "messages": []})

@frontend_router.get("/documents", response_class=HTMLResponse)
async def documents(request: Request):
    """Render the documents page"""
    return templates.TemplateResponse("documents.html", {"request": request, "current_user": {"username": "User"}, "messages": []})

@frontend_router.get("/upload", response_class=HTMLResponse)
async def upload(request: Request):
    """Render the document upload page"""
    return templates.TemplateResponse("upload.html", {"request": request, "current_user": {"username": "User"}, "messages": []})

@frontend_router.get("/template-upload", response_class=HTMLResponse)
async def template_upload(request: Request):
    """Render the template upload page"""
    return templates.TemplateResponse("template_upload.html", {"request": request, "current_user": {"username": "User"}, "messages": []})

@frontend_router.get("/templates", response_class=HTMLResponse)
async def templates_page(request: Request):
    """Render the templates listing page"""
    return templates.TemplateResponse("templates.html", {"request": request, "current_user": {"username": "User"}, "messages": []})

@frontend_router.get("/logout")
async def logout(request: Request):
    """Logout the user"""
    return {"status": "success", "message": "Logged out successfully"}

# These endpoints are for form submissions and will redirect to the appropriate page
# They're not used in the SPA implementation but are here for completeness
@frontend_router.post("/login")
async def login_post():
    """Handle login form submissions (not used in SPA)"""
    raise HTTPException(status_code=308, detail="Use the API endpoint at /auth/login instead")

@frontend_router.post("/register")
async def register_post():
    """Handle registration form submissions (not used in SPA)"""
    raise HTTPException(status_code=308, detail="Use the API endpoint at /auth/register instead")

@frontend_router.get("/admin", response_class=HTMLResponse)
async def admin_dashboard(request: Request):
    """
    Render the admin dashboard page.
    This page is protected and only accessible to admin users.
    
    Note: This is a frontend route that serves the HTML template.
    Actual data protection happens in the API endpoints that the
    frontend will call. We don't do server-side authorization checks
    here because the SPA architecture handles auth via JWT tokens
    in the API calls.
    """
    # The actual authorization check happens client-side with JWT tokens
    # when making API calls to the admin endpoints
    return templates.TemplateResponse("admin/dashboard.html", {
        "request": request, 
        "current_user": {"username": "Admin", "is_admin": True},
        "messages": []
    })