
import csv
from pathlib import Path

from django.conf import settings
from django.core.management.base import BaseCommand, CommandError
from django.db import transaction

from GameSightApp.models import VideojuegoCatalogo


def numero(valor):
    try:
        if valor is None or str(valor).strip() == "":
            return None
        return float(valor)
    except (ValueError, TypeError):
        return None


class Command(BaseCommand):
    help = "Importa videojuegos desde videojuegos.csv"

    def handle(self, *args, **options):
        archivo = Path(settings.BASE_DIR) / "videojuegos.csv"

        if not archivo.exists():
            raise CommandError(
                f"No se encontró el archivo: {archivo}"
            )

        juegos = []
        ids = set()

        with archivo.open(
            "r", encoding="utf-8-sig", newline=""
        ) as f:
            lector = csv.DictReader(f)

            requeridas = {
                "game_id",
                "title",
                "all_genres",
                "user_rating",
                "metacritic",
                "popularity_score",
                "engagement_score",
                "avg_playtime_hours",
                "all_platforms",
                "release_year",
            }

            if not requeridas.issubset(set(lector.fieldnames or [])):
                raise CommandError(
                    "Faltan columnas necesarias en el CSV. "
                    f"Columnas encontradas: {lector.fieldnames}"
                )

            for fila in lector:
                try:
                    game_id = int(fila["game_id"])
                except (ValueError, TypeError):
                    continue

                titulo = (fila.get("title") or "").strip()

                if not titulo or game_id in ids:
                    continue

                ids.add(game_id)
                anio_num = numero(fila.get("release_year"))

                juegos.append(
                    VideojuegoCatalogo(
                        game_id=game_id,
                        titulo=titulo,
                        anio=int(anio_num) if anio_num else None,
                        genero=(fila.get("all_genres") or "")[:255],
                        rating=numero(fila.get("user_rating")),
                        metacritic=numero(fila.get("metacritic")),
                        popularidad=(
                            numero(fila.get("popularity_score")) or 0
                        ),
                        engagement=numero(
                            fila.get("engagement_score")
                        ),
                        horas_promedio=numero(
                            fila.get("avg_playtime_hours")
                        ),
                        plataformas=fila.get("all_platforms") or "",
                    )
                )

        if not juegos:
            raise CommandError(
                "No se encontraron videojuegos válidos para importar."
            )

        with transaction.atomic():
            VideojuegoCatalogo.objects.all().delete()
            VideojuegoCatalogo.objects.bulk_create(
                juegos, batch_size=1000
            )

        total = VideojuegoCatalogo.objects.count()

        self.stdout.write(
            self.style.SUCCESS(
                f"Importación terminada: {total} videojuegos."
            )
        )
