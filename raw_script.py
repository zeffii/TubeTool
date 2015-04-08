import bpy
import bmesh
from mathutils import Vector

obj = bpy.context.edit_object
me = obj.data
bm = bmesh.from_edit_mesh(me)

def median(face):
    med = Vector()
    for vert in face.verts:
        vec = vert.co
        med = med + vec
    return med / len(face.verts)

# get active face indices
medians = []
normals = []
faces = [f for f in bm.faces if f.select]
for f in faces:
    if len(medians) > 2:
        # dont select more than 2 faces.
        break
    normals.append(f.normal)
    medians.append(median(f))

bevel_depth = (medians[0]-faces[0].verts[0].co).length
scale2 = (medians[1]-faces[1].verts[0].co).length
op2_scale = scale2 / bevel_depth


def add_curve(medians, normals, curvename):
    curvedata = bpy.data.curves.new(name=curvename, type='CURVE')
    curvedata.dimensions = '3D'
 
    obj = bpy.data.objects.new('Obj'+curvename, curvedata)
    obj.location = (0,0,0) #object origin
    bpy.context.scene.objects.link(obj)
 
    polyline = curvedata.splines.new('BEZIER')
    polyline.bezier_points.add(1)
    polyline.use_smooth = False
    
    obj.data.fill_mode = 'FULL'
    obj.data.bevel_depth = bevel_depth
    obj.data.bevel_resolution = 4
 
    point = polyline.bezier_points[0]
    co = medians[0]
    point.co = co
    point.handle_left = co - (normals[0]*2)
    point.handle_right = co + (normals[0]*2)
    
    point = polyline.bezier_points[1]
    point.radius *= op2_scale
    co = medians[1]
    point.co = co
    point.handle_right = co - (normals[1]*2)
    point.handle_left = co + (normals[1]*2)
    
    polyline.order_u = len(polyline.points)-1  
    
add_curve(medians, normals, "curvename")    
bm.free()
