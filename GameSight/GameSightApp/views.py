from collections import Counter
from statistics import mean

from django.core.paginator import Paginator
from django.db.models import Avg, Count
from django.shortcuts import render

from django.contrib.auth import authenticate, login, logout
from django.contrib.admin.views.decorators import staff_member_required
from django.views.decorators.http import require_POST
from django.shortcuts import redirect, render

from .models import VideojuegoCatalogo

from django.db.models import Q

def separar_valores(valor):
    if not valor:
        return []

    texto = str(valor).strip().strip("[]")
    for separador in (";", "|"):
        texto = texto.replace(separador, ",")

    return list(dict.fromkeys(
        elemento.strip().strip("'\" ")
        for elemento in texto.split(",")
        if elemento.strip().strip("'\" ")
    ))


def normalizar_100(valor, minimo, maximo):
    if valor is None:
        return 0
    if maximo == minimo:
        return 50
    resultado = ((float(valor) - float(minimo)) / (float(maximo) - float(minimo))) * 100
    return max(0, min(100, round(resultado)))


def obtener_stats_base():
    catalogo = VideojuegoCatalogo.objects.all()
    total_juegos = catalogo.count()

    promedios = catalogo.aggregate(
        rating_promedio=Avg("rating"),
        popularidad_promedio=Avg("popularidad"),
        horas_promedio=Avg("horas_promedio"),
        engagement_promedio=Avg("engagement"),
        metacritic_promedio=Avg("metacritic"),
        ratings_disponibles=Count("rating"),
    )

    conteo_generos = Counter()
    conteo_plataformas = Counter()

    juegos_base = list(
        catalogo.values(
            "titulo",
            "anio",
            "genero",
            "rating",
            "metacritic",
            "popularidad",
            "engagement",
            "horas_promedio",
            "plataformas",
        )
    )

    for juego in juegos_base:
        conteo_generos.update(separar_valores(juego["genero"]))
        conteo_plataformas.update(separar_valores(juego["plataformas"]))

    generos_top = [
        {"genero": nombre, "total": cantidad}
        for nombre, cantidad in conteo_generos.most_common(10)
    ]

    plataformas_top = [
        {"consola": nombre, "total": cantidad}
        for nombre, cantidad in conteo_plataformas.most_common(8)
    ]

    ratings_top = [
        {"titulo": juego.titulo, "rating": juego.rating}
        for juego in catalogo.filter(
            rating__isnull=False
        ).order_by("-rating", "titulo")[:10]
    ]

    popularidades_top = [
        {"titulo": juego.titulo, "popularidad": juego.popularidad}
        for juego in catalogo.filter(
            popularidad__isnull=False
        ).order_by("-popularidad", "titulo")[:10]
    ]

    engagement_top = [
        {
            "titulo": juego.titulo,
            "engagement": juego.engagement,
            "rating": juego.rating,
            "popularidad": juego.popularidad,
        }
        for juego in catalogo.filter(
            engagement__isnull=False,
            rating__isnull=False,
            popularidad__isnull=False,
        ).order_by("-engagement")[:10]
    ]

    # Filtros del admin
    busqueda = ""
    genero_seleccionado = ""
    plataforma_seleccionada = ""
    rating_filtro = ""
    popularidad_filtro = ""

    lista_generos = sorted(conteo_generos.keys())
    lista_plataformas = sorted(conteo_plataformas.keys())

    # Tendencia por año
    anios_counter = Counter()
    for juego in juegos_base:
        if juego["anio"]:
            anios_counter[str(juego["anio"])] += 1

    tendencia_anios = [
        {"anio": anio, "total": total}
        for anio, total in sorted(anios_counter.items(), key=lambda x: x[0])[-12:]
    ]

    # Distribución ratings
    buckets = {
        "1-2": 0,
        "2-4": 0,
        "4-6": 0,
        "6-8": 0,
        "8-10": 0,
    }

    for juego in juegos_base:
        r = juego["rating"]
        if r is None:
            continue
        r = float(r)
        if r < 2:
            buckets["1-2"] += 1
        elif r < 4:
            buckets["2-4"] += 1
        elif r < 6:
            buckets["4-6"] += 1
        elif r < 8:
            buckets["6-8"] += 1
        else:
            buckets["8-10"] += 1

    distribucion_ratings = [
        {"rango": k, "total": v} for k, v in buckets.items()
    ]

    # Scatter popularidad vs engagement
    scatter_pop_eng = []
    for juego in juegos_base:
        if juego["popularidad"] is not None and juego["engagement"] is not None:
            scatter_pop_eng.append({
                "x": round(float(juego["popularidad"]), 2),
                "y": round(float(juego["engagement"]), 2),
            })

    scatter_pop_eng = scatter_pop_eng[:250]

    # Catálogo paginado
    juegos_filtrados = catalogo.order_by("-popularidad", "titulo")
    paginador = Paginator(juegos_filtrados, 100)
    pagina = paginador.get_page(1)

    juegos = [
        {
            "titulo": juego.titulo,
            "genero": juego.genero,
            "rating": juego.rating,
            "popularidad": juego.popularidad,
            "metacritic": juego.metacritic,
            "engagement": juego.engagement,
            "horas_promedio": juego.horas_promedio,
            "anio": juego.anio,
            "plataformas": juego.plataformas,
        }
        for juego in pagina.object_list
    ]

    return {
        "catalogo": catalogo,
        "total_juegos": total_juegos,
        "rating_promedio": promedios["rating_promedio"],
        "popularidad_promedio": promedios["popularidad_promedio"],
        "horas_promedio": promedios["horas_promedio"],
        "engagement_promedio": promedios["engagement_promedio"],
        "metacritic_promedio": promedios["metacritic_promedio"],
        "ratings_disponibles": promedios["ratings_disponibles"],
        "generos": generos_top,
        "ratings": ratings_top,
        "popularidades": popularidades_top,
        "engagement": engagement_top,
        "consolas": plataformas_top,
        "lista_generos": lista_generos,
        "lista_plataformas": lista_plataformas,
        "busqueda": busqueda,
        "genero_seleccionado": genero_seleccionado,
        "plataforma_seleccionada": plataforma_seleccionada,
        "rating_filtro": rating_filtro,
        "popularidad_filtro": popularidad_filtro,
        "pagina": pagina,
        "juegos": juegos,
        "genero_principal": generos_top[0] if generos_top else None,
        "juego_mejor_valorado": ratings_top[0] if ratings_top else None,
        "juego_mas_popular": popularidades_top[0] if popularidades_top else None,
        "tendencia_anios": tendencia_anios,
        "distribucion_ratings": distribucion_ratings,
        "scatter_pop_eng": scatter_pop_eng,
        "raw_juegos": juegos_base,
        "conteo_generos": conteo_generos,
        "conteo_plataformas": conteo_plataformas,
    }


def index(request):
    total_juegos = VideojuegoCatalogo.objects.count()
    contexto = {
        "total_juegos": total_juegos,
        "total_variables": 43,
    }
    return render(request, "GameSightApp/index.html", contexto)



def dashboard(request):
    base = obtener_stats_base()
    catalogo = base["catalogo"]

    busqueda = request.GET.get("q", "").strip()
    genero_seleccionado = request.GET.get("genero", "").strip()
    plataforma_seleccionada = request.GET.get("plataforma", "").strip()
    rating_filtro = request.GET.get("rating", "").strip()
    popularidad_filtro = request.GET.get("popularidad", "").strip()

    juegos_filtrados = catalogo

    if busqueda:
        juegos_filtrados = juegos_filtrados.filter(
            Q(titulo__icontains=busqueda) |
            Q(genero__icontains=busqueda) |
            Q(plataformas__icontains=busqueda)
    )

    if genero_seleccionado:
        juegos_filtrados = juegos_filtrados.filter(genero__icontains=genero_seleccionado)

    if plataforma_seleccionada:
        juegos_filtrados = juegos_filtrados.filter(plataformas__icontains=plataforma_seleccionada)

    if rating_filtro == "alta":
        juegos_filtrados = juegos_filtrados.filter(rating__gte=8)
    elif rating_filtro == "media":
        juegos_filtrados = juegos_filtrados.filter(rating__gte=5, rating__lt=8)
    elif rating_filtro == "baja":
        juegos_filtrados = juegos_filtrados.filter(rating__lt=5)

    if popularidad_filtro == "alta":
        juegos_filtrados = juegos_filtrados.filter(popularidad__gte=70)
    elif popularidad_filtro == "media":
        juegos_filtrados = juegos_filtrados.filter(popularidad__gte=40, popularidad__lt=70)
    elif popularidad_filtro == "baja":
        juegos_filtrados = juegos_filtrados.filter(popularidad__lt=40)

    juegos_filtrados = juegos_filtrados.order_by("-popularidad", "titulo")

    paginador = Paginator(juegos_filtrados, 100)
    pagina = paginador.get_page(request.GET.get("page"))

    juegos = [
        {
            "titulo": juego.titulo,
            "genero": juego.genero,
            "rating": juego.rating,
            "popularidad": juego.popularidad,
            "metacritic": juego.metacritic,
            "engagement": juego.engagement,
            "horas_promedio": juego.horas_promedio,
            "anio": juego.anio,
            "plataformas": juego.plataformas,
        }
        for juego in pagina.object_list
    ]

    contexto = {
        **base,
        "busqueda": busqueda,
        "genero_seleccionado": genero_seleccionado,
        "plataforma_seleccionada": plataforma_seleccionada,
        "rating_filtro": rating_filtro,
        "popularidad_filtro": popularidad_filtro,
        "pagina": pagina,
        "juegos": juegos,
        "resultados_encontrados": paginador.count,
    }

    return render(request, "GameSightApp/admin.html", contexto)


def dashboard_usuario(request):
    base = obtener_stats_base()
    juegos_base = base["raw_juegos"]

    # Inputs usuario
    nombre = request.GET.get("nombre", "Project Nebula").strip() or "Project Nebula"
    genero = request.GET.get("genero_usuario", "Aventura").strip() or "Aventura"
    plataforma = request.GET.get("plataforma_usuario", "PC, PlayStation 5").strip() or "PC, PlayStation 5"
    modelo = request.GET.get("modelo", "Premium (pago único)").strip() or "Premium (pago único)"
    modo = request.GET.get("modo", "Singleplayer").strip() or "Singleplayer"
    horas = request.GET.get("horas", "15-25").strip() or "15-25"
    num_plataformas = request.GET.get("num_plataformas", "2").strip() or "2"
    precio = request.GET.get("precio", "49.99").strip() or "49.99"

    rating_promedio = float(base["rating_promedio"] or 0)
    popularidad_promedio = float(base["popularidad_promedio"] or 0)
    engagement_promedio = float(base["engagement_promedio"] or 0)
    horas_promedio = float(base["horas_promedio"] or 0)

    rating_valores = [j["rating"] for j in juegos_base if j["rating"] is not None]
    popularidad_valores = [j["popularidad"] for j in juegos_base if j["popularidad"] is not None]
    engagement_valores = [j["engagement"] for j in juegos_base if j["engagement"] is not None]
    horas_valores = [j["horas_promedio"] for j in juegos_base if j["horas_promedio"] is not None]

    # promedio por género
    juegos_genero = [j for j in juegos_base if genero.lower() in (j["genero"] or "").lower()]
    if juegos_genero:
        rating_genero = mean([j["rating"] for j in juegos_genero if j["rating"] is not None] or [rating_promedio])
        popularidad_genero = mean([j["popularidad"] for j in juegos_genero if j["popularidad"] is not None] or [popularidad_promedio])
        engagement_genero = mean([j["engagement"] for j in juegos_genero if j["engagement"] is not None] or [engagement_promedio])
        horas_genero = mean([j["horas_promedio"] for j in juegos_genero if j["horas_promedio"] is not None] or [horas_promedio])
    else:
        rating_genero = rating_promedio
        popularidad_genero = popularidad_promedio
        engagement_genero = engagement_promedio
        horas_genero = horas_promedio

    # heurística usuario
    try:
        precio_num = float(precio)
    except:
        precio_num = 49.99

    try:
        n_plats = int(num_plataformas)
    except:
        n_plats = 2

    calidad = min(100, round((rating_genero / 10) * 100 + 8))
    popularidad_score = min(100, round(normalizar_100(popularidad_genero, min(popularidad_valores or [0]), max(popularidad_valores or [100])) + 5))
    engagement_score = min(100, round(normalizar_100(engagement_genero, min(engagement_valores or [0]), max(engagement_valores or [100])) + (3 if "multi" not in modo.lower() else 6)))
    retencion = min(100, round(normalizar_100(horas_genero, min(horas_valores or [0]), max(horas_valores or [100])) + (4 if "15" in horas or "25" in horas else 0)))
    alcance = min(100, round(55 + min(n_plats * 6, 20) + (5 if "PC" in plataforma else 0) + (4 if precio_num < 40 else 0)))

    radar_usuario = [calidad, popularidad_score, engagement_score, retencion, alcance]
    radar_dataset = [
        round((rating_promedio / 10) * 100) if rating_promedio else 50,
        round(normalizar_100(popularidad_promedio, min(popularidad_valores or [0]), max(popularidad_valores or [100]))),
        round(normalizar_100(engagement_promedio, min(engagement_valores or [0]), max(engagement_valores or [100]))),
        round(normalizar_100(horas_promedio, min(horas_valores or [0]), max(horas_valores or [100]))),
        60,
    ]

    similares = sorted(
        [
            j for j in juegos_base
            if genero.lower() in (j["genero"] or "").lower()
        ],
        key=lambda x: (
            abs((x["rating"] or rating_promedio) - rating_genero) +
            abs((x["popularidad"] or popularidad_promedio) - popularidad_genero)
        )
    )[:5]

    similares_tabla = []
    for i, s in enumerate(similares, start=1):
        similares_tabla.append({
            "n": i,
            "nombre": s["titulo"],
            "genero": s["genero"] or "Sin datos",
            "plataforma": s["plataformas"] or "Sin datos",
            "calidad": round(((s["rating"] or rating_promedio) / 10) * 100),
            "engagement": round(s["engagement"] or engagement_promedio or 0),
        })

    comparacion_barras = [
        {"dimension": "Calidad", "mi_proyecto": calidad, "promedio_genero": round((rating_genero / 10) * 100)},
        {"dimension": "Popularidad", "mi_proyecto": popularidad_score, "promedio_genero": round(normalizar_100(popularidad_genero, min(popularidad_valores or [0]), max(popularidad_valores or [100])))},
        {"dimension": "Engagement", "mi_proyecto": engagement_score, "promedio_genero": round(normalizar_100(engagement_genero, min(engagement_valores or [0]), max(engagement_valores or [100])))},
        {"dimension": "Retención", "mi_proyecto": retencion, "promedio_genero": round(normalizar_100(horas_genero, min(horas_valores or [0]), max(horas_valores or [100])))},
        {"dimension": "Alcance", "mi_proyecto": alcance, "promedio_genero": 65},
    ]

    contexto = {
        **base,
        "input_nombre": nombre,
        "input_genero": genero,
        "input_plataforma": plataforma,
        "input_modelo": modelo,
        "input_modo": modo,
        "input_horas": horas,
        "input_num_plataformas": num_plataformas,
        "input_precio": precio,
        "score_calidad": calidad,
        "score_engagement": engagement_score,
        "score_popularidad": popularidad_score,
        "score_retencion": retencion,
        "score_alcance": alcance,
        "tag_popularidad": "Alta" if popularidad_score >= 75 else "Media" if popularidad_score >= 50 else "Baja",
        "radar_usuario": radar_usuario,
        "radar_dataset": radar_dataset,
        "comparacion_barras": comparacion_barras,
        "similares_tabla": similares_tabla,
    }

    return render(request, "GameSightApp/usuario.html", contexto)


def ingresar(request):
    if request.method == "POST":
        tipo = request.POST.get("tipo", "usuario")

        # El correo y contraseña son solo demostrativos.
        # No se verifican ni se guardan.

        if tipo == "admin":
            return redirect("dashboard")

        return redirect("dashboard_usuario")

    return render(
        request,
        "GameSightApp/login.html"
    )


@require_POST
def salir(request):
    logout(request)
    return redirect("index")
