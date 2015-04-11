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

from bpy.props import (
    IntProperty, FloatProperty, StringProperty, BoolProperty
)


def median(face):
    med = Vector()
    for vert in face.verts:
        vec = vert.co
        med = med + vec
    return med / len(face.verts)


def update_simple_tube(oper, context):

    generated_name = oper.generated_name

    obj_main = bpy.context.edit_object
    mw = obj_main.matrix_world
    me = obj_main.data
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
    bevel_depth = (medians[0] - (faces[0].verts[0].co)).length
    scale2 = (medians[1] - (faces[1].verts[0].co)).length
    op2_scale = scale2 / bevel_depth

    def modify_curve(medians, normals, curvename):
        print('this happens')
        obj = bpy.data.objects[generated_name]
        curvedata = obj.data
        polyline = curvedata.splines[0]

        polyline.use_smooth = oper.show_smooth
        obj.data.fill_mode = 'FULL'
        obj.data.bevel_depth = bevel_depth
        obj.data.bevel_resolution = oper.subdiv
        obj.show_wire = oper.show_wire

        # Point 0
        point1 = polyline.bezier_points[0]
        co = medians[0]
        point1.co = co
        point1.handle_left = co - (normals[0] * oper.handle_ext_1)
        point1.handle_right = co + (normals[0] * oper.handle_ext_1)

        # Point 1
        point2 = polyline.bezier_points[1]
        point2.radius = point1.radius * op2_scale
        co = medians[1]
        point2.co = co
        point2.handle_right = co - (normals[1] * oper.handle_ext_2)
        point2.handle_left = co + (normals[1] * oper.handle_ext_2)

        # polyline.order_u = len(polyline.points) - 1
        polyline.resolution_u = oper.tube_resolution_u

    print('generated name:', generated_name)
    modify_curve(medians, normals, generated_name)


class AddSimpleTube(bpy.types.Operator):

    bl_idname = "mesh.add_curvebased_tube"
    bl_label = "Add Simple Tube"
    bl_options = {'REGISTER', 'UNDO'}

    base_name = StringProperty(default='TT_tube')
    generated_name = StringProperty(default='')

    # Dummy variables for the time being
    subdiv = IntProperty(
        name="Profile Subdivision",
        description="subdivision level for the profile (circumference)",
        default=4, min=0, max=16)
    tube_resolution_u = IntProperty(min=0, default=12, max=30)

    handle_ext_1 = FloatProperty(min=-4.0, default=2.0, max=4.0)
    handle_ext_2 = FloatProperty(min=-4.0, default=2.0, max=4.0)

    show_smooth = BoolProperty(default=False)
    show_wire = BoolProperty(default=False)
    end_operator = BoolProperty(default=False)  # unused .

    def draw(self, context):
        layout = self.layout
        col = layout.column()
        col.prop(self, "subdiv", text="sub V")
        col.prop(self, "tube_resolution_u", text="sub U")

        col.prop(self, "handle_ext_1", text="handle 1")
        col.prop(self, "handle_ext_2", text="handle 2")

        row = layout.row()
        row.prop(self, "show_smooth", text="show smooth")
        row.prop(self, "show_wire", text="show wire")

    def __init__(self):
        print("Start")
        '''
            - create curve
            - assign default values
            - add to scene
            - record given name
        '''
        scn = bpy.context.scene
        obj_main = bpy.context.edit_object
        mw = obj_main.matrix_world

        curvedata = bpy.data.curves.new(name=self.base_name, type='CURVE')
        curvedata.dimensions = '3D'

        obj = bpy.data.objects.new('Obj_' + curvedata.name, curvedata)
        obj.location = (0, 0, 0)  # object origin
        bpy.context.scene.objects.link(obj)
        self.generated_name = obj.name

        obj.matrix_world = mw.copy()

        polyline = curvedata.splines.new('BEZIER')
        polyline.bezier_points.add(1)
        polyline.use_smooth = False
        obj.data.fill_mode = 'FULL'

        update_simple_tube(self, bpy.context)

    def __del__(self):
        print("End")

    def execute(self, context):
        update_simple_tube(self, context)
        return {'FINISHED'}

    def modal(self, context, event):
        if event.type == 'RET' and event.value == 'PRESS':
            return {'FINISHED'}

        return {'RUNNING_MODAL'}

    def invoke(self, context, event):

        self.execute(context)
        context.window_manager.modal_handler_add(self)
        return {'RUNNING_MODAL'}


def register():
    bpy.utils.register_class(AddSimpleTube)


def unregister():
    bpy.utils.unregister_class(AddSimpleTube)
