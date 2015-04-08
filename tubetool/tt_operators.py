# ***** BEGIN GPL LICENSE BLOCK *****
#
# This program is free software; you may redistribute it, and/or
# modify it, under the terms of the GNU General Public License
# as published by the Free Software Foundation - either version 2
# of the License, or (at your option) any later version.
#
# This program is distributed in the hope that it will be useful,
# but WITHOUT ANY WARRANTY; without even the implied warranty of
# MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE. See the
# GNU General Public License for more details.
#
# You should have received a copy of the GNU General Public License
# along with this program. If not, write to:
#
#   the Free Software Foundation Inc.
#   51 Franklin Street, Fifth Floor
#   Boston, MA 02110-1301, USA
#
# or go online at: http://www.gnu.org/licenses/ to view license options.
#
# ***** END GPL LICENCE BLOCK *****

import bpy
import bmesh
from mathutils import Vector
from bpy.props import IntProperty, FloatProperty


def median(face):
    med = Vector()
    for vert in face.verts:
        vec = vert.co
        med = med + vec
    return med / len(face.verts)


def perform_simple_tube(oper, context):

    # subdiv, handle_ext_1, handle_ext_2:

    obj = bpy.context.edit_object
    me = obj.data
    bm = bmesh.from_edit_mesh(me)

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

    # This will automatically scale the bezierpoint radii as a
    # function of the size of the polygons
    bevel_depth = (medians[0] - faces[0].verts[0].co).length
    scale2 = (medians[1] - faces[1].verts[0].co).length
    op2_scale = scale2 / bevel_depth

    def add_curve(medians, normals, curvename):
        curvedata = bpy.data.curves.new(name=curvename, type='CURVE')
        curvedata.dimensions = '3D'

        obj = bpy.data.objects.new('Obj' + curvename, curvedata)
        obj.location = (0, 0, 0)  # object origin
        bpy.context.scene.objects.link(obj)

        polyline = curvedata.splines.new('BEZIER')
        polyline.bezier_points.add(1)
        polyline.use_smooth = False

        obj.data.fill_mode = 'FULL'
        obj.data.bevel_depth = bevel_depth
        obj.data.bevel_resolution = oper.subdiv

        # Point 0
        point = polyline.bezier_points[0]
        co = medians[0]
        point.co = co
        point.handle_left = co - (normals[0] * 2 * oper.handle_ext_1)
        point.handle_right = co + (normals[0] * 2)

        # Point 1
        point = polyline.bezier_points[1]
        point.radius *= op2_scale
        co = medians[1]
        point.co = co
        point.handle_right = co - (normals[1] * 2 * oper.handle_ext_2)
        point.handle_left = co + (normals[1] * 2)

        polyline.order_u = len(polyline.points) - 1

    add_curve(medians, normals, "curvename")
    # bm.free()


class AddSimpleTube(bpy.types.Operator):

    bl_idname = "mesh.add_curvebased_tube"
    bl_label = "Add Simple Tube"
    bl_options = {'REGISTER', 'UNDO'}

    subdiv = IntProperty(
        name="num profile verts",
        description="how many verts in profile shape",
        default=4, min=1, max=16)

    handle_ext_1 = FloatProperty(min=0.001, default=1.0, max=4.0)
    handle_ext_2 = FloatProperty(min=0.001, default=1.0, max=4.0)

    def execute(self, context):
        perform_simple_tube(self, context)
        return {'FINISHED'}


def register():
    bpy.utils.register_class(AddSimpleTube)


def unregister():
    bpy.utils.unregister_class(AddSimpleTube)
