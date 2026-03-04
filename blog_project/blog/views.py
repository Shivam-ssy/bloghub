from django.shortcuts import render, get_object_or_404, redirect
from django.contrib.auth import authenticate, login, logout
from django.contrib.auth.decorators import login_required
from django.contrib import messages
from django.db.models import Q
from .models import CustomUser, Post, Tag


# ─── AUTH ─────────────────────────────────────────────────────────────────────

def login_view(request):
    if request.user.is_authenticated:
        return redirect("home_")
    error = None
    if request.method == "POST":
        email    = request.POST.get("email", "").strip().lower()
        password = request.POST.get("password", "")
        user = authenticate(request, email=email, password=password)
        if user is not None:
            login(request, user)
            next_url = request.POST.get("next") or request.GET.get("next") or "home_"
            return redirect(next_url)
        else:
            error = "Invalid email or password."
    return render(request, "blog/login.html", {
        "error": error, "next": request.GET.get("next", ""), "form_data": request.POST,
    })


def signup_view(request):
    if request.user.is_authenticated:
        return redirect("home_")
    errors = {}
    if request.method == "POST":
        name      = request.POST.get("name", "").strip()
        email     = request.POST.get("email", "").strip().lower()
        password1 = request.POST.get("password1", "")
        password2 = request.POST.get("password2", "")
        if not name:
            errors["name"] = "Full name is required."
        if not email:
            errors["email"] = "Email is required."
        elif CustomUser.objects.filter(email=email).exists():
            errors["email"] = "An account with that email already exists."
        if not password1:
            errors["password1"] = "Password is required."
        elif len(password1) < 8:
            errors["password1"] = "Password must be at least 8 characters."
        if password1 != password2:
            errors["password2"] = "Passwords do not match."
        if not errors:
            user = CustomUser.objects.create_user(email=email, name=name, password=password1)
            login(request, user)
            return redirect("home_")
    return render(request, "blog/sign.html", {"errors": errors, "form_data": request.POST})


def logout_view(request):
    logout(request)
    return redirect("index")   # goes back to landing page after logout


# ─── PAGES ────────────────────────────────────────────────────────────────────

def index(request):
    """Public landing page. Logged-in users are sent straight to home."""
    if request.user.is_authenticated:
        return redirect("home_")
    return render(request, "blog/index.html")


def home(request):
    """
    Main feed — open to everyone.
    Logged-in users also see a 'My Posts' tab via ?filter=mine.
    Edit/Delete buttons only appear on posts the logged-in user authored.
    """
    filter_param = request.GET.get("filter", "all")
    q = request.GET.get("q", "").strip()

    posts = Post.objects.select_related("author").prefetch_related("tags").order_by("-created_at")

    if q:
        posts = posts.filter(
            Q(title__icontains=q) | Q(info__icontains=q) | Q(tags__name__icontains=q)
        ).distinct()

    my_posts_count = 0
    if request.user.is_authenticated:
        my_posts_count = Post.objects.filter(author=request.user).count()
        if filter_param == "mine":
            posts = posts.filter(author=request.user)

    return render(request, "blog/home.html", {
        "posts": posts, "filter": filter_param,
        "search_query": q, "my_posts_count": my_posts_count,
    })


def post_details(request, id):
    """Full post view — open to everyone."""
    post = get_object_or_404(
        Post.objects.select_related("author").prefetch_related("tags"), id=id
    )
    return render(request, "blog/details.html", {"post": post})


# ─── CRUD (login required) ────────────────────────────────────────────────────

@login_required(login_url="login")
def post_create(request):
    all_tags = Tag.objects.all()
    if request.method == "POST":
        title = request.POST.get("title", "").strip()
        info = request.POST.get("info", "").strip()
        description = request.POST.get("description", "").strip()
        tag_ids = request.POST.getlist("tags")
        image = request.FILES.get("image")
        errors = _validate_post(title, info, description, image, require_image=True)
        if not errors:
            post = Post.objects.create(
                author=request.user, title=title, info=info,
                description=description, image=image,
            )
            if tag_ids:
                post.tags.set(Tag.objects.filter(id__in=tag_ids))
            messages.success(request, "Post published!")
            return redirect("post_details", id=post.id)
        return render(request, "blog/post_create.html", {
            "errors": errors, "all_tags": all_tags,
            "selected_tags": Tag.objects.filter(id__in=tag_ids), "form_data": request.POST,
        })
    return render(request, "blog/post_create.html", {"all_tags": all_tags, "selected_tags": []})


@login_required(login_url="login")
def post_edit(request, id):
    post = get_object_or_404(Post, id=id)
    if post.author != request.user:
        messages.error(request, "You can only edit your own posts.")
        return redirect("post_details", id=id)
    all_tags = Tag.objects.all()
    if request.method == "POST":
        title = request.POST.get("title", "").strip()
        info = request.POST.get("info", "").strip()
        description = request.POST.get("description", "").strip()
        tag_ids = request.POST.getlist("tags")
        image = request.FILES.get("image")
        errors = _validate_post(title, info, description, image, require_image=False)
        if not errors:
            post.title = title; post.info = info; post.description = description
            if image:
                post.image = image
            post.save()
            post.tags.set(Tag.objects.filter(id__in=tag_ids))
            messages.success(request, "Post updated!")
            return redirect("post_details", id=post.id)
        return render(request, "blog/post_create.html", {
            "post": post, "errors": errors, "all_tags": all_tags,
            "selected_tags": Tag.objects.filter(id__in=tag_ids), "form_data": request.POST,
        })
    return render(request, "blog/post_create.html", {
        "post": post, "all_tags": all_tags, "selected_tags": post.tags.all(),
    })


@login_required(login_url="login")
def post_delete(request, id):
    post = get_object_or_404(Post, id=id)
    if post.author != request.user:
        messages.error(request, "You can only delete your own posts.")
        return redirect("post_details", id=id)
    if request.method == "POST":
        post.delete()
        messages.success(request, "Post deleted.")
        return redirect("home_")
    return redirect("post_details", id=id)


def _validate_post(title, info, description, image, require_image=True):
    errors = {}
    if not title:
        errors["title"] = "Title is required."
    elif len(title) > 200:
        errors["title"] = "Title must be 200 characters or fewer."
    if not info:
        errors["info"] = "Short summary is required."
    elif len(info) > 300:
        errors["info"] = "Summary must be 300 characters or fewer."
    if not description:
        errors["description"] = "Content is required."
    if require_image and not image:
        errors["image"] = "A cover image is required."
    return errors