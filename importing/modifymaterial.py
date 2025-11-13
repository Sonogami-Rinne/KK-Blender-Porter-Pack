
# This file performs the following operations

#	Remove unused material slots on all objects
#	Remap duplicate material slots on all objects

#	Replace all materials with templates from the KK Shader file
# 	Remove all duplicate node groups after importing everything

# 	Import all textures from .pmx directory
# 	Saturates all main textures and creates dark versions of all main textures
# 	Load all textures to correct spot on all materials
# 	Sets up the normal smoothing geometry nodes group
# 	Sets up drivers to make the gag eye shapekeys work correctly

# 	Load all colors from KK_MaterialDataComplete.json to correct spot on all materials
# 	Adds an outline modifier and outline materials to the face, body, hair and outfit meshes

# Color and image saturation code taken from MediaMoots https://github.com/FlailingFog/KK-Blender-Porter-Pack/blob/ecad6a136e86aaf6c51194705157200797f91e5f/importing/importcolors.py
# Dark color conversion code taken from Xukmi https://github.com/xukmi/KKShadersPlus/tree/main/Shaders


import bpy
from pathlib import Path
from .. import common as c

class modify_material(bpy.types.Operator):
    bl_idname = "kkbp.modifymaterial"
    bl_label = bl_idname
    bl_description = bl_idname
    bl_options = {'REGISTER', 'UNDO'}

    def execute(self, context):
        try:
            is_svs = c.is_svs()

            self.load_materials()
            self.remove_unused_material_slots()
            self.remap_duplicate_material_slots()

            self.load_images()
            self.replace_materials_and_link_textures()
            self.SVS_set_body_alpha_mask()

            if not is_svs:
                self.change_body_render_method()
                self.replace_materials_for_tears_tongue_gageye()

            self.link_textures_for_tongue_tear_gag()
            self.import_and_setup_smooth_normals()
            if not is_svs:
                self.setup_gag_eye_material_drivers()

            c.clean_orphaned_data()
            return {'FINISHED'}
        except Exception as error:
            c.handle_error(self, error)
            return {"CANCELLED"}

    def load_materials(self):
        c.switch(c.get_body(), 'object')
        templateList = [
            'KK Body',
            'KK Tears',
            'KK Gag00',
            'KK Gag01',
            'KK Gag02',
            'KK EyeR (hitomi)',
            'KK EyeL (hitomi)',
            'KK Eyebrows (mayuge)',
            'KK Eyeline down',
            'KK Eyeline kage',
            'KK Eyeline up',
            'KK Eyewhites (sirome)',
            'KK Face',
            'KK General',
            'KK Hair',
            'KK Nose',
            'KK Teeth (tooth)',
            'KK Simple',
            'KK Glasses',
            'Outline General',
            'Outline Body',
            'KK Light Dark Texture',
            'KK Transparent',
            'SVS Light Dark Texture'
        ]
        c.import_from_library_file(category='Material', list_of_items=templateList, use_fake_user=True)
    # %% Main functions
    def remove_unused_material_slots(self):
        '''Remove unused mat slots on all visible objects'''
        objects = c.get_outfits()
        objects.extend(c.get_alts())
        objects.append(c.get_body)
        objects.extend(c.get_hairs())
        for object in objects:
            try:
                c.switch(object, 'object')
                bpy.ops.object.material_slot_remove_unused()

                #If this is an outfit, and there's only one material slot, check if it's a duplicate material.
                #If it's a duplicate the object actually had no materials to begin with, but the material_slot_remove_unused function left a slot behind
                #This can happen if the outfit does not contain any clothes
                if len(object.material_slots) == 1 and object.get('outfit') and bpy.data.objects.get('Hair ' + object.name):
                    if object.material_slots[0].material.get('id') == bpy.data.objects.get(object.name.replace('Ouftit', 'Hair Outfit')).material_slots[0].material.get('id'):
                        c.kklog(f'No materials detected in outfit "{object.name}". Deleting...', 'warn')
                        bpy.data.objects.remove(object)
            except:
                pass
        c.print_timer('remove_unused_material_slots')

    def remap_duplicate_material_slots(self):
        c.switch(c.get_body(), 'object')
        objects = c.get_outfits()
        objects.extend(c.get_alts())
        objects.append(c.get_body())
        objects.extend(c.get_hairs())


        for obj in objects:
            c.switch(obj, 'object')
            bpy.ops.object.material_slot_remove_unused()
            c.switch(obj, 'edit')
            #combine duplicated material slots
            for mat_name in [o.name for o in obj.data.materials]:
                index = 1
                base_material = bpy.data.materials.get(mat_name)
                while redundant_material := bpy.data.materials.get(f'{mat_name}.{index:03d}'):
                    index += 1
                    redundant_material.user_remap(base_material)
                    bpy.data.materials.remove(redundant_material)

            #then clean material slots by going through each slot and reassigning the slots that are repeated
            repeats = {}
            material_list = obj.data.materials
            for index, mat in enumerate(material_list):
                if mat.name not in repeats:
                    repeats[mat.name] = [index]
                else:
                    repeats[mat.name].append(index)

            for material_name in repeats.keys():
                if len(repeats[material_name]) > 1:
                    for repeated_slot in repeats[material_name]:
                        #don't touch the first slot
                        if repeated_slot == repeats[material_name][0]:
                            continue
                        c.kklog("Moving duplicate material {} in slot {} to the original slot {}".format(material_name, repeated_slot, repeats[material_name][0]))
                        obj.active_material_index = repeated_slot
                        bpy.ops.object.material_slot_select()
                        obj.active_material_index = repeats[material_name][0]
                        bpy.ops.object.material_slot_assign()
                        bpy.ops.mesh.select_all(action='DESELECT')
            c.switch(obj, 'object')
            bpy.ops.object.material_slot_remove_unused()
        c.print_timer('remap_duplicate_material_slots')

    def replace_materials_for_tears_tongue_gageye(self):

        #give the tears a material template
        c_name = c.get_name()
        if tears := c.get_tears():
            template = bpy.data.materials['KK Tears'].copy()
            template.name = 'KK Tears ' + c_name
            template['tears'] = True
            template['id'] = c.get_material_names('cf_O_namida_L')[0]
            tears.material_slots[0].material = bpy.data.materials[template.name]
            template_group = template.node_tree.nodes['textures'].node_tree.copy()
            template.node_tree.nodes['textures'].node_tree = template_group
            template_group.name += ' ' + c_name

        #replace tongue material if it exists
        if c.get_body().material_slots.get('KK General ' + c_name):
            #Make the tongue material unique so parts of the General Template aren't overwritten
            template = bpy.data.materials['KK General'].copy()
            template.name = 'KK Tongue ' + c_name
            template['tongue'] = True
            template['bake'] = True
            # template['id'] = c.get_material_names('o_tang')[0]
            for material_name in c.get_material_names('o_tang'): # avoid getting the deleted material
                if bpy.data.materials.get(material_name):
                    template['id'] = material_name
                    break
            if template.get('id') is None:
                c.kklog('Failed to replace tongue material', 'warn')

            c.get_body().material_slots['KK General ' + c_name].material = template
            template_group = template.node_tree.nodes['textures'].node_tree.copy()
            template.node_tree.nodes['textures'].node_tree = template_group
            template_group.name = 'Tex Tongue ' + c_name
            template_group_pos = template.node_tree.nodes['textures'].node_tree.nodes['pospattern'].node_tree.copy()
            template.node_tree.nodes['textures'].node_tree.nodes['pospattern'].node_tree = template_group_pos
            template_group_pos.name = 'Position Tongue ' + c_name

            #give the rigged tongue the existing material template
            if c.get_tongue():
                c.get_tongue().material_slots[0].material = template

        #give the gag eyes a material template if they exist
        if gag := c.get_gags():
            for num in ['00', '01', '02']:
                template = bpy.data.materials['KK Gag'+num].copy()
                template['gag'] = True
                template['id'] = c.get_material_names('cf_O_gag_eye_'+num)[0]
                gag.material_slots['cf_m_gageye_'+num].material = template
                template.name = 'KK Gag' + num + ' ' + c_name
                template_group = template.node_tree.nodes['textures'].node_tree.copy()
                template.node_tree.nodes['textures'].node_tree = template_group
                template_group.name = 'Tex Gag' + num + ' ' + c_name
        c.print_timer('replace_materials_for_tears_tongue_gageye')

    def load_images(self):
        c.switch(c.get_body(), 'object')
        file_dir = Path(bpy.context.scene.kkbp.import_dir)

        files = list(file_dir.rglob('**/pre_light/*'))
        files.extend(list(file_dir.rglob('**/pre_dark/*')))
        files.extend(list(file_dir.rglob('*_AM.png')))
        files.extend(list(file_dir.rglob('*_NMP_CNV.png')))
        files.extend(list(file_dir.rglob('*_NMPD_CNV.png')))
        files.extend(list(file_dir.rglob('*_Cloth_alpha.png')))
        files.extend(list(file_dir.rglob('*_Cloth_alpha_bot.png')))
        files.extend(list(file_dir.rglob('*_Normal_map.png')))
        files.extend(list(file_dir.rglob('*_Normal.png')))
        files.extend(list(file_dir.rglob('*_DetailNormal.png')))
        files.extend(list(file_dir.rglob('cf_m_gageye_0*.png')))
        files.extend(list(file_dir.rglob('cf_m_namida_00_MT_CT.png')))

        for file in files:
            bpy.ops.image.open(filepath=str(file), use_udim_detecting=False)
            try:
                bpy.data.images[file.name].pack()
            except:
                c.kklog(
                    'This image was not automatically loaded in because its filename exceeds 64 characters: ' + file.name, type='error')

    def replace_materials_and_link_textures(self):
        prefix = c.get_prefix()
        is_svs = c.is_svs()

        remap = {
            '_light.png': '_light.png',
            '_dark.png': '_dark.png',
            '_NMP_CNV.png': '_NMP_CNV.png',
            '_NMPD_CNV.png': '_NMPD_CNV.png',
            '_AM.png': '_AM.png',
            '_Normal_map.png': '_NMP_CNV.png',
            '_Normal.png': '_NMP_CNV.png',
            '_DetailNormal.png': '_NMPD_CNV.png'
        }

        textures = list(remap.keys())

        target_materials = c.json_file_manager.get_json_file(f"{prefix}_LightDarkMaterials.json")
        meshes = [('body', c.get_body()), ('tongue', c.get_tongue())]

        def swap_mesh_material(original_material: str, target_material: str, mesh_type: str, mesh):
            # remove dupes and check the material slot actually exists
            if mesh.material_slots.get(original_material):
                template = bpy.data.materials[target_material].copy()
                template[mesh_type] = True
                template['name'] = c.get_name()
                template['id'] = original_material
                template['coord'] = mesh.get('coord')
                template.name = prefix + ' ' + original_material
                mesh.material_slots[original_material].material = template
            else:
                c.kklog(
                    f'material or template wasn\'t found when replacing body materials: {str(original_material)}, {target_material}', 'warn')

        for hair in c.get_hairs():
            meshes.append(('hair', hair))
        for outfit in c.get_outfits():
            meshes.append(('outfit', outfit))
        for alt in c.get_alts():
            meshes.append(('outfit', alt))

        for mesh_type, mesh in meshes:
            if mesh is None:
                continue
            c.switch(mesh, 'OBJECT')
            if mesh.data.uv_layers is None:
                continue
            for material_name in target_materials:
                if (material_index := mesh.material_slots.find(material_name)) >= 0:
                    # Update the shader
                    swap_mesh_material(material_name, f'{prefix} Light Dark Texture', mesh_type, mesh)
                    material = mesh.material_slots[material_index].material
                    material.node_tree.nodes["shader"].inputs[0].default_value = 2 if material.name != 'KK cf_m_face_00' else 0

                    for texture_name in textures:
                        if image := bpy.data.images.get(material_name + texture_name):
                            material.node_tree.nodes[remap[texture_name]].image = image
                    material.node_tree.update_tag()

            for material_slot in mesh.material_slots:
                #  Replace mesh's materials that do not show in the list with a transparent one
                if not material_slot.material.name.startswith(prefix):
                    swap_mesh_material(material_slot.material.name, f'KK Transparent', mesh_type, mesh)

                #If the in-game shader of this material is set to "main alpha" or glasses, set the material to "blended" in blender
                shaders = ['Shader Forge/main_alpha', 'Koikano/main_clothes_alpha', 'xukmi/MainAlphaPlus', 'xukmi/MainAlphaPlusTess', 'xukmi/MainItemAlphaPlus', 'IBL_Shader_alpha',]
                #find this material in the MaterialDataComplete.json and see if it's an alpha shader
                material = material_slot.material
                if c.get_shader_name(material['id']) in shaders:
                    c.kklog('Detected alpha shader. Setting render method to blended: {}'.format(material['id']))
                    material.surface_render_method = 'BLENDED'
                    material.use_transparency_overlap = False
                
                shaders = ['Shader Forge/toon_glasses_lod0', 'Koikano/main_clothes_item_glasses']
                if c.get_shader_name(material['id']) in shaders:
                    c.kklog('Detected glasses shader. Setting render method to blended: {}'.format(material['id']))
                    material.surface_render_method = 'BLENDED'
                    material['glasses'] = True

                #special exception to clip the emblem image because I am tired of seeing it repeat at the edges
                if 'KK cf_m_emblem ' in material.name:
                    material.node_tree.nodes['_light.png'].extension = 'CLIP'
                    material.node_tree.nodes['_dark.png'].extension = 'CLIP'

        # Do not forget tongue.001
        if not is_svs and c.get_tongue():
            if (material_index := c.get_tongue().material_slots.find('cf_m_tang.001')) >= 0:
                swap_mesh_material('cf_m_tang.001', 'KK Light Dark Texture', 'tongue', c.get_tongue())
                for texture_name in textures:
                    if image := bpy.data.images.get('cf_m_tang' + texture_name):
                        c.get_tongue().material_slots[material_index].material.node_tree.nodes[texture_name] = image

        # force to update
        bpy.context.view_layer.update()
        bpy.context.evaluated_depsgraph_get().update()

    def SVS_set_body_alpha_mask(self):
        if not c.is_svs():
            return
        file_dir = Path(bpy.context.scene.kkbp.import_dir)
        material_name = c.json_file_manager.get_material_info_by_smr('o_body')[0]['MaterialInformation'][0]['MaterialName']
        material = c.get_body().material_slots.get('SVS ' + material_name).material

        # if files := list(file_dir.rglob('*_Cloth_alpha.png')):
        #     for fi in files:
        #
        for file in file_dir.rglob('*_Cloth_alpha.png'):
            if image := bpy.data.images.get(file.name):
                material.node_tree.nodes['_AM.png'].image = image
                break

        for file in file_dir.rglob('*_Cloth_alpha_bot.png'):
            if image := bpy.data.images.get(file.name):
                material.node_tree.nodes['_AMB.png'].image = image
                break

        material.node_tree.update_tag()

    def change_body_render_method(self):
        prefix = c.get_prefix()
        mats = c.get_material_names('cf_O_eyeline')
        for mat in [
            'cf_O_eyeline_low',
            'cf_O_noseline',
            'cf_O_mayuge',
            'cf_Ohitomi_L',
            'cf_Ohitomi_L02',
            'cf_Ohitomi_R02']:
            mats.extend(c.get_material_names(mat))

        for mat in mats:
            material = bpy.data.materials.get(f'{prefix} ' + mat)
            if material:
                material.surface_render_method = 'BLENDED'
            # material.use_transparency_overlap = False
        
        #move the eyeline down material slot up so it doesn't appear over the eyeline up
        body = c.get_body()
        c.switch(body, 'object')
        if mat := body.material_slots.get('KK cf_m_eyeline_down'):
            print(body.data.materials.find(mat.name))
            body.active_material_index = body.data.materials.find(mat.name)
            bpy.ops.object.material_slot_move(direction='UP')
            bpy.ops.object.material_slot_move(direction='UP')
        
    def link_textures_for_tongue_tear_gag(self):

        #load all gag eye textures if it exists
        if c.get_gags():
            self.image_load('Gag00', '_cf_t_gageye_00_MT_CT.png')
            self.image_load('Gag00', '_cf_t_gageye_02_MT_CT.png')
            self.image_load('Gag00', '_cf_t_gageye_04_MT_CT.png')
            self.image_load('Gag00', '_cf_t_gageye_05_MT_CT.png')
            self.image_load('Gag00', '_cf_t_gageye_06_MT_CT.png')
            self.image_load('Gag01', '_cf_t_gageye_03_MT_CT.png')
            self.image_load('Gag01', '_cf_t_gageye_01_MT_CT.png')
            self.image_load('Gag02', '_cf_t_gageye_07_MT_CT.png')
            self.image_load('Gag02', '_cf_t_gageye_08_MT_CT.png')
            self.image_load('Gag02', '_cf_t_gageye_09_MT_CT.png')

        #load the tears texture in
        if c.get_tears():
            self.image_load('Tears', '_MT_CT.png')

        c.print_timer('link_textures_for_tongue_tear_gag')

    def import_and_setup_smooth_normals(self):
        '''Sets up the Smooth Normals geo nodes setup for smoother face, body, hair and clothes normals'''
        try:
            #import all the node groups
            body = c.get_body()
            c.import_from_library_file('NodeTree', ['.Raw Shading (smooth normals)', '.Raw Shading (smooth body normals)', '.Smooth Normals', '.Other Smooth Normals'], True)
            c.switch(body, 'object')
            geo_nodes = body.modifiers.new(name = 'Normal Smoothing', type = 'NODES')
            geo_nodes.node_group = bpy.data.node_groups['.Smooth Normals']
            geo_nodes.show_viewport = False
            geo_nodes.show_render = False
            for ob in c.get_hairs():
                geo_nodes = ob.modifiers.new(name = 'Normal Smoothing', type = 'NODES')
                geo_nodes.node_group = bpy.data.node_groups['.Other Smooth Normals']
                geo_nodes.show_viewport = False
                geo_nodes.show_render = False
            outfits = c.get_outfits()
            outfits.extend(c.get_alts())
            for ob in outfits:
                geo_nodes = ob.modifiers.new(name = 'Normal Smoothing', type = 'NODES')
                geo_nodes.node_group = bpy.data.node_groups['.Other Smooth Normals']
                geo_nodes.show_viewport = False
                geo_nodes.show_render = False
        except:
            #i don't feel like dealing with any errors related to this
            c.kklog('The normal smoothing wasnt setup correctly. Oh well.', 'warn')
        c.print_timer('import_and_setup_smooth_normals')

    def setup_gag_eye_material_drivers(self):
        '''setup gag eye drivers'''
        if c.get_gags():
            body = c.get_body()
            gag_keys = [
                'Circle Eyes 1',
                'Circle Eyes 2',
                'Spiral Eyes',
                'Heart Eyes',
                'Fiery Eyes',
                'Cartoony Wink',
                'Vertical Line',
                'Cartoony Closed',
                'Horizontal Line',
                'Cartoony Crying'
            ]

            def create_driver(material, expression1, expression2):
                skey_driver = bpy.data.materials[material].node_tree.nodes['Parser'].inputs[0].driver_add('default_value')
                skey_driver.driver.type = 'SCRIPTED'
                for key in gag_keys:
                    newVar = skey_driver.driver.variables.new()
                    newVar.name = key.replace(' ','')
                    newVar.type = 'SINGLE_PROP'
                    newVar.targets[0].id_type = 'KEY'
                    newVar.targets[0].id = body.data.shape_keys
                    newVar.targets[0].data_path = 'key_blocks["' + key + '"].value'
                skey_driver.driver.expression = expression1
                skey_driver = bpy.data.materials[material].node_tree.nodes['hider'].inputs[0].driver_add('default_value')
                skey_driver.driver.type = 'SCRIPTED'
                for key in gag_keys:
                    newVar = skey_driver.driver.variables.new()
                    newVar.name = key.replace(' ','')
                    newVar.type = 'SINGLE_PROP'
                    newVar.targets[0].id_type = 'KEY'
                    newVar.targets[0].id = body.data.shape_keys
                    newVar.targets[0].data_path = 'key_blocks["' + key + '"].value'
                skey_driver.driver.expression = expression2

            create_driver (
                'KK Gag00 ' + c.get_name(),
                '0 if CircleEyes1 else 1 if CircleEyes2 else 2 if CartoonyClosed else 3 if VerticalLine else 4',
                'CircleEyes1 or CircleEyes2 or CartoonyClosed or VerticalLine or HorizontalLine'
                )

            create_driver (
                'KK Gag01 ' + c.get_name(),
                '0 if HeartEyes else 1',
                'HeartEyes or SpiralEyes'
                )

            create_driver (
                'KK Gag02 ' + c.get_name(),
                '0 if CartoonyCrying else 1 if CartoonyWink else 2',
                'CartoonyCrying or CartoonyWink or FieryEyes'
                )
        c.print_timer('setup_gag_eye_material_drivers')

    # %% Supporting functions
    @staticmethod
    def apply_texture_data_to_image(mat: str, image: str, node:str, group = 'textures'):
        '''Sets offset and scale of an image node using the TextureData.json '''
        json_tex_data = c.json_file_manager.get_json_file('KK_TextureData.json')
        texture_data = [t for t in json_tex_data if t["textureName"] == image]
        if texture_data and bpy.data.materials.get(mat):
            #Apply Offset and Scale
            bpy.data.materials[mat].node_tree.nodes[group].node_tree.nodes[node].texture_mapping.translation[0] = texture_data[0]["offset"]["x"]
            bpy.data.materials[mat].node_tree.nodes[group].node_tree.nodes[node].texture_mapping.translation[1] = texture_data[0]["offset"]["y"]
            bpy.data.materials[mat].node_tree.nodes[group].node_tree.nodes[node].texture_mapping.scale[0] = texture_data[0]["scale"]["x"]
            bpy.data.materials[mat].node_tree.nodes[group].node_tree.nodes[node].texture_mapping.scale[1] = texture_data[0]["scale"]["y"]

    def image_load(self, material_name: str, image_suffix = '', image_override = None, node_override = None, group_override = None):
        '''Automatically load image into mat's texture slot'''
        #get the id from the material
        material_name = 'KK ' + material_name + ' ' + c.get_name()
        material = bpy.data.materials[material_name]
        #get the image name using the id and the suffix
        image_name = image_override if image_override else material['id'] + image_suffix
        #then load the image into the texture slot
        if bpy.data.images.get(image_name):
            node = node_override if node_override else image_name.replace(material['id'], '')
            group = group_override if group_override else 'textures'
            bpy.data.materials[material_name].node_tree.nodes[group].node_tree.nodes[node].image = bpy.data.images[image_name]
            #also apply scaling and offset data to the image
            self.apply_texture_data_to_image(material_name, image_name, node, group)
        else:
            c.kklog('File wasnt found, skipping: ' + image_name)
