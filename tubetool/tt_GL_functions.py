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
from mathutils import Vector

#  reusing
# https://github.com/nortikin/sverchok/blob/master/ui/index_viewer_draw.py


SpaceView3D = bpy.types.SpaceView3D

callback_dict = {}


def get_handles(oper):
    obj = bpy.data.objects[oper.generated_name]
    curvedata = obj.data
    polyline = curvedata.splines[0]

    handles = []
    points = [0, -1] if not oper.flip_v else [-1, 0]

    for p in points:
        point = polyline.bezier_points[p]
        a = point.handle_left
        b = point.co
        c = point.handle_right
        handles.append([a, b, c])

    return handles


def tag_redraw_all_view3d():
    context = bpy.context

    # Py cant access notifers
    for window in context.window_manager.windows:
        for area in window.screen.areas:
            if area.type == 'VIEW_3D':
                for region in area.regions:
                    if region.type == 'WINDOW':
                        region.tag_redraw()


def callback_disable_all():
    global callback_dict
    temp_list = list(callback_dict.keys())
    for n_id in temp_list:
        if n_id:
            callback_disable(n_id)


def draw_callback_px(self, context):

    obj_curve = bpy.data.objects[self.generated_name]
    handles = get_handles(self)

    font_id = 0  # XXX, need to find out how best to get this.

    # draw some text
    blf.position(font_id, 15, 30, 0)
    blf.size(font_id, 20, 72)
    blf.draw(font_id, "Hello Word ")

    # 50% alpha, 2 pixel width line
    bgl.glEnable(bgl.GL_BLEND)
    bgl.glColor4f(0.7, 0.7, 0.5, 0.5)
    bgl.glLineWidth(2)

    for handle in handles:
        bgl.glBegin(bgl.GL_LINE_STRIP)

        chain = []
        for vtx in handle:
            world_point = obj_curve.matrix_world * vtx
            bgl.glVertex3f(*world_point[:])

        bgl.glEnd()

    # restore opengl defaults
    bgl.glLineWidth(1)
    bgl.glDisable(bgl.GL_BLEND)
    bgl.glColor4f(0.0, 0.0, 0.0, 1.0)
