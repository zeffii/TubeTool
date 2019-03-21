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

bl_info = {
    "name": "Tube Tool",
    "author": "Dealga McArdle",
    "version": (0, 0, 4),
    "blender": (2, 80, 0),
    "location": "specials menu (key W)",
    "description": "Adds curve with endpoints on two arbitrary polygons",
    "wiki_url": "",
    "tracker_url": "",
    "category": "Mesh"}

if 'bpy' in globals():
    print(__package__, 'detected reload event! cool.')

    if 'tt_operators' in globals():
        print('doing reloads')
        import imp
        imp.reload(tt_operators)

else:
    from . import tt_operators


import bpy


def menu_func(self, context):
    self.layout.operator("mesh.add_curvebased_tube", text="Add Tubing")
    self.layout.separator()


def register():
    tt_operators.register()
    bpy.types.VIEW3D_MT_edit_mesh_context_menu.prepend(menu_func)


def unregister():
    bpy.types.VIEW3D_MT_edit_mesh_context_menu.remove(menu_func)
    tt_operators.unregister()
