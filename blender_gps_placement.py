"""
TOMBEAU DES ASKIA — Script de placement GPS dans Blender
=========================================================
Comment utiliser :
  1. Ouvre Blender
  2. Va dans l'onglet "Scripting" (barre du haut)
  3. Clique "Ouvrir" et charge ce fichier
  4. Clique "Exécuter le script" (bouton ▶ ou Alt+P)
  5. Une image satellite apparaît + le modèle est importé
  6. Déplace le modèle librement sur la carte
  7. Lis les coordonnées GPS en temps réel dans le panneau
     "Tombeau GPS" (barre latérale droite, touche N)
  8. Clique "Copier le code" quand tu es satisfait
"""

import bpy
import urllib.request
import math
import os

# ═══════════════════════════════════════════════════
#  CONFIGURATION — modifie si nécessaire
# ═══════════════════════════════════════════════════
CENTER_LAT = 16.27970          # GPS centre de la carte
CENTER_LNG = -0.03925
ZOOM       = 17                # Zoom satellite (17 = vue détaillée)
TILES_GRID = 3                 # Grille de tuiles : 3x3 (plus de contexte)
GLB_PATH   = r"C:\Users\Kabakoo Apprenant.e\Desktop\MES PROJETS\tombeau-des-askia\assets\3d\Tombeaux_des_Askia.glb"
# ═══════════════════════════════════════════════════


# ── Conversion GPS → numéro de tuile ──
def deg2num(lat, lng, zoom):
    lat_r = math.radians(lat)
    n = 2 ** zoom
    x = int((lng + 180) / 360 * n)
    y = int((1 - math.asinh(math.tan(lat_r)) / math.pi) / 2 * n)
    return x, y

# ── Taille réelle d'une tuile en mètres ──
def tile_size_meters(lat, zoom):
    lat_r = math.radians(lat)
    return 156543.03392 * math.cos(lat_r) / (2 ** zoom) * 256


# ════════════════════════════════════════════════════
#  1. TÉLÉCHARGEMENT ET ASSEMBLAGE DES TUILES
# ════════════════════════════════════════════════════
def download_tiles():
    try:
        from PIL import Image
        import io
        use_pil = True
    except ImportError:
        use_pil = False

    tx_c, ty_c = deg2num(CENTER_LAT, CENTER_LNG, ZOOM)
    half = TILES_GRID // 2
    tmp_dir = bpy.app.tempdir

    if use_pil:
        # Assemble les tuiles en une seule image
        total_px = 256 * TILES_GRID
        mosaic = Image.new('RGB', (total_px, total_px))
        for dy in range(TILES_GRID):
            for dx in range(TILES_GRID):
                tx = tx_c - half + dx
                ty = ty_c - half + dy
                url = f"https://mt1.google.com/vt/lyrs=s&x={tx}&y={ty}&z={ZOOM}"
                req = urllib.request.Request(url, headers={'User-Agent': 'Mozilla/5.0'})
                with urllib.request.urlopen(req, timeout=10) as r:
                    data = r.read()
                tile_img = Image.open(io.BytesIO(data)).convert('RGB')
                mosaic.paste(tile_img, (dx * 256, dy * 256))
        out = os.path.join(tmp_dir, "satellite_askia_mosaic.jpg")
        mosaic.save(out, quality=90)
        return out, TILES_GRID
    else:
        # Sans PIL : télécharge seulement la tuile centrale
        tx, ty = tx_c, ty_c
        url = f"https://mt1.google.com/vt/lyrs=s&x={tx}&y={ty}&z={ZOOM}"
        req = urllib.request.Request(url, headers={'User-Agent': 'Mozilla/5.0'})
        out = os.path.join(tmp_dir, "satellite_askia.jpg")
        with urllib.request.urlopen(req, timeout=10) as r:
            with open(out, 'wb') as f:
                f.write(r.read())
        return out, 1


# ════════════════════════════════════════════════════
#  2. CONSTRUCTION DE LA SCÈNE
# ════════════════════════════════════════════════════
def setup_scene(img_path, n_tiles):
    # Nettoie la scène (garde seulement la caméra et la lumière)
    for obj in list(bpy.data.objects):
        if obj.type in ('MESH', 'EMPTY'):
            bpy.data.objects.remove(obj, do_unlink=True)

    # Taille réelle en mètres de la mosaïque
    one_tile_m = tile_size_meters(CENTER_LAT, ZOOM)
    plane_m    = one_tile_m * n_tiles

    # Crée le plan satellite (1 unité Blender = 1 mètre)
    bpy.ops.mesh.primitive_plane_add(size=plane_m, location=(0, 0, 0))
    plane = bpy.context.active_object
    plane.name = "Satellite_Gao"
    plane.lock_location = (True, True, True)  # immobile

    # Applique la texture satellite
    mat = bpy.data.materials.new("SatelliteMat")
    mat.use_nodes = True
    nodes = mat.node_tree.nodes
    links = mat.node_tree.links
    bsdf  = nodes["Principled BSDF"]
    bsdf.inputs['Roughness'].default_value = 1.0
    try:
        bsdf.inputs['Specular'].default_value = 0.0
    except Exception:
        pass

    tex = nodes.new('ShaderNodeTexImage')
    img = bpy.data.images.load(img_path)
    tex.image = img
    links.new(bsdf.inputs['Base Color'], tex.outputs['Color'])
    plane.data.materials.append(mat)

    # Repère visuel : croix au centre (= GPS de référence)
    bpy.ops.object.empty_add(type='PLAIN_AXES', location=(0, 0, 0))
    marker = bpy.context.active_object
    marker.name = "GPS_Centre_Tombeau"
    marker.empty_display_size = 5
    marker.lock_location = (True, True, True)

    # Importe le modèle GLB
    if os.path.exists(GLB_PATH):
        bpy.ops.import_scene.gltf(filepath=GLB_PATH)
        model = bpy.context.active_object
        model.name = "Tombeau_Askia_3D"
        model.location = (0, 0, 0)
        print(f"✅ Modèle importé : {model.name}")
    else:
        print(f"⚠️  GLB non trouvé : {GLB_PATH}")
        print("   Place manuellement ton modèle sur la carte.")

    # Ajuste la vue
    bpy.ops.object.select_all(action='SELECT')
    bpy.ops.view3d.view_selected()

    print(f"✅ Scène prête — plan satellite {plane_m:.0f}m × {plane_m:.0f}m")
    print(f"   Centre GPS : {CENTER_LAT}°N, {CENTER_LNG}°")


# ════════════════════════════════════════════════════
#  3. PANNEAU GPS TEMPS RÉEL
# ════════════════════════════════════════════════════
from bpy.types import Panel, Operator

class GPS_PT_Panel(Panel):
    bl_label      = "📍 Position GPS"
    bl_idname     = "GPS_PT_panel"
    bl_space_type = 'VIEW_3D'
    bl_region_type= 'UI'
    bl_category   = "Tombeau GPS"

    def draw(self, context):
        layout = self.layout
        obj = context.active_object

        if not obj or obj.name in ("Satellite_Gao", "GPS_Centre_Tombeau"):
            layout.label(text="Sélectionne le modèle 3D", icon='INFO')
            return

        lat_r       = math.radians(CENTER_LAT)
        m_per_lat   = 111000
        m_per_lng   = 111000 * math.cos(lat_r)

        # Dans Blender : X = Est, Y = Nord
        model_lat = CENTER_LAT + obj.location.y / m_per_lat
        model_lng = CENTER_LNG + obj.location.x / m_per_lng
        model_z   = obj.location.z

        box = layout.box()
        box.label(text="Coordonnées GPS du modèle", icon='WORLD')
        col = box.column(align=True)
        col.label(text=f"LAT  :  {model_lat:.6f} °N")
        col.label(text=f"LNG  :  {model_lng:.6f} °")
        col.label(text=f"Z    :  {model_z:.2f} m (décalage vertical)")

        layout.separator()
        box2 = layout.box()
        box2.label(text="Référence centre carte :", icon='PINNED')
        box2.label(text=f"{CENTER_LAT}°N  {CENTER_LNG}°")

        layout.separator()
        layout.operator("gps.copy_coords", text="📋  Copier le code", icon='COPYDOWN')
        layout.operator("gps.reset_model", text="↩  Recentrer le modèle", icon='LOOP_BACK')


class GPS_OT_Copy(Operator):
    bl_idname = "gps.copy_coords"
    bl_label  = "Copier coordonnées GPS"

    def execute(self, context):
        obj = context.active_object
        if not obj:
            self.report({'WARNING'}, "Aucun objet sélectionné")
            return {'CANCELLED'}

        lat_r     = math.radians(CENTER_LAT)
        model_lat = CENTER_LAT + obj.location.y / 111000
        model_lng = CENTER_LNG + obj.location.x / (111000 * math.cos(lat_r))
        model_z   = obj.location.z

        code = (
            f"// GPS — copié depuis Blender\n"
            f"const GPS_LNG = {model_lng:.6f};\n"
            f"const GPS_LAT =  {model_lat:.6f};\n"
            f"const GPS_ALT =  256;\n"
            f"// Décalage Z modèle : {model_z:.2f}"
        )
        context.window_manager.clipboard = code
        self.report({'INFO'}, f"✅ Copié !  LAT={model_lat:.6f}  LNG={model_lng:.6f}")
        return {'FINISHED'}


class GPS_OT_Reset(Operator):
    bl_idname = "gps.reset_model"
    bl_label  = "Recentrer le modèle"

    def execute(self, context):
        obj = context.active_object
        if obj:
            obj.location = (0, 0, 0)
        return {'FINISHED'}


# ════════════════════════════════════════════════════
#  ENREGISTREMENT & LANCEMENT
# ════════════════════════════════════════════════════
classes = [GPS_PT_Panel, GPS_OT_Copy, GPS_OT_Reset]

def register():
    for cls in classes:
        try:
            bpy.utils.unregister_class(cls)
        except Exception:
            pass
        bpy.utils.register_class(cls)

register()

# Lance le téléchargement et construit la scène
print("⏳ Téléchargement de l'image satellite...")
try:
    img_path, n_tiles = download_tiles()
    print(f"✅ Image satellite téléchargée : {img_path}")
    setup_scene(img_path, n_tiles)
    print("\n════════════════════════════════════════")
    print("  Scène prête ! Déplace le modèle")
    print("  sur la carte et lis les GPS dans")
    print("  le panneau 'Tombeau GPS' (touche N)")
    print("════════════════════════════════════════\n")
except Exception as e:
    print(f"❌ Erreur : {e}")
    print("Vérifie ta connexion Internet et relance le script.")
