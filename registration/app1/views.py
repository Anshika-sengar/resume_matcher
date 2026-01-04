from django.shortcuts import render, HttpResponse, redirect
from django.contrib.auth.models import User
from django.contrib.auth import authenticate, login, logout
from django.contrib.auth.decorators import login_required

from .forms import ResumeMatchForm
from .models import ResumeMatch

import PyPDF2
import re
import os
import uuid

from sklearn.feature_extraction.text import TfidfVectorizer
from sklearn.metrics.pairwise import cosine_similarity

from pdf2image import convert_from_path
from docx2pdf import convert


# ================================================================
# CONFIG
# ================================================================
BASE_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
MEDIA_DIR = os.path.join(BASE_DIR, "media")
RESUME_IMG_DIR = os.path.join(MEDIA_DIR, "resume_images")

# Retrieve POPPLER_PATH from environment variables for deployment
POPPLER_PATH = os.getenv("POPPLER_PATH", r"C:\poppler\poppler\Library\bin")  # Local (Windows) or Update for production environment


# ================================================================
# AUTH FUNCTIONS
# ================================================================
def SignUpPage(request):
    if request.method == 'POST':
        if request.POST.get('password1') != request.POST.get('password2'):
            return HttpResponse("Passwords do not match")

        User.objects.create_user(
            request.POST.get('username'),
            request.POST.get('email'),
            request.POST.get('password1')
        )
        return redirect('login')

    return render(request, 'signup.html')


def LoginPage(request):
    if request.method == 'POST':
        user = authenticate(
            request,
            username=request.POST.get('username'),
            password=request.POST.get('pass')
        )
        if user:
            login(request, user)
            return redirect('home')

        return HttpResponse("Invalid credentials")

    return render(request, 'login.html')


def LogoutPage(request):
    logout(request)
    return redirect('login')


# ================================================================
# PDF TEXT EXTRACTION
# ================================================================
def extract_text_from_pdf(file_obj):
    try:
        reader = PyPDF2.PdfReader(file_obj)
        return "\n".join(page.extract_text() or "" for page in reader.pages)
    except Exception as e:
        print("PDF TEXT EXTRACTION ERROR:", e)
        return ""


# ================================================================
# MATCH SCORE LOGIC
# ================================================================
def token_set(text):
    return {
        t for t in re.findall(r'\b[a-zA-Z0-9\-]+\b', text.lower())
        if len(t) > 2
    }


def compute_score(resume_text, jd_text):
    try:
        tfidf = TfidfVectorizer(stop_words='english').fit_transform(
            [resume_text, jd_text]
        )
        score = round(
            cosine_similarity(tfidf[0:1], tfidf[1:2])[0][0] * 100, 2
        )
    except Exception:
        score = 0

    missing = token_set(jd_text) - token_set(resume_text)
    return score, ", ".join(list(missing)[:12]) or "No missing keywords."


# ================================================================
# CONVERT RESUME TO IMAGE (DEPLOYMENT SAFE)
# ================================================================
def convert_resume_to_images(file_path):

    os.makedirs(RESUME_IMG_DIR, exist_ok=True)
    file_path = os.path.abspath(file_path)

    # DOC/DOCX → PDF (Conversion)
    ext = os.path.splitext(file_path)[1].lower()
    if ext in ['.doc', '.docx']:
        pdf_path = file_path.replace(ext, '.pdf')
        convert(file_path, pdf_path)
        file_path = pdf_path

    image_urls = []

    try:
        # Convert PDF to Image (Using Poppler Path for PDF extraction)
        pages = convert_from_path(
            file_path,
            poppler_path=POPPLER_PATH,
            dpi=150,
            fmt="jpeg",
            use_pdftocairo=True,
            first_page=1,
            last_page=1
        )

        # Save each page as an image
        for page in pages:
            filename = f"resume_{uuid.uuid4().hex}.jpg"
            save_path = os.path.join(RESUME_IMG_DIR, filename)
            page.save(save_path, "JPEG")

            image_urls.append(f"/media/resume_images/{filename}")
            print("IMAGE SAVED:", save_path)

    except Exception as e:
        print("PDF to Image ERROR:", e)

    return image_urls


# ================================================================
# HOME PAGE FUNCTION
# ================================================================
@login_required(login_url='login')
def HomePage(request):

    if request.method == 'POST':
        form = ResumeMatchForm(request.POST, request.FILES)
        if form.is_valid():

            # Save uploaded resume as PDF
            resume_file = request.FILES['resume_file']
            saved_pdf = os.path.join(
                MEDIA_DIR,
                f"resume_{uuid.uuid4().hex}.pdf"
            )

            with open(saved_pdf, "wb+") as f:
                for chunk in resume_file.chunks():
                    f.write(chunk)

            # Extract text from the saved PDF
            with open(saved_pdf, "rb") as f:
                resume_text = extract_text_from_pdf(f)

            # Compute match score with the job description
            score, suggestions = compute_score(
                resume_text,
                form.cleaned_data['job_description']
            )

            # Save match details
            match = form.save(commit=False)
            match.user = request.user
            match.match_score = score
            match.suggestions = suggestions
            match.save()

            # Convert the saved resume to images
            images = convert_resume_to_images(saved_pdf)
            print("IMAGES:", images)

            return render(request, "home.html", {
                "form": ResumeMatchForm(),
                "result": match,
                "images": images
            })

    return render(request, "home.html", {"form": ResumeMatchForm()})
