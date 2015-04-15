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


class TubeCallbackOps(bpy.types.Operator):

    bl_idname = "object.tube_callback"
    bl_label = "Tube Callback (private)"

    current_name = StringProperty(default='')
    fn = StringProperty(default='')
    default = FloatProperty()

    def dispatch(self, context, type_op):
        wm = context.window_manager
        operators = wm.operators

        # only do this part if also current_name is passed in
        if self.current_name:
            
            cls = None
            for k in operators:
                if k.bl_idname == 'MESH_OT_add_curvebased_tube':
                    if k.generated_name == self.current_name:
                        cls = k
            
            if not cls:
                ''' all callback functions require a valid class reference '''
                return

            if type_op == 'reset_radii':
                print('attempt reset:', cls.generated_name)
                cls.main_scale = 1.0
                cls.point1_scale = 1.0
                cls.point2_scale = 1.0

            else:
                # would prefer to be implicit.. but self.default is OK for now.
                # ideally, the value is derived from the default of the  property
                # of cls.type_op. but for now it is passed explicitely. 
                # Barf. Dryheave.
                setattr(cls, type_op, self.default)  
                cls.execute(context)


    def execute(self, context):
        self.dispatch(context, self.fn)
        return {'FINISHED'}



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

    if not oper.flip_u:
        faces = [f for f in bm.faces if f.select]
    else:
        faces = list(reversed([f for f in bm.faces if f.select]))

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

        pointA, pointB = [0, -1] if not oper.flip_v else [-1, 0]

        # Point 0
        ''' default scale or radius point1 == 1 '''
        point1 = polyline.bezier_points[pointA]
        co = medians[0]
        point1.radius = 1 * oper.main_scale * oper.point1_scale
        point1.co = co
        point1.handle_left = (co - (normals[0] * oper.handle_ext_1)) 
        point1.handle_right = (co + (normals[0] * oper.handle_ext_1)) 

        # Point 1
        point2 = polyline.bezier_points[pointB]
        point2.radius = (1 * op2_scale) * oper.main_scale * oper.point2_scale
        co = medians[1]
        point2.co = co
        point2.handle_right = (co - (normals[1] * oper.handle_ext_2)) 
        point2.handle_left = (co + (normals[1] * oper.handle_ext_2)) 

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

    handle_ext_1 = FloatProperty(min=-8.0, default=2.0, max=8.0)
    handle_ext_2 = FloatProperty(min=-8.0, default=2.0, max=8.0)

    show_smooth = BoolProperty(default=False)
    show_wire = BoolProperty(default=False)
    end_operator = BoolProperty(default=False)  # unused .

    main_scale = FloatProperty(min=0.0001, default=1.0, max=5.0)
    point1_scale = FloatProperty(min=0.0001, default=1.0, max=5.0)
    point2_scale = FloatProperty(min=0.0001, default=1.0, max=5.0)

    flip_v = BoolProperty()
    flip_u = BoolProperty()    

    def draw(self, context):
        layout = self.layout
        callback = "object.tube_callback"
        
        col = layout.column()
        col.prop(self, "subdiv", text="sub V")
        col.prop(self, "tube_resolution_u", text="sub U")
        col.prop(self, "main_scale", text="overall scale")

        col.separator()

        def prop_n_reset(split, pname, pstr, default):
            ''' I draw a slider and an operator to reset the slider '''
            pid = split.row(align=True)
            pid.prop(self, pname, text=pstr)
            a = pid.operator(callback, text="", icon="LINK")
            a.fn = pname
            a.current_name = self.generated_name
            a.default = default

        # ROW 1
        row = col.row(); split = row.split(percentage=0.5)
        prop_n_reset(split, "handle_ext_1", "handle 1", 2.0)  # left
        prop_n_reset(split, "point1_scale", "radius_1", 1.0)  # right

        # ROW 2
        row = col.row(); split = row.split()
        prop_n_reset(split, "handle_ext_2", "handle 2", 2.0)  # left
        prop_n_reset(split, "point2_scale", "radius_2", 1.0)  # right


        row = layout.row()
        split = row.split(percentage=0.5)
        col_left = split.column()

        col_left.label("display")
        col_left.prop(self, "show_smooth", text="show smooth", toggle=True)
        col_left.prop(self, "show_wire", text="show wire", toggle=True)

        col_right = split.column()
        col_right.label("flip directions")
        col_right.prop(self, "flip_u", text='flip u sides', toggle=True)
        col_right.prop(self, "flip_v", text='flip v sides', toggle=True)

        row = layout.row()
        k = row.operator(callback, text="Reset radii")
        k.fn = 'reset_radii'
        k.current_name = self.generated_name

    def __init__(self):
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


def register():
    bpy.utils.register_class(TubeCallbackOps)
    bpy.utils.register_class(AddSimpleTube)


def unregister():
    bpy.utils.unregister_class(AddSimpleTube)
    bpy.utils.unregister_class(TubeCallbackOps)
