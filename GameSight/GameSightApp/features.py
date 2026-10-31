from collections import Counter
from statistics import median

from django.shortcuts import get_object_or_404, redirect, render
from django.views.decorators.http import require_POST
from .models import AnalisisVideojuego, VideojuegoCatalogo
from functools import wraps
from django.contrib.auth.decorators import login_required
from django.http import HttpResponseForbidden

def obtener_sesion(request):
    if not request.session.session_key:
        request.session.create()

    return request.session.session_key


def convertir_float(valor):
    try:
        return float(valor)
    except (ValueError, TypeError):
        return None


def obtener_comparables(genero, plataforma, horas):
    catalogo = VideojuegoCatalogo.objects.filter(
        popularidad__isnull=False
    )

    if genero:
        catalogo = catalogo.filter(
            genero__icontains=genero
        )

    juegos = list(
        catalogo.values(
            "titulo",
            "genero",
            "plataformas",
            "rating",
            "popularidad",
            "engagement",
            "horas_promedio",
        )
    )

    candidatos = juegos

    if plataforma:
        filtrados = [
            j for j in candidatos
            if plataforma.lower() in
            (j["plataformas"] or "").lower()
        ]

        if len(filtrados) >= 20:
            candidatos = filtrados

    if horas is not None:
        filtrados = [
            j for j in candidatos
            if j["horas_promedio"] is not None
            and abs(j["horas_promedio"] - horas)
            <= max(5, horas * 0.35)
        ]

        if len(filtrados) >= 20:
            candidatos = filtrados

    if len(candidatos) < 10:
        candidatos = list(
            VideojuegoCatalogo.objects.filter(
                popularidad__isnull=False
            ).values(
                "titulo",
                "genero",
                "plataformas",
                "rating",
                "popularidad",
                "engagement",
                "horas_promedio",
            )
        )

        alcance = "Catálogo general"
    elif len(candidatos) == len(juegos):
        alcance = "Género seleccionado"
    else:
        alcance = "Género y características similares"

    return candidatos, alcance


def calcular_analisis(genero, plataforma, horas):
    juegos, alcance = obtener_comparables(
        genero, plataforma, horas
    )

    popularidades = [
        float(j["popularidad"])
        for j in juegos
        if j["popularidad"] is not None
    ]

    ratings = [
        float(j["rating"])
        for j in juegos
        if j["rating"] is not None
    ]

    engagements = [
        float(j["engagement"])
        for j in juegos
        if j["engagement"] is not None
    ]

    if not popularidades:
        raise ValueError(
            "No hay suficientes datos de popularidad."
        )

    popularidad_mediana = median(popularidades)

    rating_mediano = (
        median(ratings) if ratings else None
    )

    engagement_mediano = (
        median(engagements) if engagements else None
    )

    # Comparar la popularidad mediana del grupo
    # con la distribución del catálogo completo.

    popularidad_global = list(
        VideojuegoCatalogo.objects.filter(
            popularidad__isnull=False
        ).values_list(
            "popularidad", flat=True
        )
    )

    if not popularidad_global:
        raise ValueError("No hay datos para comparar.")

    indice = round(
        sum(
            1 for valor in popularidad_global
            if valor <= popularidad_mediana
        ) / len(popularidad_global) * 100
    )

    if indice >= 67:
        nivel = "Potencial relativo alto"
    elif indice >= 34:
        nivel = "Potencial relativo medio"
    else:
        nivel = "Potencial relativo bajo"

    ejemplos = sorted(
        juegos,
        key=lambda j: abs(
            float(j["popularidad"]) -
            popularidad_mediana
        )
    )[:6]

    return {
        "indice": indice,
        "nivel": nivel,
        "muestra": len(juegos),
        "alcance": alcance,
        "popularidad_mediana": round(
            popularidad_mediana, 2
        ),
        "rating_mediano": (
            round(rating_mediano, 2)
            if rating_mediano is not None else None
        ),
        "engagement_mediano": (
            round(engagement_mediano, 2)
            if engagement_mediano is not None else None
        ),
        "ejemplos": ejemplos,
    }



def contexto_formulario():
    generos = Counter()
    plataformas = Counter()

    datos = VideojuegoCatalogo.objects.values_list(
        "genero", "plataformas"
    ).iterator(chunk_size=2000)

    for genero, plataforma in datos:
        for valor in (genero or "").replace(
            ";", "|"
        ).replace(",", "|").split("|"):
            if valor.strip():
                generos[valor.strip()] += 1

        for valor in (plataforma or "").replace(
            ";", "|"
        ).replace(",", "|").split("|"):
            if valor.strip():
                plataformas[valor.strip()] += 1

    # Los 8 géneros con más videojuegos
    top_generos = generos.most_common(8)

    return {
        # Opciones del formulario original
        "generos_opciones": [
            g for g, _ in generos.most_common(40)
        ],
        "plataformas_opciones": [
            p for p, _ in plataformas.most_common(30)
        ],

        # KPI: total de videojuegos almacenados en AWS
        "cantidad_catalogo":
            VideojuegoCatalogo.objects.count(),

        # Datos para el gráfico de géneros
        "grafico_generos": {
            "labels": [
                genero for genero, cantidad in top_generos
            ],
            "values": [
                cantidad for genero, cantidad in top_generos
            ],
        },
    }


def user_overview(request):
    contexto = contexto_formulario()

    # Consultar análisis del usuario actual
    registros = AnalisisVideojuego.objects.filter(
        session_key=obtener_sesion(request)
    )

    # KPI 2: total de análisis realizados
    contexto["total_historial"] = registros.count()

    # KPI 3: total de favoritos guardados
    contexto["total_favoritos"] = registros.filter(
        favorito=True
    ).count()

    # Tabla: últimos 5 videojuegos analizados
    contexto["ultimos_analisis"] = registros.order_by(
        "-creado"
    )[:5]

    return render(
        request,
        "GameSightApp/usuario.html",
        contexto,
    )


@require_POST
def analizar(request):
    nombre = request.POST.get(
        "nombre", ""
    ).strip()[:160]

    genero = request.POST.get(
        "genero", ""
    ).strip()[:100]

    plataforma = request.POST.get(
        "plataforma", ""
    ).strip()[:120]

    modelo = request.POST.get(
        "modelo", ""
    ).strip()[:50]

    modo = request.POST.get(
        "modo", ""
    ).strip()[:50]

    horas = convertir_float(
        request.POST.get("horas")
    )

    precio = convertir_float(
        request.POST.get("precio")
    )

    errores = []

    if not nombre:
        errores.append("Ingresa el nombre del juego.")

    if not genero:
        errores.append("Selecciona un género.")

    if not plataforma:
        errores.append("Selecciona una plataforma.")

    if horas is None or not 0 <= horas <= 10000:
        errores.append("Ingresa horas válidas.")

    if precio is None or not 0 <= precio <= 10000:
        errores.append("Ingresa un precio válido.")

    if errores:
        contexto = contexto_formulario()
        contexto["errores"] = errores
        contexto["formulario"] = request.POST

        return render(
            request,
            "GameSightApp/usuario.html",
            contexto,
            status=400,
        )

    resultado = calcular_analisis(
        genero, plataforma, horas
    )

    registro = AnalisisVideojuego.objects.create(
        session_key=obtener_sesion(request),
        nombre=nombre,
        genero=genero,
        plataforma=plataforma,
        modelo=modelo,
        modo=modo,
        horas_estimadas=horas,
        precio=precio,
        indice=resultado["indice"],
        nivel=resultado["nivel"],
        muestra=resultado["muestra"],
        alcance_muestra=resultado["alcance"],
        popularidad_mediana=resultado[
            "popularidad_mediana"
        ],
        rating_mediano=resultado[
            "rating_mediano"
        ],
        engagement_mediano=resultado[
            "engagement_mediano"
        ],
    )

    return redirect(
        "gamesight_resultado",
        pk=registro.pk,
    )

def historial(request):
    registros = AnalisisVideojuego.objects.filter(
        session_key=obtener_sesion(request)
    )

    return render(
        request,
        "GameSightApp/historial.html",
        {"registros": registros},
    )

def resultado(request, pk):
    juego = get_object_or_404(
        AnalisisVideojuego,
        pk=pk,
        session_key=obtener_sesion(request),
    )

    juegos, _ = obtener_comparables(
        juego.genero,
        juego.plataforma,
        juego.horas_estimadas,
    )

    ejemplos = sorted(
        juegos,
        key=lambda j: abs(
            float(j["popularidad"]) -
            juego.popularidad_mediana
        )
    )[:6]

    return render(
        request,
        "GameSightApp/resultado.html",
        {
            "juego": juego,
            "ejemplos": ejemplos,
        },
    )

@require_POST
def favorito(request, pk):
    juego = get_object_or_404(
        AnalisisVideojuego,
        pk=pk,
        session_key=obtener_sesion(request),
    )

    juego.favorito = not juego.favorito

    juego.save(update_fields=["favorito"])

    return redirect(
        "gamesight_resultado",
        pk=pk,
    )


def favoritos(request):
    registros = AnalisisVideojuego.objects.filter(
        session_key=obtener_sesion(request),
        favorito=True,
    )

    return render(
        request,
        "GameSightApp/historial.html",
        {
            "registros": registros,
            "solo_favoritos": True,
        },
    )