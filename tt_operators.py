# This file is part of project Sverchok. It's copyrighted by the contributors
# recorded in the version control history of the file, available from
# its original location https://github.com/nortikin/sverchok/commit/master
#  
# SPDX-License-Identifier: GPL3
# License-Filename: LICENSE


import bpy
import bmesh
from mathutils import Vector
from mathutils.geometry import normal

from bpy.props import (
    IntProperty, FloatProperty, StringProperty, BoolProperty
)



current_mode = {}

docstring = """select two verts or polygons only, then run this operator. selections can be on separate objects."""

class TubeCallbackOps(bpy.types.Operator):

    bl_idname = "object.tube_callback"
    bl_label = "Tube Callback (private)"
    bl_options = {"INTERNAL"}

    current_name: StringProperty(default='')
    fn: StringProperty(default='')
    default: FloatProperty()

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

            if type_op == "Reset radii":
                print('attempt reset:', cls.generated_name)
                cls.main_scale = 1.0
                cls.point1_scale = 1.0
                cls.point2_scale = 1.0

            elif type_op == "To Mesh":
                cls.make_real()

            # else:
            #     # would prefer to be implicit.. but self.default is OK for now.
            #     # ideally, the value is derived from the prop default
            #     # of cls.type_op. but for now it is passed explicitely.
            #     # Barf. Dryheave.
            #     setattr(cls, type_op, self.default)
            #     # cls.execute(context)

    def execute(self, context):
        self.dispatch(context, self.fn)
        return {'FINISHED'}


def median(face):
    return face.calc_center_median()

def avg_edge_length_of_connected_edges(v):
    if not v.link_edges:
        return 0
    lengths = [e.calc_length() for e in v.link_edges]
    return sum(lengths) / len(lengths)


def get_medians_and_normals(oper, context, mode):
    """
    because this is a post hoc implementation to cater for 2.8 ability to multi-select objects in 
    edit mode, this is a verbose routine. 

    """
    medians = []
    normals = []
    extra_data = None

    if mode == "ONE":
        obj_main = bpy.context.edit_object
        me = obj_main.data
        bm = bmesh.from_edit_mesh(me)

        # get active face indices
        faces = [f for f in bm.faces if f.select]
        if oper.flip_u:
            faces = list(reversed(faces))

        for f in faces:
            if len(medians) > 2:
                # dont select more than 2 faces.
                break
            normals.append(f.normal)
            medians.append(median(f))

        bevel_depth = (medians[0] - (faces[0].verts[0].co)).length
        scale2 = (medians[1] - (faces[1].verts[0].co)).length
        op2_scale = scale2 / bevel_depth
        extra_data = bevel_depth, scale2, op2_scale

    elif mode == "TWO":
        obj_one = bpy.context.selected_objects[0]
        obj_two = bpy.context.selected_objects[1]

        first_coords = []
        objs = [obj_two, obj_one] if oper.flip_u else [obj_one, obj_two]
        for obj in objs:
            m = obj.matrix_world
            bm = bmesh.from_edit_mesh(obj.data)

            # instead of transforming the entire bm using bmesh.ops.transform
            # we can multiply only the selected geometry. hopefully
            f = [f for f in bm.faces if f.select][0]
            first_coords.append(m @ f.verts[0].co)
            normals.append(normal([(m @ v.co) for v in f.verts]))
            medians.append(m @ median(f))

        bevel_depth = (medians[0] - first_coords[0]).length
        scale2 = (medians[1] - first_coords[1]).length
        op2_scale = scale2 / bevel_depth
        extra_data = bevel_depth, scale2, op2_scale

    elif mode == "THREE":
        # single object, two verts
        obj_main = bpy.context.edit_object
        me = obj_main.data
        bm = bmesh.from_edit_mesh(me)
        # verts = []
        avg_edge_length = []
        for v in bm.verts:
            if len(medians) > 2:
                break
            if v.select:
                # verts.append(v)
                avg_edge_length.append(avg_edge_length_of_connected_edges(v))
                normals.append(v.normal)
                medians.append(v.co)

        # use v.link_edges ,  (average length)/2 of all link_edges 
        bevel_depth = avg_edge_length[0] / 2
        scale2 = avg_edge_length[1] / 2
        op2_scale = scale2 / bevel_depth
        extra_data = bevel_depth, scale2, op2_scale

    elif mode == "FOUR":
        # two objects, single vert each
        obj_one = bpy.context.selected_objects[0]
        obj_two = bpy.context.selected_objects[1]
        verts = []
        avg_edge_length = []
        objs = [obj_two, obj_one] if oper.flip_u else [obj_one, obj_two]
        for obj in objs:

            if len(medians) > 2:
                break

            m = obj.matrix_world
            bm = bmesh.from_edit_mesh(obj.data)
            for v in bm.verts:
                if v.select:
                    verts.append(v)
                    avg_edge_length.append(avg_edge_length_of_connected_edges(v))
                    normals.append(v.normal)  # not sure why this has weird results with "m @ v.normal"
                    medians.append(m @ v.co)
                    break

        bevel_depth = avg_edge_length[0] / 2
        scale2 = avg_edge_length[1] / 2
        op2_scale = scale2 / bevel_depth
        extra_data = bevel_depth, scale2, op2_scale


    return medians, normals, extra_data


def update_simple_tube(oper, context):

    generated_name = oper.generated_name
    if not generated_name:
        print('being called without any geometry')
        return

    mode = current_mode.get(hash(oper))
    print('found mode:', mode)

    details = get_medians_and_normals(oper, context, mode)
    if not details:
        return
    else:
        medians, normals, extra_data = details
        bevel_depth, scale2, op2_scale = extra_data


    def modify_curve(medians, normals, curvename):

        obj = bpy.data.objects.get(generated_name)

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
        if oper.equal_radii:
            point1.radius = 1 * oper.main_scale
        else:
            point1.radius = 1 * oper.main_scale * oper.point1_scale

        point1.co = co
        point1.handle_left = (co - (normals[0] * oper.handle_ext_1))
        point1.handle_right = (co + (normals[0] * oper.handle_ext_1))

        # Point 1
        point2 = polyline.bezier_points[pointB]
        if oper.equal_radii:
            point2.radius = 1 * oper.main_scale
        else:
            point2.radius = 1 * op2_scale * oper.main_scale * oper.point2_scale

        co = medians[1]
        point2.co = co
        point2.handle_right = (co - (normals[1] * oper.handle_ext_2))
        point2.handle_left = (co + (normals[1] * oper.handle_ext_2))

        polyline.resolution_u = oper.tube_resolution_u

    # print('generated name:', generated_name)
    modify_curve(medians, normals, generated_name)

def updateOperator(self, context, origin):
    if getattr(self, origin):
        print("cm triggered")
        setattr(self, origin, False)
        prop_name = origin.replace("reset_", "")
        self.property_unset(prop_name)
        update_simple_tube(self, context)

class AddSimpleTube(bpy.types.Operator):

    bl_idname = "mesh.add_curvebased_tube"
    bl_label = "Add Simple Tube"
    bl_options = {'REGISTER', 'UNDO'}

    base_name: StringProperty(default='TT_tube')
    generated_name: StringProperty(default='')

    subdiv: IntProperty(
        name="Profile Subdivision",
        description="subdivision level for the profile (circumference)",
        default=4, min=0, max=16)

    tube_resolution_u: IntProperty(
        min=0, default=12, max=30,
        description="subdivision level for the length of the initial curve")

    handle_ext_1: FloatProperty(min=-8.0, default=2.0, max=8.0)
    handle_ext_2: FloatProperty(min=-8.0, default=2.0, max=8.0)

    show_smooth: BoolProperty(default=False)
    show_wire: BoolProperty(default=False)
    keep_operator_alive: BoolProperty(default=True)

    main_scale: FloatProperty(min=0.0001, default=1.0, max=5.0)
    point1_scale: FloatProperty(min=0.0001, default=1.0, max=5.0)
    point2_scale: FloatProperty(min=0.0001, default=1.0, max=5.0)

    flip_v: BoolProperty()
    flip_u: BoolProperty()

    equal_radii: BoolProperty(default=0)

    do_not_process: BoolProperty(default=False)
    initialized_curve: BoolProperty(default=False)

    reset_handle_ext_1: BoolProperty(default=False, update=lambda s, c: updateOperator(s, c, "reset_handle_ext_1"))
    reset_point1_scale: BoolProperty(default=False, update=lambda s, c: updateOperator(s, c, "reset_point1_scale"))
    reset_point2_scale: BoolProperty(default=False, update=lambda s, c: updateOperator(s, c, "reset_point2_scale"))
    reset_handle_ext_2: BoolProperty(default=False, update=lambda s, c: updateOperator(s, c, "reset_handle_ext_2"))

    def are_two_objects_in_editmode(self):
        objs = bpy.context.selected_objects
        if objs and len(objs) == 2:
            if all((obj.type == "MESH" and obj.mode == "EDIT") for obj in objs):
                return True

    def draw(self, context):
        layout = self.layout
        callback = "object.tube_callback"

        col = layout.column()
        col_row = col.row()
        col_row.prop(self, "subdiv", text="V")
        col_row.prop(self, "tube_resolution_u", text="U")

        col_row = col.row()
        col_row.prop(self, "equal_radii", text="equal radii")
        col_row.prop(self, "main_scale", text="overall scale")

        col.separator()

        def prop_n_reset(split, pname, display_name, enabled=True):
            ''' I draw a slider and an operator to reset the slider '''
            pid = split.row(align=True)
            pid.enabled = enabled
            pid.prop(self, pname, text=display_name)
            pid.prop(self, "reset_" + pname, text="", icon="LINKED")
            

        er = not self.equal_radii
        # ROW 1
        row = col.row(); split = row.split(factor=0.5)
        prop_n_reset(split, "handle_ext_1", "handle 1")       # left
        prop_n_reset(split, "point1_scale", "radius 1", er)  # right

        # ROW 2
        row = col.row(); split = row.split()
        prop_n_reset(split, "handle_ext_2", "handle 2")      # left
        prop_n_reset(split, "point2_scale", "radius 2", er)  # right

        # next row
        row = layout.row()
        split = row.split(factor=0.5)
        col_left = split.column()

        col_left.label(text="display")
        left_row = col_left.row()
        left_row.prop(self, "show_smooth", text="smooth", toggle=True)
        left_row.prop(self, "show_wire", text="wire", toggle=True)

        col_right = split.column()
        col_right.label(text="flip over")
        right_row = col_right.row()
        right_row.prop(self, "flip_u", text='Direction', toggle=True)
        right_row.prop(self, "flip_v", text='Normal', toggle=True)

        col = layout.column()

        k = col.operator(callback, text="Reset radii")
        k.fn = "Reset radii"
        k.current_name = self.generated_name

        k = col.operator(callback, text="To Mesh")
        k.fn = 'To Mesh'
        k.current_name = self.generated_name

    def initialize_new_tube(self, context):

        """
        - create curve
        - assign default values
        - add to scene
        - record given name
        """

        scn = bpy.context.scene
        obj_main = bpy.context.edit_object
        objects_main = bpy.context.selected_objects if self.are_two_objects_in_editmode() else None

        self_id = hash(self)
        current_mode[self_id] = None

        if obj_main and not objects_main:
            # if face mode and single object
            if (obj_main.data.total_face_sel == 2):
                mw = obj_main.matrix_world
                current_mode[self_id] = "ONE"
            elif (obj_main.data.total_vert_sel == 2):
                mw = obj_main.matrix_world
                current_mode[self_id] = "THREE"
            else:
                self.do_not_process = True
                self.report({'WARNING'}, 'if only one object is selected, then select two faces or verts only')
                return

        elif objects_main:

            if all((obj.data.total_face_sel == 1) for obj in objects_main):
                current_mode[self_id] = "TWO"
            elif all((obj.data.total_vert_sel == 1) for obj in objects_main):
                current_mode[self_id] = "FOUR"
            else:
                self.do_not_process = True
                self.report({'WARNING'}, 'if two objects are selected, then select one face on each object')
                return
        else:
            msg = 'if one object in edit mode, pick 2 faces/verts only. if two objects in edit mode, pick 1 face/vertex on each.'
            self.report({'WARNING'}, msg)
            return

        curvedata = bpy.data.curves.new(name=self.base_name, type='CURVE')
        curvedata.dimensions = '3D'

        obj = bpy.data.objects.new('Obj_' + curvedata.name, curvedata)
        obj.location = (0, 0, 0)  # object origin
        bpy.context.collection.objects.link(obj)
        self.generated_name = obj.name
        print(':::', self.generated_name, current_mode)

        if current_mode[self_id] in {"ONE", "THREE"}:
            obj.matrix_world = mw.copy()

        polyline = curvedata.splines.new('BEZIER')
        polyline.bezier_points.add(1)
        polyline.use_smooth = False
        obj.data.fill_mode = 'FULL'


    @classmethod
    def poll(self, context):
        # return self.do_not_process
        obj = bpy.context.edit_object
        print(f"faces={obj.data.total_face_sel}, verts={obj.data.total_vert_sel}")
        if obj and obj.data.total_face_sel == 2 or obj.data.total_vert_sel == 2:
            return True

        return self.are_two_objects_in_editmode()

    def make_real(self):
        objects = bpy.data.objects
        obj = objects[self.generated_name]  # this curve object

        settings = False
        modifiers = True
        obj_data = obj.to_mesh() # bpy.context.depsgraph, apply_modifiers=modifiers, calc_undeformed=settings)

        obj_n = objects.new('MESHED_' + obj.name, obj_data)
        obj_n.location = (0, 0, 0)
        obj_n.matrix_world = obj.matrix_world.copy()
        bpy.context.collection.objects.link(obj_n)
        obj.hide_render = True
        obj.hide_viewport = True
        # return obj_n

    def execute(self, context):

        if self.do_not_process:
            return {'CANCELLED'}
        else:
            self.initialize_new_tube(context)
            update_simple_tube(self, context)
            return {'FINISHED'}


TubeCallbackOps.__doc__ = docstring
AddSimpleTube.__doc__ = docstring

classes = [TubeCallbackOps, AddSimpleTube]
register, unregister = bpy.utils.register_classes_factory(classes)
