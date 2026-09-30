import uuid

import django.db.models.deletion
from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ("products", "0005_product_is_discounted"),
    ]

    operations = [
        migrations.RenameField(
            model_name="product",
            old_name="image",
            new_name="cover_image",
        ),
        migrations.AlterField(
            model_name="product",
            name="cover_image",
            field=models.ImageField(upload_to="products/"),
        ),
        migrations.CreateModel(
            name="ProductImage",
            fields=[
                ("id", models.UUIDField(default=uuid.uuid4, editable=False, primary_key=True, serialize=False)),
                ("image", models.ImageField(upload_to="products/sub_images/")),
                ("created_at", models.DateTimeField(auto_now_add=True)),
                ("product", models.ForeignKey(on_delete=django.db.models.deletion.CASCADE, related_name="sub_images", to="products.product")),
            ],
            options={
                "ordering": ["created_at"],
            },
        ),
    ]
