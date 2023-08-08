"""
    This file is part of Pickup.

    Copyright (C) 2023 Project Studio Q inc.

    Animation Offset Shift is free software; you can redistribute it and/or
    modify it under the terms of the GNU General Public License
    as published by the Free Software Foundation; either version 2
    of the License, or (at your option) any later version.

    This program is distributed in the hope that it will be useful,
    but WITHOUT ANY WARRANTY; without even the implied warranty of
    MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
    GNU General Public License for more details.

    You should have received a copy of the GNU General Public License
    along with this program; if not, write to the Free Software
    Foundation, Inc., 51 Franklin Street, Fifth Floor, Boston, MA  02110-1301, USA.
"""

import bpy
import ctypes
from bpy_extras.io_utils import ImportHelper
from bpy_extras.io_utils import ExportHelper

# -----------------------------------------------------------------------------

OBJECT_PICKUP_HEADER = "StudioQ:Object Pickup"
OBJECT_PICKUP_FILE_VERSION = 100
VK_LBUTTON = 0x01
VK_SHIFT = 0x10
VK_CONTROL = 0x11
last_selected_object_name = ""
windows_mode = False

# -----------------------------------------------------------------------------

def _show_object( o, hide_select_only = False ):
    def f( lc ):
        nonlocal o
        c = lc.collection

        if o.name not in c.all_objects:
            return

        c.hide_select = False
        if not hide_select_only:
            lc.exclude = False
            lc.hide_viewport = False

            c.hide_viewport = False

        for t in lc.children:
            f( t )

    f( bpy.context.view_layer.layer_collection )

def _select_object( object_name, value ):
    if object_name not in bpy.data.objects:
        return

    o = bpy.data.objects[object_name]

    # 表示されているか？
    if not o.visible_get( ):
        _show_object( o )
        o.hide_set( False )
        o.select_set( False )
        o.hide_select = False
        o.hide_viewport = False
    else:
        _show_object( o, True )

    # オブジェクトを選択する
    o.select_set( True )

def _set_QANIM_SAVE_object_pickup_single_object( self, value ):
    context = bpy.context
    mode = context.scene.q_bp_object_group_mode

    if mode == "DEFAULT":
        global last_selected_object_name

        group = None
        for g in context.scene.q_bp_object_groups:
            for t in g.objects:
                if t.object_name == self.object_name:
                    group = g
                    break

        # デフォルト
        lbutton_state = ctypes.windll.user32.GetAsyncKeyState( VK_LBUTTON )
        shift_select = False
        reset_select = False
        if any(t.select_get( ) for t in bpy.data.objects):
            if lbutton_state & 1 == 0:
                pass
            else:
                shift_select = ( ctypes.windll.user32.GetKeyState( VK_SHIFT ) & 0x8000 ) != 0
                if not shift_select:
                    reset_select = ( ctypes.windll.user32.GetKeyState( VK_CONTROL ) & 0x8000 ) == 0
                else:
                    value = True
        else:
            value = True

        if reset_select:
            bpy.ops.object.select_all(action= "DESELECT")
            value = True

        if shift_select and group:
            selecting = False
            sorted_objects = [t for t in group.objects]
            if context.scene.q_bp_object_group_sort:
                sorted_objects = sorted(sorted_objects, key= lambda x: x.object_name )
            for t in sorted_objects:
                if t.object_name == self.object_name or t.object_name == last_selected_object_name:
                    selecting = not selecting
                if selecting:
                    _select_object( t.object_name, True )

        _select_object( self.object_name, value )
        last_selected_object_name = self.object_name
    elif mode == "BLENDER_CHECK":
        # Blenderチェックマーク式
        _select_object( self.object_name, value )

def _get_QANIM_SAVE_object_pickup_single_object( self ):
    if self.object_name in bpy.data.objects:
        return bpy.data.objects[self.object_name].select_get( )

    return False

class QANIM_SAVE_object_pickup_single_object(bpy.types.PropertyGroup):
    object_name: bpy.props.StringProperty( default= "None" )
    select: bpy.props.BoolProperty( default= False, set= _set_QANIM_SAVE_object_pickup_single_object, get= _get_QANIM_SAVE_object_pickup_single_object, options= {'SKIP_SAVE'} )

class QANIM_SAVE_object_pickup_group(bpy.types.PropertyGroup):
    show: bpy.props.BoolProperty( default= False )
    name: bpy.props.StringProperty( default= "New Group" )
    objects: bpy.props.CollectionProperty( type= QANIM_SAVE_object_pickup_single_object )

# -----------------------------------------------------------------------------

class QANIM_OT_object_pickup_register(bpy.types.Operator):
    bl_idname = "qanim.object_pickup_register"
    bl_label = "New"
    bl_options = {'REGISTER', 'UNDO'}
    bl_description = "Register Object Pickup"

    @classmethod
    def poll(cls, context):
        return context.selected_objects and 0 < len( context.selected_objects )

    def execute(self, context):
        new_group = context.scene.q_bp_object_groups.add( )
        new_group.name = "New Group"

        for o in context.selected_objects:
            t = new_group.objects.add( )
            t.object_name = o.name

        return {'FINISHED'}

class QANIM_OT_object_pickup_mirror(bpy.types.Operator):
    bl_idname = "qanim.object_pickup_mirror"
    bl_label = "LR Mirror"
    bl_options = {'REGISTER', 'UNDO'}
    bl_description = "Mirror Object Group"

    group_index: bpy.props.IntProperty( )

    def execute(self, context):
        original = context.scene.q_bp_object_groups[self.group_index]

        new_group = context.scene.q_bp_object_groups.add( )
        new_group.name = original.name + " Mirror"

        for t in original.objects:
            new = new_group.objects.add( )
            name = t.object_name
            if name[-1] == "L":
                name = name[0:-1] + "R"
            elif name[-1] == "R":
                name = name[0:-1] + "L"
            new.object_name = name

        return {'FINISHED'}

class QANIM_OT_object_pickup_delete(bpy.types.Operator):
    bl_idname = "qanim.object_pickup_delete"
    bl_label = "Delete"
    bl_options = {'REGISTER', 'UNDO'}
    bl_description = "Delete Object Group"

    group_index: bpy.props.IntProperty( )

    def execute(self, context):
        context.scene.q_bp_object_groups.remove( self.group_index )
        return {'FINISHED'}

class QANIM_OT_object_pickup_single_add(bpy.types.Operator):
    bl_idname = "qanim.object_pickup_single_add"
    bl_label = "Append"
    bl_options = {'REGISTER', 'UNDO'}
    bl_description = "Append Object to Group"

    group_index: bpy.props.IntProperty( )

    @classmethod
    def poll(cls, context):
        return context.selected_objects and 0 < len( context.selected_objects )

    def execute(self, context):
        group = context.scene.q_bp_object_groups[self.group_index]

        for o in context.selected_objects:
            found = False
            for t in group.objects:
                if t.object_name == o.name:
                    found = True
                    break
            if found:
                continue

            t = group.objects.add( )
            t.object_name = o.name

        return {'FINISHED'}

class QANIM_OT_object_pickup_single_delete(bpy.types.Operator):
    bl_idname = "qanim.object_pickup_single_delete"
    bl_label = "Remove"
    bl_options = {'REGISTER', 'UNDO'}
    bl_description = "Remove Single Object From Group"

    group_index: bpy.props.IntProperty( )
    selected_item_index: bpy.props.IntProperty( )

    def execute(self, context):
        context.scene.q_bp_object_groups[self.group_index].objects.remove( self.selected_item_index )
        return {'FINISHED'}

class QANIM_OT_object_pickup_save(bpy.types.Operator):
    bl_idname = "qanim.object_pickup_save"
    bl_label = "Save"
    bl_options = {'REGISTER', 'UNDO'}
    bl_description = "Save Object Group to JSON"

    json_path: bpy.props.StringProperty( )

    def execute(self, context):
        data = {}
        for group in context.scene.q_bp_object_groups:
            data[group.name] = [t.object_name for t in group.objects]

        import json
        with open( self.json_path, 'w' ) as f:
            json.dump({
                "name": OBJECT_PICKUP_HEADER
            ,   "version": OBJECT_PICKUP_FILE_VERSION
            ,   "data": data
            }, f )

        return {'FINISHED'}

class QANIM_OT_object_pickup_load(bpy.types.Operator):
    bl_idname = "qanim.object_pickup_load"
    bl_label = "Load"
    bl_options = {'REGISTER', 'UNDO'}
    bl_description = "Load Object Group from JSON"

    json_path: bpy.props.StringProperty( )

    def execute(self, context):
        import json
        try:
            with open( self.json_path, 'r' ) as f:
                all_data = json.load( f )
            if "name" not in all_data or all_data["name"] != OBJECT_PICKUP_HEADER:
                self.report({"ERROR"}, "このJSONはObject Pickup用ではありません。")
                raise Exception( "Header Error" )
            if "data" not in all_data:
                self.report({"ERROR"}, "このJSONはObject Pickup用ではありません。")
                raise Exception( "Data Error" )
            data = all_data["data"]
        except:
            return {'CANCELLED'}

        for group_name, objects in data.items( ):
            group = None
            for t in context.scene.q_bp_object_groups:
                if t.name == group_name:
                    group = t
                    break
            if not group:
                group = context.scene.q_bp_object_groups.add( )
                group.name = group_name

            for object_name in objects:
                found = False
                for t in group.objects:
                    if t.object_name == object_name:
                        found = True
                        break
                if not found:
                    new = group.objects.add( )
                    new.object_name = object_name

        return {'FINISHED'}

class QANIM_OT_object_pickup_load_from_blend(bpy.types.Operator):
    bl_idname = "qanim.object_pickup_load_from_blend"
    bl_label = "Load from Blend file"
    bl_options = {'REGISTER', 'UNDO'}
    bl_description = "Load Object Group from Blend file"

    blend_path: bpy.props.StringProperty( )

    def execute(self, context):
        import os
        if not os.path.exists( self.blend_path ):
            self.report({'ERROR'}, "%s というファイルは存在しません。" % self.blend_path )
            return {'CANCELLED'}

        import tempfile
        with tempfile.TemporaryDirectory() as dname:
            tmp_path = os.path.join( dname, "object_group.txt" ).replace( "\\", "/" )
            import subprocess
            subprocess.run([
                "blender.exe"
            ,   "--background"
            ,   self.blend_path
            ,   "--python-expr", "import bpy; bpy.ops.qanim.object_pickup_save( json_path= \"%s\" ); import sys; sys.exit( 0 )" % tmp_path
            ] )

            bpy.ops.qanim.object_pickup_load( json_path= tmp_path )

        return {'FINISHED'}

class QANIM_OT_object_pickup_select_path_import_json(bpy.types.Operator, ImportHelper):
    """
        JSONファイルパスを設定する
    """
    bl_idname = "qanim.object_pickup_select_path_import_json"
    bl_label = "Select JSON Path"
    bl_description = "Import a .json file"
    bl_options = {'REGISTER', 'UNDO'}

    #filename_ext = ".json"
    filter_glob: bpy.props.StringProperty(
        default="*.json",
        options={'HIDDEN'},
    )

    def invoke(self, context, event):
        fp = self.filepath
        if fp:
            ext = fp.rsplit(".", 1)
            if ext != "json":
                fp = ".json"
        else:
            fp = ".json"
        self.filepath = fp

        context.window_manager.fileselect_add(self)
        return {'RUNNING_MODAL'}

    def execute(self, context):
        context.scene.q_bp_object_group_import_json_path = self.filepath
        bpy.ops.wm.redraw_timer(type='DRAW_WIN_SWAP', iterations=1)
        return {'FINISHED'}

class QANIM_OT_object_pickup_select_path_export_json(bpy.types.Operator, ExportHelper):
    """
        JSONファイルパスを設定する
    """
    bl_idname = "qanim.object_pickup_select_path_export_json"
    bl_label = "Select JSON Path"
    bl_description = "Export a .json file"
    bl_options = {'REGISTER', 'UNDO'}

    filename_ext = ".json"
    filter_glob: bpy.props.StringProperty(
        default='*.json',
        options={'HIDDEN'}
    )

    def execute(self, context):
        context.scene.q_bp_object_group_export_json_path = self.filepath
        bpy.ops.wm.redraw_timer(type='DRAW_WIN_SWAP', iterations=1)
        return {'FINISHED'}

class QANIM_OT_object_pickup_select_path_blend(bpy.types.Operator, ImportHelper):
    """
        Blendファイルパスを設定する
    """
    bl_idname = "qanim.object_pickup_select_path_blend"
    bl_label = "Select Blend Path"
    bl_description = "Import a .blend file"
    bl_options = {'REGISTER', 'UNDO'}

    #filename_ext = ".blend"
    filter_glob: bpy.props.StringProperty(
        default="*.blend",
        options={'HIDDEN'},
    )

    def invoke(self, context, event):
        fp = self.filepath
        if fp:
            ext = fp.rsplit(".", 1)
            if ext != "blend":
                fp = ".blend"
        else:
            fp = ".blend"
        self.filepath = fp

        context.window_manager.fileselect_add(self)
        return {'RUNNING_MODAL'}

    def execute(self, context):
        context.scene.q_bp_object_group_input_blend_path = self.filepath
        bpy.ops.wm.redraw_timer(type='DRAW_WIN_SWAP', iterations=1)
        return {'FINISHED'}

# -----------------------------------------------------------------------------

class QANIM_PT_object_pickup(bpy.types.Panel):
    bl_label = "Object Pickup"
    bl_idname = "QANIM_PT_object_pickup"
    bl_space_type = "VIEW_3D"
    bl_region_type = "UI"
    bl_category = "Q_ANIM"
    bl_options = {'DEFAULT_CLOSED'}

    @classmethod
    def poll(cls, context):
        return context.mode == 'OBJECT'

    def draw(self, context):
        layout = self.layout

        row = layout.row( )
        col = row.column( )
        col.alignment = 'LEFT'
        col.operator( QANIM_OT_object_pickup_register.bl_idname )
        col = row.column( )
        col.alignment = 'RIGHT'
        col.prop( context.scene, "q_bp_object_group_search_name", text= "", icon= "VIEWZOOM")
        col = row.column( )
        col.alignment = 'RIGHT'
        col.prop( context.scene, "q_bp_object_group_sort", text= "", icon= "SORTALPHA")

        sorted_groups = [t for t in context.scene.q_bp_object_groups]
        if context.scene.q_bp_object_group_sort:
            sorted_groups = sorted(sorted_groups, key= lambda x: x.name )
                
        box = layout.row( ).box( )
        group_index = 0
        for group in sorted_groups:
            if context.scene.q_bp_object_group_search_name != "" and context.scene.q_bp_object_group_search_name.lower( ) not in group.name.lower( ):
                continue

            row = box.row( )
            col = row.column( )
            col.alignment = 'LEFT'
            col.prop(group, "show", icon_only= True, icon="DISCLOSURE_TRI_DOWN" if group.show else "DISCLOSURE_TRI_RIGHT", emboss= False)
            col = row.column( )
            col.prop(group, "name", text= "")

            if group.show:
                row = box.row( )
                col = row.column( )
                col.alignment = 'RIGHT'
                op = col.operator( QANIM_OT_object_pickup_single_add.bl_idname )
                op.group_index = group_index
                col = row.column( )
                col.alignment = 'RIGHT'
                op = col.operator( QANIM_OT_object_pickup_mirror.bl_idname )
                op.group_index = group_index
                col = row.column( )
                col.alignment = 'RIGHT'
                op = col.operator( QANIM_OT_object_pickup_delete.bl_idname )
                op.group_index = group_index
                col = row.column( )

                index = 0
                sorted_objects = [t for t in group.objects]
                if context.scene.q_bp_object_group_sort:
                    sorted_objects = sorted(sorted_objects, key= lambda x: x.object_name )
                
                for t in sorted_objects:
                    row = box.row( )
                    col = row.column( )
                    col.alignment = 'LEFT'
                    col.label(text= "")
                    col = row.column( )
                    col.alignment = 'LEFT'
                    if t.object_name in bpy.data.objects:
                        col.prop(t, "select", text= t.object_name)
                    else:
                        col.label(text= t.object_name, icon= "ERROR")
                        #col.alert = True
                    col = row.column( )
                    col = row.column( )
                    col.alignment = 'RIGHT'
                    op = col.operator(QANIM_OT_object_pickup_single_delete.bl_idname)
                    op.group_index = group_index
                    op.selected_item_index = index
                    index += 1
            else:
                col = row.column( )
            group_index += 1

        row = layout.row( )
        row.prop(context.scene, "q_bp_object_group_import_export", expand=True)
        row = layout.row( )

        if context.scene.q_bp_object_group_import_export == "IMPORT":
            col = row.column( )
            col.prop(context.scene, "q_bp_object_group_import_json_path", text="Import from")
            col = row.column( )
            col.alignment = "RIGHT"
            col.operator(QANIM_OT_object_pickup_select_path_import_json.bl_idname, text="", icon="FILE_FOLDER")
            col = row.column( )
            col.alignment = "RIGHT"
            col.operator( QANIM_OT_object_pickup_load.bl_idname ).json_path = context.scene.q_bp_object_group_import_json_path
        elif context.scene.q_bp_object_group_import_export == "EXPORT":
            col = row.column( )
            col.prop(context.scene, "q_bp_object_group_export_json_path", text="Export to")
            col = row.column( )
            col.alignment = "RIGHT"
            col.operator(QANIM_OT_object_pickup_select_path_export_json.bl_idname, text="", icon="FILE_FOLDER")
            col = row.column( )
            col.alignment = "RIGHT"
            col.operator( QANIM_OT_object_pickup_save.bl_idname ).json_path = context.scene.q_bp_object_group_export_json_path
        elif context.scene.q_bp_object_group_import_export == "BLEND":
            col = row.column( )
            col.prop(context.scene, "q_bp_object_group_input_blend_path", text="Import from Blend file")
            col = row.column( )
            col.alignment = "RIGHT"
            col.operator(QANIM_OT_object_pickup_select_path_blend.bl_idname, text="", icon="FILE_FOLDER")
            col = row.column( )
            col.alignment = "RIGHT"
            col.operator( QANIM_OT_object_pickup_load_from_blend.bl_idname ).blend_path = context.scene.q_bp_object_group_input_blend_path

        global windows_mode
        if windows_mode:
            row = layout.row( )
            col = row.column( )
            col.prop(context.scene, "q_bp_object_group_mode")

# -----------------------------------------------------------------------------

classes = (
    QANIM_SAVE_object_pickup_single_object,
    QANIM_SAVE_object_pickup_group,
    QANIM_PT_object_pickup,
    QANIM_OT_object_pickup_register,
    QANIM_OT_object_pickup_mirror,
    QANIM_OT_object_pickup_delete,
    QANIM_OT_object_pickup_single_add,
    QANIM_OT_object_pickup_single_delete,
    QANIM_OT_object_pickup_save,
    QANIM_OT_object_pickup_load,
    QANIM_OT_object_pickup_load_from_blend,
    QANIM_OT_object_pickup_select_path_import_json,
    QANIM_OT_object_pickup_select_path_export_json,
    QANIM_OT_object_pickup_select_path_blend,
)

def register():
    """
        クラス登録
    """
    for i in classes:
        bpy.utils.register_class(i)

    _initialize( )

def unregister():
    """
        クラス登録解除
    """
    _deinitialize( )

    for i in classes:
        bpy.utils.unregister_class(i)

def _initialize( ):
    """
        初期化
    """

    global windows_mode
    windows_mode = hasattr( ctypes, "windll" )

    bpy.types.Scene.q_bp_object_groups = bpy.props.CollectionProperty(
        name="Hyper Object Selection Sets Group",
        type= QANIM_SAVE_object_pickup_group
    )
    bpy.types.Scene.q_bp_object_group_search_name = bpy.props.StringProperty( options={'HIDDEN'} )
    bpy.types.Scene.q_bp_object_group_sort = bpy.props.BoolProperty( default= True, options={'HIDDEN'} )
    bpy.types.Scene.q_bp_object_group_input_blend_path = bpy.props.StringProperty( options={'HIDDEN'} )
    bpy.types.Scene.q_bp_object_group_export_json_path = bpy.props.StringProperty( options={'HIDDEN'} )
    bpy.types.Scene.q_bp_object_group_import_json_path = bpy.props.StringProperty( options={'HIDDEN'} )
    bpy.types.Scene.q_bp_object_group_import_export = bpy.props.EnumProperty(
        name= "読み書きモード"
    ,   default= 'IMPORT'
    ,   options={'HIDDEN'}
    ,   items=(
            ('IMPORT', 'Import', 'インポートする'),
            ('EXPORT', 'Export', 'エクスポートする'),
            ('BLEND', 'Blend', 'Blendファイルから読み込む'),
        )
    )
    bpy.types.Scene.q_bp_object_group_mode = bpy.props.EnumProperty(
        name= "Check Mode"
    ,   default= 'DEFAULT' if windows_mode else 'BLENDER_CHECK'
    ,   options={'HIDDEN'}
    ,   items=(
            ('DEFAULT', 'Default', '通常の選択と同じ挙動'),
            ('BLENDER_CHECK', 'Blender Check', 'Blenderのチェックマークと同じ挙動'),
        )
    )

def _deinitialize( ):
    """
        後始末
    """
    del bpy.types.Scene.q_bp_object_groups
    del bpy.types.Scene.q_bp_object_group_search_name
    del bpy.types.Scene.q_bp_object_group_sort
    del bpy.types.Scene.q_bp_object_group_input_blend_path
    del bpy.types.Scene.q_bp_object_group_import_json_path
    del bpy.types.Scene.q_bp_object_group_export_json_path
    del bpy.types.Scene.q_bp_object_group_import_export
    del bpy.types.Scene.q_bp_object_group_mode
