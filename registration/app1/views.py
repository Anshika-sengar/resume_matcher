from django.shortcuts import render, HttpResponse, redirect
from django.contrib.auth.models import User
from django.contrib.auth import authenticate, login, logout
from django.contrib.auth.decorators import login_required

from .forms import ResumeMatchForm
from .models import ResumeMatch

# pdf processing & simple NLP
import io
import PyPDF2
from sklearn.feature_extraction.text import TfidfVectorizer
from sklearn.metrics.pairwise import cosine_similarity
import re


# ==========================
# SIGNUP PAGE
# ==========================
def SignUpPage(request):
    if request.method == 'POST':
        uname = request.POST.get('username')
        email = request.POST.get('email')
        pass1 = request.POST.get('password1')
        pass2 = request.POST.get('password2')

        if pass1 != pass2:
            return HttpResponse("Passwords do not match")
        else:
            my_user = User.objects.create_user(uname, email, pass1)
            my_user.save()
            return redirect('login')

    return render(request, 'signup.html')


# ==========================
# LOGIN PAGE
# ==========================
def LoginPage(request):
    if request.method == 'POST':
        username = request.POST.get('username')
        pass1 = request.POST.get('pass')
        user = authenticate(request, username=username, password=pass1)

        if user is not None:
            login(request, user)
            return redirect('home')   # ← redirect correctly to home
        else:
            return HttpResponse("Invalid credentials")

    return render(request, 'login.html')


# ==========================
# LOGOUT PAGE
# ==========================
def LogoutPage(request):
    logout(request)
    return redirect('login')


# ==========================
# PDF TEXT EXTRACTION
# ==========================
def extract_text_from_pdf(file_obj):
    try:
        reader = PyPDF2.PdfReader(file_obj)
        text_pages = []
        for p in reader.pages:
            txt = p.extract_text()
            if txt:
                text_pages.append(txt)
        return "\n".join(text_pages)
    except Exception:
        try:
            file_obj.seek(0)
            data = file_obj.read()
            return data.decode(errors='ignore')
        except Exception:
            return ""


# ==========================
# KEYWORD CLEANING
# ==========================
def simple_token_set(text):
    tokens = re.findall(r'\b[a-zA-Z0-9\-\+]+\b', text.lower())
    tokens = [t for t in tokens if len(t) > 2]
    return set(tokens)


# ==========================
# RESUME VS JD MATCH
# ==========================
def compute_match_and_suggestions(resume_text, jd_text):
    try:
        vect = TfidfVectorizer(stop_words='english', max_features=4000)
        tfidf = vect.fit_transform([resume_text, jd_text])
        sim = cosine_similarity(tfidf[0:1], tfidf[1:2])[0][0]
        score = float(sim) * 100.0
    except Exception:
        score = 0.0

    jd_tokens = simple_token_set(jd_text)
    resume_tokens = simple_token_set(resume_text)
    missing = jd_tokens - resume_tokens

    suggestions_list = list(missing)[:12]
    suggestions_text = ", ".join(suggestions_list) if suggestions_list else "No missing keywords."

    return round(score, 2), suggestions_text


# ==========================
# HOME PAGE (SHOWN AFTER LOGIN)
# ==========================
@login_required(login_url='login')
def HomePage(request):
    user = request.user
    had_previous = ResumeMatch.objects.filter(user=user).exists()

    if request.method == 'POST':
        form = ResumeMatchForm(request.POST, request.FILES)

        if form.is_valid():
            instance = form.save(commit=False)
            instance.user = user

            file_obj = request.FILES.get('resume_file')
            resume_text = extract_text_from_pdf(file_obj)
            jd_text = form.cleaned_data.get('job_description') or ""

            score, suggestions = compute_match_and_suggestions(resume_text, jd_text)

            instance.match_score = score
            instance.suggestions = suggestions
            instance.save()

            return render(request, 'home.html', {
                'form': ResumeMatchForm(),
                'result': instance,
                'had_previous': True
            })

        # form error
        return render(request, 'home.html', {'form': form, 'had_previous': had_previous})

    else:
        form = ResumeMatchForm()
        last_result = ResumeMatch.objects.filter(user=user).order_by('-created_at').first()

        return render(request, 'home.html', {
            'form': form,
            'last_result': last_result,
            'had_previous': had_previous
        })
