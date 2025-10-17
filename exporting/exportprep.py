#simplfies bone count using the merge weights function in CATS

import bpy, traceback, time, os
from .. import common as c
from ..interface.dictionary_en import t

def prep_operations(prep_type, simp_type):

    c.kklog('\nPrepping for export...')
    armature = c.get_armature()
    c.switch(armature, 'pose')
    bpy.ops.armature.collection_show_all()
    
    # If exporting for Unreal...
    if prep_type == 'E':
        #Rename some bones to make it match Mannequin skeleton
        #Not necessary, but allows Unreal automatically recognize and match bone names when retargeting
        ue_rename_dict = {
            'Hips': 'pelvis',
            'Spine': 'spine_01',
            'Chest': 'spine_02',
            'Upper Chest': 'spine_03',
            'Neck': 'neck',
            'Head': 'head',
            'Left shoulder': 'clavicle_l',
            'Right shoulder': 'clavicle_r',
            'Left arm': 'upperarm_l',
            'Right arm': 'upperarm_r',
            'Left elbow': 'lowerarm_l',
            'Right elbow': 'lowerarm_r',
            'Left wrist': 'hand_l',
            'Right wrist': 'hand_r',

            'Left leg': 'thigh_l',
            'Right leg': 'thigh_r',
            'Left knee': 'calf_l',
            'Right knee': 'calf_r',
            'cf_j_leg03_L': 'foot_l',
            'cf_j_leg03_R': 'foot_r',
            'Left toe': 'ball_l',
            'Right toe': 'ball_r',
        }
        for bone in ue_rename_dict:
            if armature.data.bones.get(bone):
                armature.data.bones[bone].name = ue_rename_dict[bone]

        c.switch(armature, 'edit')

        #Make all the bones on the legs face the same direction, otherwise IK won't work in Unreal
        armature.data.edit_bones["calf_l"].tail.z = armature.data.edit_bones["calf_l"].head.z + 0.1
        armature.data.edit_bones["calf_l"].head.y += 0.01
        armature.data.edit_bones["calf_r"].tail.z = armature.data.edit_bones["calf_r"].head.z + 0.1
        armature.data.edit_bones["calf_r"].head.y += 0.01

        armature.data.edit_bones["ball_l"].tail.z = armature.data.edit_bones["ball_l"].head.z
        armature.data.edit_bones["ball_l"].tail.y = armature.data.edit_bones["ball_l"].head.y - 0.05
        armature.data.edit_bones["ball_r"].tail.z = armature.data.edit_bones["ball_r"].head.z
        armature.data.edit_bones["ball_r"].tail.y = armature.data.edit_bones["ball_r"].head.y - 0.05

        c.switch(armature, 'pose')

    #If simplifying the bones...
    if simp_type in ['A', 'B']:
        bpy.ops.pose.select_all(action='DESELECT')

        #Move pupil bones to layer 1
        if armature.data.bones.get('Left Eye'):
            armature.data.bones['Left Eye'].collections.clear()
            armature.data.collections['Torso'].assign(armature.data.bones.get('Left Eye'))
            armature.data.bones['Right Eye'].collections.clear()
            armature.data.collections['Torso'].assign(armature.data.bones.get('Right Eye'))
        
        #If simple is selected, only delete the junk layer
        for bone in armature.data.bones:
            if bone.collections.get('Junk'):
                bone.select = True
        
        #if very simple selected, also get 3-5,12,17-19
        if simp_type in ['A']:
            for bone in armature.data.bones:
                select_bool = (bone.collections.get('Charamaker bones')  or 
                               bone.collections.get('Deform bones')  or 
                               bone.collections.get('NSFW')  or 
                               bone.collections.get('Face') or 
                               bone.collections.get('Face (MCH)') or 
                               bone.collections.get('Rigged tongue')
                               )
                if select_bool:
                    bone.select = True
        
        c.kklog('Using the merge weights function in CATS to simplify bones...')
        bpy.ops.object.mode_set(mode='EDIT')
        bpy.ops.kkbp.cats_merge_weights()

    #If exporting for VRM or VRC...
    if prep_type in ['A', 'D']:
        c.kklog('Editing armature for VRM...')
        c.switch(armature, 'edit')

        #Rearrange bones to match CATS output 
        if armature.data.edit_bones.get('Pelvis'):
            armature.data.edit_bones['Pelvis'].parent = None
            armature.data.edit_bones['Spine'].parent = armature.data.edit_bones['Pelvis']
            armature.data.edit_bones['Hips'].name = 'dont need lol'
            armature.data.edit_bones['Pelvis'].name = 'Hips'
            armature.data.edit_bones['Left leg'].parent = armature.data.edit_bones['Hips']
            armature.data.edit_bones['Right leg'].parent = armature.data.edit_bones['Hips']
            armature.data.edit_bones['Left ankle'].parent = armature.data.edit_bones['Left knee']
            armature.data.edit_bones['Right ankle'].parent = armature.data.edit_bones['Right knee']
            armature.data.edit_bones['Left shoulder'].parent = armature.data.edit_bones['Upper Chest']
            armature.data.edit_bones['Right shoulder'].parent = armature.data.edit_bones['Upper Chest']
            armature.data.edit_bones.remove(armature.data.edit_bones['dont need lol'])

        bpy.ops.object.mode_set(mode='POSE')
        bpy.ops.pose.select_all(action='DESELECT')

        #Merge specific bones for unity rig autodetect
        merge_these = ['cf_j_waist02', 'cf_s_waist01', 'cf_s_hand_L', 'cf_s_hand_R']
        #Delete the upper chest for VR chat models, since it apparently causes errors with eye tracking
        if prep_type == 'D':
            merge_these.append('Upper Chest')
            c.kklog('Removing Upper Chest bone for VRC...')
        for bone in armature.data.bones:
            if bone.name in merge_these:
                bone.select = True

        bpy.ops.object.mode_set(mode='EDIT')
        bpy.ops.kkbp.cats_merge_weights()
        bpy.ops.armature.collection_remove_unused()
        c.switch(armature, 'object')

        #remove the eye UV warp modifiers
        c.kklog('Removing eye UV warp modifiers...')
        body = c.get_body()
        if mod := body.modifiers.get('Left Eye UV warp'):
            mod.show_viewport = False
        if mod := body.modifiers.get('Right Eye UV warp'):
            mod.show_viewport = False


def create_material_atlas():
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
                        simplified_mat.node_tree.nodes['textures'].node_tree.nodes[bake_type].image = bpy.data.images.get(simplified_name + ' ' + bake_type + '.png')
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
            emissive_node = nodes.new('ShaderNodeEmission')
            emissive_node.name = 'Emission'
            image_node = nodes.new('ShaderNodeTexImage')
            image_node.name = 'Image Texture'
            links.new(emissive_node.inputs[0], image_node.outputs[0])
            image_node.image = nodes['_light.png'].image
        context.view_layer.objects.active = obj
        bpy.ops.object.material_slot_remove_unused()

    #call the material combiner script
    bpy.ops.kkbp.combiner()

    #replace all images with the atlas in a new atlas material
    bake_types = ['light', 'dark', 'normal']
    for index, obj in enumerate([o for o in bpy.data.collections[c.get_name() + ' atlas'].all_objects if o.type == 'MESH']):
        #fix modifiers for all objects in this collection
        for mod in obj.modifiers:
            if mod.type == 'ARMATURE':
                #fix the armature modifier to use the copied aramture
                copied_armature = [o for o in bpy.data.collections[c.get_name() + ' atlas'].all_objects if o.type == 'ARMATURE'][0]
                mod.object = copied_armature
        
        #check if this object had any atlas-able materials to begin with. If not, skip
        if not [mat_slot.material for mat_slot in obj.material_slots if mat_slot.material.get('name')]:
            continue

        for bake_type in bake_types:
            #check for atlas dupes
            atlas_image_name = f'{sanitizeMaterialName(obj.name).replace("001","")}_{bake_type}.png'
            if bpy.data.images.get(atlas_image_name):
                bpy.data.images.remove(bpy.data.images.get(atlas_image_name))
            #the atlas image is originally named after the index of the object. Rename it to the object name
            original_image_path = os.path.join(context.scene.kkbp.import_dir, 'atlas_files', f'{index}_{bake_type}.png')
            new_image_path = os.path.join(context.scene.kkbp.import_dir, 'atlas_files', atlas_image_name)
            if os.path.exists(original_image_path):
                try:
                    os.rename(original_image_path, new_image_path)
                except:
                    #rename failed because the file already exists. Delete the old one and try again
                    os.remove(new_image_path)
                    os.rename(original_image_path, new_image_path)
            #then load it into blender
            atlas_image = bpy.data.images.load(new_image_path)
            bpy.data.images.remove(bpy.data.images.get(f'{index}_{bake_type}.png'))
            for material in [mat_slot.material for mat_slot in obj.material_slots if mat_slot.material.get('name')]:
                if node := material.node_tree.nodes.get('_light.png'):
                    image = node.image
                else:
                    continue
                
                if image:
                    if image.name == 'Template: Pattern Placeholder':
                        image = None
                if not image:
                    print(image)
                    continue
                else:
                    if not bpy.data.materials.get('{} Atlas'.format(material.name)):
                        #remove the emission nodes from earlier
                        if material.node_tree.nodes.get('Emission'):
                            material.node_tree.nodes.remove(material.node_tree.nodes['Image Texture'])
                            material.node_tree.nodes.remove(material.node_tree.nodes['Emission'])
                        atlas_material = material.copy()
                        atlas_material['atlas'] = True
                        atlas_material.name = '{} Atlas'.format(material.name)
                    else:
                        atlas_material =  bpy.data.materials.get('{} Atlas'.format(material.name))
                    atlas_material.node_tree.nodes['_light.png' if bake_type == 'light' else '_dark.png' if bake_type == 'dark' else '_NMP_CNV.png'].image = atlas_image
                    #load in the light image to the dark slot to make it look better when only the light colors are baked.
                    # This will be overwritten with the dark image in the next loop if the user baked it
                    if bake_type == 'light':
                        atlas_material.node_tree.nodes['_dark.png'].image = atlas_image

        #replace all images with the atlas in a new atlas material
        for mat_slot in [m for m in obj.material_slots if m.material.get('name')]:
            material = mat_slot.material
            atlas_material = bpy.data.materials.get('{} Atlas'.format(material.name))
            mat_slot.material = atlas_material

    #setup the new collection for exporting
    layer_collection = bpy.context.view_layer.layer_collection
    layerColl = recurLayerCollection(layer_collection, c.get_name() + ' atlas')
    bpy.context.view_layer.active_layer_collection = layerColl
    bpy.ops.collection.exporter_add(name="IO_FH_fbx")
    bpy.data.collections[c.get_name() + ' atlas'].exporters[0].export_properties.object_types = {'EMPTY', 'ARMATURE', 'MESH', 'OTHER'}
    bpy.data.collections[c.get_name() + ' atlas'].exporters[0].export_properties.use_mesh_modifiers = False
    bpy.data.collections[c.get_name() + ' atlas'].exporters[0].export_properties.add_leaf_bones = False
    bpy.data.collections[c.get_name() + ' atlas'].exporters[0].export_properties.bake_anim = False
    bpy.data.collections[c.get_name() + ' atlas'].exporters[0].export_properties.apply_scale_options = 'FBX_SCALE_ALL'
    bpy.data.collections[c.get_name() + ' atlas'].exporters[0].export_properties.path_mode = 'COPY'
    bpy.data.collections[c.get_name() + ' atlas'].exporters[0].export_properties.embed_textures = False
    bpy.data.collections[c.get_name() + ' atlas'].exporters[0].export_properties.mesh_smooth_type = 'OFF'
    bpy.data.collections[c.get_name() + ' atlas'].exporters[0].export_properties.filepath = os.path.join(folderpath.replace('baked_files', 'atlas_files'), f'{sanitizeMaterialName(c.get_name())} exported model atlas.fbx')

    #hide the new collection
    c.show_layer_collection('Rigged tongue ' + c.get_name() + '.001', True)
    c.show_layer_collection(c.get_name() + ' atlas', True)
    remove_orphan_data()

def sanitizeMaterialName(text: str) -> str:
    '''Mat names need to be sanitized else you can't delete the files with windows explorer'''
    for ch in ['\\','`','*','<','>','.',':','?','|','/','\"']:
        if ch in text:
            text = text.replace(ch,'')
    return text

class export_prep(bpy.types.Operator):
    bl_idname = "kkbp.exportprep"
    bl_label = "Prep for target application"
    bl_description = t('export_prep_tt')
    bl_options = {'REGISTER', 'UNDO'}
    
    def execute(self, context):
        scene = context.scene.kkbp
        prep_type = scene.prep_dropdown
        simp_type = scene.simp_dropdown
        last_step = time.time()
        try:
            c.toggle_console()
            prep_operations(prep_type, simp_type)
            create_material_atlas()
            c.kklog('Finished in ' + str(time.time() - last_step)[0:4] + 's')
            c.toggle_console()
            return {'FINISHED'}
        except:
            c.kklog('Unknown python error occurred', type = 'error')
            c.kklog(traceback.format_exc())
            self.report({'ERROR'}, traceback.format_exc())
            return {"CANCELLED"}
    
