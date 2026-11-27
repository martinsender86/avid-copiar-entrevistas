# -*- coding: utf-8 -*-
"""
copiar_entrevistas_25.py

Busca en todos los bins (.avb) de una carpeta de proyecto de Avid Media Composer
los SUBCLIPS cuyo nombre contenga "ENTREVISTA" y cuyo FPS sea 25
(excluyendo los que tengan [B] o [MC] en el nombre),
y los copia a un bin destino de otro proyecto.

Funciona en Windows y en Mac (en Mac se abre con el .command del mismo nombre).

Requisitos:
    Python 3.8+  y  pip install pyavb

Uso:
    python copiar_entrevistas_25.py              -> copia
    python copiar_entrevistas_25.py --dry-run    -> solo lista lo que copiaría

IMPORTANTE: el bin destino tiene que estar CERRADO en Avid mientras corre el script
(si no existe, el script lo crea vacío). Los bins de origen solo se leen.
"""

import os
import re
import sys
import shutil
import argparse
import datetime
import glob

try:
    import avb
except ImportError:
    sys.exit("Falta la librería pyavb. Instalala con:  pip install pyavb")


# ----------------------------------------------------------------------------
# CONFIGURACIÓN
# ----------------------------------------------------------------------------
# Rutas desde la raíz del disco, con "/" (sirven igual en Windows y en Mac).
# El script busca solo en qué disco están: en Windows prueba F: y después las
# otras letras; en Mac, los discos de /Volumes.
CARPETA_ORIGEN_REL = "SOLRAC/_Avid Projects/SOLRAC/03. MATERIAL EDICION"
BIN_DESTINO_REL    = "SOLRAC/_Avid Projects/SOLRAC/ENTREVISTAS 25 FPS-PARA DESGRABAR.avb"

# Opcional: forzar el disco si hay más de uno con esta estructura
# (por ej. el original y un clon). Vacío = automático.
#   Windows: "F:"      Mac: "/Volumes/SOLRAC_A1"
DISCO = ""

PALABRA_CLAVE  = "ENTREVISTA"   # se busca sin distinguir mayúsculas/minúsculas
FPS_BUSCADO    = 25.0
TOLERANCIA     = 0.01
BUSCAR_EN_SUBCARPETAS = True

# Se excluyen clips con estas etiquetas entre corchetes en el nombre.
ETIQUETAS_EXCLUIDAS = ["MC", "B"]
# ----------------------------------------------------------------------------


def discos_candidatos():
    if DISCO:
        return [DISCO]
    if os.name == "nt":
        import string
        return ["F:"] + ["%s:" % d for d in string.ascii_uppercase if d != "F"]
    if sys.platform == "darwin":
        return sorted(glob.glob("/Volumes/*"))
    return sorted(glob.glob("/mnt/*") + glob.glob("/media/*/*"))


def en_disco(disco, rel):
    if os.name == "nt" and disco.endswith(":"):
        disco += "\\"
    return os.path.join(disco, *rel.split("/"))


def resolver_rutas():
    """Devuelve (carpeta_origen, bin_destino) en el disco donde esté el proyecto."""
    encontrados = []
    for d in discos_candidatos():
        if os.path.isdir(en_disco(d, CARPETA_ORIGEN_REL)):
            encontrados.append(d)
    if not encontrados:
        sys.exit("No encuentro la carpeta de origen en ningún disco:\n  " + CARPETA_ORIGEN_REL +
                 "\n¿Está conectado el disco? Si está, revisá CARPETA_ORIGEN_REL o completá DISCO.")
    if len(encontrados) > 1:
        sys.exit("La carpeta de origen está en más de un disco:\n  " + "\n  ".join(encontrados) +
                 "\nCompletá DISCO en la configuración del script con el que corresponde.")
    d = encontrados[0]
    return en_disco(d, CARPETA_ORIGEN_REL), en_disco(d, BIN_DESTINO_REL)


def fps_del_clip(mob):
    """FPS como lo muestra la columna FPS del bin: el edit rate del video del
    master clip. Si el clip no tiene video (solo audio), usa el edit rate del mob."""
    for track in mob.tracks:
        comp = getattr(track, "component", None)
        if comp is not None and comp.media_kind == "picture":
            return float(comp.edit_rate)
    return float(mob.edit_rate)


def etiqueta_excluida(nombre):
    etiquetas = re.findall(r"\[\s*([^\]]+?)\s*\]", nombre)
    excluidas = set(e.upper() for e in ETIQUETAS_EXCLUIDAS)
    return any(e.upper() in excluidas for e in etiquetas)


def es_fps_buscado(fps):
    return abs(fps - FPS_BUSCADO) <= TOLERANCIA


def listar_bins(carpeta):
    bins = []
    if BUSCAR_EN_SUBCARPETAS:
        for raiz, _, archivos in os.walk(carpeta):
            for a in archivos:
                if a.lower().endswith(".avb") and not a.startswith("."):
                    bins.append(os.path.join(raiz, a))
    else:
        for a in os.listdir(carpeta):
            if a.lower().endswith(".avb") and not a.startswith("."):
                bins.append(os.path.join(carpeta, a))
    return sorted(bins)


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--dry-run", action="store_true",
                        help="No escribe nada, solo muestra qué copiaría")
    args = parser.parse_args()

    global CARPETA_ORIGEN, BIN_DESTINO
    CARPETA_ORIGEN, BIN_DESTINO = resolver_rutas()
    print("Origen:  " + CARPETA_ORIGEN)
    print("Destino: " + BIN_DESTINO)

    if not os.path.isdir(CARPETA_ORIGEN):
        sys.exit("No existe la carpeta de origen:\n  " + CARPETA_ORIGEN)
    if not os.path.isfile(BIN_DESTINO):
        if args.dry_run:
            print("(El bin destino no existe; se va a crear al copiar)")
        else:
            with avb.open() as nuevo_bin:
                nuevo_bin.write(BIN_DESTINO)
            print("Bin destino creado:\n  " + BIN_DESTINO)

    destino_abs = os.path.normcase(os.path.abspath(BIN_DESTINO))
    bins = [b for b in listar_bins(CARPETA_ORIGEN)
            if os.path.normcase(os.path.abspath(b)) != destino_abs]

    print("Bins encontrados en origen: %d" % len(bins))

    clave = PALABRA_CLAVE.upper()
    copiados, ya_estaban, otro_fps, excluidos = [], [], [], []
    errores = []

    with (avb.open(BIN_DESTINO) if os.path.isfile(BIN_DESTINO) else avb.open()) as dst:
        ids_en_destino = set(m.mob_id for m in dst.content.mobs)

        for ruta_bin in bins:
            nombre_bin = os.path.basename(ruta_bin)
            try:
                with avb.open(ruta_bin) as src:
                    # Lo que se ve en el bin: master clips y subclips.
                    # Se excluyen los group clips / multigroups ([mc]).
                    # (los source/file mobs ocultos tienen user_placed = False)
                    visibles = [it.mob for it in src.content.items
                                if it.user_placed
                                and it.mob.mob_type != "SourceMob"
                                and getattr(it.mob, "usage", None) == "subclip"]
                    for mob in visibles:
                        nombre = mob.name or ""
                        if clave not in nombre.upper():
                            continue
                        if etiqueta_excluida(nombre):
                            excluidos.append((nombre, nombre_bin))
                            continue

                        fps = fps_del_clip(mob)
                        if not es_fps_buscado(fps):
                            otro_fps.append((nombre, round(fps, 3), nombre_bin))
                            continue

                        if mob.mob_id in ids_en_destino:
                            ya_estaban.append((nombre, nombre_bin))
                            continue

                        copiados.append((nombre, nombre_bin))
                        if args.dry_run:
                            ids_en_destino.add(mob.mob_id)
                            continue

                        # El clip va visible en el bin; el master clip y los
                        # source/file mobs de los que depende van "ocultos",
                        # como los guarda Avid.
                        nuevo = mob.copy(dst)
                        item = dst.content.add_mob(nuevo)
                        item.user_placed = True
                        ids_en_destino.add(mob.mob_id)

                        for dep in mob.dependant_mobs():
                            if dep.mob_id in ids_en_destino:
                                continue
                            dep_item = dst.content.add_mob(dep.copy(dst))
                            dep_item.user_placed = False
                            ids_en_destino.add(dep.mob_id)

            except Exception as e:
                errores.append((nombre_bin, repr(e)))

        # ---- reporte ----
        print("\nClips a copiar (%d):" % len(copiados))
        for n, b in copiados:
            print("  + %-50s  [%s]" % (n, b))
        if ya_estaban:
            print("\nYa estaban en el bin destino, se saltean (%d):" % len(ya_estaban))
            for n, b in ya_estaban:
                print("  = %-50s  [%s]" % (n, b))
        if excluidos:
            print("\nExcluidos por [MC] / [B] (%d):" % len(excluidos))
            for n, b in excluidos:
                print("  x %-50s  [%s]" % (n, b))
        if otro_fps:
            print("\nTienen '%s' pero NO son 25 (%d):" % (PALABRA_CLAVE, len(otro_fps)))
            for n, f, b in otro_fps:
                print("  - %-50s  %s fps  [%s]" % (n, f, b))
        if errores:
            print("\nBins que no se pudieron leer (%d):" % len(errores))
            for b, e in errores:
                print("  ! %s: %s" % (b, e))

        if args.dry_run:
            print("\n--dry-run: no se modificó nada.")
            return
        if not copiados:
            print("\nNada nuevo para copiar. El bin destino quedó igual.")
            return

        # backup del bin destino antes de tocarlo
        sello = datetime.datetime.now().strftime("%Y%m%d_%H%M%S")
        backup = BIN_DESTINO[:-4] + "_BACKUP_" + sello + ".avb.bak"
        shutil.copy2(BIN_DESTINO, backup)

        temporal = BIN_DESTINO + ".tmp"
        dst.write(temporal)

    # se reemplaza recién cuando el archivo nuevo quedó escrito entero
    os.replace(temporal, BIN_DESTINO)
    print("\nListo: %d clips copiados a\n  %s" % (len(copiados), BIN_DESTINO))
    print("Backup del bin anterior:\n  %s" % backup)


if __name__ == "__main__":
    main()
