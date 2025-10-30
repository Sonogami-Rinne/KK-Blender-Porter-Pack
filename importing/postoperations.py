
# This file performs the following operations

# 	Hide all clothes except the first outfit (alts are always hidden)

#   (Cycles) Applies Cycles conversion script
#   (Eevee Mod) Applies Eevee Mod conversion script
#   (Rigify) Applies Rigify conversion script
#   (SFW) Runs SFW cleanup script

# 	Clean orphaned data as long as users = 0 and fake user = False

# Parts of cycles replacement was taken from https://github.com/FlailingFog/KK-Blender-Porter-Pack/issues/234


import bpy
from .. import common as c

class post_operations(bpy.types.Operator):
    bl_idname = "kkbp.postoperations"
    bl_label = bl_idname
    bl_description = bl_idname
    bl_options = {'REGISTER', 'UNDO'}
    
    def execute(self, context):
        try:
            self.hide_unused_objects()

            self.apply_cycles()
            self.apply_eeveemod()
            self.apply_rigify()
            self.apply_sfw()
            self.separate_meshes()
            self.apply_outlines()
            
            c.switch(c.get_armature(), 'object')
            c.clean_orphaned_data()
            c.set_viewport_shading('SOLID')

            return {'FINISHED'}
        except Exception as error:
            c.handle_error(self, error)
            return {"CANCELLED"}

    # %% Main functions    
    def hide_unused_objects(self):
        """
        Hides unused objects in the Blender scene based on certain conditions.

        This method performs the following operations:
        1. Ensures the armature is not hidden.
        3. Hides all outfits except the one with the lowest ID.
        4. Moves eyegags and tears into their own collection.
        5. Always hides the rigged tongue if present.
        6. Always hides the Bone Widgets collection.
        """
        c.get_armature().hide_set(False)
        #hide all outfits except the first one
        #but don't hide the collection if separate by material is enabled
        clothes_and_hair = c.get_outfits()
        clothes_and_hair.extend(c.get_hairs())
        outfit_ids = (int(c['id']) for c in clothes_and_hair if c.get('id'))
        outfit_ids = list(set(outfit_ids))
        for id in outfit_ids:
            clothes_in_this_id = [c for c in clothes_and_hair if c.get('id') == str(id).zfill(2)]
            c.move_and_hide_collection(clothes_in_this_id, 'Outfit ' + str(id).zfill(2) + ' ' + c.get_name(), hide = (id != min(outfit_ids) and bpy.context.scene.kkbp.categorize_dropdown != 'B'))

        #put any clothes variations into their own collection
        outfit_ids = (int(c['id']) for c in c.get_alts() if c.get('id'))
        outfit_ids = list(set(outfit_ids))
        for index, id in enumerate(outfit_ids):
            clothes_in_this_id = [c for c in c.get_alts() if c.get('id') == str(id).zfill(2)]
            c.switch(clothes_in_this_id[0], 'OBJECT')
            #find the character index
            character_collection_index = len(bpy.context.view_layer.layer_collection.children)-1
            #find the index of the outfit collection
            for i, child in enumerate(bpy.context.view_layer.layer_collection.children[character_collection_index].children):
                if child.name == 'Outfit ' + str(id).zfill(2) + ' ' + c.get_name():
                    break
            for ob in clothes_in_this_id:
                ob.select_set(True)
                bpy.context.view_layer.objects.active=ob
            new_collection_name = 'Alts ' + str(id).zfill(2) + ' ' + c.get_name()
            #extremely confusing move to under the clothes collection. Index is the outfit index + outfit collection index (starts at 1) + Scene collection (1) +  + character collection index (usually 0) + 1
            bpy.ops.object.move_to_collection(collection_index = (index+i) + 1 + (character_collection_index + 1), is_new = True, new_collection_name = new_collection_name)
            #then hide the alts
            child.children[0].exclude = True

        #put the eyegags and tears into their own collection
        face_objects = []
        if c.get_gags():
            face_objects.append(c.get_gags())
        if c.get_tears():
            face_objects.append(c.get_tears())
        if face_objects:
            c.move_and_hide_collection(face_objects, 'Tears and gag eyes ' + c.get_name(), hide = False)

        #always hide the rigged tongue if present
        if c.get_tongue():
            c.move_and_hide_collection([c.get_tongue()], 'Rigged tongue ' + c.get_name(), hide = True)
        
        #always hide the hitboxes collection
        if bpy.data.collections.get('Hitboxes ' + c.get_name()):
            c.switch(c.get_armature(), 'OBJECT')
            for child in bpy.context.view_layer.layer_collection.children[0].children:
                if ('Hitboxes ' + c.get_name()) in child.name:
                    child.exclude = True

        #always hide the bone widgets collection
        if bpy.data.collections.get('Bone Widgets'):
            c.switch(c.get_armature(), 'OBJECT')
            for child in bpy.context.view_layer.layer_collection.children[0].children:
                if child.name == 'Bone Widgets':
                    child.exclude = True

    def apply_cycles(self):
        if not bpy.context.scene.kkbp.shader_dropdown in ['B', 'D']:
            return
        c.kklog('Applying Cycles adjustments...')
        c.import_from_library_file('NodeTree', ['.Cycles', '.Cycles no shadows', '.Cycles Classic'], True)
        c.import_from_library_file('Image', ['Template: Black'], True)
                    
        ####fix the eyelash mesh overlap
        # deselect everything and make body active object
        c.switch(c.get_body(), 'edit')

        # move the eyeline out a bit
        bpy.context.object.active_material_index = c.get_body().data.materials.find('KK cf_m_eyeline_down')
        bpy.ops.object.material_slot_select()
        bpy.ops.transform.translate(value=(0, -1 * 0.0002, 0))
        bpy.context.object.active_material_index = c.get_body().data.materials.find('KK cf_m_eyeline_00_up')
        bpy.ops.object.material_slot_select()
        bpy.ops.transform.translate(value=(0, -1 * 0.0003, 0))
        c.switch(c.get_body(), 'object')

        ignore_list = [
            'KK Eyebrows (mayuge) ' + c.get_name(),
            'KK EyeL (hitomi) ' + c.get_name(),
            'KK EyeR (hitomi) ' + c.get_name(),
            'KK Eyeline up ' + c.get_name(),
            'KK Eyewhites (sirome) ' + c.get_name()]
        everything = [c.get_body()]
        everything.extend(c.get_hairs())
        everything.extend(c.get_alts())
        everything.extend(c.get_outfits())

        #add cycles node group
        for object in everything:
            for node_tree in [mat_slot.material.node_tree for mat_slot in object.material_slots if mat_slot.material.name not in ignore_list]:
                nodes = node_tree.nodes
                if nodes.get('shader'):
                    nodes['shader'].node_tree = bpy.data.node_groups['.Cycles' if bpy.context.scene.kkbp.shader_dropdown == 'B' else '.Cycles Classic']

                    #Cycles makes missing images PINK (?!) instead of black for some reason and this screws with the shaders
                    #If an image is missing, fill it in with Template: Black
                    if nodes.get('_NMP_CNV.png'):
                        for image_node in [n for n in nodes if n.type == 'TEX_IMAGE']:
                            if not image_node.image:
                                image_node.image = bpy.data.images['Template: Black']
        
        #set eyeline up and eyebrows as shadowless
        shadowless_mats =  ['KK cf_m_eyeline_00_up', 'KK cf_m_eyeline_down', 'KK cf_m_mayuge_00']
        for mat_name in shadowless_mats:
            if mat := bpy.data.materials.get(mat_name):
                if node := mat.node_tree.nodes.get('shader'):
                    node.node_tree = bpy.data.node_groups['.Cycles no shadows']
                
        bpy.context.scene.render.engine = 'CYCLES'
        bpy.context.scene.cycles.preview_samples = 10

    def apply_eeveemod(self):
        if not bpy.context.scene.kkbp.shader_dropdown == 'C':
            return
        c.import_from_library_file('NodeTree', ['.Eevee Mod'], True)

        c.kklog('Applying Eevee Shader adjustments...')
        #Import eevee mod node group and replace the combine colors group with the eevee mod group
        ignore_list = [
            'KK cf_m_mayuge_00',
            'KK cf_m_hitomi_00_cf_Ohitomi_L02',
            'KK cf_m_hitomi_00_cf_Ohitomi_R02',
            'KK cf_m_eyeline_00_up',
            'KK cf_m_sirome_00']
        everything = [c.get_body()]
        everything.extend(c.get_hairs())
        everything.extend(c.get_alts())
        everything.extend(c.get_outfits())
        
        for object in everything:
            for node_tree in [mat_slot.material.node_tree for mat_slot in object.material_slots if mat_slot.material.name not in ignore_list]:
                nodes = node_tree.nodes
                links = node_tree.links
                if nodes.get('shader'):
                    nodes['shader'].node_tree = bpy.data.node_groups['.Eevee Mod']

        #select entire face and body, then reset vectors to prevent Amb Occ seam around the neck 
        body = c.get_body()
        bpy.ops.object.select_all(action='DESELECT')
        body.select_set(True)
        bpy.context.view_layer.objects.active=body
        bpy.ops.object.mode_set(mode = 'EDIT')
        body.active_material_index = 1
        bpy.ops.object.material_slot_select()
        bpy.ops.mesh.normals_tools(mode='RESET')
        bpy.ops.object.mode_set(mode = 'OBJECT')
    
    @classmethod
    def apply_rigify(cls):
        self = cls

        #SVS is not supported yet
        if c.is_svs():
            c.kklog('Rigify conversion skipped for SVS characters.')
            return

        if not bpy.context.scene.kkbp.armature_dropdown == 'Rigify':
            return
        
        #Activate the built in Rigify addon if it isn't already enabled.
        if "rigify" not in bpy.context.preferences.addons:
            c.kklog('Rigify was not enabled. Enabling it now...', 'warn')
            bpy.ops.preferences.addon_enable(module='rigify')
            bpy.ops.wm.save_userpref()
        
        c.kklog('Running Rigify conversion scripts...')
        armature = c.get_armature()
        c.switch(armature, 'object')

        #run a script to prepare the armature for rigify
        bpy.ops.kkbp.rigbefore('INVOKE_DEFAULT')
        
        #generate the rigify rig
        bpy.ops.pose.rigify_generate()

        #cleanup the generated rigify rig
        bpy.ops.kkbp.rigafter('INVOKE_DEFAULT')

        #make sure everything is deselected in edit mode for the body
        c.switch(c.get_body(), 'edit')
        c.switch(c.get_body(), 'object')

        #then finally switch to the rig as the last selected object
        c.switch(c.get_rig(), 'object')
        bpy.context.scene.tool_settings.transform_pivot_point = 'INDIVIDUAL_ORIGINS'
        bpy.context.tool_settings.mesh_select_mode = (False, False, True) #enable face select in edit mode
        return {'FINISHED'}

    def apply_sfw(self):
        if not bpy.context.scene.kkbp.sfw_mode:
            return
        c.kklog('Applying mesh adjustments...')
        #mark nsfw parts of mesh as freestyle faces so they don't show up in the outline
        body = c.get_body()
        c.switch(body, mode = 'EDIT')
        def mark_group_as_freestyle(group_list):
            for group in group_list:
                group_found = body.vertex_groups.find(group)      
                if group_found > -1:
                    bpy.context.object.active_material_index = group_found
                    bpy.ops.object.vertex_group_select()
                # else:
                #     c.kklog('Group wasn\'t found when freestyling vertex groups: ' + group, 'warn')
            bpy.ops.mesh.mark_freestyle_face(clear=False)
        freestyle_list = [
            'cf_j_bnip02_L', 'cf_j_bnip02_R',
            'cf_s_bust03_L', 'cf_s_bust03_R']
        mark_group_as_freestyle(freestyle_list)
        bpy.ops.mesh.select_all(action = 'DESELECT')

        #delete nsfw parts of the mesh
        def delete_group_and_bone(ob, group_list):
            c.switch(ob, 'EDIT')
            bpy.ops.mesh.select_all(action = 'DESELECT')
            for group in group_list:
                group_found = ob.vertex_groups.find(group)      
                if group_found > -1:
                    bpy.context.object.vertex_groups.active_index = group_found
                    bpy.ops.object.vertex_group_select()
                # else:
                    # c.kklog('Group wasn\'t found when deleting vertex groups: ' + group, 'warn')
            bpy.ops.mesh.delete(type='VERT')
            bpy.ops.mesh.select_all(action = 'DESELECT')

        delete_list = ['cf_s_bnip025_L', 'cf_s_bnip025_R', 'cf_s_bnip02_L', 'cf_s_bnip02_R',
        'cf_j_kokan', 'cf_j_ana', 'cf_d_ana', 'cf_d_kokan', 'cf_s_ana',
        'Vagina_Root', 'Vagina_B', 'Vagina_F', 'Vagina_001_L', 'Vagina_002_L',
        'Vagina_003_L', 'Vagina_004_L', 'Vagina_005_L',  'Vagina_001_R', 'Vagina_002_R',
        'Vagina_003_R', 'Vagina_004_R', 'Vagina_005_R']
        delete_group_and_bone(body, delete_list)
        #also do this on the clothes because the bra can show up
        delete_list = ['cf_s_bnip02_L', 'cf_s_bnip02_R', 'cf_s_bnip025_L', 'cf_s_bnip025_R', ]
        for ob in [o for o in bpy.data.objects if o.get('outfit')]:
            delete_group_and_bone(ob, delete_list)

        #delete nsfw bones
        rig = c.get_rig()
        if bpy.context.scene.kkbp.sfw_mode and bpy.context.scene.kkbp.armature_dropdown == 'Rigify':
            rig.data.collections_all['NSFW'].is_visible = True
            def delete_bone(group_list):
                bpy.ops.object.mode_set(mode = 'OBJECT')
                bpy.ops.object.select_all(action='DESELECT')
                rig.select_set(True)
                bpy.context.view_layer.objects.active = rig
                bpy.ops.object.mode_set(mode = 'EDIT')
                bpy.ops.armature.select_all(action='DESELECT')
                for bone in group_list:
                    if rig.data.bones.get(bone):
                        rig.data.edit_bones[bone].select = True
                        bpy.ops.kkbp.cats_merge_weights()
                    # else:
                    #     c.kklog('Bone wasn\'t found when deleting bones: ' + bone, 'warn')
                bpy.ops.armature.select_all(action='DESELECT')
                bpy.ops.object.mode_set(mode = 'OBJECT')

            delete_list = ['cf_s_bnip025_L', 'cf_s_bnip025_R',
            'cf_j_kokan', 'cf_j_ana', 'cf_d_ana', 'cf_d_kokan', 'cf_s_ana',
            'cf_J_Vagina_root',
            'cf_J_Vagina_B',
            'cf_J_Vagina_F',
            'cf_J_Vagina_L.005',
            'cf_J_Vagina_R.005',
            'cf_J_Vagina_L.004',
            'cf_J_Vagina_L.001',
            'cf_J_Vagina_L.002',
            'cf_J_Vagina_L.003',
            'cf_J_Vagina_R.001',
            'cf_J_Vagina_R.002',
            'cf_J_Vagina_R.003',
            'cf_J_Vagina_R.004',
            'cf_j_bnip02root_L',
            'cf_j_bnip02_L',
            'cf_s_bnip01_L',
            #'cf_s_bust03_L',
            'cf_s_bust02_L',
            'cf_j_bnip02root_R',
            'cf_j_bnip02_R',
            'cf_s_bnip01_R',
            #'cf_s_bust03_R',
            'cf_s_bust02_R',]
            delete_bone(delete_list)
            rig.data.collections_all['NSFW'].is_visible = False
            rig.data.collections_all['NSFW'].name = 'Chest'

    def separate_meshes(self):
        if bpy.context.scene.kkbp.categorize_dropdown == 'B':
            #separate each outfit by material
            for obj in c.get_outfits():
                if obj.modifiers.get('Outline Modifier'):
                    obj.modifiers['Outline Modifier'].show_render = False
                    obj.modifiers['Outline Modifier'].show_viewport = False
                c.switch(obj, 'OBJECT')
                bpy.ops.object.material_slot_remove_unused()
                c.switch(obj, 'EDIT')
                bpy.ops.mesh.separate(type='MATERIAL')

            #once they are all separated, rename them to their material name
            for obj in c.get_outfits():
                try:
                    obj.name = obj.material_slots[0].name
                except:
                    #oh well
                    pass

    def apply_outlines(self):
        if not bpy.context.scene.kkbp.use_outline or c.is_svs():
            return
        c.kklog('Adding outlines to character...')
        self.add_outlines_to_body()
        self.add_outlines_to_hair_clothes()

    def add_outlines_to_body(self):
        #Add face and body outlines, then load in the clothes transparency mask to body outline
        body = c.get_body()
        c.switch(body, 'object')
        mod = body.modifiers.new(type='SOLIDIFY', name='Outline Modifier')
        mod.thickness = 0.0005
        mod.offset = 0
        mod.material_offset = len(body.material_slots)
        mod.use_flip_normals = True
        mod.use_rim = False
        mod.name = 'Outline Modifier'
        mod.show_expanded = False
        #face first
        if bpy.data.materials.get('KK cf_m_face_00'):
            faceOutlineMat = bpy.data.materials['KK cf_m_face_00'].copy()
            faceOutlineMat.name = 'Outline cf_m_face_00'
            body.data.materials.append(faceOutlineMat)
            faceOutlineMat.use_backface_culling = True
            faceOutlineMat.use_backface_culling_shadow = True
            faceOutlineMat.node_tree.nodes['_light.png'].image = bpy.data.images['Template: BlackWithAlpha']
        else:
            c.kklog('Could not find face material to create outline from.', 'error')
        if bpy.data.materials.get('KK cf_m_body'):
            body_outline_mat = bpy.data.materials['KK cf_m_body'].copy()
            body_outline_mat.name = 'Outline cf_m_body'
            body.data.materials.append(body_outline_mat)
            body_outline_mat.use_backface_culling = True
            body_outline_mat.use_backface_culling_shadow = True
            body_outline_mat.node_tree.nodes['_light.png'].image = bpy.data.images['Template: BlackWithAlpha']
        else:
            c.kklog('Could not find face material to create outline from.', 'error')
        c.print_timer('add_outlines_to_body')

    def add_outlines_to_hair_clothes(self):
        #Give each piece of hair/clothes with an alphamask on each object it's own outline group
        objects = c.get_hairs()
        objects.extend(c.get_outfits())
        objects.extend(c.get_alts())

        outline_starts = {}

        for ob in objects:
            #Get the length of the material list before starting
            outlineStart = len(ob.material_slots)
            outline_starts[ob.name] = outlineStart
            #link all polygons to material name
            mats_to_gons = {}
            for slot in ob.material_slots:
                mats_to_gons[slot.material.name] = []
            for gon in ob.data.polygons:
                    mats_to_gons[ob.material_slots[gon.material_index].material.name].append(gon)
            #find all materials that use an alpha mask or maintex
            alpha_users = []
            for mat in ob.material_slots:
                AlphaImage = mat.material.node_tree.nodes['_AM.png'].image    if mat.material.node_tree.nodes['_AM.png'].image.name    != 'Template: Placeholder' else None
                MainImage =  mat.material.node_tree.nodes['_light.png'].image if mat.material.node_tree.nodes['_light.png'].image.name != 'Template: Placeholder' else None
                if AlphaImage or MainImage:
                    alpha_users.append(mat.material.name)
            #reorder material_list to place alpha/maintex users first
            new_mat_list_order = [mat_slot.material.name for mat_slot in ob.material_slots if mat_slot.material.name not in alpha_users]
            new_mat_list_order = alpha_users + new_mat_list_order
            #reorder mat slot list
            for index, mat_slot in enumerate(ob.material_slots):
                mat_slot.material = bpy.data.materials[new_mat_list_order[index]]
            #create slots for new alpha user outlines
            for index, mat in enumerate(alpha_users):
                ob.data.materials.append(None)
                OutlineMat = bpy.data.materials[mat].copy()
                OutlineMat.name = bpy.data.materials[mat].name.replace('KK ', 'Outline ')
                OutlineMat.use_backface_culling = True
                OutlineMat.use_backface_culling_shadow = True
                OutlineMat.node_tree.links.remove(OutlineMat.node_tree.nodes['_light.png'].outputs[0].links[0])
                OutlineMat.node_tree.nodes['shader'].inputs['Light image'].default_value = (0, 0, 0, 1)
                ob.material_slots[index + outlineStart].material = OutlineMat
            #if the outline material is for a glasses material, disable it
                if bpy.data.materials[mat].get('glasses'):
                    OutlineMat.node_tree.links.remove(OutlineMat.node_tree.nodes['shader'].inputs['Light image alpha'].links[0])
            #update polygon material indexes
            for mat in mats_to_gons:
                for gon in mats_to_gons[mat]:
                    gon.material_index = new_mat_list_order.index(mat)

        #Add a general outline that covers the rest of the materials on the object that don't need transparency
        for ob in objects:
            bpy.context.view_layer.objects.active = ob
            mod = ob.modifiers.new(
                type='SOLIDIFY',
                name='Outline Modifier')
            mod.thickness = 0.0005
            mod.offset = 1
            mod.material_offset = outline_starts[ob.name]
            mod.use_flip_normals = True
            mod.use_rim = False
            mod.show_expanded = False
            finalOutlineMat = ob.material_slots[0].material.copy()
            finalOutlineMat.use_backface_culling = True
            finalOutlineMat.use_backface_culling_shadow = True
            finalOutlineMat.node_tree.nodes['_light.png'].image = bpy.data.images['Template: BlackWithAlpha']
            finalOutlineMat.node_tree.nodes['_AM.png'].image = bpy.data.images['Template: Placeholder']
            finalOutlineMat.name = 'Outline ' + ob.name
            ob.data.materials.append(finalOutlineMat)
        c.print_timer('add_outlines_to_hair_clothes')
