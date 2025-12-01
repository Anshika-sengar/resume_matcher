from django.shortcuts import render, HttpResponse, redirect
from django.contrib.auth.models import User
from django.contrib.auth import authenticate, login, logout
from django.contrib.auth.decorators import login_required

from .forms import ResumeMatchForm
from .models import ResumeMatch

import PyPDF2
import re
from sklearn.feature_extraction.text import TfidfVectorizer
from sklearn.metrics.pairwise import cosine_similarity

# For image conversion
from pdf2image import convert_from_path
from docx2pdf import convert
import os

# Folder where images will be stored
RESUME_IMG_DIR = "media/resume_images/"

# Your correct Poppler path
POPPLER_PATH = r"C:\Users\IPCC\Downloads\Release-25.11.0-0\poppler-25.11.0\Library\bin"


# =============================================================
# SIGNUP
# =============================================================
def SignUpPage(request):
    if request.method == 'POST':
        uname = request.POST.get('username')
        email = request.POST.get('email')
        pass1 = request.POST.get('password1')
        pass2 = request.POST.get('password2')

        if pass1 != pass2:
            return HttpResponse("Passwords do not match")

        User.objects.create_user(uname, email, pass1)
        return redirect('login')

    return render(request, 'signup.html')


# =============================================================
# LOGIN
# =============================================================
def LoginPage(request):
    if request.method == 'POST':
        username = request.POST.get('username')
        pass1 = request.POST.get('pass')

        user = authenticate(request, username=username, password=pass1)
        if user:
            login(request, user)
            return redirect('home')
        else:
            return HttpResponse("Invalid credentials")

    return render(request, 'login.html')


# =============================================================
# LOGOUT
# =============================================================
def LogoutPage(request):
    logout(request)
    return redirect('login')


# =============================================================
# EXTRACT TEXT FROM PDF
# =============================================================
def extract_text_from_pdf(file_obj):
    try:
        reader = PyPDF2.PdfReader(file_obj)
        text_pages = []
        for page in reader.pages:
            txt = page.extract_text()
            if txt:
                text_pages.append(txt)
        return "\n".join(text_pages)
    except:
        return ""


# =============================================================
# CLEAN TOKENS
# =============================================================
def token_set(text):
    tokens = re.findall(r'\b[a-zA-Z0-9\-]+\b', text.lower())
    return set([t for t in tokens if len(t) > 2])


# =============================================================
# MATCH SCORE + SUGGESTIONS
# =============================================================
def compute_score(resume_text, jd_text):
    try:
        vectorizer = TfidfVectorizer(stop_words='english')
        tfidf = vectorizer.fit_transform([resume_text, jd_text])
        similarity = cosine_similarity(tfidf[0:1], tfidf[1:2])[0][0]
        score = round(similarity * 100, 2)
    except:
        score = 0

    resume_tokens = token_set(resume_text)
    jd_tokens = token_set(jd_text)
    missing = jd_tokens - resume_tokens

    suggestions = ", ".join(list(missing)[:12])
    if not suggestions:
        suggestions = "No missing keywords."

    return score, suggestions


# =============================================================
# RESUME → IMAGE (PDF + DOC/DOCX)
# =============================================================
def convert_resume_to_images(file_path):

    ext = file_path.split(".")[-1].lower()

    # Create folder if not exist
    os.makedirs(RESUME_IMG_DIR, exist_ok=True)

    # If resume is DOC/DOCX → convert to PDF first
    if ext in ["doc", "docx"]:
        pdf_path = file_path.replace(ext, "pdf")
        convert(file_path, pdf_path)
        file_path = pdf_path

    # Convert PDF to image
    pages = convert_from_path(file_path, dpi=160, poppler_path=POPPLER_PATH)

    image_paths = []

    for i, page in enumerate(pages):
        image_filename = f"resume_page_{i+1}.jpg"
        saved_path = os.path.join(RESUME_IMG_DIR, image_filename)

        # Save the image
        page.save(saved_path, "JPEG")

        # URL path to show in HTML
        image_paths.append(f"/media/resume_images/{image_filename}")

    return image_paths


# =============================================================
# HOME PAGE (MAIN FUNCTION)
# =============================================================
@login_required(login_url='login')
def HomePage(request):

    if request.method == 'POST':
        form = ResumeMatchForm(request.POST, request.FILES)

        if form.is_valid():

            # SAVE resume file first
            resume_file = request.FILES['resume_file']
            saved_path = f"media/{resume_file.name}"

            with open(saved_path, "wb+") as dest:
                for chunk in resume_file.chunks():
                    dest.write(chunk)

            # Extract text
            resume_text = extract_text_from_pdf(open(saved_path, "rb"))
            jd_text = form.cleaned_data['job_description']

            # Compute match & suggestions
            score, suggestions = compute_score(resume_text, jd_text)

            # Save result into DB
            match = form.save(commit=False)
            match.user = request.user
            match.match_score = score
            match.suggestions = suggestions
            match.save()

            # Convert file to images
            image_list = convert_resume_to_images(saved_path)

            return render(request, "home.html", {
                "form": ResumeMatchForm(),
                "result": match,
                "images": image_list
            })

        else:
            return render(request, "home.html", {"form": ResumeMatchForm()})

    return render(request, "home.html", {"form": ResumeMatchForm()})
