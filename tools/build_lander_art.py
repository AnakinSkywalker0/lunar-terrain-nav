"""Build an original, illustrative robotic lunar lander in Blender 4.5.

Run: blender --background --python tools/build_lander_art.py
Geometry is a visual concept, not a flight-qualified hardware design.
Blender Z is up; FBX export converts to Unity Y up. One unit is one metre.
"""
import bpy
import math
import json
from pathlib import Path
from mathutils import Vector

ROOT = Path(__file__).resolve().parents[1]
ART = ROOT / 'art/lander'
UNITY = ROOT / 'LANTERN/Assets/Art/Lander'
OUT = ROOT / 'deliverables/lander'
for p in (ART, UNITY, OUT):
    p.mkdir(parents=True, exist_ok=True)
bpy.ops.object.select_all(action='SELECT')
bpy.ops.object.delete(use_global=False)
bpy.context.scene.unit_settings.system = 'METRIC'
bpy.context.scene.unit_settings.scale_length = 1
parts = []

def material(name, color, metal=0, rough=.4):
    m = bpy.data.materials.new(name)
    m.diffuse_color = (*color, 1)
    m.use_nodes = True
    p = m.node_tree.nodes.get('Principled BSDF')
    p.inputs['Base Color'].default_value = (*color, 1)
    p.inputs['Metallic'].default_value = metal
    p.inputs['Roughness'].default_value = rough
    return m

gold = material('MLI_Gold', (.55, .29, .055), .75, .36)
silver = material('Titanium', (.55, .61, .65), .8, .28)
white = material('Ceramic_White', (.81, .84, .84), .15, .38)
dark = material('Graphite', (.035, .045, .06), .55, .38)
black = material('Nozzle_Interior', (.009, .013, .02), .15, .8)
blue = material('Solar_Cells', (.018, .055, .16), .65, .25)
glass = material('Optics_Blue', (.02, .22, .31), .65, .12)
orange = material('Warning_Amber', (.95, .32, .035), .2, .4)
# Procedural foil texture for the Blender preview. Mesh panels also have creases;
# Unity's materials use the portable base colours, not this procedural shader.
nt = gold.node_tree
noise = nt.nodes.new('ShaderNodeTexNoise')
noise.inputs['Scale'].default_value = 42
noise.inputs['Detail'].default_value = 3
bump = nt.nodes.new('ShaderNodeBump')
bump.inputs['Strength'].default_value = .22
bump.inputs['Distance'].default_value = .025
nt.links.new(noise.outputs['Fac'], bump.inputs['Height'])
nt.links.new(bump.outputs['Normal'], nt.nodes.get('Principled BSDF').inputs['Normal'])

def finish(obj, name, mat, bevel=0, smooth=False):
    obj.name = name
    obj.data.materials.append(mat)
    if bevel:
        mod = obj.modifiers.new('Machined edges', 'BEVEL')
        mod.width = bevel
        mod.segments = 2
    if smooth:
        for f in obj.data.polygons:
            f.use_smooth = True
    parts.append(obj)
    return obj

def box(name, pos, size, mat, bevel=.015):
    bpy.ops.mesh.primitive_cube_add(size=1, location=pos)
    o = bpy.context.object
    o.scale = size
    bpy.ops.object.transform_apply(location=False, rotation=False, scale=True)
    return finish(o, name, mat, bevel)

def cylinder(name, pos, radius, depth, mat, vertices=32):
    bpy.ops.mesh.primitive_cylinder_add(vertices=vertices, radius=radius, depth=depth, location=pos)
    return finish(bpy.context.object, name, mat, .012, vertices > 12)

def rod(name, a, b, radius, mat):
    a, b = Vector(a), Vector(b)
    o = cylinder(name, (a+b)/2, radius, (b-a).length, mat, 16)
    o.rotation_euler = (b-a).to_track_quat('Z', 'Y').to_euler()
    return o

def sphere(name, pos, size, mat):
    bpy.ops.mesh.primitive_uv_sphere_add(segments=32, ring_count=16, location=pos)
    o = bpy.context.object
    o.scale = size
    return finish(o, name, mat, smooth=True)

def lathe(name, profile, mat, count=64):
    vs = [(r*math.cos(2*math.pi*i/count), r*math.sin(2*math.pi*i/count), z)
          for r,z in profile for i in range(count)]
    fs = []
    for j in range(len(profile)-1):
        for i in range(count):
            ni=(i+1)%count
            fs.append((j*count+i, j*count+ni, (j+1)*count+ni, (j+1)*count+i))
    mesh=bpy.data.meshes.new(name)
    mesh.from_pydata(vs, [], fs)
    mesh.update()
    o=bpy.data.objects.new(name,mesh)
    bpy.context.collection.objects.link(o)
    return finish(o,name,mat,smooth=True)

# Octagonal bus with independent thermal blankets and exposed edge rails.
cylinder('Octagonal structural bus', (0,0,2.08), 1.38, 1.30, dark, 8)
for z in (1.42,2.74):
    cylinder('Deck perimeter', (0,0,z), 1.43, .10, silver, 8)
for i in range(8):
    a=(i+.5)*math.pi/4
    radial=Vector((math.cos(a),math.sin(a),0))
    tangent=Vector((-math.sin(a),math.cos(a),0))
    # Four triangles around a slightly raised centre give shallow foil folds.
    center=radial*1.285+Vector((0,0,2.08))
    vs=[center+tangent*x+Vector((0,0,z)) for x,z in [(-.49,-.56),(.49,-.56),(.49,.56),(-.49,.56)]]
    vs.append(center+radial*.045+Vector((0,0,.12)))
    mesh=bpy.data.meshes.new('Blanket mesh')
    mesh.from_pydata(vs,[],[(0,1,4),(1,2,4),(2,3,4),(3,0,4)])
    mesh.update()
    o=bpy.data.objects.new('Gold thermal blanket %02d'%i,mesh)
    bpy.context.collection.objects.link(o)
    finish(o,o.name,gold)
    for z in (1.54,2.62):
        for t in (-.43,.43):
            sphere('Blanket fastener',center+tangent*t+Vector((0,0,z-2.08))+radial*.015,(.035,.035,.035),silver)

# Four splayed legs; pads sit on z=0. Attachment struts triangulate each leg.
for i in range(4):
    a=i*math.pi/2+math.pi/4
    r=Vector((math.cos(a),math.sin(a),0))
    t=Vector((-math.sin(a),math.cos(a),0))
    foot=r*2.55+Vector((0,0,.16))
    knee=r*2.28+Vector((0,0,.74))
    top=r*1.04+Vector((0,0,2.58))
    rod('Primary leg %d'%i,top,knee,.085,silver)
    rod('Shock absorber %d'%i,top.lerp(knee,.25),top.lerp(knee,.62),.13,gold)
    rod('Lower piston %d'%i,knee,foot,.065,silver)
    for sign in (-1,1):
        rod('Triangulated brace',r*.95+t*(sign*.66)+Vector((0,0,1.48)),knee,.043,silver)
    cylinder('Footpad %d'%i,(foot.x,foot.y,.07),.44,.14,dark)
    cylinder('Footpad upper dish',(foot.x,foot.y,.15),.35,.05,gold)
    sphere('Landing joint',foot,(.13,.13,.13),silver)
    for k in (-1,0,1):
        rib=box('Footpad reinforcement',(foot.x,foot.y+k*.16,.19),(.54,.028,.025),silver,.003)

# Bell with actual open mouth and a separate dark internal surface.
profile=[(.57,.54),(.49,.73),(.32,1.02),(.20,1.24),(.23,1.46)]
lathe('Main engine bell',profile,silver)
lathe('Engine inner liner',[(r-.012,z+.008) for r,z in reversed(profile)],black)
lathe('Nozzle lip',[(.57,.54),(.585,.55),(.58,.57),(.55,.57)],dark)
cylinder('Engine throat',(0,0,1.47),.24,.18,dark)
for a in (0,math.pi/2,math.pi,3*math.pi/2):
    rod('Engine mount',(.3*math.cos(a),.3*math.sin(a),1.2),(.8*math.cos(a),.8*math.sin(a),1.5),.035,silver)

# Exposed tanks on top, feed lines, electronics, radiators, and small RCS pods.
for x in (-.65,.65):
    sphere('Propellant tank',(x,.3,3.0),(.41,.41,.50),silver)
    cylinder('Tank neck',(x,.3,3.51),.10,.13,gold)
    rod('Propellant feed',(x,.3,3.56),(x,-.28,3.56),.025,silver)
    rod('Propellant downpipe',(x,-.28,3.56),(x,-.28,2.75),.025,silver)
box('Avionics enclosure',(0,-.52,2.94),(.74,.61,.35),white)
for i in range(10):
    box('Radiator fin',(-.32+i*.071,-.52,3.135),(.026,.53,.05),silver,.002)
for x,y in ((1.1,0),(-1.1,0),(0,1.1),(0,-1.1)):
    box('RCS pod',(x,y,2.65),(.25,.25,.30),dark)
    for d in (-.075,.075):
        cylinder('RCS nozzle',(x+d,y,2.46),.055,.12,silver,16)

# Front-facing navigation instruments; actual simulation remains in Lumen scripts.
box('Navigation instrument mount',(0,-1.33,2.12),(.82,.20,.43),white)
for x in (-.26,.26):
    rod('Stereo camera shroud',(x,-1.43,2.17),(x,-1.57,2.17),.105,dark)
    rod('Stereo lens',(x,-1.572,2.17),(x,-1.583,2.17),.075,glass)
box('Nadir lidar head',(0,-.94,1.35),(.30,.33,.20),white)
cylinder('Lidar aperture',(0,-.94,1.23),.11,.035,glass)

# Raised communications dish, tilted away from the top deck.
rod('Antenna mast',(.0,.65,2.8),(.0,.65,3.8),.045,silver)
dish=lathe('High gain reflector',[(0,0),(.16,.025),(.35,.10),(.57,.26)],white)
shell=dish.modifiers.new('Reflector shell thickness','SOLIDIFY')
shell.thickness=.012
dish.location=(0,.65,3.70)
dish.rotation_euler=(math.radians(26),0,math.radians(-15))
axis=dish.rotation_euler.to_matrix()
for a in (0,2*math.pi/3,4*math.pi/3):
    p=axis@Vector((.55*math.cos(a),.55*math.sin(a),.25))+dish.location
    end=axis@Vector((0,0,.61))+dish.location
    rod('Reflector feed support',p,end,.013,silver)
sphere('Antenna feed',end,(.065,.065,.08),dark)
rod('Omni antenna',(-.9,.6,2.8),(-.9,.6,4.22),.016,silver)

# Two solar wings with individually visible cell grid and hinge structure.
for sign in (-1,1):
    rod('Solar boom',(sign*.9,.12,2.83),(sign*2.1,.12,2.83),.05,silver)
    panel=box('Solar panel frame',(sign*2.05,.12,2.89),(1.22,1.52,.07),silver)
    for row in range(8):
        for col in range(6):
            x=sign*2.05-.51+col*.204
            y=.12-.65+row*.185
            box('Photovoltaic cell',(x,y,2.94),(.19,.171,.018),blue,.002)

# Front mission name plate. Text converted to mesh for FBX portability.
box('Mission plate',(0,-1.43,1.70),(.80,.026,.23),dark)
bpy.ops.object.text_add(location=(-.34,-1.453,1.64),rotation=(math.pi/2,0,0))
label=bpy.context.object
label.data.body='LANTERN'
label.data.size=.155
label.data.extrude=.001
bpy.ops.object.convert(target='MESH')
finish(bpy.context.object,'LANTERN mission lettering',white)

# Export visual meshes only. Render stage is deliberately excluded.
bpy.ops.object.select_all(action='DESELECT')
for o in parts:
    o.select_set(True)
bpy.context.view_layer.objects.active=parts[0]
bpy.ops.export_scene.fbx(filepath=str(UNITY/'LANTERN_Lander.fbx'),use_selection=True,
    object_types={'MESH'},apply_unit_scale=True,apply_scale_options='FBX_SCALE_UNITS',
    axis_forward='-Z',axis_up='Y',bake_space_transform=True,use_mesh_modifiers=True,
    add_leaf_bones=False,bake_anim=False,path_mode='AUTO')
materials={m.name:{'color':list(m.diffuse_color),'metallic':m.node_tree.nodes.get('Principled BSDF').inputs['Metallic'].default_value,
                  'roughness':m.node_tree.nodes.get('Principled BSDF').inputs['Roughness'].default_value}
           for m in (gold,silver,white,dark,black,blue,glass,orange)}
(UNITY/'materials.json').write_text(json.dumps(materials,indent=2))

floor=material('Studio floor',(.035,.048,.065),.05,.6)
bpy.ops.mesh.primitive_plane_add(size=200,location=(0,0,-.012))
bpy.context.object.name='Preview floor - not exported'
bpy.context.object.data.materials.append(floor)
scene=bpy.context.scene
scene.world.color=(.12,.12,.12)
def area(name,loc,power,size,color):
    bpy.ops.object.light_add(type='AREA',location=loc)
    o=bpy.context.object
    o.name=name
    o.data.energy=power
    o.data.shape='DISK'
    o.data.size=size
    o.data.color=color
    o.rotation_euler=(Vector((0,0,1.9))-o.location).to_track_quat('-Z','Y').to_euler()
area('Key softbox',(3,-6,9),2000,7,(1,.89,.76))
area('Blue fill',(-6,-2,5),1400,6,(.65,.80,1))
area('Rim light',(2,5,8),2400,5,(.8,.9,1))
bpy.ops.object.camera_add(location=(8,-11,7))
camera=bpy.context.object
camera.rotation_euler=(Vector((0,0,1.85))-camera.location).to_track_quat('-Z','Y').to_euler()
camera.data.type='ORTHO'
camera.data.ortho_scale=8.3
scene.camera=camera
scene.render.engine='CYCLES'
scene.cycles.samples=32
scene.cycles.use_denoising=True
scene.render.resolution_x=1440
scene.render.resolution_y=1100
scene.render.resolution_percentage=100
scene.view_settings.view_transform='AgX'
scene.render.image_settings.file_format='PNG'
scene.render.filepath=str(OUT/'LANTERN_Lander_Blender.png')
bpy.ops.wm.save_as_mainfile(filepath=str(ART/'LANTERN_Lander.blend'))
bpy.ops.render.render(write_still=True)
print('LANTERN_ART_COMPLETE',len(parts),'mesh parts')
