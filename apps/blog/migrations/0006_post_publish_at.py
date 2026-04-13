from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('blog', '0005_post_published_at_alter_post_status'),
    ]

    operations = [
        migrations.AddField(
            model_name='post',
            name='publish_at',
            field=models.DateTimeField(blank=True, null=True),
        ),
    ]
