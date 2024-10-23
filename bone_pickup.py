import bpy
import ctypes
from bpy_extras.io_utils import ImportHelper, ExportHelper

# -----------------------------------------------------------------------------

BONE_PICKUP_HEADER = "StudioQ:Bone Pickup"
BONE_PICKUP_FILE_VERSION = 101
VK_LBUTTON = 0x01
VK_SHIFT = 0x10
VK_CONTROL = 0x11
last_selected_bone_name = ""
windows_mode = False

# -----------------------------------------------------------------------------

def _set_QANIM_SAVE_bone_pickup_single_bone( self, value ):
    context = bpy.context

    group = _get_group_by_single_bone( self )
    group.high_light = False
    if group is None or group.object is None:
        o = context.active_object
    else:
        o = group.object
        o.select_set( True )

    bones = o.data.bones if context.mode == "POSE" else o.data.edit_bones

    mode = context.scene.q_bp_bone_group_mode
    if mode == "DEFAULT":
        global last_selected_bone_name

        group = None
        for g in context.scene.q_bp_bone_groups:
            for t in g.bones:
                if t.bone_name == self.bone_name:
                    group = g
                    break

        # デフォルト
        lbutton_state = ctypes.windll.user32.GetAsyncKeyState( VK_LBUTTON )
        shift_select = False
        reset_select = False
        if 0 < len( context.selected_pose_bones ):
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
            # 全ボーンの選択を解除
            for arm in bpy.data.armatures:
                temp_bones = arm.bones if context.mode == "POSE" else arm.edit_bones
                for t in temp_bones:
                    t.select = False
            value = True

        if shift_select and group:
            selecting = False
            sorted_bones = [t for t in group.bones]
            if context.scene.q_bp_bone_group_sort:
                sorted_bones = sorted(sorted_bones, key= lambda x: x.bone_name )
            for t in sorted_bones:
                if t.bone_name == self.bone_name or t.bone_name == last_selected_bone_name:
                    selecting = not selecting
                if t.bone_name in bones and selecting:
                    bones[t.bone_name].select = True

        if self.bone_name in bones:
            bones[self.bone_name].select = value
        last_selected_bone_name = self.bone_name
    elif mode == "BLENDER_CHECK":
        # Blenderチェックマーク式
        if self.bone_name in bones:
            bones[self.bone_name].select = value

def _get_QANIM_SAVE_bone_pickup_single_bone( self ):
    context = bpy.context

    group = _get_group_by_single_bone( self )
    if group is None or group.object is None:
        o = context.active_object
    else:
        o = group.object

    bones = o.data.bones if context.mode == "POSE" else o.data.edit_bones
    if self.bone_name in bones:
        return bones[self.bone_name].select

    return False

def _get_group_by_single_bone( bone ):
    for group in bpy.context.scene.q_bp_bone_groups:
        for t in group.bones:
            if bone.as_pointer( ) == t.as_pointer( ):
                return group

    return None

def _filter_armature_object( self, obj ):
    if obj is not None:
        return obj.type == "ARMATURE"
    else:
        return True

def _set_QANIM_SAVE_bone_pickup_ui_name( self, value ):
    self.name = value
    self.high_light = True

def _get_QANIM_SAVE_bone_pickup_ui_name( self ):
    return self.name

class QANIM_SAVE_bone_pickup_single_bone(bpy.types.PropertyGroup):
    bone_name: bpy.props.StringProperty( default= "None", options={"HIDDEN"} )
    # XXX: リンクしたオブジェクトで object.data.bones[].select がUI上で編集できなくなるので、setter/getterを利用してPythonから書き込む
    select: bpy.props.BoolProperty( default= False, set= _set_QANIM_SAVE_bone_pickup_single_bone, get= _get_QANIM_SAVE_bone_pickup_single_bone, options= {'SKIP_SAVE', 'HIDDEN'} )

class QANIM_SAVE_bone_pickup_group(bpy.types.PropertyGroup):
    show: bpy.props.BoolProperty( default= False, options={"HIDDEN"} )
    high_light: bpy.props.BoolProperty( default= False, options={"HIDDEN"} )
    object: bpy.props.PointerProperty( type=bpy.types.Object, poll= _filter_armature_object, options={"HIDDEN"} )
    name: bpy.props.StringProperty( default= "New Group", options={"HIDDEN"} )
    ui_name: bpy.props.StringProperty( default= "New Group", set= _set_QANIM_SAVE_bone_pickup_ui_name, get= _get_QANIM_SAVE_bone_pickup_ui_name, options={"HIDDEN"} )
    bones: bpy.props.CollectionProperty( type= QANIM_SAVE_bone_pickup_single_bone, options={"HIDDEN"} )

# -----------------------------------------------------------------------------

class QANIM_OT_bone_pickup_register(bpy.types.Operator):
    bl_idname = "qanim.bone_pickup_register"
    bl_label = "新規登録"
    bl_options = {'REGISTER', 'UNDO'}
    bl_description = "Register Bone Pickup"

    @classmethod
    def poll(cls, context):
        return (
            context.active_object
        and context.active_object.type == "ARMATURE"
        and (
                ( context.selected_pose_bones_from_active_object and 0 < len( context.selected_pose_bones_from_active_object ) )
            or  ( context.selected_editable_bones and 0 < len( context.selected_editable_bones ) )
            )
        )

    def execute(self, context):
        new_group = context.scene.q_bp_bone_groups.add( )
        new_group.object = context.active_object
        new_group.name = "New Group"
        new_group.high_light = True

        bones = context.selected_pose_bones_from_active_object if context.mode == "POSE" else context.selected_editable_bones

        for pb in bones:
            bone = new_group.bones.add( )
            bone.bone_name = pb.name

        return {'FINISHED'}

class QANIM_OT_bone_pickup_copy(bpy.types.Operator):
    bl_idname = "qanim.bone_pickup_copy"
    bl_label = "コピー"
    bl_options = {'REGISTER', 'UNDO'}
    bl_description = "Copy Bone Group"

    group_index: bpy.props.IntProperty( )

    def execute(self, context):
        original = context.scene.q_bp_bone_groups[self.group_index]

        new_group = context.scene.q_bp_bone_groups.add( )
        new_group.object = original.object
        new_group.name = original.name + " Copy"

        for t in original.bones:
            bone = new_group.bones.add( )
            bone.bone_name = t.bone_name

        return {'FINISHED'}

class QANIM_OT_bone_pickup_mirror(bpy.types.Operator):
    bl_idname = "qanim.bone_pickup_mirror"
    bl_label = "LRミラー"
    bl_options = {'REGISTER', 'UNDO'}
    bl_description = "Mirror Bone Group"

    group_index: bpy.props.IntProperty( )

    def execute(self, context):
        original = context.scene.q_bp_bone_groups[self.group_index]

        new_group = context.scene.q_bp_bone_groups.add( )
        new_group.object = original.object
        if original.name[-2:] == "_R":
            new_group.name = original.name[:-2] + "_L"
        elif original.name[-2:] == "_L":
            new_group.name = original.name[:-2] + "_R"
        else:
            new_group.name = original.name + " Mirror"

        for t in original.bones:
            bone = new_group.bones.add( )
            name = t.bone_name
            if name[-1] == "L":
                name = name[0:-1] + "R"
            elif name[-1] == "R":
                name = name[0:-1] + "L"
            bone.bone_name = name

        return {'FINISHED'}

class QANIM_OT_bone_pickup_delete(bpy.types.Operator):
    bl_idname = "qanim.bone_pickup_delete"
    bl_label = "削除"
    bl_options = {'REGISTER', 'UNDO'}
    bl_description = "Delete Bone Group"

    group_index: bpy.props.IntProperty( )

    def execute(self, context):
        context.scene.q_bp_bone_groups.remove( self.group_index )
        return {'FINISHED'}

class QANIM_OT_bone_pickup_single_add(bpy.types.Operator):
    bl_idname = "qanim.bone_pickup_single_add"
    bl_label = "追加"
    bl_options = {'REGISTER', 'UNDO'}
    bl_description = "Register Bone Pickup"

    group_index: bpy.props.IntProperty( )

    @classmethod
    def poll(cls, context):
        return (
            context.active_object
        and (
                ( context.selected_pose_bones_from_active_object and 0 < len( context.selected_pose_bones_from_active_object ) )
            or  ( context.selected_editable_bones and 0 < len( context.selected_editable_bones ) )
            )
        )

    def execute(self, context):
        group = context.scene.q_bp_bone_groups[self.group_index]
        group.high_light = False
        bones = context.selected_pose_bones_from_active_object if context.mode == "POSE" else context.selected_editable_bones

        for pb in bones:
            found = False
            for t in group.bones:
                if t.bone_name == pb.name:
                    found = True
                    break
            if found:
                continue

            bone = group.bones.add( )
            bone.bone_name = pb.name

        return {'FINISHED'}

class QANIM_OT_bone_pickup_single_delete(bpy.types.Operator):
    bl_idname = "qanim.bone_pickup_single_delete"
    bl_label = "削除"
    bl_options = {'REGISTER', 'UNDO'}
    bl_description = "Delete Single Bone From Group"

    group_index: bpy.props.IntProperty( )
    selected_item_index: bpy.props.IntProperty( )

    def execute(self, context):
        group = context.scene.q_bp_bone_groups[self.group_index]
        group.bones.remove( self.selected_item_index )
        group.high_light = False
        return {'FINISHED'}

class QANIM_OT_bone_pickup_save(bpy.types.Operator):
    bl_idname = "qanim.bone_pickup_save"
    bl_label = "書出"
    bl_options = {'REGISTER', 'UNDO'}
    bl_description = "Save Bone Group to JSON"

    json_path: bpy.props.StringProperty( )

    def execute(self, context):
        data = []
        for group in context.scene.q_bp_bone_groups:
            if not group.object or not group.object.q_bp_bone_group_export:
                continue

            data.append({
                "group_name": group.name
            ,   "object_name": group.object.name if group.object else ""
            ,   "bones": [t.bone_name for t in group.bones]
            })

        import json
        with open( self.json_path, 'w' ) as f:
            json.dump({
                "name": BONE_PICKUP_HEADER
            ,   "version": BONE_PICKUP_FILE_VERSION
            ,   "data": data
            }, f )

        return {'FINISHED'}

class QANIM_OT_bone_pickup_load(bpy.types.Operator):
    bl_idname = "qanim.bone_pickup_load"
    bl_label = "読込"
    bl_options = {'REGISTER', 'UNDO'}
    bl_description = "Load Bone Group from JSON"

    json_path: bpy.props.StringProperty( )

    def execute(self, context):
        import json
        try:
            with open( self.json_path, 'r' ) as f:
                all_data = json.load( f )
            if "data" in all_data and "name" in all_data and type( all_data["name"] ) is str:
                if all_data["name"] == BONE_PICKUP_HEADER:
                    data = all_data["data"]
                    version = all_data["version"]
                else:
                    self.report({"ERROR"}, "このJSONはBone Pickup用ではありません。")
                    raise Exception("error")
            else:
                # 旧バージョン(廃止予定)
                data = all_data
                version = 100
        except:
            return {'CANCELLED'}

        if version == 100:
            conved_data = []
            for name, bones in data.items( ):
                conved_data.append({
                    "group_name": name,
                    "object_name": "",
                    "bones": bones
                })
            data = conved_data

        for group_prop in data:
            group_name = group_prop["group_name"]
            bones = group_prop["bones"]
            obj_name = group_prop["object_name"]
            obj = bpy.data.objects[obj_name] if obj_name in bpy.data.objects else None

            group = None
            for t in context.scene.q_bp_bone_groups:
                if t.name == group_name:
                    group = t
                    break
            if not group:
                group = context.scene.q_bp_bone_groups.add( )
                group.object = obj
                group.name = group_name

            for bone_name in bones:
                found = False
                for t in group.bones:
                    if t.bone_name == bone_name:
                        found = True
                        break
                if not found:
                    new_bone = group.bones.add( )
                    new_bone.bone_name = bone_name

        return {'FINISHED'}

class QANIM_OT_bone_pickup_load_from_blend(bpy.types.Operator):
    bl_idname = "qanim.bone_pickup_load_from_blend"
    bl_label = "読込"
    bl_options = {'REGISTER', 'UNDO'}
    bl_description = "Load Bone Group from Blend file"

    blend_path: bpy.props.StringProperty( )

    def execute(self, context):
        import os
        if not os.path.exists( self.blend_path ):
            self.report({'ERROR'}, "%s というファイルは存在しません。" % self.blend_path )
            return {'CANCELLED'}

        import tempfile
        with tempfile.TemporaryDirectory() as dname:
            tmp_path = os.path.join( dname, "bone_group.txt" ).replace( "\\", "/" )
            import subprocess
            subprocess.run([
                "blender.exe"
            ,   "--background"
            ,   self.blend_path
            ,   "--python-expr", "import bpy; bpy.ops.qanim.bone_pickup_save( json_path= \"%s\" ); import sys; sys.exit( 0 )" % tmp_path
            ] )

            bpy.ops.qanim.bone_pickup_load( json_path= tmp_path )

        return {'FINISHED'}

class QANIM_OT_bone_pickup_select_path_import_json(bpy.types.Operator, ImportHelper):
    """
        JSONファイルパスを設定する
    """
    bl_idname = "qanim.bone_pickup_select_path_import_json"
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
        context.scene.q_bp_bone_group_import_json_path = self.filepath
        bpy.ops.wm.redraw_timer(type='DRAW_WIN_SWAP', iterations=1)
        return {'FINISHED'}

class QANIM_OT_bone_pickup_select_path_export_json(bpy.types.Operator, ExportHelper):
    """
        JSONファイルパスを設定する
    """
    bl_idname = "qanim.bone_pickup_select_path_export_json"
    bl_label = "Select JSON Path"
    bl_description = "Export a .json file"
    bl_options = {'REGISTER', 'UNDO'}

    filename_ext = ".json"
    filter_glob: bpy.props.StringProperty(
        default='*.json',
        options={'HIDDEN'}
    )

    def execute(self, context):
        context.scene.q_bp_bone_group_export_json_path = self.filepath
        bpy.ops.wm.redraw_timer(type='DRAW_WIN_SWAP', iterations=1)
        return {'FINISHED'}

class QANIM_OT_bone_pickup_select_path_blend(bpy.types.Operator, ImportHelper):
    """
        Blendファイルパスを設定する
    """
    bl_idname = "qanim.bone_pickup_select_path_blend"
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
        context.scene.q_bp_bone_group_input_blend_path = self.filepath
        bpy.ops.wm.redraw_timer(type='DRAW_WIN_SWAP', iterations=1)
        return {'FINISHED'}

class QANIM_OT_bone_pickup_copy_all(bpy.types.Operator):
    bl_idname = "qanim.bone_pickup_copy_all"
    bl_label = "コピー"
    bl_options = {'REGISTER', 'UNDO'}
    bl_description = "Bone Group Copy All with Object"

    from_object_name: bpy.props.StringProperty( )

    def execute(self, context):
        for group in context.scene.q_bp_bone_groups:
            if ( group.object and group.object.name != self.from_object_name ) or ( not group.object and self.from_object_name != "" ):
                continue

            new_group = context.scene.q_bp_bone_groups.add( )
            new_group.object = context.scene.q_bp_bone_group_copy_all_to_object
            new_group.name = group.name

            for t in group.bones:
                bone = new_group.bones.add( )
                bone.bone_name = t.bone_name

        return {'FINISHED'}

class QANIM_OT_bone_pickup_all_select(bpy.types.Operator):
    bl_idname = "qanim.bone_pickup_all_select"
    bl_label = "全て選択"
    bl_options = {'REGISTER', 'UNDO'}
    bl_description = "All Select Bones in Bone Group"

    group_index: bpy.props.IntProperty( )

    def execute(self, context):
        group = context.scene.q_bp_bone_groups[self.group_index]

        for bone in group.bones:
            bone.select = True

        return {'FINISHED'}

# -----------------------------------------------------------------------------

class QANIM_PT_bone_pickup(bpy.types.Panel):
    bl_label = "Bone Pickup"
    bl_idname = "QANIM_PT_bone_pickup"
    bl_space_type = "VIEW_3D"
    bl_region_type = "UI"
    bl_category = "Q_ANIM"
    bl_options = {'DEFAULT_CLOSED'}

    @classmethod
    def poll(cls, context):
        return (
                context.mode == 'EDIT_ARMATURE'
            or  context.mode == 'POSE'
        )

    def draw(self, context):
        layout = self.layout

        def indent( base ):
            col = base.column( )
            col.alignment = 'LEFT'
            col.label(text= "")

        row = layout.row( )
        col = row.column( )
        col.alignment = 'LEFT'
        col.operator( QANIM_OT_bone_pickup_register.bl_idname )
        col = row.column( )
        col.alignment = 'RIGHT'
        col.prop( context.scene, "q_bp_bone_group_search_name", text= "", icon= "VIEWZOOM")
        col = row.column( )
        col.alignment = 'RIGHT'
        col.prop( context.scene, "q_bp_bone_group_sort", text= "", icon= "SORTALPHA")

        row = layout.row( )
        col = row.column( )
        col.prop( context.scene, "q_bp_bone_group_edit_object_name", text= "アーマチュア変更モード" )

        o = context.active_object
        if not o:
            return
        # 存在確認のためだけに用意はしておく
        bones = o.data.bones if bpy.context.mode == "POSE" else o.data.edit_bones
        if not bones:
            return

        # 関連オブジェクトを収集
        sorted_object_names = list(set(group.object.name if group.object else "" for group in context.scene.q_bp_bone_groups))
        if context.scene.q_bp_bone_group_sort:
            sorted_object_names = sorted(sorted_object_names, key= lambda x: x )

        # オブジェクト
        box = layout.row( ).box( )
        for obj_name in sorted_object_names:
            if obj_name != "" and obj_name in bpy.data.objects:
                obj = bpy.data.objects[obj_name]
                inbox = box.box( )
                row = inbox.row( )
                col = row.column( )
                col.alignment = 'LEFT'
                col.prop(obj, "q_bp_bone_group_show", text= obj_name, icon="DISCLOSURE_TRI_DOWN" if obj.q_bp_bone_group_show else "DISCLOSURE_TRI_RIGHT", emboss= False)
                col = row.column( )
                if not obj.q_bp_bone_group_show:
                    continue
                sorted_groups = [t for t in context.scene.q_bp_bone_groups if t.object and t.object.name == obj_name]
                if context.scene.q_bp_bone_group_edit_object_name:
                    row = inbox.row( )
                    col = row.column( )
                    col.alignment = 'LEFT'
                    col.label(text= "")
                    col = row.column( )
                    col.prop( context.scene, "q_bp_bone_group_copy_all_to_object", text= "コピー先" )
                    col = row.column( )
                    col.alignment = 'RIGHT'
                    col.operator( QANIM_OT_bone_pickup_copy_all.bl_idname ).from_object_name = obj_name
            else:
                obj = None
                if not any( group.object is None for group in context.scene.q_bp_bone_groups ):
                    continue
                inbox = box.box( )
                row = inbox.row( )
                col = row.column( )
                col.alignment = 'LEFT'
                col.prop(context.scene, "q_bp_bone_group_show_no_armature", text= "どのアーマチュアにも紐付いていないグループ", icon="DISCLOSURE_TRI_DOWN" if context.scene.q_bp_bone_group_show_no_armature else "DISCLOSURE_TRI_RIGHT", emboss= False)
                col = row.column( )
                if not context.scene.q_bp_bone_group_show_no_armature:
                    continue
                sorted_groups = [t for t in context.scene.q_bp_bone_groups if t.object is None]

            # 検索
            if context.scene.q_bp_bone_group_search_name != "":
                for group in sorted_groups.copy():
                    if context.scene.q_bp_bone_group_search_name.lower( ) not in group.name.lower( ):
                        sorted_groups.remove( group )

            # グループ名でソート
            if context.scene.q_bp_bone_group_sort:
                sorted_groups = sorted(sorted_groups, key= lambda x: x.name )

            for group in sorted_groups:
                # グループID
                group_index = 0
                for t in context.scene.q_bp_bone_groups:
                    if t.as_pointer( ) == group.as_pointer( ):
                        break
                    group_index += 1

                row = inbox.row( )
                row.alert = group.high_light
                indent( row )
                col = row.column( )
                col.alignment = 'LEFT'
                col.prop(group, "show", icon_only= True, icon="DISCLOSURE_TRI_DOWN" if group.show else "DISCLOSURE_TRI_RIGHT", emboss= False)
                col = row.column( )
                col.prop(group, "ui_name", text= "")

                if group.show:
                    row = inbox.row( )
                    indent( row )
                    indent( row )
                    col = row.column( )
                    col.alignment = 'LEFT'
                    op = col.operator( QANIM_OT_bone_pickup_single_add.bl_idname )
                    op.group_index = group_index
                    col = row.column( )
                    col.alignment = 'LEFT'
                    op = col.operator( QANIM_OT_bone_pickup_copy.bl_idname )
                    op.group_index = group_index
                    col = row.column( )
                    col.alignment = 'LEFT'
                    op = col.operator( QANIM_OT_bone_pickup_mirror.bl_idname )
                    op.group_index = group_index
                    col = row.column( )
                    col.alignment = 'LEFT'
                    op = col.operator( QANIM_OT_bone_pickup_all_select.bl_idname )
                    op.group_index = group_index
                    col = row.column( )
                    col.alignment = 'LEFT'
                    op = col.operator( QANIM_OT_bone_pickup_delete.bl_idname )
                    op.group_index = group_index

                    if context.scene.q_bp_bone_group_edit_object_name:
                        row = inbox.row( )
                        indent( row )
                        indent( row )
                        col = row.column( )
                        col.prop( group, "object", text= "アーマチュア" )

                    index = 0
                    sorted_bones = [t for t in group.bones]
                    if context.scene.q_bp_bone_group_sort:
                        sorted_bones = sorted(sorted_bones, key= lambda x: x.bone_name )
                    
                    for t in sorted_bones:
                        row = inbox.row( )
                        indent( row )
                        indent( row )
                        col = row.column( )
                        col.alignment = 'LEFT'
                        if t.bone_name in bones:
                            col.prop(t, "select", text= t.bone_name)
                        else:
                            col.label(text= t.bone_name, icon= "ERROR")
                            #col.alert = True
                        col = row.column( )
                        col = row.column( )
                        col.alignment = 'RIGHT'
                        op = col.operator(QANIM_OT_bone_pickup_single_delete.bl_idname)
                        op.group_index = group_index
                        op.selected_item_index = index
                        index += 1
                else:
                    col = row.column( )

        row = layout.row( )
        row.prop(context.scene, "q_bp_bone_group_import_export", expand=True)
        row = layout.row( )

        if context.scene.q_bp_bone_group_import_export == "IMPORT":
            col = row.column( )
            col.prop(context.scene, "q_bp_bone_group_import_json_path", text="インポート元")
            col = row.column( )
            col.alignment = "RIGHT"
            col.operator(QANIM_OT_bone_pickup_select_path_import_json.bl_idname, text="", icon="FILE_FOLDER")
            col = row.column( )
            col.alignment = "RIGHT"
            col.operator( QANIM_OT_bone_pickup_load.bl_idname ).json_path = context.scene.q_bp_bone_group_import_json_path
        elif context.scene.q_bp_bone_group_import_export == "EXPORT":
            col = row.column( )
            col.prop(context.scene, "q_bp_bone_group_export_json_path", text="エクスポート先")
            col = row.column( )
            col.alignment = "RIGHT"
            col.operator(QANIM_OT_bone_pickup_select_path_export_json.bl_idname, text="", icon="FILE_FOLDER")
            col = row.column( )
            col.alignment = "RIGHT"
            col.operator( QANIM_OT_bone_pickup_save.bl_idname ).json_path = context.scene.q_bp_bone_group_export_json_path
            row = layout.row( )
            box = row.box( )
            box.label( text= "出力対象アーマチュア:" )
            founded = {}
            for g in context.scene.q_bp_bone_groups:
                if not g.object:
                    continue
                if g.object.name in founded:
                    continue
                founded[g.object.name] = True
                col = box.column( )
                col.prop(g.object, "q_bp_bone_group_export", text= g.object.name)
        elif context.scene.q_bp_bone_group_import_export == "BLEND":
            col = row.column( )
            col.prop(context.scene, "q_bp_bone_group_input_blend_path", text="Blendから読み込み")
            col = row.column( )
            col.alignment = "RIGHT"
            col.operator(QANIM_OT_bone_pickup_select_path_blend.bl_idname, text="", icon="FILE_FOLDER")
            col = row.column( )
            col.alignment = "RIGHT"
            col.operator( QANIM_OT_bone_pickup_load_from_blend.bl_idname ).blend_path = context.scene.q_bp_bone_group_input_blend_path

        global windows_mode
        if windows_mode:
            row = layout.row( )
            col = row.column( )
            col.prop(context.scene, "q_bp_bone_group_mode")

# -----------------------------------------------------------------------------

classes = (
    QANIM_SAVE_bone_pickup_single_bone,
    QANIM_SAVE_bone_pickup_group,
    QANIM_PT_bone_pickup,
    QANIM_OT_bone_pickup_register,
    QANIM_OT_bone_pickup_copy,
    QANIM_OT_bone_pickup_mirror,
    QANIM_OT_bone_pickup_delete,
    QANIM_OT_bone_pickup_single_add,
    QANIM_OT_bone_pickup_single_delete,
    QANIM_OT_bone_pickup_save,
    QANIM_OT_bone_pickup_load,
    QANIM_OT_bone_pickup_load_from_blend,
    QANIM_OT_bone_pickup_select_path_import_json,
    QANIM_OT_bone_pickup_select_path_export_json,
    QANIM_OT_bone_pickup_select_path_blend,
    QANIM_OT_bone_pickup_copy_all,
    QANIM_OT_bone_pickup_all_select,
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

    bpy.types.Object.q_bp_bone_group_show = bpy.props.BoolProperty(
        default= True,
        options= {'HIDDEN'},
        override= {'LIBRARY_OVERRIDABLE'},
    )
    bpy.types.Object.q_bp_bone_group_export = bpy.props.BoolProperty(
        default= True,
        options= {'HIDDEN'},
        override= {'LIBRARY_OVERRIDABLE'},
    )

    bpy.types.Scene.q_bp_bone_groups = bpy.props.CollectionProperty(
        name="Hyper Bone Selection Sets Group",
        type= QANIM_SAVE_bone_pickup_group,
        options={'HIDDEN'}
    )
    bpy.types.Scene.q_bp_bone_group_copy_all_to_object = bpy.props.PointerProperty( type= bpy.types.Object, poll= _filter_armature_object, options={'HIDDEN'} )
    bpy.types.Scene.q_bp_bone_group_search_name = bpy.props.StringProperty( options={'HIDDEN'} )
    bpy.types.Scene.q_bp_bone_group_sort = bpy.props.BoolProperty( default= True, options={'HIDDEN'} )
    bpy.types.Scene.q_bp_bone_group_edit_object_name = bpy.props.BoolProperty( default= False, options={'HIDDEN'} )
    bpy.types.Scene.q_bp_bone_group_show_no_armature = bpy.props.BoolProperty( default= True, options={'HIDDEN'} )
    bpy.types.Scene.q_bp_bone_group_input_blend_path = bpy.props.StringProperty( options={'HIDDEN'} )
    bpy.types.Scene.q_bp_bone_group_export_json_path = bpy.props.StringProperty( options={'HIDDEN'} )
    bpy.types.Scene.q_bp_bone_group_import_json_path = bpy.props.StringProperty( options={'HIDDEN'} )
    bpy.types.Scene.q_bp_bone_group_import_export = bpy.props.EnumProperty(
        name= "読み書きモード"
    ,   default= 'IMPORT'
    ,   options={'HIDDEN'}
    ,   items=(
            ('IMPORT', 'Import', 'インポートする'),
            ('EXPORT', 'Export', 'エクスポートする'),
            ('BLEND', 'Blend', 'Blendファイルから読み込む'),
        )
    )
    bpy.types.Scene.q_bp_bone_group_mode = bpy.props.EnumProperty(
        name= "モード"
    ,   default= 'DEFAULT' if windows_mode else 'BLENDER_CHECK'
    ,   options={'HIDDEN'}
    ,   items=(
            ('DEFAULT', 'デフォルト', '通常の選択と同じ挙動'),
            ('BLENDER_CHECK', 'Blenderチェック式', 'Blenderのチェックマークと同じ挙動'),
        )
    )

def _deinitialize( ):
    """
        後始末
    """
    del bpy.types.Object.q_bp_bone_group_show
    del bpy.types.Scene.q_bp_bone_groups
    del bpy.types.Scene.q_bp_bone_group_copy_all_to_object
    del bpy.types.Scene.q_bp_bone_group_search_name
    del bpy.types.Scene.q_bp_bone_group_sort
    del bpy.types.Scene.q_bp_bone_group_edit_object_name
    del bpy.types.Scene.q_bp_bone_group_show_no_armature
    del bpy.types.Scene.q_bp_bone_group_input_blend_path
    del bpy.types.Scene.q_bp_bone_group_import_json_path
    del bpy.types.Scene.q_bp_bone_group_export_json_path
    del bpy.types.Scene.q_bp_bone_group_import_export
    del bpy.types.Scene.q_bp_bone_group_mode
