bl_info = {
    "name": "VSE Image and Video Motion Library",
    "author": "ChatGPT",
    "version": (1, 6, 1),
    "blender": (5, 0, 0),
    "location": "Sequencer > Sidebar > Motion Lib",
    "description": "Motion tools for VSE with per-animation sound selector",
    "category": "Sequencer",
}

import bpy
import os
import random


# =========================
# Sound Helpers
# =========================

ANIM_SOUND_KEYS = {
    "a01": "zoom_in",
    "a02": "zoom_out",
    "a03": "fade_in",
    "a04": "fade_out",
    "a09": "rotate_r",
    "a10": "rotate_l",
    "a11": "bounce_zoom",
    "a12": "pulse",
    "a18": "slow_in",
    "a19": "slow_out",
    "a20": "fast_in",
    "a21": "fast_out",
    "a23": "blink",
    "a24": "ultra_zoom",
}

SOUND_EXTS = (".wav", ".mp3", ".ogg", ".flac", ".aac", ".m4a")


def _sound_prop(prefix, suffix):
    return f"{prefix}_sound_{suffix}"


def register_sound_props():
    for prefix in ANIM_SOUND_KEYS:
        setattr(
            bpy.types.Scene,
            _sound_prop(prefix, "mode"),
            bpy.props.EnumProperty(
                name="Sound Mode",
                items=[
                    ('NONE', "No Sound", ""),
                    ('FILE', "Single File", ""),
                    ('FOLDER', "Folder", ""),
                ],
                default='NONE',
            )
        )

        setattr(
            bpy.types.Scene,
            _sound_prop(prefix, "file"),
            bpy.props.StringProperty(
                name="Sound File",
                subtype='FILE_PATH',
                default="",
            )
        )

        setattr(
            bpy.types.Scene,
            _sound_prop(prefix, "folder"),
            bpy.props.StringProperty(
                name="Sound Folder",
                subtype='DIR_PATH',
                default="",
            )
        )

        setattr(
            bpy.types.Scene,
            _sound_prop(prefix, "ui_open"),
            bpy.props.BoolProperty(
                name="Show Sound Settings",
                default=False,
            )
        )


def unregister_sound_props():
    for prefix in ANIM_SOUND_KEYS:
        for suffix in ("mode", "file", "folder", "ui_open"):
            prop_name = _sound_prop(prefix, suffix)
            if hasattr(bpy.types.Scene, prop_name):
                delattr(bpy.types.Scene, prop_name)


def _find_folder_sound(folder_path, sound_key):
    if not folder_path or not os.path.isdir(folder_path):
        return None

    folder = os.path.abspath(folder_path)
    sound_key = sound_key.lower().strip()

    for ext in SOUND_EXTS:
        candidate = os.path.join(folder, sound_key + ext)
        if os.path.isfile(candidate):
            return candidate

    files = [
        os.path.join(folder, f)
        for f in os.listdir(folder)
        if os.path.isfile(os.path.join(folder, f))
        and f.lower().endswith(SOUND_EXTS)
    ]

    if not files:
        return None

    return random.choice(files)


def play_motion_sound(context, anim_prefix):
    scene = context.scene
    sound_key = ANIM_SOUND_KEYS.get(anim_prefix)

    if not sound_key:
        return False

    mode = getattr(scene, _sound_prop(anim_prefix, "mode"), 'NONE')

    if mode == 'NONE':
        return False

    filepath = None

    if mode == 'FILE':
        filepath = bpy.path.abspath(getattr(scene, _sound_prop(anim_prefix, "file"), ""))
        if not filepath or not os.path.isfile(filepath):
            return False

    elif mode == 'FOLDER':
        folder = bpy.path.abspath(getattr(scene, _sound_prop(anim_prefix, "folder"), ""))
        filepath = _find_folder_sound(folder, sound_key)
        if not filepath:
            return False

    else:
        return False

    if scene.sequence_editor is None:
        scene.sequence_editor_create()

    try:
        bpy.ops.sequencer.sound_strip_add(
            filepath=filepath,
            frame_start=scene.frame_current,
            channel=5,
        )
        return True
    except Exception:
        return False


# =========================
# Helpers
# =========================

def get_strip(context):
    scene = context.scene
    if not scene.sequence_editor:
        return None
    return scene.sequence_editor.active_strip


def require_strip(self, context, allowed_types=None):
    strip = get_strip(context)

    if not strip:
        self.report({'WARNING'}, "No active strip")
        return None

    if allowed_types and strip.type not in allowed_types:
        self.report({'WARNING'}, f"Unsupported strip type: {strip.type}")
        return None

    return strip


def _apply_keyframes(rna, prop, a, b, f1, f2):
    setattr(rna, prop, a)
    rna.keyframe_insert(data_path=prop, frame=f1)
    setattr(rna, prop, b)
    rna.keyframe_insert(data_path=prop, frame=f2)


def _find_prop_target(strip, candidates):
    targets = []
    if hasattr(strip, "transform") and strip.transform:
        targets.append(strip.transform)
    targets.append(strip)

    for t in targets:
        for p in candidates:
            if hasattr(t, p):
                return t, p
    return None, None


def _kf_any(strip, candidates, a, b, f1, f2):
    target, prop = _find_prop_target(strip, candidates)
    if not target:
        return False
    _apply_keyframes(target, prop, a, b, f1, f2)
    return True


def kf_scale_x(s, a, b, f1, f2):
    return _kf_any(s, ("scale_x", "scale_start_x"), a, b, f1, f2)


def kf_scale_y(s, a, b, f1, f2):
    return _kf_any(s, ("scale_y", "scale_start_y"), a, b, f1, f2)


def kf_rotation(s, a, b, f1, f2):
    return _kf_any(s, ("rotation", "rotation_start"), a, b, f1, f2)


def kf_alpha(s, a, b, f1, f2):
    return _kf_any(s, ("blend_alpha",), a, b, f1, f2)


def finish(op, ok):
    if not ok:
        op.report({'WARNING'}, "Animation failed")
        return {'CANCELLED'}
    return {'FINISHED'}


# =========================
# UI
# =========================

def draw_anim_sound(layout, scene, prefix, operator_id, operator_text):
    box = layout.box()

    row = box.row(align=True)
    row.scale_y = 1.25

    prop_name = _sound_prop(prefix, "ui_open")
    is_open = getattr(scene, prop_name)

    row.prop(
        scene,
        prop_name,
        text="",
        icon='TRIA_DOWN' if is_open else 'TRIA_RIGHT',
        emboss=False
    )

    btn = row.row(align=True)
    btn.scale_x = 1.55
    btn.scale_y = 1.15
    btn.operator(operator_id, text=operator_text)

    if is_open:
        sub = box.column(align=True)
        sub.use_property_split = True
        sub.use_property_decorate = False
        sub.separator(factor=0.2)

        mode_row = sub.row(align=True)
        mode_row.prop(scene, _sound_prop(prefix, "mode"), text="Sound Mode")

        mode = getattr(scene, _sound_prop(prefix, "mode"), 'NONE')

        if mode == 'FILE':
            sub.prop(scene, _sound_prop(prefix, "file"), text="Sound File")
        elif mode == 'FOLDER':
            sub.prop(scene, _sound_prop(prefix, "folder"), text="Sound Folder")
        else:
            sub.label(text="Choose File or Folder to show sound settings")


def draw_category_box(layout, title, items, scene):
    box = layout.box()
    head = box.row(align=True)
    head.label(text=title)

    col = box.column(align=True)
    col.scale_y = 1.0

    for prefix, operator_id, operator_text in items:
        draw_anim_sound(col, scene, prefix, operator_id, operator_text)

# =========================
# ANIMATIONS
# =========================

class VSE_OT_a01(bpy.types.Operator):
    bl_idname = "vse.a01"
    bl_label = "Zoom In"
    def execute(self, context):
        s = require_strip(self, context, {'IMAGE','MOVIE','TEXT'})
        if not s: return {'CANCELLED'}
        f = context.scene.frame_current
        ok = kf_scale_x(s,1,1.4,f,f+20) and kf_scale_y(s,1,1.4,f,f+20)
        if ok:
            play_motion_sound(context, "a01")
        return finish(self, ok)


class VSE_OT_a02(bpy.types.Operator):
    bl_idname = "vse.a02"
    bl_label = "Zoom Out"
    def execute(self, context):
        s = require_strip(self, context, {'IMAGE','MOVIE','TEXT'})
        if not s: return {'CANCELLED'}
        f = context.scene.frame_current
        ok = kf_scale_x(s,1.4,1,f,f+20) and kf_scale_y(s,1.4,1,f,f+20)
        if ok:
            play_motion_sound(context, "a02")
        return finish(self, ok)


class VSE_OT_a03(bpy.types.Operator):
    bl_idname = "vse.a03"
    bl_label = "Fade In"
    def execute(self, context):
        s = require_strip(self, context, {'IMAGE','MOVIE','TEXT'})
        if not s: return {'CANCELLED'}
        f = context.scene.frame_current
        ok = kf_alpha(s,0,1,f,f+20)
        if ok:
            play_motion_sound(context, "a03")
        return finish(self, ok)


class VSE_OT_a04(bpy.types.Operator):
    bl_idname = "vse.a04"
    bl_label = "Fade Out"
    def execute(self, context):
        s = require_strip(self, context, {'IMAGE','MOVIE','TEXT'})
        if not s: return {'CANCELLED'}
        f = context.scene.frame_current
        ok = kf_alpha(s,1,0,f,f+20)
        if ok:
            play_motion_sound(context, "a04")
        return finish(self, ok)


class VSE_OT_a09(bpy.types.Operator):
    bl_idname = "vse.a09"
    bl_label = "Rotate R"
    def execute(self, context):
        s = require_strip(self, context, {'IMAGE','MOVIE','TEXT'})
        if not s: return {'CANCELLED'}
        f = context.scene.frame_current
        ok = kf_rotation(s,-0.5,0,f,f+20)
        if ok:
            play_motion_sound(context, "a09")
        return finish(self, ok)


class VSE_OT_a10(bpy.types.Operator):
    bl_idname = "vse.a10"
    bl_label = "Rotate L"
    def execute(self, context):
        s = require_strip(self, context, {'IMAGE','MOVIE','TEXT'})
        if not s: return {'CANCELLED'}
        f = context.scene.frame_current
        ok = kf_rotation(s,0.5,0,f,f+20)
        if ok:
            play_motion_sound(context, "a10")
        return finish(self, ok)


class VSE_OT_a11(bpy.types.Operator):
    bl_idname = "vse.a11"
    bl_label = "Bounce Zoom"
    def execute(self, context):
        s = require_strip(self, context, {'IMAGE','MOVIE','TEXT'})
        if not s: return {'CANCELLED'}
        f = context.scene.frame_current
        ok = (
            kf_scale_x(s,1,1.6,f,f+10) and
            kf_scale_x(s,1.6,1.2,f+10,f+20) and
            kf_scale_y(s,1,1.6,f,f+10) and
            kf_scale_y(s,1.6,1.2,f+10,f+20)
        )
        if ok:
            play_motion_sound(context, "a11")
        return finish(self, ok)


class VSE_OT_a12(bpy.types.Operator):
    bl_idname = "vse.a12"
    bl_label = "Pulse"
    def execute(self, context):
        s = require_strip(self, context, {'IMAGE','MOVIE','TEXT'})
        if not s: return {'CANCELLED'}
        f = context.scene.frame_current
        ok = (
            kf_scale_x(s,1,1.2,f,f+10) and
            kf_scale_x(s,1.2,1,f+10,f+20) and
            kf_scale_y(s,1,1.2,f,f+10) and
            kf_scale_y(s,1.2,1,f+10,f+20)
        )
        if ok:
            play_motion_sound(context, "a12")
        return finish(self, ok)


class VSE_OT_a18(bpy.types.Operator):
    bl_idname = "vse.a18"
    bl_label = "Slow In"
    def execute(self, context):
        s = require_strip(self, context, {'IMAGE','MOVIE','TEXT'})
        if not s: return {'CANCELLED'}
        f = context.scene.frame_current
        ok = kf_scale_x(s,1,1.3,f,f+40)
        if ok:
            play_motion_sound(context, "a18")
        return finish(self, ok)


class VSE_OT_a19(bpy.types.Operator):
    bl_idname = "vse.a19"
    bl_label = "Slow Out"
    def execute(self, context):
        s = require_strip(self, context, {'IMAGE','MOVIE','TEXT'})
        if not s: return {'CANCELLED'}
        f = context.scene.frame_current
        ok = kf_scale_x(s,1.3,1,f,f+40)
        if ok:
            play_motion_sound(context, "a19")
        return finish(self, ok)


class VSE_OT_a20(bpy.types.Operator):
    bl_idname = "vse.a20"
    bl_label = "Fast In"
    def execute(self, context):
        s = require_strip(self, context, {'IMAGE','MOVIE','TEXT'})
        if not s: return {'CANCELLED'}
        f = context.scene.frame_current
        ok = kf_scale_x(s,1,1.5,f,f+10)
        if ok:
            play_motion_sound(context, "a20")
        return finish(self, ok)


class VSE_OT_a21(bpy.types.Operator):
    bl_idname = "vse.a21"
    bl_label = "Fast Out"
    def execute(self, context):
        s = require_strip(self, context, {'IMAGE','MOVIE','TEXT'})
        if not s: return {'CANCELLED'}
        f = context.scene.frame_current
        ok = kf_scale_x(s,1.5,1,f,f+10)
        if ok:
            play_motion_sound(context, "a21")
        return finish(self, ok)


class VSE_OT_a23(bpy.types.Operator):
    bl_idname = "vse.a23"
    bl_label = "Blink"
    def execute(self, context):
        s = require_strip(self, context, {'IMAGE','MOVIE','TEXT'})
        if not s: return {'CANCELLED'}
        f = context.scene.frame_current
        ok = kf_alpha(s,1,0,f,f+5) and kf_alpha(s,0,1,f+5,f+10)
        if ok:
            play_motion_sound(context, "a23")
        return finish(self, ok)


class VSE_OT_a24(bpy.types.Operator):
    bl_idname = "vse.a24"
    bl_label = "Ultra Zoom"
    def execute(self, context):
        s = require_strip(self, context, {'IMAGE','MOVIE','TEXT'})
        if not s: return {'CANCELLED'}
        f = context.scene.frame_current
        ok = kf_scale_x(s,1,2,f,f+15) and kf_scale_y(s,1,2,f,f+15)
        if ok:
            play_motion_sound(context, "a24")
        return finish(self, ok)


# =========================
# UI PANEL
# =========================

class VSE_PT_motion_lib(bpy.types.Panel):
    bl_label = "🎬 Motion Library"
    bl_space_type = 'SEQUENCE_EDITOR'
    bl_region_type = 'UI'
    bl_category = "Motion Lib"

    def draw(self, context):
        layout = self.layout
        scene = context.scene

        layout.use_property_split = False
        layout.use_property_decorate = False

        header = layout.box()
        col = header.column(align=True)
        col.scale_y = 1.1
        col.label(text="VSE Image Motion Library")
        col.label(text="Fast motion tools with optional sound per animation")

        layout.separator(factor=0.5)

        draw_category_box(layout, "Zoom", [
            ("a01", "vse.a01", "Zoom In"),
            ("a02", "vse.a02", "Zoom Out"),
            ("a11", "vse.a11", "Bounce Zoom"),
            ("a12", "vse.a12", "Pulse"),
            ("a24", "vse.a24", "Ultra Zoom"),
        ], scene)

        draw_category_box(layout, "Fade", [
            ("a03", "vse.a03", "Fade In"),
            ("a04", "vse.a04", "Fade Out"),
            ("a23", "vse.a23", "Blink"),
        ], scene)

        draw_category_box(layout, "Rotation", [
            ("a09", "vse.a09", "Rotate R"),
            ("a10", "vse.a10", "Rotate L"),
        ], scene)

        draw_category_box(layout, "Speed", [
            ("a18", "vse.a18", "Slow In"),
            ("a19", "vse.a19", "Slow Out"),
            ("a20", "vse.a20", "Fast In"),
            ("a21", "vse.a21", "Fast Out"),
        ], scene)

# =========================
# REGISTER
# =========================

classes = [
    VSE_OT_a01, VSE_OT_a02, VSE_OT_a03, VSE_OT_a04,
    VSE_OT_a09, VSE_OT_a10, VSE_OT_a11, VSE_OT_a12,
    VSE_OT_a18, VSE_OT_a19, VSE_OT_a20, VSE_OT_a21,
    VSE_OT_a23, VSE_OT_a24,
    VSE_PT_motion_lib,
]


def register():
    for c in classes:
        bpy.utils.register_class(c)
    register_sound_props()


def unregister():
    unregister_sound_props()
    for c in reversed(classes):
        bpy.utils.unregister_class(c)


if __name__ == "__main__":
    register()