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

import bgl
import blf
import math
import bpy
import bmesh
from mathutils import Vector, Matrix

from bgl import (
    glEnable, glDisable, glBegin, glEnd,
    Buffer, GL_FLOAT, GL_BYTE, GL_INT,
    glGetIntegerv, glGetFloatv,
    glColor3f, glVertex3f, glColor4f, glPointSize, glLineWidth,
    glLineStipple, glPolygonStipple, glHint, glShadeModel,
    #
    GL_MATRIX_MODE, GL_MODELVIEW_MATRIX, GL_MODELVIEW, GL_PROJECTION,
    glMatrixMode, glLoadMatrixf, glPushMatrix, glPopMatrix, glLoadIdentity,
    glGenLists, glNewList, glEndList, glCallList, glFlush, GL_COMPILE,
    #
    GL_POINTS, GL_POINT_SIZE, GL_POINT_SMOOTH, GL_POINT_SMOOTH_HINT,
    GL_LINE, GL_LINES, GL_LINE_STRIP, GL_LINE_LOOP, GL_LINE_STIPPLE,
    GL_POLYGON, GL_POLYGON_STIPPLE, GL_TRIANGLES, GL_QUADS, GL_BLEND,
    GL_NICEST, GL_FASTEST, GL_FLAT, GL_SMOOTH, GL_LINE_SMOOTH_HINT)

'''

Good luck figuring out how this works. If you are coming from a point of
complete bright eye - never seen bgl or openGL before - the boilerplate
for this beast is everything except:

- get_curve_handles
- draw_callback_px

The rest is for dealing with adding the GL drawing mechanism to the
correct location (SpaceView3D) and removing it when done.

'''


SpaceView3D = bpy.types.SpaceView3D

callback_dict = {}


def get_curve_handles(caller):
    obj = bpy.data.objects[caller.generated_name]
    curvedata = obj.data
    polyline = curvedata.splines[0]

    handles = []
    points = [0, -1] if not caller.flip_v else [-1, 0]

    for p in points:
        point = polyline.bezier_points[p]
        a = point.handle_left.xyz
        b = point.co.xyz
        c = point.handle_right.xyz
        handles.append([a, b, c])

    return handles


def draw_callback_px(caller, context):
    obj_curve = bpy.data.objects[caller.generated_name]
    handles = get_curve_handles(caller)

    glEnable(GL_BLEND)
    glEnable(GL_POINT_SIZE)

    glLineWidth(2)
    glPointSize(4)

    col1 = (0.9, 0.3, 0.9, 0.9)
    col2 = (0.9, 0.9, 0.3, 0.9)
    temp_colors = [col1, col2]

    for idx, handle in enumerate(handles):

        glColor4f(*temp_colors[idx])
        glBegin(GL_LINE_STRIP)
        for vtx in handle:
            world_point = obj_curve.matrix_world * vtx
            glVertex3f(*world_point)
        glEnd()

        glColor4f(0.6, 0.6, 0.9, 0.9)
        glBegin(GL_POINTS)
        for vtx in handle:
            world_point = obj_curve.matrix_world * vtx
            glVertex3f(*world_point)
        glEnd()

    print('should have drawn')
    print(list(callback_dict.keys()))

    # restore opengl defaults
    glLineWidth(1)
    glDisable(GL_BLEND)
    glDisable(GL_POINT_SIZE)
    glColor4f(0.0, 0.0, 0.0, 1.0)


def tag_redraw_all_view3d():
    context = bpy.context
    for window in context.window_manager.windows:
        for area in window.screen.areas:
            if area.type == 'VIEW_3D':
                for region in area.regions:
                    if region.type == 'WINDOW':
                        region.tag_redraw()


def callback_enable(self):
    global callback_dict
    
    if self.n_id in callback_dict:
        return
    args = (self, bpy.context)
    handle_pixel = SpaceView3D.draw_handler_add(
        draw_callback_px, args, 'WINDOW', 'POST_VIEW')
    callback_dict[self.n_id] = handle_pixel
    tag_redraw_all_view3d()


def callback_disable(n_id):
    global callback_dict
    handle_pixel = callback_dict.get(n_id, None)
    if not handle_pixel:
        return
    SpaceView3D.draw_handler_remove(handle_pixel, 'WINDOW')
    del callback_dict[n_id]
    tag_redraw_all_view3d()


def callback_disable_all():
    global callback_dict
    temp_list = list(callback_dict.keys())
    for n_id in temp_list:
        if n_id:
            callback_disable(n_id)


def unregister():
    callback_disable_all()
