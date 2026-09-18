"""Run in Blender (including via MCP) to rebuild MegaMek's low-poly board assets.

New datablocks live in their own scene; existing scenes are never edited. Runtime
models use Z up, one hex = 84 x 72 units, and one feature height = 1 unit.
"""
import bpy
import json
import math
import random
from pathlib import Path
from mathutils import Vector

ROOT = Path(__file__).resolve().parents[1]
OUT = ROOT / 'data/models/board'
OUT.mkdir(parents=True, exist_ok=True)
SCENE = bpy.data.scenes.new('MegaMek board assets')
COLLECTION = SCENE.collection
STATS = {}


def material(name, color):
    mat = bpy.data.materials.new('MM ' + name)
    mat.diffuse_color = (*color, 1)
    if mat.use_nodes:
        node = next((n for n in mat.node_tree.nodes if n.type == 'BSDF_PRINCIPLED'), None)
        if node:
            node.inputs['Base Color'].default_value = (*color, 1)
    return mat


WALL = material('concrete', (.38, .42, .43))
ROOF = material('roof', (.22, .27, .29))
TRIM = material('coping', (.65, .65, .58))
METAL = material('steel', (.24, .33, .37))


def mesh_object(name, vertices, faces, materials, indices):
    mesh = bpy.data.meshes.new(name)
    mesh.from_pydata(vertices, [], faces)
    mesh.update()
    obj = bpy.data.objects.new(name, mesh)
    COLLECTION.objects.link(obj)
    for mat in materials:
        mesh.materials.append(mat)
    for polygon, index in zip(mesh.polygons, indices):
        polygon.material_index = index
    return obj


def prism(name, polygon, bottom=0, top=1, open_edges=()):
    n = len(polygon)
    vertices = [(x, y, bottom) for x, y in polygon] + [(x, y, top) for x, y in polygon]
    faces = [tuple(range(n, 2*n)), tuple(reversed(range(n)))]
    indices = [1, 0]
    for i in range(n):
        j = (i+1) % n
        # Closed walls also cover steps between connected sections of unequal height.
        faces.append((i, j, j+n, i+n))
        indices.append(0)
    # Coping is an actual flat ring. It adds two triangles per edge, not pixels.
    start = len(vertices)
    vertices += [(x*.955, y*.955, top+.008) for x, y in polygon]
    vertices += [(x, y, top+.008) for x, y in polygon]
    for i in range(n):
        if i not in open_edges:
            j = (i+1) % n
            faces.append((start+i, start+n+i, start+n+j, start+j))
            indices.append(2)
    return mesh_object(name, vertices, faces, [WALL, ROOF, TRIM], indices)


def export(name, objects, normalize=False):
    """Small explicit G3DJ exporter: Blender triangulates, runtime only loads."""
    vertices, shared, parts = [], {}, {}
    bounds = [obj.matrix_world @ Vector(corner) for obj in objects for corner in obj.bound_box]
    low = Vector(tuple(min(v[i] for v in bounds) for i in range(3)))
    high = Vector(tuple(max(v[i] for v in bounds) for i in range(3)))
    for obj in objects:
        mesh = obj.data
        mesh.calc_loop_triangles()
        normal_matrix = obj.matrix_world.to_3x3().inverted().transposed()
        for tri in mesh.loop_triangles:
            mat = mesh.materials[tri.material_index] if mesh.materials else None
            role = 'wall' if mat == WALL else 'roof' if mat == ROOF else 'surface'
            indices = parts.setdefault(role, [])
            color = mat.diffuse_color[:3] if mat else (.35, .45, .25)
            if mat and mat.use_nodes:
                node = next((n for n in mat.node_tree.nodes if n.type == 'BSDF_PRINCIPLED'), None)
                if node:
                    color = node.inputs['Base Color'].default_value[:3]
            # Blender stores linear-light colors. libGDX's default shader writes
            # directly to the display framebuffer, so export display-space colors.
            color = tuple(12.92*c if c <= .0031308 else 1.055*c**(1/2.4)-.055 for c in color)
            if normalize:
                color = tuple(min(1,max(.12,c*1.15)) for c in color)
            normal = (normal_matrix @ tri.normal).normalized()
            for index in tri.vertices:
                pos = obj.matrix_world @ mesh.vertices[index].co
                if normalize:
                    span = high.z-low.z
                    pos = Vector(((pos.x-(low.x+high.x)/2)/span*30,
                                  (pos.y-(low.y+high.y)/2)/span*30, (pos.z-low.z)/span))
                    # Normals for the exported anisotropic normalization.
                    n = Vector((normal.x/30, normal.y/30, normal.z)).normalized()
                else:
                    n = normal
                uv = (pos.x/24, pos.y/24) if abs(n.z) > .5 else (
                    (pos.x if abs(n.y) > abs(n.x) else pos.y)/24, pos.z)
                vertex = tuple(round(v, 6) for v in (*pos, *n, *color, 1, *uv))
                if vertex not in shared:
                    shared[vertex] = len(vertices)//12
                    vertices.extend(vertex)
                indices.append(shared[vertex])
    materials = []
    for role in parts:
        entry = {'id':role,'diffuse':[1,1,1]}
        if role in ('roof','wall'):
            entry['textures'] = [{'id':'concrete','filename':'textures/concrete.png','type':'DIFFUSE'}]
        materials.append(entry)
    model = {'version': [0, 1], 'id': name,
             'meshes': [{'attributes': ['POSITION','NORMAL','COLOR','TEXCOORD0'], 'vertices': vertices,
                         'parts': [{'id':role,'type':'TRIANGLES','indices':indices} for role,indices in parts.items()]}],
             'materials':materials,
             'nodes':[{'id':name,'parts':[{'meshpartid':role,'materialid':role} for role in parts]}]}
    (OUT / (name+'.g3dj')).write_text(json.dumps(model,separators=(',',':')))
    STATS[name] = {'triangles': sum(len(indices) for indices in parts.values())//3, 'vertices': len(vertices)//12}


shapes = [
    [(-26,-23),(26,-23),(26,23),(-26,23)],
    [(-29,-14),(-18,-27),(19,-27),(30,-14),(30,15),(18,27),(-18,27),(-29,14)],
    [(-28,-26),(27,-26),(27,-6),(7,-6),(7,26),(-28,26)],
    [(29*math.cos(a*math.tau/12),27*math.sin(a*math.tau/12)) for a in range(12)],
]
round_shape = [(24*math.cos(a*math.tau/12),24*math.sin(a*math.tau/12)) for a in range(12)]
export('tank', [prism('Tank', round_shape)])
export('industrial', [prism('Factory', shapes[2],0,.75),
                      prism('Tower', [(12,4),(21,4),(21,14),(12,14)], .3,1)])
# A bridge arm runs from the centre towards north; instances rotate for each exit.
# The deck is at z=0, with underside/girders below and rails just above it.
export('bridge', [prism('Deck',[(-12,0),(12,0),(12,36),(-12,36)],-.14,0),
                  prism('Left rail',[(-12,0),(-10,0),(-10,36),(-12,36)],0,.13),
                  prism('Right rail',[(10,0),(12,0),(12,36),(10,36)],0,.13)])

# Crops have one elevation level in the rules. Authored crossed blades preserve
# that height without lifting a farmland image into a solid block.
crop = material('dry crop', (.31,.29,.08))
vertices, faces = [], []
for row in range(5):
    for column in range(6):
        x,y = (column-2.5)*7,(row-2)*10
        height=.72+((column*7+row*3)%4)*.09
        for dx,dy in ((2,0),(0,2)):
            start=len(vertices)
            vertices += [(x-dx,y-dy,0),(x+dx,y+dy,0),(x,y,height)]
            faces += [(start,start+1,start+2),(start+2,start+1,start)]
export('field',[mesh_object('Crop rows',vertices,faces,[crop],[0]*len(faces))])

# Import the user's CC0 Quaternius source into the isolated asset scene. Keep the
# authored colors, simplify only when a source exceeds the foliage budget.
nature = ROOT / 'TO_SORT/many_trees/Ultimate Nature Pack - Jun 2019/OBJ'
old_scene = bpy.context.window.scene if bpy.context.window else None
if bpy.context.window:
    bpy.context.window.scene = SCENE
for name, source in [('tree','CommonTree_1'),('pine','PineTree_1'),
                     ('tree-snow','CommonTree_Snow_1'),('pine-snow','PineTree_Snow_1'),
                     ('palm','PalmTree_1')]:
    path = nature / (source+'.obj')
    if not path.exists():
        # Fail explicitly; never silently substitute a green tree for snow.
        candidates = sorted(nature.glob(('*Snow*' if 'snow' in name else '*Tree*')+'.obj'))
        raise FileNotFoundError(str(path)+'; candidates: '+str([p.name for p in candidates[:12]]))
    before = set(bpy.data.objects)
    bpy.ops.wm.obj_import(filepath=str(path), forward_axis='NEGATIVE_Z', up_axis='Y')
    objects = [o for o in bpy.data.objects if o not in before and o.type=='MESH']
    for obj in objects:
        if obj.name not in COLLECTION.objects:
            COLLECTION.objects.link(obj)
        bpy.context.view_layer.objects.active = obj
        obj.select_set(True)
        triangles = sum(len(p.vertices)-2 for p in obj.data.polygons)
        if triangles > 500:
            mod = obj.modifiers.new('Game foliage budget', 'DECIMATE')
            mod.ratio = 500/triangles
            bpy.ops.object.modifier_apply(modifier=mod.name)
        obj.select_set(False)
    bpy.context.view_layer.update()
    export(name,objects,normalize=True)
if old_scene:
    bpy.context.window.scene = old_scene

# Periodic procedural material maps. Noise coordinates wrap in both directions;
# UVs repeat in world units on cliff faces instead of stretching the hex artwork.
texture_dir = OUT / 'textures'
texture_dir.mkdir(exist_ok=True)
palette = {'dirt':(.36,.27,.18),'sand':(.63,.52,.34),'rock':(.38,.40,.39),
           'concrete':(.48,.49,.46),'snow':(.77,.84,.87),'grass':(.28,.38,.16),
           'bed':(.30,.29,.21)}
for kind, base in palette.items():
    # Retain art-directed albedos after the initial generation pass.
    if (texture_dir/(kind+'.png')).exists() and kind in ('dirt','sand','rock','concrete'):
        continue
    size = 128
    rng = random.Random(kind)
    phases = [rng.random()*math.tau for _ in range(6)]
    pixels = []
    for y in range(size):
        for x in range(size):
            u,v = x/size*math.tau,y/size*math.tau
            noise = sum(math.sin((i+2)*u+phases[i])*math.cos((i+1)*v+phases[5-i])/(i+2)
                        for i in range(6))*.09
            strata = math.sin(v*8+math.sin(u*2)*.7)*.035 if kind in ('dirt','sand','rock') else 0
            grain = (rng.random()-.5)*.055
            pixels.extend([max(0,min(1,c+noise+strata+grain)) for c in base]+[1])
    image = bpy.data.images.new('MM '+kind, width=size,height=size,alpha=True)
    image.pixels.foreach_set(pixels)
    image.filepath_raw = str(texture_dir/(kind+'.png'))
    image.file_format = 'PNG'
    image.save()
    # Surface cover descending over the exposed face, with a ragged alpha edge.
    if kind != 'bed':
        cover = []
        for y in range(size):
            for x in range(size):
                index=(y*size+x)*4
                edge=.34+.08*math.sin(x/size*math.tau*5)+.055*math.sin(x/size*math.tau*13)
                alpha=max(0,min(1,(y/size-edge)*18))
                cover.extend(pixels[index:index+3]+[alpha])
        rim = bpy.data.images.new('MM '+kind+' cover',width=size,height=size,alpha=True)
        rim.pixels.foreach_set(cover)
        rim.filepath_raw=str(texture_dir/(kind+'-rim.png'))
        rim.file_format='PNG'
        rim.save()

(OUT/'manifest.json').write_text(json.dumps(STATS,indent=2))
# Save only the authored library, never replace the user's open file.
bpy.data.libraries.write(str(ROOT/'tools/board-assets.blend'), set(SCENE.objects), fake_user=True)
result = {'directory':str(OUT),'models':len(STATS), 'max_triangles':max(v['triangles'] for v in STATS.values())}
print(json.dumps(result),flush=True)
