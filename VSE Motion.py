bl_info = {
    "name": "VSE Motion Library",
    "author": "ChatGPT",
    "version": (1, 8, 13),
    "blender": (5, 0, 0),
    "location": "Sequencer > Sidebar > VSE Motion",
    "description": "Motion tools for VSE with per-animation sound selector, sound-length match, and repeat controls",
    "category": "Sequencer",
}

import bpy
import os


# =========================
# Sound Helpers
# =========================

ANIM_SOUND_KEYS = {
    "a03": "fade_in",
    "a04": "fade_out",
    "a05": "slide_left",
    "a06": "slide_right",
    "a07": "slide_down",
    "a08": "pop_in",
    "a09": "rotate_r",
    "a10": "rotate_l",
    "a12": "pulse",
    "a13": "shake",
    "a14": "wobble",
    "a18": "slow_in",
    "a19": "slow_out",
    "a23": "blink",
    "a25": "move_up",
}

SOUND_EXTS = (".wav", ".mp3", ".ogg", ".flac", ".aac", ".m4a")

REPEATABLE_PREFIXES = {
    "a05", "a06", "a07", "a08",
    "a09", "a10", "a12", "a13",
    "a14", "a18", "a19", "a23", "a25",
}

REPEAT_GAP = 20

REPEAT_DURATIONS = {
    "a05": 20,
    "a06": 20,
    "a07": 20,
    "a08": 20,
    "a09": 20,
    "a10": 20,
    "a12": 20,
    "a13": 20,
    "a14": 20,
    "a18": 40,
    "a19": 40,
    "a23": 10,
    "a25": 20,
}


def _sound_prop(prefix, suffix):
    return f"{prefix}_sound_{suffix}"


def _repeat_prop(prefix, suffix):
    return f"{prefix}_repeat_{suffix}"


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


def register_repeat_props():
    for prefix in REPEATABLE_PREFIXES:
        setattr(
            bpy.types.Scene,
            _repeat_prop(prefix, "ui_open"),
            bpy.props.BoolProperty(
                name="Show Repeat Settings",
                default=False,
            )
        )
        setattr(
            bpy.types.Scene,
            _repeat_prop(prefix, "count"),
            bpy.props.IntProperty(
                name="Repeat Count",
                default=2,
                min=1,
                max=999,
            )
        )
        setattr(
            bpy.types.Scene,
            _repeat_prop(prefix, "infinite"),
            bpy.props.BoolProperty(
                name="Infinite Repeat",
                default=False,
            )
        )


def unregister_repeat_props():
    for prefix in REPEATABLE_PREFIXES:
        for suffix in ("ui_open", "count", "infinite"):
            prop_name = _repeat_prop(prefix, suffix)
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

    candidates = []
    for f in os.listdir(folder):
        full = os.path.join(folder, f)
        if not os.path.isfile(full):
            continue
        lower = f.lower()
        if not lower.endswith(SOUND_EXTS):
            continue

        stem, _ext = os.path.splitext(lower)
        if stem == sound_key or stem.startswith(sound_key + "_") or stem.startswith(sound_key + "-"):
            candidates.append(full)

    if len(candidates) == 1:
        return candidates[0]

    if len(candidates) > 1:
        candidates.sort()
        return candidates[0]

    return None


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
        channel = 1
        seqs = getattr(scene.sequence_editor, "sequences", None)

        if seqs is None:
            seqs = getattr(scene.sequence_editor, "strips", [])

        if seqs:
            for seq in seqs:
                if seq.channel >= channel:
                    channel = seq.channel + 1

        bpy.ops.sequencer.sound_strip_add(
            filepath=filepath,
            frame_start=scene.frame_current,
            channel=channel,
        )
        return True
    except Exception:
        return False


def _sound_filepath_for_prefix(scene, prefix):
    sound_key = ANIM_SOUND_KEYS.get(prefix)
    if not sound_key:
        return None

    mode = getattr(scene, _sound_prop(prefix, "mode"), 'NONE')

    if mode == 'FILE':
        filepath = bpy.path.abspath(getattr(scene, _sound_prop(prefix, "file"), ""))
        return filepath if filepath and os.path.isfile(filepath) else None

    if mode == 'FOLDER':
        folder = bpy.path.abspath(getattr(scene, _sound_prop(prefix, "folder"), ""))
        return _find_folder_sound(folder, sound_key)

    return None


def _measure_sound_frames(scene, filepath):
    if not filepath or not os.path.isfile(filepath):
        return None

    if scene.sequence_editor is None:
        scene.sequence_editor_create()

    seq_editor = scene.sequence_editor

    seqs = getattr(seq_editor, "sequences", None)
    if seqs is None:
        seqs = getattr(seq_editor, "strips", None)

    if seqs is None:
        return None

    used_channels = {s.channel for s in seqs}
    channel = 1
    while channel in used_channels and channel < 128:
        channel += 1
    channel = min(channel, 128)

    temp_name = "__VSE_TEMP_SOUND_LENGTH__"

    temp = seqs.new_sound(temp_name, filepath, channel, scene.frame_current)

    try:
        return max(1, int(round(temp.frame_final_duration)))
    finally:
        try:
            seqs.remove(temp)
        except Exception:
            pass


def _sound_duration_frames(scene, prefix):
    filepath = _sound_filepath_for_prefix(scene, prefix)
    if not filepath:
        return None
    return _measure_sound_frames(scene, filepath)


def _scale_points(base_frame, points, original_total, target_total):
    if not target_total or original_total <= 0:
        return [(base_frame + offset, value) for offset, value in points]

    scale = float(target_total) / float(original_total)
    out = []

    for offset, value in points:
        frame = base_frame + int(round(offset * scale))
        if out and frame <= out[-1][0]:
            frame = out[-1][0] + 1
        out.append((frame, value))

    return out


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
        if self and hasattr(self, "report"):
            self.report({'WARNING'}, "No active strip")
        return None

    if allowed_types and strip.type not in allowed_types:
        if self and hasattr(self, "report"):
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


def _current_value(strip, candidates, default=0.0):
    target, prop = _find_prop_target(strip, candidates)
    if not target or not prop:
        return default, None, None

    try:
        return float(getattr(target, prop)), target, prop
    except Exception:
        return default, None, None


def _base_value(base_values, key, strip, candidates, default=0.0):
    if base_values and key in base_values:
        try:
            return float(base_values[key])
        except Exception:
            return default

    value, _, _ = _current_value(strip, candidates, default)
    return value


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


def kf_move_x(s, a, b, f1, f2):
    return _kf_any(s, ("offset_x", "location_x"), a, b, f1, f2)


def kf_move_y(s, a, b, f1, f2):
    return _kf_any(s, ("offset_y", "location_y"), a, b, f1, f2)


def kf_multi_any(strip, candidates, points):
    target, prop = _find_prop_target(strip, candidates)
    if not target:
        return False

    for frame, value in points:
        setattr(target, prop, value)
        target.keyframe_insert(data_path=prop, frame=frame)

    return True


def finish(op, ok):
    if not ok:
        op.report({'WARNING'}, "Animation failed")
        return {'CANCELLED'}
    return {'FINISHED'}


# =========================
# Motion Logic
# =========================

def run_motion(anim_prefix, context, play_sound=True, reporter=None, base_values=None, target_duration=None):
    scene = context.scene
    strip = require_strip(reporter, context, {'IMAGE', 'MOVIE', 'TEXT', 'COLOR'})
    if not strip:
        return False

    f = scene.frame_current
    ok = False
    dur = int(target_duration) if target_duration else None

    if anim_prefix == "a03":
        base_alpha = _base_value(base_values, ("blend_alpha",), strip, ("blend_alpha",), 0.0)
        ok = kf_alpha(strip, base_alpha, 1.0, f, f + (dur or 20))

    elif anim_prefix == "a04":
        base_alpha = _base_value(base_values, ("blend_alpha",), strip, ("blend_alpha",), 1.0)
        ok = kf_alpha(strip, base_alpha, 0.0, f, f + (dur or 20))

    elif anim_prefix == "a05":
        base_x = _base_value(base_values, ("offset_x", "location_x"), strip, ("offset_x", "location_x"), 0.0)
        ok = _kf_any(strip, ("offset_x", "location_x"), base_x, base_x - 400.0, f, f + (dur or 20))

    elif anim_prefix == "a06":
        base_x = _base_value(base_values, ("offset_x", "location_x"), strip, ("offset_x", "location_x"), 0.0)
        ok = _kf_any(strip, ("offset_x", "location_x"), base_x, base_x + 400.0, f, f + (dur or 20))

    elif anim_prefix == "a07":
        base_y = _base_value(base_values, ("offset_y", "location_y"), strip, ("offset_y", "location_y"), 0.0)
        ok = _kf_any(strip, ("offset_y", "location_y"), base_y, base_y - 250.0, f, f + (dur or 20))

    elif anim_prefix == "a08":
        base_sx = _base_value(base_values, ("scale_x", "scale_start_x"), strip, ("scale_x", "scale_start_x"), 1.0)
        base_sy = _base_value(base_values, ("scale_y", "scale_start_y"), strip, ("scale_y", "scale_start_y"), 1.0)
        total = dur or 20
        ok = (
            _kf_any(strip, ("scale_x", "scale_start_x"), max(0.01, base_sx - 0.15), base_sx, f, f + total) and
            _kf_any(strip, ("scale_y", "scale_start_y"), max(0.01, base_sy - 0.15), base_sy, f, f + total)
        )

    elif anim_prefix == "a09":
        base_rot = _base_value(base_values, ("rotation", "rotation_start"), strip, ("rotation", "rotation_start"), 0.0)
        ok = _kf_any(strip, ("rotation", "rotation_start"), base_rot, base_rot - 0.35, f, f + (dur or 20))

    elif anim_prefix == "a10":
        base_rot = _base_value(base_values, ("rotation", "rotation_start"), strip, ("rotation", "rotation_start"), 0.0)
        ok = _kf_any(strip, ("rotation", "rotation_start"), base_rot, base_rot + 0.35, f, f + (dur or 20))

    elif anim_prefix == "a12":
        base_sx = _base_value(base_values, ("scale_x", "scale_start_x"), strip, ("scale_x", "scale_start_x"), 1.0)
        base_sy = _base_value(base_values, ("scale_y", "scale_start_y"), strip, ("scale_y", "scale_start_y"), 1.0)
        total = dur or 20
        points_x = _scale_points(f, [
            (0, base_sx),
            (10, max(0.01, base_sx + 0.10)),
            (20, max(0.01, base_sx)),
        ], 20, total)
        points_y = _scale_points(f, [
            (0, base_sy),
            (10, max(0.01, base_sy + 0.10)),
            (20, max(0.01, base_sy)),
        ], 20, total)

        ok = (
            kf_multi_any(strip, ("scale_x", "scale_start_x"), points_x) and
            kf_multi_any(strip, ("scale_y", "scale_start_y"), points_y)
        )

    elif anim_prefix == "a13":
        base_x = _base_value(base_values, ("offset_x", "location_x"), strip, ("offset_x", "location_x"), 0.0)
        total = dur or 20
        ok = kf_multi_any(strip, ("offset_x", "location_x"), _scale_points(f, [
            (0, base_x),
            (4, base_x - 25.0),
            (8, base_x + 25.0),
            (12, base_x - 14.0),
            (16, base_x + 14.0),
            (20, base_x),
        ], 20, total))

    elif anim_prefix == "a14":
        base_rot = _base_value(base_values, ("rotation", "rotation_start"), strip, ("rotation", "rotation_start"), 0.0)
        total = dur or 20
        ok = kf_multi_any(strip, ("rotation", "rotation_start"), _scale_points(f, [
            (0, base_rot),
            (5, base_rot - 0.12),
            (10, base_rot + 0.12),
            (15, base_rot - 0.05),
            (20, base_rot),
        ], 20, total))

    elif anim_prefix == "a18":
        base_sx = _base_value(base_values, ("scale_x", "scale_start_x"), strip, ("scale_x", "scale_start_x"), 1.0)
        base_sy = _base_value(base_values, ("scale_y", "scale_start_y"), strip, ("scale_y", "scale_start_y"), 1.0)
        ok = (
            _kf_any(strip, ("scale_x", "scale_start_x"), max(0.01, base_sx), max(0.01, base_sx + 0.25), f, f + (dur or 40)) and
            _kf_any(strip, ("scale_y", "scale_start_y"), max(0.01, base_sy), max(0.01, base_sy + 0.25), f, f + (dur or 40))
        )

    elif anim_prefix == "a19":
        base_sx = _base_value(base_values, ("scale_x", "scale_start_x"), strip, ("scale_x", "scale_start_x"), 1.0)
        base_sy = _base_value(base_values, ("scale_y", "scale_start_y"), strip, ("scale_y", "scale_start_y"), 1.0)
        ok = (
            _kf_any(strip, ("scale_x", "scale_start_x"), max(0.01, base_sx + 0.25), max(0.01, base_sx), f, f + (dur or 40)) and
            _kf_any(strip, ("scale_y", "scale_start_y"), max(0.01, base_sy + 0.25), max(0.01, base_sy), f, f + (dur or 40))
        )

    elif anim_prefix == "a23":
        base_alpha = _base_value(base_values, ("blend_alpha",), strip, ("blend_alpha",), 1.0)
        peak = 1.0 if base_alpha < 0.5 else base_alpha
        half = (dur or 10) // 2
        ok = kf_alpha(strip, peak, 0.0, f, f + half) and kf_alpha(strip, 0.0, peak, f + half, f + (dur or 10))

    elif anim_prefix == "a25":
        base_y = _base_value(base_values, ("offset_y", "location_y"), strip, ("offset_y", "location_y"), 0.0)
        ok = _kf_any(strip, ("offset_y", "location_y"), base_y, base_y + 260.0, f, f + (dur or 20))

    if ok and play_sound:
        play_motion_sound(context, anim_prefix)

    return ok


# =========================
# Repeat Helpers
# =========================

def _repeat_duration(prefix):
    return REPEAT_DURATIONS.get(prefix, 20)


def _repeat_step(prefix):
    return _repeat_duration(prefix) + REPEAT_GAP


def _snapshot_motion_values(strip):
    snapshot = {}
    props = [
        ("scale_x", "scale_start_x"),
        ("scale_y", "scale_start_y"),
        ("rotation", "rotation_start"),
        ("blend_alpha",),
        ("offset_x", "location_x"),
        ("offset_y", "location_y"),
    ]

    for candidates in props:
        target, prop = _find_prop_target(strip, candidates)
        if target and prop:
            try:
                snapshot[candidates] = float(getattr(target, prop))
            except Exception:
                pass

    return snapshot


def _restore_motion_values(strip, snapshot):
    for candidates, value in snapshot.items():
        target, prop = _find_prop_target(strip, candidates)
        if target and prop:
            try:
                setattr(target, prop, value)
            except Exception:
                pass


def _repeat_cycle(op, context, anim_prefix, cycle_frame, base_values):
    scene = context.scene
    scene.frame_set(cycle_frame)
    return run_motion(anim_prefix, context, play_sound=False, reporter=op, base_values=base_values)


def _repeat_motion_exec(op, context, anim_prefix):
    if anim_prefix not in REPEATABLE_PREFIXES:
        op.report({'WARNING'}, "This animation is not repeatable")
        return False

    scene = context.scene
    strip = require_strip(op, context, {'IMAGE', 'MOVIE', 'TEXT', 'COLOR'})
    if not strip:
        return False

    count = getattr(scene, _repeat_prop(anim_prefix, "count"), 2)
    infinite = getattr(scene, _repeat_prop(anim_prefix, "infinite"), False)

    step = _repeat_step(anim_prefix)
    start_frame = scene.frame_current
    strip_end = strip.frame_final_end

    mode_prop = _sound_prop(anim_prefix, "mode")
    old_mode = getattr(scene, mode_prop, 'NONE')

    snapshot = _snapshot_motion_values(strip)
    setattr(scene, mode_prop, 'NONE')

    try:
        i = 0
        cycle_frame = start_frame

        while True:
            if not infinite and i >= int(count):
                break

            if infinite:
                if cycle_frame + _repeat_duration(anim_prefix) > strip_end:
                    break

            _restore_motion_values(strip, snapshot)

            ok = _repeat_cycle(op, context, anim_prefix, cycle_frame, snapshot)
            if not ok:
                return False

            i += 1
            cycle_frame = start_frame + (i * step)

    finally:
        setattr(scene, mode_prop, old_mode)
        scene.frame_set(start_frame)

    return True


# =========================
# UI Operators
# =========================

class VSE_OT_toggle_sound_ui(bpy.types.Operator):
    bl_idname = "vse.toggle_sound_ui"
    bl_label = "Toggle Sound Settings"
    bl_options = {'REGISTER', 'UNDO'}

    anim_prefix: bpy.props.StringProperty()

    def execute(self, context):
        scene = context.scene
        prop_name = _sound_prop(self.anim_prefix, "ui_open")

        if not hasattr(scene, prop_name):
            self.report({'WARNING'}, "Sound UI property not found")
            return {'CANCELLED'}

        current = getattr(scene, prop_name)
        setattr(scene, prop_name, not current)
        return {'FINISHED'}


class VSE_OT_toggle_repeat_ui(bpy.types.Operator):
    bl_idname = "vse.toggle_repeat_ui"
    bl_label = "Toggle Repeat Settings"
    bl_options = {'REGISTER', 'UNDO'}

    anim_prefix: bpy.props.StringProperty()

    def execute(self, context):
        if self.anim_prefix not in REPEATABLE_PREFIXES:
            self.report({'WARNING'}, "Repeat is disabled for this animation")
            return {'CANCELLED'}

        scene = context.scene
        prop_name = _repeat_prop(self.anim_prefix, "ui_open")

        if not hasattr(scene, prop_name):
            self.report({'WARNING'}, "Repeat UI property not found")
            return {'CANCELLED'}

        current = getattr(scene, prop_name)
        setattr(scene, prop_name, not current)
        return {'FINISHED'}


class VSE_OT_repeat_motion(bpy.types.Operator):
    bl_idname = "vse.repeat_motion"
    bl_label = "Repeat Motion"
    bl_options = {'REGISTER', 'UNDO'}

    anim_prefix: bpy.props.StringProperty()

    def execute(self, context):
        ok = _repeat_motion_exec(self, context, self.anim_prefix)
        return finish(self, ok)


class VSE_OT_match_motion_to_sound(bpy.types.Operator):
    bl_idname = "vse.match_motion_to_sound"
    bl_label = "Match Motion to Sound"
    bl_options = {'REGISTER', 'UNDO'}

    anim_prefix: bpy.props.StringProperty()

    def execute(self, context):
        scene = context.scene
        sound_frames = _sound_duration_frames(scene, self.anim_prefix)

        if not sound_frames:
            self.report({'WARNING'}, "No valid sound file found")
            return {'CANCELLED'}

        ok = run_motion(
            self.anim_prefix,
            context,
            play_sound=True,
            reporter=self,
            target_duration=sound_frames,
        )
        return finish(self, ok)


# =========================
# UI
# =========================

def draw_anim_sound(layout, scene, prefix, operator_id, operator_text):
    box = layout.box()

    row = box.row(align=True)
    row.scale_y = 1.25

    prop_name = _sound_prop(prefix, "ui_open")
    is_open = getattr(scene, prop_name)

    toggle = row.row(align=True)
    toggle.scale_x = 0.7
    toggle_btn = toggle.operator("vse.toggle_sound_ui", text="▼" if is_open else "▶")
    toggle_btn.anim_prefix = prefix

    btn = row.row(align=True)
    btn.scale_x = 1.45
    btn.operator(operator_id, text=operator_text)

    if prefix in REPEATABLE_PREFIXES:
        repeat = row.row(align=True)
        repeat.scale_x = 0.75
        repeat_btn = repeat.operator("vse.toggle_repeat_ui", text="↻")
        repeat_btn.anim_prefix = prefix

    if is_open:
        sub = box.column(align=True)
        sub.use_property_split = True
        sub.use_property_decorate = False
        sub.separator(factor=0.2)

        sub.prop(scene, _sound_prop(prefix, "mode"), text="Sound Mode")

        mode = getattr(scene, _sound_prop(prefix, "mode"), 'NONE')

        if mode == 'FILE':
            sub.prop(scene, _sound_prop(prefix, "file"), text="Sound File")
        elif mode == 'FOLDER':
            sub.prop(scene, _sound_prop(prefix, "folder"), text="Sound Folder")
        else:
            sub.label(text="Choose File or Folder to show sound settings")

        match_btn = sub.operator("vse.match_motion_to_sound", text="Match Animation to Sound")
        match_btn.anim_prefix = prefix

    if prefix in REPEATABLE_PREFIXES:
        repeat_open = getattr(scene, _repeat_prop(prefix, "ui_open"))
        if repeat_open:
            rep_box = box.column(align=True)
            rep_box.use_property_split = False
            rep_box.use_property_decorate = False
            rep_box.separator(factor=0.2)

            top = rep_box.row(align=True)
            top.prop(scene, _repeat_prop(prefix, "count"), text="Count")
            top.prop(scene, _repeat_prop(prefix, "infinite"), text="∞", toggle=True)

            run = rep_box.row(align=True)
            run_btn = run.operator("vse.repeat_motion", text="Repeat Now")
            run_btn.anim_prefix = prefix


def draw_category_box(layout, title, items, scene):
    box = layout.box()
    head = box.row(align=True)
    head.label(text=title)

    col = box.column(align=True)
    for prefix, operator_id, operator_text in items:
        draw_anim_sound(col, scene, prefix, operator_id, operator_text)


# =========================
# ANIMATIONS
# =========================

class VSE_OT_a03(bpy.types.Operator):
    bl_idname = "vse.a03"
    bl_label = "Fade In"

    def execute(self, context):
        ok = run_motion("a03", context, play_sound=True, reporter=self)
        return finish(self, ok)


class VSE_OT_a04(bpy.types.Operator):
    bl_idname = "vse.a04"
    bl_label = "Fade Out"

    def execute(self, context):
        ok = run_motion("a04", context, play_sound=True, reporter=self)
        return finish(self, ok)


class VSE_OT_a05(bpy.types.Operator):
    bl_idname = "vse.a05"
    bl_label = "Slide Left"

    def execute(self, context):
        ok = run_motion("a05", context, play_sound=True, reporter=self)
        return finish(self, ok)


class VSE_OT_a06(bpy.types.Operator):
    bl_idname = "vse.a06"
    bl_label = "Slide Right"

    def execute(self, context):
        ok = run_motion("a06", context, play_sound=True, reporter=self)
        return finish(self, ok)


class VSE_OT_a07(bpy.types.Operator):
    bl_idname = "vse.a07"
    bl_label = "Slide Down"

    def execute(self, context):
        ok = run_motion("a07", context, play_sound=True, reporter=self)
        return finish(self, ok)


class VSE_OT_a08(bpy.types.Operator):
    bl_idname = "vse.a08"
    bl_label = "Soft Pop In"

    def execute(self, context):
        ok = run_motion("a08", context, play_sound=True, reporter=self)
        return finish(self, ok)


class VSE_OT_a09(bpy.types.Operator):
    bl_idname = "vse.a09"
    bl_label = "Rotate Right"

    def execute(self, context):
        ok = run_motion("a09", context, play_sound=True, reporter=self)
        return finish(self, ok)


class VSE_OT_a10(bpy.types.Operator):
    bl_idname = "vse.a10"
    bl_label = "Rotate Left"

    def execute(self, context):
        ok = run_motion("a10", context, play_sound=True, reporter=self)
        return finish(self, ok)


class VSE_OT_a12(bpy.types.Operator):
    bl_idname = "vse.a12"
    bl_label = "Gentle Pulse"

    def execute(self, context):
        ok = run_motion("a12", context, play_sound=True, reporter=self)
        return finish(self, ok)


class VSE_OT_a13(bpy.types.Operator):
    bl_idname = "vse.a13"
    bl_label = "Shake"

    def execute(self, context):
        ok = run_motion("a13", context, play_sound=True, reporter=self)
        return finish(self, ok)


class VSE_OT_a14(bpy.types.Operator):
    bl_idname = "vse.a14"
    bl_label = "Wobble"

    def execute(self, context):
        ok = run_motion("a14", context, play_sound=True, reporter=self)
        return finish(self, ok)


class VSE_OT_a18(bpy.types.Operator):
    bl_idname = "vse.a18"
    bl_label = "Slow In"

    def execute(self, context):
        ok = run_motion("a18", context, play_sound=True, reporter=self)
        return finish(self, ok)


class VSE_OT_a19(bpy.types.Operator):
    bl_idname = "vse.a19"
    bl_label = "Slow Out"

    def execute(self, context):
        ok = run_motion("a19", context, play_sound=True, reporter=self)
        return finish(self, ok)


class VSE_OT_a23(bpy.types.Operator):
    bl_idname = "vse.a23"
    bl_label = "Blink"

    def execute(self, context):
        ok = run_motion("a23", context, play_sound=True, reporter=self)
        return finish(self, ok)


class VSE_OT_a25(bpy.types.Operator):
    bl_idname = "vse.a25"
    bl_label = "Move Up"

    def execute(self, context):
        ok = run_motion("a25", context, play_sound=True, reporter=self)
        return finish(self, ok)


# =========================
# UI PANEL
# =========================

class VSE_PT_motion_lib(bpy.types.Panel):
    bl_label = "VSE Motion Library"
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
        col.label(text="VSE Motion Library")
        col.label(text="Clean motion tools with sound per animation")

        layout.separator(factor=0.5)

        draw_category_box(layout, "Zoom & Emphasis", [
            ("a08", "vse.a08", "Soft Pop In"),
            ("a12", "vse.a12", "Gentle Pulse"),
            ("a18", "vse.a18", "Slow In"),
            ("a19", "vse.a19", "Slow Out"),
        ], scene)

        draw_category_box(layout, "Fade", [
            ("a03", "vse.a03", "Fade In"),
            ("a04", "vse.a04", "Fade Out"),
            ("a23", "vse.a23", "Blink"),
        ], scene)

        draw_category_box(layout, "Move", [
            ("a05", "vse.a05", "Slide Left"),
            ("a06", "vse.a06", "Slide Right"),
            ("a07", "vse.a07", "Slide Down"),
            ("a25", "vse.a25", "Move Up"),
        ], scene)

        draw_category_box(layout, "Rotation & Effects", [
            ("a09", "vse.a09", "Rotate Right"),
            ("a10", "vse.a10", "Rotate Left"),
            ("a14", "vse.a14", "Wobble"),
            ("a13", "vse.a13", "Shake"),
        ], scene)


# =========================
# REGISTER
# =========================

classes = [
    VSE_OT_toggle_sound_ui,
    VSE_OT_toggle_repeat_ui,
    VSE_OT_repeat_motion,
    VSE_OT_match_motion_to_sound,
    VSE_OT_a03, VSE_OT_a04, VSE_OT_a05, VSE_OT_a06,
    VSE_OT_a07, VSE_OT_a08, VSE_OT_a09, VSE_OT_a10,
    VSE_OT_a12, VSE_OT_a13, VSE_OT_a14, VSE_OT_a18,
    VSE_OT_a19, VSE_OT_a23, VSE_OT_a25,
    VSE_PT_motion_lib,
]


def register():
    for c in classes:
        bpy.utils.register_class(c)
    register_sound_props()
    register_repeat_props()


def unregister():
    unregister_repeat_props()
    unregister_sound_props()
    for c in reversed(classes):
        bpy.utils.unregister_class(c)


if __name__ == "__main__":
    register()