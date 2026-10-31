# This is an auto-generated Django model module.
# You'll have to do the following manually to clean this up:
#   * Rearrange models' order
#   * Make sure each model has one field with primary_key=True
#   * Make sure each ForeignKey and OneToOneField has `on_delete` set to the desired behavior
#   * Remove `managed = False` lines if you wish to allow Django to create, modify, and delete the table
# Feel free to rename the models, but don't rename db_table values or field names.
from django.db import models


class Usuarios(models.Model):
    id_usuario = models.IntegerField(primary_key=True)
    nombre_usuario = models.CharField(unique=True, max_length=50)
    email = models.CharField(unique=True, max_length=50)
    region = models.CharField(max_length=50)

    class Meta:
        managed = False
        db_table = 'USUARIOS'


class Juegos(models.Model):
    id_juego = models.AutoField(primary_key=True)
    titulo = models.CharField(max_length=50)
    genero = models.CharField(max_length=50)
    rating = models.DecimalField(max_digits=5, decimal_places=1)
    popularidad = models.IntegerField()

    class Meta:
        managed = False
        db_table = 'juegos'


class UsuarioJuegos(models.Model):
    id_usuario = models.ForeignKey(Usuarios, models.DO_NOTHING, db_column='id_usuario', blank=True, null=True)
    id_juego = models.ForeignKey(Juegos, models.DO_NOTHING, db_column='id_juego', blank=True, null=True)
    horas_jugadas = models.IntegerField(blank=True, null=True)
    consola = models.CharField(max_length=50)
    idioma = models.CharField(max_length=30, blank=True, null=True)

    class Meta:
        managed = False
        db_table = 'usuario_juegos'


class VideojuegoCatalogo(models.Model):
    game_id = models.IntegerField(primary_key=True)
    titulo = models.CharField(max_length=255, db_index=True)
    anio = models.IntegerField(null=True, blank=True)
    genero = models.CharField(max_length=255, blank=True, db_index=True)
    rating = models.FloatField(null=True, blank=True)
    metacritic = models.FloatField(null=True, blank=True)
    popularidad = models.FloatField(default=0)
    engagement = models.FloatField(null=True, blank=True)
    horas_promedio = models.FloatField(null=True, blank=True)
    plataformas = models.TextField(blank=True)

    class Meta:
        ordering = ["-popularidad"]

    def __str__(self):
        return self.titulo

class AnalisisVideojuego(models.Model):
    session_key = models.CharField(max_length=40, db_index=True)
    creado = models.DateTimeField(auto_now_add=True)

    nombre = models.CharField(max_length=160)
    genero = models.CharField(max_length=100)
    plataforma = models.CharField(max_length=120)

    modelo = models.CharField(max_length=50, blank=True)
    modo = models.CharField(max_length=50, blank=True)

    horas_estimadas = models.FloatField(default=0)
    precio = models.FloatField(default=0)

    indice = models.PositiveSmallIntegerField()
    nivel = models.CharField(max_length=40)

    muestra = models.PositiveIntegerField(default=0)
    alcance_muestra = models.CharField(max_length=140)

    popularidad_mediana = models.FloatField(default=0)
    rating_mediano = models.FloatField(null=True, blank=True)
    engagement_mediano = models.FloatField(null=True, blank=True)

    favorito = models.BooleanField(default=False)

    class Meta:
        ordering = ["-creado"]

    def __str__(self):
        return self.nombre