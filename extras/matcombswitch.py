import bpy
from ..interface.dictionary_en import t
from .. import common as c

class mat_comb_switch(bpy.types.Operator):
    bl_idname = "kkbp.matcombswitch"
    bl_label = "Material combiner switch"
    bl_description = t('mat_comb_switch_tt')
    bl_options = {'REGISTER', 'UNDO'}

    def execute(self, context):
        #toggle textures for the combiner script
        for obj in [o for o in bpy.data.collections[c.get_name() + ' atlas'].all_objects if o.type == 'MESH']:
            for mat in [mat_slot.material for mat_slot in obj.material_slots if mat_slot.material.get('name')]:
                nodes = mat.node_tree.nodes
                if not nodes.get('_light.png'):
                    continue
                if nodes['Image Texture'].image.name.endswith('_light.png'):
                    nodes['Image Texture'].image = bpy.data.images[nodes['Image Texture'].image.name.replace('_light.png', '_dark.png')]
                else:
                    nodes['Image Texture'].image = bpy.data.images[nodes['Image Texture'].image.name.replace('_dark.png', '_light.png')]

        return {'FINISHED'}
