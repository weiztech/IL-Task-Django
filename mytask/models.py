from django.db import models


class Planet(models.Model):
    name = models.CharField(max_length=300)
    description = models.TextField(blank=True, null=True)
    # distance format in million kilometers from earth
    distance = models.IntegerField()
    # Found date
    date = models.DateField()

    def __str__(self) -> str:
        return self.name
