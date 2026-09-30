from django.db import migrations


class Migration(migrations.Migration):

    dependencies = [
        ("address", "0001_initial"),
    ]

    operations = [
        migrations.RenameField(
            model_name="address",
            old_name="address_line1",
            new_name="address",
        ),
        migrations.RemoveField(
            model_name="address",
            name="address_line2",
        ),
    ]
