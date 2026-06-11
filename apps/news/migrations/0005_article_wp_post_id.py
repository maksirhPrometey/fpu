from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ("news", "0004_local_image_fields"),
    ]

    operations = [
        migrations.AddField(
            model_name="article",
            name="wp_post_id",
            field=models.IntegerField(
                blank=True,
                db_index=True,
                null=True,
                unique=True,
                verbose_name="WordPress ID",
            ),
        ),
        migrations.AddField(
            model_name="article",
            name="source_url",
            field=models.URLField(blank=True, max_length=500, verbose_name="Джерело (URL)"),
        ),
    ]
