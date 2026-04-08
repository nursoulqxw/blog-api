#!/usr/bin/env bash
# start.sh — bring the project from zero to a running dev server.
# Usage: bash scripts/start.sh
# Works on a freshly cloned repo as well as an already-set-up project.

set -euo pipefail   # stop on first error; treat unset vars as errors

# ---------------------------------------------------------------------------
# Colour helpers
# ---------------------------------------------------------------------------
RED='\033[0;31m'; GREEN='\033[0;32m'; YELLOW='\033[1;33m'; NC='\033[0m'
info()    { echo -e "${GREEN}[INFO]${NC}  $*"; }
warn()    { echo -e "${YELLOW}[WARN]${NC}  $*"; }
error()   { echo -e "${RED}[ERROR]${NC} $*" >&2; }
die()     { error "$*"; exit 1; }

# ---------------------------------------------------------------------------
# Locate the script's directory (works when called from any CWD)
# ---------------------------------------------------------------------------
SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
PROJECT_DIR="$(cd "$SCRIPT_DIR/.." && pwd)"
cd "$PROJECT_DIR"
info "Working directory: $PROJECT_DIR"

# ---------------------------------------------------------------------------
# 1. Check required environment variables
# ---------------------------------------------------------------------------
info "Step 1/8 — Checking environment variables …"
ENV_FILE="settings/.env"

if [[ ! -f "$ENV_FILE" ]]; then
    warn "$ENV_FILE not found — creating from settings/.env.example"
    if [[ -f "settings/.env.example" ]]; then
        cp "settings/.env.example" "$ENV_FILE"
    else
        cat > "$ENV_FILE" <<EOF
BLOG_ENV_ID=local
BLOG_SECRET_KEY=dev-secret-key-change-in-production
BLOG_ALLOWED_HOSTS=localhost,127.0.0.1
BLOG_REDIS_URL=redis://127.0.0.1:6379/1
EOF
    fi
    info "Created $ENV_FILE from defaults."
fi

# Variables that must be present and non-empty
REQUIRED_VARS=(
    BLOG_ENV_ID
    BLOG_SECRET_KEY
)

missing=0
for var in "${REQUIRED_VARS[@]}"; do
    value="$(grep -E "^${var}=" "$ENV_FILE" | cut -d'=' -f2- | tr -d '[:space:]')"
    if [[ -z "$value" ]]; then
        error "Missing or empty required variable: $var  (in $ENV_FILE)"
        missing=1
    fi
done

[[ "$missing" -eq 0 ]] || die "Fix the missing variables above, then re-run this script."
info "All required environment variables are present."

# ---------------------------------------------------------------------------
# 2. Virtual environment + dependencies
# ---------------------------------------------------------------------------
info "Step 2/8 — Setting up virtual environment …"
if [[ ! -d "venv" ]]; then
    python3 -m venv venv
    info "Virtual environment created."
else
    info "Virtual environment already exists — skipping creation."
fi

info "Installing Python dependencies …"
venv/bin/pip install --quiet --upgrade pip
venv/bin/pip install --quiet -r requirements/base.txt
info "Dependencies installed."

# ---------------------------------------------------------------------------
# Helper: run manage.py inside the venv
# ---------------------------------------------------------------------------
manage() { venv/bin/python manage.py "$@"; }

# ---------------------------------------------------------------------------
# 3. Migrations
# ---------------------------------------------------------------------------
info "Step 3/8 — Running migrations …"
manage migrate --no-input
info "Migrations complete."

# ---------------------------------------------------------------------------
# 4. Collect static files
# ---------------------------------------------------------------------------
info "Step 4/8 — Collecting static files …"
manage collectstatic --no-input --quiet
info "Static files collected."

# ---------------------------------------------------------------------------
# 5. Compile translations
# ---------------------------------------------------------------------------
info "Step 5/8 — Compiling translation files …"
manage compilemessages --ignore=venv 2>/dev/null || warn "compilemessages failed (non-fatal)."
info "Translations compiled."

# ---------------------------------------------------------------------------
# 6. Create superuser (skip if already exists)
# ---------------------------------------------------------------------------
info "Step 6/8 — Creating superuser …"
SUPERUSER_EMAIL="admin@blog.local"
SUPERUSER_PASSWORD="Admin1234!"
SUPERUSER_FIRST="Admin"
SUPERUSER_LAST="User"

manage shell -c "
from django.contrib.auth import get_user_model
User = get_user_model()
if not User.objects.filter(email='$SUPERUSER_EMAIL').exists():
    User.objects.create_superuser(
        email='$SUPERUSER_EMAIL',
        password='$SUPERUSER_PASSWORD',
        first_name='$SUPERUSER_FIRST',
        last_name='$SUPERUSER_LAST',
    )
    print('Superuser created.')
else:
    print('Superuser already exists — skipped.')
"

# ---------------------------------------------------------------------------
# 7. Seed test data
# ---------------------------------------------------------------------------
info "Step 7/8 — Seeding test data …"
manage shell -c "
import django
from django.contrib.auth import get_user_model
from apps.blog.models import Category, Tag, Post, Comment

User = get_user_model()

# Users
users_data = [
    ('alice@blog.local',  'Alice',   'Smith',  'Alicepass1!'),
    ('bob@blog.local',    'Bob',     'Jones',  'Bobpass1!'),
    ('carol@blog.local',  'Carol',   'White',  'Carolpass1!'),
]
created_users = []
for email, first, last, pw in users_data:
    u, created = User.objects.get_or_create(email=email, defaults={
        'first_name': first, 'last_name': last,
    })
    if created:
        u.set_password(pw)
        u.save()
    created_users.append(u)

# Categories
cats_data = [
    ('Technology', 'technology'),
    ('Science',    'science'),
    ('Travel',     'travel'),
]
categories = []
for name, slug in cats_data:
    c, _ = Category.objects.get_or_create(slug=slug, defaults={'name': name})
    categories.append(c)

# Tags
tags_data = ['python', 'django', 'rest-api', 'tutorial', 'news']
tags = []
for name in tags_data:
    t, _ = Tag.objects.get_or_create(slug=name, defaults={'name': name})
    tags.append(t)

# Posts (mix of draft and published)
posts_data = [
    ('Hello World',          'hello-world',           'published'),
    ('Django Tips',          'django-tips',           'published'),
    ('Async Python',         'async-python',          'published'),
    ('REST API Design',      'rest-api-design',       'published'),
    ('Travel Diary: Almaty', 'travel-diary-almaty',   'published'),
    ('Draft Post 1',         'draft-post-1',          'draft'),
    ('Draft Post 2',         'draft-post-2',          'draft'),
]
posts = []
for title, slug, status in posts_data:
    p, created = Post.objects.get_or_create(slug=slug, defaults={
        'title': title,
        'body': f'Body of {title}. ' * 10,
        'author': created_users[0],
        'category': categories[0],
        'status': status,
    })
    if created:
        p.tags.set(tags[:3])
    posts.append(p)

# Comments
comments_data = [
    'Great post!', 'Very helpful, thanks.', 'I learned a lot.',
    'Could you explain more?', 'Excellent writing!',
]
for i, body in enumerate(comments_data):
    Comment.objects.get_or_create(
        post=posts[i % len(posts)],
        author=created_users[i % len(created_users)],
        body=body,
    )

print('Seed data OK.')
"
info "Test data seeded."

# ---------------------------------------------------------------------------
# 8. Start development server
# ---------------------------------------------------------------------------
info "Step 8/8 — Starting development server …"

echo ""
echo -e "${GREEN}======================================${NC}"
echo -e "${GREEN}  Blog API — Development Server       ${NC}"
echo -e "${GREEN}======================================${NC}"
echo ""
echo -e "  API root    : ${YELLOW}http://127.0.0.1:8000/api/${NC}"
echo -e "  Swagger UI  : ${YELLOW}http://127.0.0.1:8000/api/docs/${NC}"
echo -e "  ReDoc       : ${YELLOW}http://127.0.0.1:8000/api/redoc/${NC}"
echo -e "  Admin panel : ${YELLOW}http://127.0.0.1:8000/admin/${NC}"
echo ""
echo -e "  Superuser email    : ${YELLOW}${SUPERUSER_EMAIL}${NC}"
echo -e "  Superuser password : ${YELLOW}${SUPERUSER_PASSWORD}${NC}"
echo ""
echo -e "${GREEN}======================================${NC}"
echo ""

manage runserver