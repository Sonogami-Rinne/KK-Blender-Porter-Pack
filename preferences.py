#The preferences for the plugin 

import bpy
from bpy.props import BoolProperty, EnumProperty, StringProperty, IntProperty

from .interface.dictionary_en import t

from .interface.dictionary_en import t

class KKBPPreferences(bpy.types.AddonPreferences):
    # this must match the add-on name, use '__package__'
    # when defining this in a submodule of a python package.
    bl_idname = __package__

    shader_dropdown : EnumProperty(
        items=(
            ("A", t('shader_A'), ''),
            ("B", t('shader_B'), ''),
            ("D", t('shader_D'), ''),
            ("C", t('shader_C'), t('shader_C_tt')),
        ), name="", default='A', description="Shader")

    use_rigify : BoolProperty(
        description=t('use_rigify_tt'),
        default = True)

    sfw_mode : BoolProperty(
        description=t('sfw_mode_tt'),
        default = False)

    fix_seams : BoolProperty(
        description=t('seams_tt'),
        default = True)
    
    use_outline : BoolProperty(
        description= t('outline_tt'),
        default = True)
    
    separate_clothes : BoolProperty(
        description=t('cat_drop'),
        default=False)
    
    prep_dropdown : EnumProperty(
    items=(
        ("VRM", t('prep_drop_A'), t('prep_drop_A_tt')),
        #("C", "MikuMikuDance - PMX compatible", " "),
        ("VRC", t('prep_drop_D'), t('prep_drop_D_tt')),
        ("Unreal", t('prep_drop_E'), t('prep_drop_E_tt')),
        ("Koikatsu", t('prep_drop_F'), t('prep_drop_F_tt')),
        ("no_change", t('prep_drop_B'), t('prep_drop_B_tt')),
    ), name="", default='VRM', description=t('prep_drop'))

    simp_dropdown : EnumProperty(
        items=(
            ("A", t('simp_drop_A'), t('simp_drop_A_tt')),
            ("B", t('simp_drop_B'), t('simp_drop_B_tt')),
            ("C", t('simp_drop_C'), t('simp_drop_C_tt')),
        ), name="", default='A', description=t('simp_drop'))

    atlas_dropdown : EnumProperty(
        items=(
            ("Atlas", t('use_atlas'), ""),
            ("skip_eyes", t('atlas_no_eyes'), ""),
            ("None", t('dont_use_atlas'), ""),
        ), name="", default='Atlas', description=t('use_atlas_tt'))
    
    max_thread_num: IntProperty(
        min=1, max = 64,
        default=8,
        description=t('max_thread_num_tt'))

    max_image_num: IntProperty(
        min=1, max = 10,
        default=2,
        description=t('max_image_num_tt'))

    batch_rows: IntProperty(
        min=256, max = 4096,
        default=512,
        description=t('batch_rows_tt'))

    def draw(self, context):
        layout = self.layout
        splitfac = 0.5

        col = layout.column(align=True)
        row = col.row(align=True)
        row.label(text='Change the default options for the KKBP Importer below:')
                
        row = col.row(align = True)
        box = row.box()
        col = box.column(align=True)
        
        row = col.row(align=True)
        split = row.split(align = True, factor=splitfac)
        split.prop(context.scene.kkbp, "use_rigify", toggle=True, text = t('use_rigify') if context.scene.kkbp.use_rigify else t('no_rigify'))
        split.prop(context.scene.kkbp, "shader_dropdown")

        row = col.row(align=True)
        split = row.split(align = True, factor=splitfac)
        split.prop(context.scene.kkbp, "use_outline", toggle=True, text = t('outline') if context.scene.kkbp.use_outline else t('no_outline'))
        split.prop(context.scene.kkbp, "separate_clothes", toggle=True, text = t('separate') if context.scene.kkbp.separate_clothes else t('no_separate'))
        
        row = col.row(align=True)
        split = row.split(align = True, factor=splitfac)
        split.prop(context.scene.kkbp, "fix_seams", toggle=True, text = t('seams'))
        split.prop(context.scene.kkbp, "sfw_mode", toggle=True, text = t('sfw_mode'))

        box = layout.box()
        col = box.column(align=True)
        row = col.row(align=True)
        row = col.row(align=True)
        split = row.split(align=True, factor=splitfac)
        split.prop(context.scene.kkbp, "simp_dropdown")
        split.prop(context.scene.kkbp, "prep_dropdown")
        row = col.row(align=True)
        row.prop(context.scene.kkbp, "atlas_dropdown")

        col = layout.column(align=True)
        row = col.row(align=True)
        row.label(text='Change these options based on your computer specs to speed up the import process:')
        row = col.row(align=True)
        split = row.split(align=True, factor=0.33)
        split.prop(self, "max_thread_num", text = t('max_thread_num'))
        split.prop(self, "max_image_num", text = t('max_image_num'))
        split.prop(self, "batch_rows", text = t('batch_rows'))

