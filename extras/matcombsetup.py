import bpy, os
from ..interface.dictionary_en import t
from .. import common as c

class mat_comb_setup(bpy.types.Operator):
    bl_idname = "kkbp.matcombsetup"
    bl_label = "Material combiner setup"
    bl_description = t('mat_comb_tt')
    bl_options = {'REGISTER', 'UNDO'}

    def execute(self, context):
        '''Merges all the finalized material png files into a single atlas file, copies the current model and applies the atlas to the copy'''

        folderpath = os.path.join(bpy.context.scene.kkbp.import_dir, 'baked_files', '')

        # https://blender.stackexchange.com/questions/127403/change-active-collection
        #Recursivly transverse layer_collection for a particular name
        def recurLayerCollection(layerColl, collName):
            found = None
            if (layerColl.name == collName):
                return layerColl
            for layer in layerColl.children:
                found = recurLayerCollection(layer, collName)
                if found:
                    return found
        
        def remove_orphan_data():
            #revert the image back from the atlas file to the baked file   
            for mat in bpy.data.materials:
                if mat.name[-4:] == '-ORG':
                    simplified_name = mat.name[:-4]
                    if bpy.data.materials.get(simplified_name):
                        simplified_mat = bpy.data.materials[simplified_name]
                        for bake_type in ['light', 'dark', 'normal']:
                            simplified_mat.node_tree.nodes[bake_type].image = bpy.data.images.get(simplified_name + ' ' + bake_type + '.png')
            #delete orphan data
            for cat in [bpy.data.armatures, bpy.data.objects, bpy.data.meshes, bpy.data.materials, bpy.data.images, bpy.data.node_groups]:
                for block in cat:
                    if block.users == 0:
                        cat.remove(block)

        if bpy.data.collections.get(c.get_name() + ' atlas'):
            c.kklog(f'deleting previous collection "{c.get_name()} atlas" and regenerating atlas model...')
            def del_collection(coll):
                for c in coll.children:
                    del_collection(c)
                bpy.data.collections.remove(coll,do_unlink=True)
            del_collection(bpy.data.collections[c.get_name() + ' atlas'])
            remove_orphan_data()
            #show the original collection again
            c.show_layer_collection(c.get_name(), False)

        #Change the Active LayerCollection to the character collection
        layer_collection = bpy.context.view_layer.layer_collection
        layerColl = recurLayerCollection(layer_collection, c.get_name())
        bpy.context.view_layer.active_layer_collection = layerColl

        # https://blender.stackexchange.com/questions/157828/how-to-duplicate-a-certain-collection-using-python
        from collections import  defaultdict
        def copy_objects(from_col, to_col, linked, dupe_lut):
            for o in from_col.objects:
                dupe = o.copy()
                if not linked and o.data:
                    dupe.data = dupe.data.copy()
                to_col.objects.link(dupe)
                dupe_lut[o] = dupe
        def copy(parent, collection, linked=False):
            dupe_lut = defaultdict(lambda : None)
            def _copy(parent, collection, linked=False):
                cc = bpy.data.collections.new(collection.name)
                copy_objects(collection, cc, linked, dupe_lut)
                for c in collection.children:
                    _copy(cc, c, linked)
                parent.children.link(cc)
                return cc
            the_copy = _copy(parent, collection, linked)
            for o, dupe in tuple(dupe_lut.items()):
                parent = dupe_lut[o.parent]
                if parent:
                    dupe.parent = parent
            return the_copy
        context = bpy.context
        scene = context.scene
        col = context.collection
        assert(col is not scene.collection)
        copied_collection = copy(scene.collection, col)
        copied_collection.name = c.get_name() + ' atlas'

        #setup materials for the combiner script
        for obj in [o for o in bpy.data.collections[c.get_name() + ' atlas'].all_objects if o.type == 'MESH']:
            for mat in [mat_slot.material for mat_slot in obj.material_slots if mat_slot.material.get('name')]:
                nodes = mat.node_tree.nodes
                if not nodes.get('_light.png'):
                    continue
                print(mat)
                links = mat.node_tree.links
                for input in nodes['shader'].inputs:
                    if input.links:
                        links.remove(input.links[0])
                emissive_node = nodes.new('ShaderNodeBsdfPrincipled')
                emissive_node.name = 'Principled BSDF'
                image_node = nodes.new('ShaderNodeTexImage')
                image_node.name = 'Image Texture'
                links.new(emissive_node.inputs[0], image_node.outputs[0])
                links.new(emissive_node.inputs[4], image_node.outputs[1])
                output_node = [n for n in nodes if n.type == 'OUTPUT_MATERIAL'][0]
                links.new(emissive_node.outputs[0], output_node.inputs[0])
                image_node.image = nodes['_light.png'].image
            #remove outline
            c.switch(obj, 'OBJECT')
            bpy.ops.object.material_slot_remove_unused()
            #remove the solidify modifier
            for mod in [m for m in obj.modifiers if m.type == 'SOLIDIFY']:
                mod.show_viewport = False
                mod.show_render = False

        return {'FINISHED'}
