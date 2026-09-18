"""Run in Blender after prepare_building_footprints.py. Export exact roof UVs
over simplified footprint polygons, including disconnected parts and courtyards.
"""
from pathlib import Path
import bpy
import json
import math
import os
from mathutils import Vector
from mathutils.geometry import delaunay_2d_cdt

ROOT = Path(__file__).resolve().parents[1]
OUT = ROOT/'data/models/board'
entries = json.loads((ROOT/'tools/building-footprints.json').read_text())
scene = bpy.data.scenes.new('Saxarba building library')
stats = {}


def textured_material(name, image):
    material = bpy.data.materials.new(name)
    material.use_nodes = True
    shader = material.node_tree.nodes.get('Principled BSDF')
    texture = material.node_tree.nodes.new('ShaderNodeTexImage')
    texture.image = image
    material.node_tree.links.new(texture.outputs['Color'],shader.inputs['Base Color'])
    return material


facade_material = textured_material('Board facade',bpy.data.images.load(str(OUT/'textures/facade.png')))


def inside(point, loops):
    x,y=point
    result=False
    for loop in loops:
        for a,b in zip(loop,loop[1:]+loop[:1]):
            if (a[1]>y)!=(b[1]>y) and x < (b[0]-a[0])*(y-a[1])/(b[1]-a[1])+a[0]:
                result=not result
    return result


for entry_index, entry in enumerate(entries):
    if entry_index % 200 == 0:
        print(f'Building {entry_index}/{len(entries)}',flush=True)
    loops=entry['loops']
    vertices,edges=[],[]
    for loop in loops:
        start=len(vertices)
        vertices += [Vector(p) for p in loop]
        edges += [(start+i,start+(i+1)%len(loop)) for i in range(len(loop))]
    points,_,faces,*_ = delaunay_2d_cdt(vertices,edges,[],1,1e-5)
    width,height=entry['width'],entry['height']
    scale_x,scale_y=84/width,72/height
    packed,unique,roof_indices,wall_indices=[],{},[],[]
    mesh_vertices,mesh_faces,mesh_uvs,face_materials=[],[],[],[]
    roof_file=OUT/(entry['asset']+'-roof.png')
    source=bpy.data.images.load(str(roof_file),check_existing=True)
    pixels=list(source.pixels)
    # Use the roof's warm/cool palette to tint the facade without baking its
    # shadows into the walls. The facade itself supplies windows and lintels.
    colors=[pixels[i:i+3] for i in range(0,len(pixels),4)]
    avg=[sum(c[j] for c in colors)/len(colors) for j in range(3)]
    maximum=max(avg) or 1
    tint=tuple(.8+.2*c/maximum for c in avg)

    def vertex(point,z,normal,color,uv,indices):
        position=((point[0]-width/2)*scale_x,(height/2-point[1])*scale_y,z)
        value=tuple(round(v,6) for v in (*position,*normal,*color,1,*uv))
        if value not in unique:
            unique[value]=len(packed)//12
            packed.extend(value)
        indices.append(unique[value])
        return position

    for face in faces:
        poly=[points[i] for i in face]
        center=sum(poly,Vector((0,0)))/len(poly)
        if not inside(center,loops):
            continue
        # Pixel coordinates have downward Y; reverse to obtain a +Z roof.
        for i in range(1,len(poly)-1):
            triangle=[poly[0],poly[i+1],poly[i]]
            start=len(mesh_vertices)
            for p in triangle:
                mesh_vertices.append(vertex(p,1,(0,0,1),(1,1,1),(p.x/width,p.y/height),roof_indices))
                mesh_uvs.append((p.x/width,1-p.y/height))
            mesh_faces.append((start,start+1,start+2))
            face_materials.append(0)
    for loop in loops:
        distance=0
        for a,b in zip(loop,loop[1:]+loop[:1]):
            dx,dy=(b[0]-a[0])*scale_x,-(b[1]-a[1])*scale_y
            length=math.hypot(dx,dy)
            if length < 1e-5:
                continue
            # Loops are clockwise after the Y flip; this normal faces outside.
            normal=(-dy/length,dx/length,0)
            u0,u1=distance/128,(distance+length)/128
            wall=[(a,0,(u0,0)),(a,1,(u0,-.25)),(b,1,(u1,-.25)),(b,0,(u1,0))]
            start=len(mesh_vertices)
            mesh_vertices += [((p[0]-width/2)*scale_x,(height/2-p[1])*scale_y,z) for p,z,uv in wall]
            mesh_uvs += [(uv[0],-uv[1]) for p,z,uv in wall]
            mesh_faces.append((start,start+1,start+2,start+3))
            face_materials.append(1)
            for i in (0,1,2,0,2,3):
                p,z,uv=wall[i]
                vertex(p,z,normal,tint,uv,wall_indices)
            distance+=length
    asset=entry['asset']
    file=OUT/(asset+'.g3dj')
    facade=os.path.relpath(OUT/'textures/facade.png',file.parent).replace('\\','/')
    model={'version':[0,1],'id':asset,
           'meshes':[{'attributes':['POSITION','NORMAL','COLOR','TEXCOORD0'],'vertices':packed,
                      'parts':[{'id':'roof','type':'TRIANGLES','indices':roof_indices},
                               {'id':'wall','type':'TRIANGLES','indices':wall_indices}]}],
           'materials':[{'id':'roof','diffuse':[1,1,1], 'textures':[{'id':'roof','filename':roof_file.name,'type':'DIFFUSE'}]},
                        {'id':'wall','diffuse':[1,1,1], 'textures':[{'id':'facade','filename':facade,'type':'DIFFUSE'}]}],
           'nodes':[{'id':asset,'parts':[{'meshpartid':'roof','materialid':'roof'},{'meshpartid':'wall','materialid':'wall'}]}]}
    file.parent.mkdir(parents=True,exist_ok=True)
    file.write_text(json.dumps(model,separators=(',',':')))
    mesh=bpy.data.meshes.new(asset)
    mesh.from_pydata(mesh_vertices,[],mesh_faces)
    mesh.update()
    mesh.materials.append(textured_material(asset,source))
    mesh.materials.append(facade_material)
    uv_layer=mesh.uv_layers.new(name='UVMap')
    for polygon,material_index in zip(mesh.polygons,face_materials):
        polygon.material_index=material_index
        for loop_index in polygon.loop_indices:
            uv_layer.data[loop_index].uv=mesh_uvs[mesh.loops[loop_index].vertex_index]
    obj=bpy.data.objects.new(asset,mesh)
    scene.collection.objects.link(obj)
    stats[asset]={'source':entry['source'],'triangles':(len(roof_indices)+len(wall_indices))//3,
                  'vertices':len(packed)//12,'outline_vertices':sum(map(len,loops))}
(OUT/'building-manifest.json').write_text(json.dumps(stats,indent=2))
# Blender 5.2 can crash copying a newly-created scene's view layer. Export the
# objects and their dependencies directly, without copying a scene datablock.
bpy.data.libraries.write(str(ROOT/'tools/saxarba-buildings.blend'),set(scene.objects),path_remap='RELATIVE',fake_user=True)
result={'models':len(stats),'max_triangles':max(s['triangles'] for s in stats.values())}
print(json.dumps(result),flush=True)
