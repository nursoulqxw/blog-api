from django.core.management.base import BaseCommand
from django.contrib.auth import get_user_model
from apps.blog.models import Category, Tag, Post, Comment

class Command(BaseCommand):
    help = "Seed the database with test data"

    def handle(self, *args, **kwargs):
        User = get_user_model()

        # Users
        users_data = [
            ('alice@blog.local', 'Alice', 'Smith', 'Alicepass1!'),
            ('bob@blog.local', 'Bob', 'Jones', 'Bobpass1!'),
            ('carol@blog.local', 'Carol', 'White', 'Carolpass1!'),
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

        # Superuser
        if not User.objects.filter(email='admin@blog.local').exists():
            User.objects.create_superuser(
                email='admin@blog.local',
                password='Admin1234!',
                first_name='Admin',
                last_name='User',
            )

        # Categories
        cats_data = [
            ('Technology', 'technology'),
            ('Science', 'science'),
            ('Travel', 'travel'),
        ]
        categories = []
        for name, slug in cats_data:
            c, _ = Category.objects.get_or_create(slug=slug, defaults={'name': name})
            categories.append(c)

        # Tags
        tags = []
        for name in ['python', 'django', 'rest-api', 'tutorial', 'news']:
            t, _ = Tag.objects.get_or_create(slug=name, defaults={'name': name})
            tags.append(t)

        # Posts
        posts_data = [
            ('Hello World', 'hello-world', 'published'),
            ('Django Tips', 'django-tips', 'published'),
            ('Async Python', 'async-python', 'published'),
            ('REST API Design', 'rest-api-design', 'published'),
            ('Travel Diary: Almaty', 'travel-diary-almaty', 'published'),
            ('Draft Post 1', 'draft-post-1', 'draft'),
            ('Draft Post 2', 'draft-post-2', 'draft'),
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

        self.stdout.write(self.style.SUCCESS("Seed data OK."))