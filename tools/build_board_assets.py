"""Run in Blender (including via MCP) to rebuild MegaMek's low-poly board assets.

New datablocks live in their own scene; existing scenes are never edited. Runtime
models use Z up, one hex = 84 x 72 units, and one feature height = 1 unit.
"""
import bpy
import json
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


BRIDGE = material('Saxarba bridge', (1, 1, 1))
BRIDGE.use_nodes = True
bridge_texture = BRIDGE.node_tree.nodes.new('ShaderNodeTexImage')
bridge_texture.image = bpy.data.images.load(str(OUT / 'tileset/saxarba/bridges/bridge_09.png'), check_existing=True)
BRIDGE.node_tree.links.new(bridge_texture.outputs['Color'],
                          BRIDGE.node_tree.nodes.get('Principled BSDF').inputs['Base Color'])


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


def tree_texture(name, mat):
    """Use the source's material boundaries, especially its authored snow caps."""
    role = mat.name.split('.')[0]
    if role == 'Snow':
        return 'snow'
    if role in ('Wood', 'White', 'Black', 'Coconuts'):
        return 'bark-birch' if name.startswith('birch') else 'bark-palm' if name.startswith('palm') else 'bark'
    if role in ('Green', 'DarkGreen'):
        return ('needles-pine' if name.startswith('pine') else
                'leaves-willow' if name.startswith('willow') else
                'fronds-palm' if name.startswith('palm') else 'leaves-broad')
    raise ValueError(f'Unknown tree material: {name}: {mat.name}')


def export(name, objects, normalize=False, width=None, foliage=False):
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
            role = tree_texture(name, mat) if foliage else 'bridge' if mat == BRIDGE else 'surface'
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
            for index, loop in zip(tri.vertices, tri.loops):
                pos = obj.matrix_world @ mesh.vertices[index].co
                if normalize:
                    span = high.z-low.z
                    horizontal = width/max(high.x-low.x, high.y-low.y) if width else 30/span
                    pos = Vector(((pos.x-(low.x+high.x)/2)*horizontal,
                                  (pos.y-(low.y+high.y)/2)*horizontal, (pos.z-low.z)/span))
                    # Normals for the exported anisotropic normalization.
                    n = Vector((normal.x/horizontal, normal.y/horizontal, normal.z*span)).normalized()
                else:
                    n = normal
                uv = (pos.x/24, pos.y/24) if abs(n.z) > .5 else (
                    (pos.x if abs(n.y) > abs(n.x) else pos.y)/24, pos.z)
                if role == 'bridge':
                    uv = mesh.uv_layers.active.data[loop].uv
                elif foliage:
                    # Project in the tree's original proportions, before the runtime
                    # expands its normalized Z. Dominant-axis mapping avoids stretched
                    # leaves on steep faces; bark and willow retain vertical grain.
                    point = Vector((pos.x, pos.y, pos.z * 30))
                    if abs(normal.z) >= max(abs(normal.x), abs(normal.y)):
                        uv = (point.x, point.y)
                    else:
                        uv = (point.x if abs(normal.y) > abs(normal.x) else point.y, point.z)
                    repeat = 4 if role.startswith('bark') else 8 if name.startswith('birch') else 12
                    uv = (uv[0] / repeat, uv[1] / repeat)
                vertex = tuple(round(v, 6) for v in (*pos, *n, *color, 1, *uv))
                if vertex not in shared:
                    shared[vertex] = len(vertices)//12
                    vertices.extend(vertex)
                indices.append(shared[vertex])
    materials = []
    for role in parts:
        entry = {'id':role,'diffuse':[1,1,1]}
        if role == 'bridge':
            entry['textures'] = [{'id':'bridge','filename':'tileset/saxarba/bridges/bridge_09.png','type':'DIFFUSE'}]
        elif foliage:
            entry['textures'] = [{'id':role,'filename':f'textures/foliage/{role}.png','type':'DIFFUSE'}]
        materials.append(entry)
    model = {'version': [0, 1], 'id': name,
             'meshes': [{'attributes': ['POSITION','NORMAL','COLOR','TEXCOORD0'], 'vertices': vertices,
                         'parts': [{'id':role,'type':'TRIANGLES','indices':indices} for role,indices in parts.items()]}],
             'materials':materials,
             'nodes':[{'id':name,'parts':[{'meshpartid':role,'materialid':role} for role in parts]}]}
    (OUT / (name+'.g3dj')).write_text(json.dumps(model,separators=(',',':')))
    STATS[name] = {'triangles': sum(len(indices) for indices in parts.values())//3, 'vertices': len(vertices)//12}


# A bridge arm runs from the centre towards north; instances rotate for each exit.
# The deck is at z=0, with underside/girders below and rails just above it.
def bridge_beam(name, left, right, bottom, top):
    polygon = [(left,0),(right,0),(right,36),(left,36)]
    vertices = [(x,y,z) for z in (bottom,top) for x,y in polygon]
    faces = [(4,5,6,7),(3,2,1,0)] + [(i,(i+1)%4,(i+1)%4+4,i+4) for i in range(4)]
    beam = mesh_object(name, vertices, faces, [BRIDGE], [0]*6)
    mesh = beam.data
    mesh.materials.clear()
    mesh.materials.append(BRIDGE)
    uv = mesh.uv_layers.new(name='Saxarba bridge')
    for face in mesh.polygons:
        face.material_index = 0
        for loop in face.loop_indices:
            p = mesh.vertices[mesh.loops[loop].vertex_index].co
            if abs(face.normal.x) > .5:
                # Unwrap the source rail strip over the vertical rail/fascia faces.
                # This retains its longitudinal bars and supports, without stretching asphalt up the side.
                height = (p.z-bottom)/(top-bottom)
                pixel_x = 31.5+2*height if p.x < 0 else 52.5-2*height
            else:
                # Original plan-view UVs, limited to opaque texel centres to avoid alpha fringes.
                pixel_x = min(52.5, max(31.5, 42+p.x))
            uv.data[loop].uv = (pixel_x/84, .5-p.y/72)
    return beam


export('bridge', [bridge_beam('Deck', -11, 11, -.14, 0),
                  bridge_beam('Left rail', -11, -7.5, 0, .13),
                  bridge_beam('Right rail', 7.5, 11, 0, .13)])

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
nature = ROOT / 'TO_SORT/many_trees/Ultimate Nature Pack - Jun 2019'
old_scene = bpy.context.window.scene if bpy.context.window else None
if bpy.context.window:
    bpy.context.window.scene = SCENE
sources = [('tree','CommonTree_1'),('pine','PineTree_1'),
           ('tree-snow','CommonTree_Snow_1'),('pine-snow','PineTree_Snow_1'),
           ('palm','PalmTree_1'),('palm-bent','PalmTree_2')]
for name, source in [('tree-broad','CommonTree_4'),('tree-slender','CommonTree_2'),
                     ('birch','BirchTree_2'),('willow','Willow_2'),('pine-tall','PineTree_3')]:
    family, number = source.rsplit('_', 1)
    sources += [(name,source),(name+'-snow',family+'_Snow_'+number)]
for number in (1,3,6):
    sources += [('rock-'+str(number),'Rock_'+str(number)),
                ('rock-'+str(number)+'-snow','Rock_Snow_'+str(number))]
for name, source in sources:
    path = nature / 'Blends' / (source+'.blend')
    if not path.exists():
        raise FileNotFoundError(path)
    with bpy.data.libraries.load(str(path), link=False) as (available, loaded):
        loaded.objects = available.objects
    objects = [obj for obj in loaded.objects if obj and obj.type == 'MESH']
    for obj in objects:
        COLLECTION.objects.link(obj)
    bpy.context.view_layer.update()
    triangles = sum(len(p.vertices)-2 for obj in objects for p in obj.data.polygons)
    budget = 150 if name.startswith('rock-') else 480
    for obj in objects:
        bpy.context.view_layer.objects.active = obj
        obj.select_set(True)
        if triangles > budget:
            mod = obj.modifiers.new('Game asset budget', 'DECIMATE')
            mod.ratio = budget/triangles
            bpy.ops.object.modifier_apply(modifier=mod.name)
        obj.select_set(False)
    bpy.context.view_layer.update()
    export(name,objects,normalize=True,width=12 if name.startswith('rock-') else None,
           foliage=not name.startswith('rock-'))
    STATS[name]['source'] = str(path.relative_to(nature)).replace('\\', '/')
if old_scene:
    bpy.context.window.scene = old_scene

# Terrain, riverbed and rim textures are authored assets. Model rebuilds preserve them.

(OUT/'manifest.json').write_text(json.dumps(STATS,indent=2))
# Save only the authored library, never replace the user's open file.
bpy.data.libraries.write(str(ROOT/'tools/board-assets.blend'), set(SCENE.objects), fake_user=True)
result = {'directory':str(OUT),'models':len(STATS), 'max_triangles':max(v['triangles'] for v in STATS.values())}
print(json.dumps(result),flush=True)
