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

import json
import math
import bpy
import bmesh
from mathutils import Vector

''' Consider this file a massive lazyness hack, to avoid drawing BGL by hand.'''


def get_layer(gdata_owner, layer_name):

    grease_data = bpy.data.grease_pencil
    if gdata_owner not in grease_data:
        gp = grease_data.new(gdata_owner)
    else:
        gp = grease_data[gdata_owner]

    # get grease pencil layer
    if not (layer_name in gp.layers):
        layer = gp.layers.new(layer_name)
        layer.frames.new(1)
        layer.line_width = 1
    else:
        layer = gp.layers[layer_name]
        layer.frames[0].clear()

    return layer


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


def generate_gp3d_handle_repr(self, context, layer):
    layer.show_points = True
    layer.color = (.4, .9, .2)

    obj_curve = bpy.data.objects[self.generated_name]
    handles = get_handles(self)

    for handle in handles:
        s = layer.frames[0].strokes.new()
        s.draw_mode = '3DSPACE'

        chain = []
        for vtx in handle:
            world_point = obj_curve.matrix_world * vtx
            chain.append(world_point)

        s.points.add(len(chain))
        for idx, p in enumerate(chain):
            s.points[idx].co = p
