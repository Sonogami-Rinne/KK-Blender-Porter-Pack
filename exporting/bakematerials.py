# BAKE MATERIAL TO TEXTURE SCRIPT
#  Bakes all materials of an object into image textures (to use in other programs)
#  Will only bake a material if an image node is present in the green texture group
#  If no image is present, a low resolution failsafe image will be baked to account for 
#      fully opaque or transparent materials that don't rely on a texture file
#  If there are multiple image resolutions, only the highest resolution be baked
#  Materials are baked to an 8-bit PNG with an alpha channel.
#  (optional) Creates a copy of the model and generates a material atlas to the copy

# Notes:
# - This script deletes all camera objects in the scene
# - fillerplane driver + shader code taken from https://blenderartists.org/t/scripts-create-camera-image-plane/580839
# - material combiner code taken from https://github.com/Grim-es/material-combiner-addon/


import bpy, os, traceback, time, pathlib, subprocess
from .. import common as c
from ..interface.dictionary_en import t

def print_memory_usage(stri):
    run = subprocess.run('wmic OS get FreePhysicalMemory', capture_output=True)
    c.kklog((stri, '\n   mem usage ', 16000 - int(run.stdout.split(b'\r')[2].split(b'\n')[1])/1000))

#setup and return a camera
def setup_camera():
    #Delete all cameras in the scene
    for obj in bpy.context.scene.objects:
        if obj.type == 'CAMERA':
            obj.select_set(True)
        else:
            obj.select_set(False)
    bpy.ops.object.delete()
    for block in bpy.data.cameras:
        if block.users == 0:
            bpy.data.cameras.remove(block)
   
    #Add a new camera
    bpy.ops.object.camera_add(enter_editmode=False, align='VIEW', location=(0, 0, 1), rotation=(0, 0, 0))
    #save it for later
    camera = bpy.context.active_object
    #and set it as the active one
    bpy.context.scene.camera=camera
    #Set camera to orthographic
    bpy.data.cameras[camera.name].type='ORTHO'
    bpy.data.cameras[camera.name].ortho_scale=6
    bpy.context.scene.render.pixel_aspect_y=1
    bpy.context.scene.render.pixel_aspect_x=1
    return camera

def setup_geometry_nodes_and_fillerplane(camera: bpy.types.Object):
    object_to_bake = bpy.context.active_object

    #create fillerplane
    bpy.ops.mesh.primitive_plane_add()
    fillerplane = bpy.context.active_object
    c.switch(fillerplane, 'object')
    fillerplane.data.materials.append(None)
    fillerplane.data.uv_layers[0].name = 'uv_main'
    fillerplane.name = "fillerplane"
    bpy.ops.object.editmode_toggle()
    bpy.ops.mesh.select_all(action='SELECT')
    bpy.ops.transform.resize(value=(0.5,0.5,0.5))
    bpy.ops.uv.reset()
    bpy.ops.object.editmode_toggle()

    fillerplane.location = (0,0,-0.0001)

    def setup_driver_variables(driver, camera):
        cam_ortho_scale = driver.variables.new()
        cam_ortho_scale.name = 'cOS'
        cam_ortho_scale.type = 'SINGLE_PROP'
        cam_ortho_scale.targets[0].id_type = 'CAMERA'
        cam_ortho_scale.targets[0].id = bpy.data.cameras[camera.name]
        cam_ortho_scale.targets[0].data_path = 'ortho_scale'
        resolution_x = driver.variables.new()
        resolution_x.name = 'r_x'
        resolution_x.type = 'SINGLE_PROP'
        resolution_x.targets[0].id_type = 'SCENE'
        resolution_x.targets[0].id = bpy.context.scene
        resolution_x.targets[0].data_path = 'render.resolution_x'
        resolution_y = driver.variables.new()
        resolution_y.name = 'r_y'
        resolution_y.type = 'SINGLE_PROP'
        resolution_y.targets[0].id_type = 'SCENE'
        resolution_y.targets[0].id = bpy.context.scene
        resolution_y.targets[0].data_path = 'render.resolution_y'
    
    #setup X scale for bake object and plane
    driver = object_to_bake.driver_add('scale',0).driver
    driver.type = 'SCRIPTED'
    setup_driver_variables(driver, camera)
    driver.expression = "((r_x)/(r_y)*(cOS)) if (((r_x)/(r_y)) < 1) else (cOS)"

    driver = fillerplane.driver_add('scale',0).driver
    driver.type = 'SCRIPTED'
    setup_driver_variables(driver, camera)
    driver.expression = "((r_x)/(r_y)*(cOS)) if (((r_x)/(r_y)) < 1) else (cOS)"

    #setup drivers for object's Y scale
    driver = object_to_bake.driver_add('scale',1).driver
    driver.type = 'SCRIPTED'
    setup_driver_variables(driver, camera)
    driver.expression = "((r_y)/(r_x)*(cOS)) if (((r_y)/(r_x)) < 1) else (cOS)"

    driver = fillerplane.driver_add('scale',1).driver
    driver.type = 'SCRIPTED'
    setup_driver_variables(driver, camera)
    driver.expression = "((r_y)/(r_x)*(cOS)) if (((r_y)/(r_x)) < 1) else (cOS)"

    ###########################
    #import the premade flattener node to unwrap the mesh into the UV structure
    c.import_from_library_file('NodeTree', ['.Geometry Nodes'])

    #give the object a geometry node modifier
    geonodes_mod = object_to_bake.modifiers.new('Flattener', 'NODES')
    geonodes_mod.node_group = bpy.data.node_groups['.Geometry Nodes']
    identifier = [str(i) for i in geonodes_mod.keys()][0]
    geonodes_mod[identifier+'_attribute_name'] = 'uv_main'
    geonodes_mod[identifier+'_use_attribute'] = True

    #Make the originally selected object active again
    c.switch(object_to_bake, 'OBJECT')

##############################
#Changes the material of the image plane to the material of the object,
# and then puts a render of the image plane into the specified folder

def sanitizeMaterialName(text: str) -> str:
    '''Mat names need to be sanitized else you can't delete the files with windows explorer'''
    for ch in ['\\','`','*','<','>','.',':','?','|','/','\"']:
        if ch in text:
            text = text.replace(ch,'')
    return text

def bake_pass(folderpath: str, bake_type: str):
    '''Folds the body / clothes / hair down to a UV rectangle
    Places a filler plane right below it to fill in the rest of the image
    Bakes all materials on this object down to an image using the orthographic camera
    '''
    #get the currently selected object as the active object
    object_to_bake = bpy.context.active_object
    #remember what order the materials are in for later
    original_material_order = []
    for matslot in object_to_bake.material_slots:
        original_material_order.append(matslot.name)

    #if this is a light or dark pass, make sure the color output is a constant light or dark
    combine = bpy.data.node_groups['.Combine colors']
    combine.links.remove(combine.nodes['mix'].inputs[0].links[0])
    combine.nodes['mix'].inputs[0].default_value = 1 if bake_type == 'light' else 0

    #go through each material slot
    for index, current_material in enumerate(object_to_bake.data.materials):
        #Don't bake this material if it doesn't have the bake tag
        if not current_material.get('edit'):
            c.kklog(f'Detected material that cannot be finalized. Skipping: {current_material.name}')
            continue

        nodes = current_material.node_tree.nodes
        links = current_material.node_tree.links
        
        #Turn off the normals for the toon_shading shading node group input if this isn't a normal pass
        if nodes.get('textures') and bake_type != 'normal':
            toon_shading = nodes.get('textures').node_tree.nodes.get('shade')
            if toon_shading:
                original_normal_state = toon_shading.inputs[1].default_value
                toon_shading.inputs[1].default_value = 0

        #if this is a normal pass, attach the normal passthrough to the output
        elif nodes.get('textures') and bake_type == 'normal':
            if len(nodes['textures'].outputs):
                links.remove(nodes['out'].inputs[0].links[0])
                links.new(nodes['textures'].outputs[-1], nodes['out'].inputs[0])
        
        if nodes.get('textures'):
            #Go through each of the textures loaded into the textures group and get the highest resolution one
            highest_resolution = [0, 0]
            for image_node in nodes['textures'].node_tree.nodes:
                if image_node.type == 'TEX_IMAGE' and image_node.image:
                    image_size = image_node.image.size[0] * image_node.image.size[1]
                    largest_so_far = highest_resolution[0] * highest_resolution[1]
                    if image_size > largest_so_far:
                        highest_resolution = image_node.image.size
            
            resolution_multiplier = 1 #bpy.context.scene.kkbp.bake_mult
            #Render an image using the highest dimensions
            if highest_resolution:
                bpy.context.scene.render.resolution_x=highest_resolution[0] * resolution_multiplier
                bpy.context.scene.render.resolution_y=highest_resolution[1] * resolution_multiplier
            else:
                #if no images were found, render a 64px failsafe image anyway to catch 
                # materials that are a solid color, don't rely on textures, or are completely transparent
                bpy.context.scene.render.resolution_x=64
                bpy.context.scene.render.resolution_y=64

            #set every material slot except the current material to be transparent
            for matslot in object_to_bake.material_slots:
                if matslot.material != current_material:
                    matslot.material = bpy.data.materials['KK Transparent']
            
            #set the filler plane to the current material
            bpy.data.objects['fillerplane'].material_slots[0].material = current_material

            #then render it
            matname = sanitizeMaterialName(current_material.name)
            matname = matname[:-4] if matname[-4:] == '-ORG' else matname
            bpy.context.scene.render.filepath = folderpath + matname + ' ' + bake_type
            bpy.context.scene.render.image_settings.file_format='PNG'
            bpy.context.scene.render.image_settings.color_mode='RGBA'
            
            print('Rendering {} / {}'.format(index+1, len(object_to_bake.data.materials)))
            bpy.ops.render.render(write_still = True)

            #reset folderpath after render
            bpy.context.scene.render.filepath = folderpath
            
        #Restore the value in the toon_shading shading node group for the normals
        if nodes.get('textures') and bake_type != 'normal':
            toon_shading = nodes.get('textures').node_tree.nodes.get('shade')
            if toon_shading:
                toon_shading.inputs[1].default_value = original_normal_state
        
        #Restore the links if they were edited for the normal pass
        elif nodes.get('textures') and bake_type == 'normal':
            if len(nodes['textures'].outputs):
                links.remove(nodes['out'].inputs[0].links[0])
                links.new(nodes['combine'].outputs[0], nodes['out'].inputs[0])

        #reset material slots to their original order
        for material_index in range(len(original_material_order)):
            object_to_bake.material_slots[material_index].material = bpy.data.materials[original_material_order[material_index]]
    
    #reset the color output group link
    combine = bpy.data.node_groups['.Combine colors']
    combine.links.new(combine.nodes['input'].outputs[2], combine.nodes['mix'].inputs[0])

def cleanup():
    # Deselect all objects
    bpy.ops.object.select_all(action='DESELECT')
    #Select the camera
    for camera in [o for o in bpy.data.objects if o.type == 'CAMERA']:
        bpy.data.objects.remove(camera)
    #Select fillerplane
    for fillerplane in [o for o in bpy.data.objects if 'fillerplane' in o.name]:
        bpy.data.objects.remove(fillerplane)
    #delete orphan data
    for block in bpy.data.meshes:
        if block.users == 0:
            bpy.data.meshes.remove(block)
    for block in bpy.data.cameras:
        if block.users == 0:
            bpy.data.cameras.remove(block)
    for ob in [obj for obj in bpy.context.view_layer.objects if obj and obj.type == 'MESH']:
        #delete the geometry modifier
        if ob.modifiers.get('Flattener'):
            ob.modifiers.remove(ob.modifiers['Flattener'])
            #delete the two scale drivers
            ob.animation_data.drivers.remove(ob.animation_data.drivers[0])
            ob.animation_data.drivers.remove(ob.animation_data.drivers[0])
            ob.scale = (1,1,1)
    bpy.data.node_groups.remove(bpy.data.node_groups['.Geometry Nodes'])

def get_image_node(bake_type):
    dict = {
        'light': '_light.png',
        'dark' : '_dark.png',
        'normal':'_NMP_CNV.png',
        'detail':'_light.png',
    }
    return dict[bake_type]

def replace_all_baked_materials(folderpath: str, bake_object: bpy.types.Object):
    #load all baked images into blender
    fileList = pathlib.Path(folderpath).glob('*.png')
    files = [file for file in fileList if file.is_file()]
    for file in files:
        try:
            image = bpy.data.images.load(filepath=str(file))
            image.pack()
            #if there was an older version of this image, get rid of it
            if image.name[-4:] == '.001':
                if bpy.data.images.get(image.name[:-4]):
                    bpy.data.images[image.name[:-4]].user_remap(image)
                    bpy.data.images.remove(bpy.data.images[image.name[:-4]])
                    image.name = image.name[:-4]
        except:
            c.kklog(f'Could not load in file because the name exceeds 64 characters: {file}')
    
    #now all needed images are loaded into the file. Match each material to it's image textures
    for bake_type in ['light', 'dark']:
        for slot in bake_object.material_slots:
            image = bpy.data.images.get(slot.material.name.replace('-ORG', '') + f' {bake_type}.png', '')
            print(image)
            print(slot.name.replace('Edit ', 'KK '))
            print(slot.material.get(slot.name.replace('Edit ', 'KK ')))
            if image:
                if original := bpy.data.materials.get(slot.name.replace('Edit ', 'KK ')):
                    slot.material = original
                    original.node_tree.nodes[get_image_node(bake_type)].image = image

class bake_materials(bpy.types.Operator):
    bl_idname = "kkbp.bakematerials"
    bl_label = "Bake and generate atlased model"
    bl_description = t('bake_mats_tt')
    bl_options = {'REGISTER', 'UNDO'}
        
    def execute(self, context):
        try:
            #just use the pmx folder for the baked files
            scene = context.scene.kkbp
            folderpath = os.path.join(context.scene.kkbp.import_dir, 'baked_files', '')
            last_step = time.time()
            # c.toggle_console()
            c.reset_timer()
            c.kklog('Switching to EEVEE for material baking...')
            bpy.context.scene.render.engine = 'BLENDER_EEVEE_NEXT'
            c.switch(c.get_body(), 'OBJECT')
            c.set_viewport_shading('SOLID')
            
            #enable transparency
            bpy.context.scene.render.film_transparent = True
            bpy.context.scene.render.filter_size = 0.50

            for bake_object in c.get_all_bakeable_objects():
                #do a quick check to make sure this object has any materials that can be baked
                worth_baking = [m for m in bake_object.material_slots if m.material.get('edit')]
                if not worth_baking:
                    c.kklog(f'Not finalizing object because there were no materials worth baking: {bake_object.name}')
                    continue

                #make sure the collection for this object is enabled in the outliner if it is a clothing item
                if bake_object != c.get_body():
                    original_collection_state = c.get_layer_collection_state(bake_object.users_collection[0].name)
                    c.show_layer_collection(bake_object.users_collection[0].name, False)

                #hide all objects except this one
                for obj in [o for o in bpy.context.view_layer.objects if o]:
                    obj.hide_render = True
                camera = setup_camera()
                c.switch(bake_object)
                setup_geometry_nodes_and_fillerplane(camera)
                bpy.ops.wm.redraw_timer(type='DRAW_WIN_SWAP', iterations=1)                

                #perform the baking operation
                bake_types = ['light', 'dark', 'normal']
                for bake_type in bake_types:
                    bake_pass(folderpath, bake_type)
                cleanup()

                #restore the original collection state 
                if bake_object != c.get_body():
                    c.show_layer_collection(bake_object.users_collection[0].name, original_collection_state)
            
            #disable transparency
            bpy.context.scene.render.film_transparent = False
            bpy.context.scene.render.filter_size = 1.5
            for bake_object in c.get_all_bakeable_objects():
                replace_all_baked_materials(folderpath, bake_object)
            
            #show all objects again
            for obj in bpy.context.view_layer.objects:
                obj.hide_render = False
            
            c.kklog('Finished in ' + str(time.time() - last_step)[0:4] + 's')
            c.set_viewport_shading('SOLID')
            return {'FINISHED'}
        except:
            c.kklog('Unknown python error occurred', type = 'error')
            c.kklog(traceback.format_exc())
            c.set_viewport_shading('SOLID')
            self.report({'ERROR'}, traceback.format_exc())
            return {"CANCELLED"}

