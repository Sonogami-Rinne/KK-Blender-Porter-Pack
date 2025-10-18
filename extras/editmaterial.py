import bpy, numpy, math, time, concurrent.futures, threading, queue, os
from pathlib import Path
from ..interface.dictionary_en import t
from .. import common as c

class edit_material(bpy.types.Operator):
    bl_idname = "kkbp.editmaterial"
    bl_label = "Edit material"
    bl_description = 'Edit material'
    bl_options = {'REGISTER', 'UNDO'}

    #  numpy's precision
    np_number_precision = numpy.float32

    # these three parameters should be exposed in the gui and decided by user
    # This is how many cpu cores you want to use to saturate the images. 
    # If you have a better CPU, you can set it higher.
    kkbp_package_name = __package__[:__package__.rindex('.')]
    max_thread_num = bpy.context.preferences.addons[kkbp_package_name].preferences.max_thread_num

    # this is related to memory usage.
    # Actually it's not perfect because the size of each image varies.
    # If loading four 4096 * 4096, the peak memory usage could reach 16000MB.
    # If the user doesn't have this much available memory, the program will crash.
    # In that case, the user should lower the value
    max_image_num = bpy.context.preferences.addons[kkbp_package_name].preferences.max_image_num

    # this is related to cpu and memory usage.
    # This is the number of rows of pixels to process in one batch (images are saturated in batches).
    # Simply separate images in rows, ignoring that the num of column usually increase as num of rows increasing
    # For a 1024 * 1024, a batch is 512 * 1024.But for 2048 * 2048, a batch is 512 * 2048
    batch_rows = bpy.context.preferences.addons[kkbp_package_name].preferences.batch_rows

    # constants for later
    lut_pixels = None
    coord_scale = None
    coord_offset = None
    texel_height_X0 = None
    # used to protect the data_queue
    queue_lock = threading.Lock()
    data_queue = queue.Queue()

    remap_dict = {
        'cf_m_face_00':                      'KK Face',
        'cf_m_mayuge_00':                    'KK Eyebrows (mayuge)',
        'cf_m_noseline_00':                  'KK Nose',
        'cf_m_eyeline_down':                 'KK Eyeline down',
        'cf_m_eyeline_00_up':                'KK Eyeline up',
        'cf_m_hitomi_00_cf_Ohitomi_L02':     'KK EyeL (hitomi)',
        'cf_m_hitomi_00_cf_Ohitomi_R02':     'KK EyeR (hitomi)',
        'cf_m_sirome_00':                    'KK Eyewhites (sirome)',
        'cf_m_body':                         'KK Body',
        'cf_m_tooth':                        'KK Teeth (tooth)',
        'o_tang':                            'KK General',}

    def execute(self, context):
        c.json_file_manager.init()

        #replace the material with the correct template
        c.switch(bpy.context.object, 'object')
        original_material = bpy.context.object.active_material
        if original_material.get('hair'):
            new_material = self.replace_materials_for_hair_clothes('hair')
            self.load_images(new_material.name)
            self.link_textures_for_face_body(new_material.name)
            self.create_dark_textures(new_material.name)       
            self.load_json_colors(new_material.name, 'hair')
            
        elif original_material.get('outfit'):
            new_material = self.replace_materials_for_hair_clothes('outfit')
            self.load_images(new_material.name)
            self.link_textures_for_face_body(new_material.name)
            self.create_dark_textures(new_material.name)       
            self.load_json_colors(new_material.name, 'outfit')

        elif original_material.get('body'):
            new_material = self.replace_materials_for_body()
            self.load_images(new_material.name)
            self.link_textures_for_face_body(new_material.name)
            self.create_dark_textures(new_material.name)       
            self.load_json_colors(new_material.name, 'body')
            if 'cf_m_hitomi_00' in original_material.name:
                self.adjust_pupil_highlight()
            
        new_material['edit'] = True
 
        return {'FINISHED'}
    
    def init_prefab_data(self):
        '''Initialize constants for saturating textures'''
        self.lut_pixels = numpy.array(bpy.data.images['Lut_TimeDay.png'].pixels[:],dtype=self.np_number_precision).reshape(bpy.data.images['Lut_TimeDay.png'].size[1], bpy.data.images['Lut_TimeDay.png'].size[0], 4)
        #constants to ensure bot and top are within the 32 x 1024 dimensions of the lut
        self.coord_scale = numpy.array([0.0302734375, 0.96875, 31.0],dtype=self.np_number_precision)
        self.coord_offset = numpy.array([0.5 / 1024, 0.5 / 32, 0.0], dtype=self.np_number_precision)
        self.texel_height_X0 = numpy.array([1 / 32, 0], dtype=self.np_number_precision)
        

    def replace_materials_for_hair_clothes(self, type: str):
        '''Replace the selected material with the appropriate template'''
        object = bpy.context.object
        original_name = bpy.context.object.active_material.name
        original_material = bpy.context.object.active_material
        original_material.use_fake_user = True
        material_slot = object.material_slots[original_name]
        if not bpy.data.materials.get('KK Hair' if type == 'hair' else 'KK General'):
            c.import_from_library_file('Material', ['KK Hair' if type == 'hair' else 'KK General'])
        template = bpy.data.materials['KK Hair' if type == 'hair' else 'KK General'].copy()
        template['hair' if type == 'hair' else 'outfit'] = True
        template['name'] = c.get_name()

        template['id'] = original_material['id']
        template.name = original_name.replace('KK ', 'Edit ')
        material_slot.material = bpy.data.materials[template.name]

        template_group = template.node_tree.nodes['textures'].node_tree.copy()
        template_group.name = 'Tex ' + original_name + ' ' + c.get_name()
        template.node_tree.nodes['textures'].node_tree = template_group

        template_group_pos = template.node_tree.nodes['textures'].node_tree.nodes['pospattern'].node_tree.copy()
        template_group_pos.name = 'Pos ' + original_name + ' ' + c.get_name()
        template.node_tree.nodes['textures'].node_tree.nodes['pospattern'].node_tree = template_group_pos

        return template

    def replace_materials_for_body(self):
        original_name = bpy.context.object.active_material.name
        original_material = bpy.context.object.active_material
        original_material.use_fake_user = True
        
        for base_name in self.remap_dict:
            if base_name in original_name:
                new_material_name = self.remap_dict[base_name]
                if not bpy.data.materials.get(new_material_name):
                    c.import_from_library_file('Material', [new_material_name])
                template = bpy.data.materials[new_material_name].copy()
                template['body'] = True
                template['name'] = original_material['name']
                template['id'] = original_material['id']
                template.name = original_material.name.replace('KK ', 'Edit ')
                c.get_body().material_slots[original_material.name].material = template
                template_group = template.node_tree.nodes['textures'].node_tree.copy()
                template_group.name = 'Tex ' + original_material.name + ' ' + c.get_name()
                template.node_tree.nodes['textures'].node_tree = template_group
                return template
        
        c.kklog(f'An appropriate template was not found, so this body material cannot be edited: {original_material.name}', 'error')
        return None

    def load_images(self, material_to_load):
        file_dir = os.path.dirname(__file__)
        lut_image = os.path.join(file_dir, 'Lut_TimeDay.png')
        lut_image = bpy.data.images.load(str(lut_image), check_existing = True)
        lut_image.use_fake_user = True
        self.init_prefab_data()
        prefixes = material_to_load.replace('Edit ', '')

        fileList = Path(bpy.context.scene.kkbp.import_dir).rglob(f'{prefixes}*.png')
        files = [file for file in fileList if file.is_file() and "_MT" in file.name]
        unloaded = unprocessed = len(files) # unloaded: unloaded images to saturate, unprocessed: unfinished images that still need to be saturated
        last_miss_time = time.time()  # last time of accessing queue
        current_image_num = 0  # current num of concurrent processing images
        futures = []
        record = {}  # as each image is separated to several batches, this is to record each image's base info

        with concurrent.futures.ThreadPoolExecutor(max_workers=self.max_thread_num) as executor:
            # the to-output data occupies a lot of memory, so we should save them timely before loading more images
            while unloaded > 0 or unprocessed > 0:
                if (current_time := time.time()) - last_miss_time > 0.3:  # accessing queue every 0.3s, because queue is empty most of the time, so is no need to access it every loop
                    with self.queue_lock:
                        try:
                            while True: # fetching all data from queue if not empty
                                result = self.data_queue.get(timeout=0.1)
                                (result := record[result])[0] -= 1  # data in tuple: (current_image's batch num, name that the image to be saved with, image, image_data in numpy array, start time to process this image)
                                # record[result][0] -= 1
                                if result[0] == 0:
                                    image = result[2]
                                    image_pixels = result[3]
                                    image.pixels.foreach_set(image_pixels.ravel())
                                    image.save_render(os.path.join(bpy.context.scene.kkbp.import_dir, "saturated_files", result[1]))

                                    del image_pixels
                                    unprocessed -= 1
                                    current_image_num -= 1
                                    c.kklog(f'Saturating image {result[1]} takes {round(time.time() - result[4], 1)}s')
                        except queue.Empty:
                            last_miss_time = current_time
                # if there has unloaded images and current num of image in processing is smaller than the max value, then load a image and submit it.This prevent loading too many images, which pushes memory usage to a high level
                if unloaded > 0 and current_image_num < self.max_image_num:
                    unloaded -= 1
                    # skip this file if it has already been converted
                    if os.path.isfile(os.path.join(bpy.context.scene.kkbp.import_dir, 'saturated_files', (save_file_name := files[unloaded].name.replace('_MT', '_ST')))):
                        c.kklog('File already saturated. Skipping {}'.format(files[unloaded].name))
                        unprocessed -= 1
                        continue

                    current_image_num += 1
                    # Load image
                    start_time = time.time()
                    image = bpy.data.images.load(str(files[unloaded]))

                    # Submit task
                    width, height = image.size
                    image_pixels = numpy.array(image.pixels[:], dtype=self.np_number_precision).reshape(height, width, 4)

                    # separating an image to several batches to make full use of CPU
                    start_row = 0
                    while start_row < height:
                        end_row = start_row + self.batch_rows
                        if end_row > height:
                            end_row = height

                        future = executor.submit(
                            self.saturate_texture,
                            unloaded,
                            image_pixels[start_row:end_row],
                            start_row == 0
                        )
                        start_row = end_row

                        futures.append(future)

                    record[unloaded] = [math.ceil(height / self.batch_rows), save_file_name, image, image_pixels, start_time]

            bpy.data.use_autopack = True  # enable autopack on file save

            # Load all textures
            fileList = Path(bpy.context.scene.kkbp.import_dir).rglob(f'{prefixes}*.png')
            files = [file for file in fileList if file.is_file()]
            for image_file in files:
                bpy.ops.image.open(filepath=str(image_file), use_udim_detecting=False)
                try:
                    bpy.data.images[image_file.name].pack()
                except:
                    c.kklog('This image was not automatically loaded in because its filename exceeds 64 characters: ' + image_file.name, type = 'error')

            # Monitor completion
            for future in concurrent.futures.as_completed(futures):
                try:
                    future.result()
                except Exception as e:
                    c.kklog(f'Processing failed: {str(e)}')

        c.print_timer('load_images')

    def link_textures_for_face_body(self, new_material_name):
        '''Load all body textures into their texture slots'''

        for base_name in self.remap_dict:
            if base_name in new_material_name:
                match base_name:
                    case 'cf_m_face_00':
                        #load in face textures
                        c.kklog('wtf')
                        self.image_load('cf_m_face_00', '_ST_CT.png')
                        self.image_load('cf_m_face_00', '_ST_CT.png', node_override='_ST_DT.png') #attempt to default to light in case dark is not available
                        #default to colors if there's no maintex
                        if c.get_body().material_slots[ 'Edit cf_m_face_00'].material.node_tree.nodes['textures'].node_tree.nodes['_ST_CT.png'].image.name == 'Template: Placeholder':
                            c.get_body().material_slots['Edit cf_m_face_00'].material.node_tree.nodes['light'].inputs['Use main texture instead?'].default_value = 0
                            c.get_body().material_slots['Edit cf_m_face_00'].material.node_tree.nodes['dark' ].inputs['Use main texture instead?'].default_value = 0
                        self.image_load('cf_m_face_00', '_CM.png')
                        self.image_load('cf_m_face_00', '_DM.png')
                        self.image_load('cf_m_face_00', '_T4.png') #blush
                        self.image_load('cf_m_face_00', '_ST.png') #mouth interior
                        self.image_load('cf_m_face_00', '_LM.png')
                        self.image_load('cf_m_face_00', '_T5.png') #lower lip mask
                        self.image_load('cf_m_face_00', '_ot1.png') #lipstick
                        self.image_load('cf_m_face_00', '_ot2.png') #flush
                        self.image_load('cf_m_face_00', '_T3.png')
                        self.image_load('cf_m_face_00', '_T7.png')
                        self.image_load('cf_m_face_00', '_ot3.png') #eyeshadow
                        self.set_uv_type('cf_m_face_00', 'eyeshadowuv', 'uv_eyeshadow')

                    case 'cf_m_body':
                        self.image_load('cf_m_body', '_ST_CT.png')
                        self.image_load('cf_m_body', '_ST_CT.png', node_override='_ST_DT.png') #attempt to default to light in case dark is not available later on
                        #default to colors if there's no maintex
                        if c.get_body().material_slots[ 'Edit cf_m_body'].material.node_tree.nodes['textures'].node_tree.nodes['_ST_CT.png'].image.name == 'Template: Placeholder':
                            c.get_body().material_slots['Edit cf_m_body'].material.node_tree.nodes['dark' ].inputs['Use main texture instead?'].default_value = 0
                            c.get_body().material_slots['Edit cf_m_body'].material.node_tree.nodes['light'].inputs['Use main texture instead?'].default_value = 0
                        self.image_load('cf_m_body', '_CM.png') #color mask
                        self.image_load('cf_m_body', '_DM.png') #cfm female
                        self.image_load('cf_m_body', '_LM.png') #line mask for lips
                        self.image_load('cf_m_body', '_NMP_CNV.png')
                        self.image_load('cf_m_body', '_NMPD_CNV.png')
                        self.image_load('cf_m_body', '_ST.png', group_override='texturesnsfw') #chara main texture
                        self.image_load('cf_m_body', '_ot2.png', group_override='texturesnsfw') #pubic hair
                        self.image_load('cf_m_body', '_ot1.png', group_override='texturesnsfw') #cfm female
                        self.image_load('cf_m_body', '_ot1.png', group_override='texturesnsfw', node_override='_ot1.pngleft')
                        self.image_load('cf_m_body', '_T3.png') #body overlays
                        self.image_load('cf_m_body', '_T6.png')
                        self.set_uv_type('cf_m_body', 'nippleuv', 'uv_nipple_and_shine', group= 'texturesnsfw')
                        self.set_uv_type('cf_m_body', 'underuv', 'uv_underhair', group= 'texturesnsfw')
                        #find the appropriate alpha mask
                        alpha_mask = None
                        if bpy.data.images.get('_AM.png'):
                            alpha_mask = bpy.data.images.get('_AM.png')
                        elif bpy.data.images.get('_AM_00.png'):
                            alpha_mask = bpy.data.images.get('_AM_00.png')
                        else:
                            #check the other alpha mask numbers
                            for image in bpy.data.images:
                                if '_m_body_AM_' in image.name and image.name[-6:-4].isnumeric():
                                    alpha_mask = image
                                    break
                        #if there was an alpha mask detected, load it in
                        if alpha_mask:
                            self.image_load('cf_m_body', image_override = alpha_mask.name, node_override='_AM.png')

                    case 'cf_m_mayuge_00':
                        #load in the remaining face materials if they exist
                        if c.get_material_names('cf_O_mayuge'):
                            self.image_load('cf_m_mayuge_00', '_ST_CT.png')
                            self.image_load('cf_m_mayuge_00', '_ST_CT.png')
                    case 'cf_m_noseline_00':
                        if c.get_material_names('cf_O_noseline'):
                            self.image_load('cf_m_noseline_00', '_ST_CT.png')
                    case 'cf_m_eyeline_down':
                        if c.get_material_names('cf_O_eyeline_low'):
                            self.image_load('cf_m_eyeline_down', '_ST_CT.png')
                    case 'cf_m_tooth':
                        if c.get_material_names('cf_O_tooth'):
                            self.image_load('cf_m_tooth', '_ST_CT.png')
                    case 'cf_Ohitomi_R':
                        if c.get_material_names('cf_m_sirome_00'):
                            self.image_load('cf_m_sirome_00',  image_override = c.get_material_names('cf_Ohitomi_L')[0] + '_ST_CT.png', node_override = '_ST_CT.png')
                            self.image_load('cf_m_sirome_00',  image_override = c.get_material_names('cf_Ohitomi_R')[0] + '_ST_CT.png', node_override = '_ST_CT.png')
                    case 'cf_O_eyeline':
                        if c.get_material_names('cf_O_eyeline'):
                            self.image_load('cf_O_eyeline', image_override= c.get_material_names('cf_O_eyeline')[0] + '_ST_CT.png', node_override='_ST_CT.png')
                        if len(c.get_material_names('cf_O_eyeline')) > 1:
                            self.image_load('cf_O_eyeline', image_override=c.get_material_names('cf_O_eyeline')[1] + '_ST_CT.png', node_override='_ST_CT.pngkage')
                    case 'KK cf_m_hitomi_00_cf_Ohitomi_L02':
                        if c.get_material_names(f'cf_Ohitomi_L02'):
                            eye_mat = c.get_material_names(f'cf_Ohitomi_L02')[0]
                            self.image_load(f'cf_m_hitomi_00_cf_Ohitomi_L02', '_ST_CT.png')
                            self.image_load(f'cf_m_hitomi_00_cf_Ohitomi_L02', '_ST_CT.png', node_override='_ST_DT.png') #attempt to default to light in case dark is not available
                            self.image_load(f'cf_m_hitomi_00_cf_Ohitomi_L02', '_ot1.png')
                            self.image_load(f'cf_m_hitomi_00_cf_Ohitomi_L02', '_ot2.png')
                            self.image_load(f'cf_m_hitomi_00_cf_Ohitomi_L02', image_override = eye_mat[:-15] + '_cf_t_expression_00_EXPR.png', node_override= '_cf_t_expression_00_EXPR.png')
                            self.image_load(f'cf_m_hitomi_00_cf_Ohitomi_L02', image_override = eye_mat[:-15] + '_cf_t_expression_01_EXPR.png', node_override= '_cf_t_expression_01_EXPR.png')
                    case 'KK KK cf_m_hitomi_00_cf_Ohitomi_R02':
                        if c.get_material_names(f'cf_Ohitomi_R02'):
                            eye_mat = c.get_material_names(f'cf_Ohitomi_R02')[0]
                            self.image_load(f'cf_m_hitomi_00_cf_Ohitomi_R02', '_ST_CT.png')
                            self.image_load(f'cf_m_hitomi_00_cf_Ohitomi_R02', '_ST_CT.png', node_override='_ST_DT.png') #attempt to default to light in case dark is not available
                            self.image_load(f'cf_m_hitomi_00_cf_Ohitomi_R02', '_ot1.png')
                            self.image_load(f'cf_m_hitomi_00_cf_Ohitomi_R02', '_ot2.png')
                            self.image_load(f'cf_m_hitomi_00_cf_Ohitomi_R02', image_override = eye_mat[:-15] + '_cf_t_expression_00_EXPR.png', node_override= '_cf_t_expression_00_EXPR.png')
                            self.image_load(f'cf_m_hitomi_00_cf_Ohitomi_R02', image_override = eye_mat[:-15] + '_cf_t_expression_01_EXPR.png', node_override= '_cf_t_expression_01_EXPR.png')

                if base_name in ['KK cf_m_hitomi_00_cf_Ohitomi_L02', 'KK KK cf_m_hitomi_00_cf_Ohitomi_R02']:
                    #correct the eye scaling using info from the KK_ChaFileCustomFace.json
                    face_data = c.json_file_manager.get_json_file('KK_ChaFileCustomFace.json')
                    bpy.data.node_groups['.Eye Textures positioning'].nodes['eye_scale'].inputs[1].default_value = 1/(float(face_data[18]['Value']) + 0.0001)
                    bpy.data.node_groups['.Eye Textures positioning'].nodes['eye_scale'].inputs[2].default_value = 1/(float(face_data[19]['Value']) + 0.0001)

        c.print_timer('link_textures_for_face_body')

    def link_textures_for_hair(self, new_material_name):
        '''Load all hair textures into their texture slots'''
        hairMat = bpy.data.materials[new_material_name]
        #use the material name instead of hairMat.material['id'] to catch any instances of 00 01 02 materials
        hairType = hairMat.name.replace('KK ','Edit ')

        self.image_load( hairType,  '_ST_CT.png')
        self.image_load( hairType,  '_ST_CT.png', node_override='_ST_DT.png') #attempt to default to light in case dark is not available
        self.image_load( hairType,  '_DM.png')
        self.image_load( hairType,  '_CM.png')
        self.image_load( hairType,  '_HGLS.png')
        self.image_load( hairType,  '_AM.png')
        self.set_uv_type(hairType, 'hairuv', 'uv_nipple_and_shine')

        c.print_timer('link_textures_for_hair')

    def link_textures_for_clothes(self, new_material_name):
        '''Load all clothes textures into their texture slots'''
        genMat = bpy.data.materials[new_material_name]
        #use the material name instead of genMat.material['id'] to catch any instances of 00 01 02 materials
        genType = genMat.name.replace('KK ', 'Edit ')

        #load these textures if they are present
        self.image_load(genType, '_ST.png')
        self.image_load(genType, '_ST_CT.png')
        self.image_load(genType, '_AM.png')
        self.image_load(genType, '_CM.png')
        self.image_load(genType, '_DM.png')
        self.image_load(genType, '_NMP.png')
        self.image_load(genType, '_NMPD_CNV.png')
        self.image_load(genType, '_PM1.png')
        self.image_load(genType, '_PM2.png')
        self.image_load(genType, '_PM3.png')

        #If there's a plain maintex loaded, but no colored maintex loaded, make the shader use the plain maintex
        plain_but_no_main = (
            genMat.material.node_tree.nodes['textures'].node_tree.nodes['_ST_CT.png'].image.name == 'Template: Placeholder' and
            genMat.material.node_tree.nodes['textures'].node_tree.nodes['_ST.png'].image.name != 'Template: Placeholder'
            )
        if plain_but_no_main:
            genMat.material.node_tree.nodes['combine'].inputs['Use plain main texture?'].default_value = 1

        #If there's an AnotherRamp (AR) texture present, the material is likely supposed to be metallic on the red parts of the detail mask
        #I don't have a template for this, so the material will just look pure white. Turn off the shine intensity to avoid this
        image_name = genMat.material['id'] + '_AR.png'
        if bpy.data.images.get(image_name):
            genMat.material.node_tree.nodes['light'].inputs['Detail intensity (shine)'].default_value = 0
            genMat.material.node_tree.nodes['dark' ].inputs['Detail intensity (shine)'].default_value = 0

        shader_name = c.get_shader_name(genMat.material['id'])

        #If the shader of this material is set to "main opaque" then there is NOT supposed to be a color mask, but the kkbp exporter exports one anyway
        #Move the colormask to the opaque slot if one was loaded in. This way it can still be used by the plain main texture
        if genMat.material.node_tree.nodes['textures'].node_tree.nodes['_CM.png'].image:
            shaders = ['Koikano/main_clothes_opaque', 'Shader Forge/main_opaque', 'xukmi/MainOpaquePlus', 'xukmi/MainOpaquePlusTess', 'Shader Forge/main_opaque2', 'Shader Forge/main_opaque_low']
            if shader_name in shaders:
                c.kklog('Detected opaque shader. Moving color mask to color mask (plain) slot: {}'.format(genMat.material['id']))
                genMat.material.node_tree.nodes['textures'].node_tree.nodes['_CM.pngopaque'].image = genMat.material.node_tree.nodes['textures'].node_tree.nodes['_CM.png'].image
                genMat.material.node_tree.nodes['textures'].node_tree.nodes['_CM.png'].image = None

        #If the shader of this material is set to "main alpha", set the material to "blended" in blender
        shaders = ['Shader Forge/main_alpha', 'Koikano/main_clothes_alpha', 'xukmi/MainAlphaPlus', 'xukmi/MainAlphaPlusTess', 'xukmi/MainItemAlphaPlus', 'IBL_Shader_alpha', ]
        #find this material in the MaterialDataComplete.json and see if it's an alpha shader
        if shader_name in shaders:
            c.kklog('Detected alpha shader. Setting render method to blended: {}'.format(genMat.material['id']))
            if bpy.app.version[0] == 3:
                genMat.material.blend_method = 'BLEND'
            else:
                genMat.material.surface_render_method = 'BLENDED'

        #If the shader of this material is set to "glasses", replace the entire shader with
        shaders = ['Shader Forge/toon_glasses_lod0', 'Koikano/main_clothes_item_glasses',]
        #find this material in the MaterialDataComplete.json and see if it's a glasses shader
        if shader_name in shaders:
            c.kklog('Detected glasses shader. Replacing material with KK Glasses: {}'.format(genMat.material['id']))

            original_textures_group = genMat.material.node_tree.nodes['textures'].node_tree
            template = bpy.data.materials['KK Glasses'].copy()
            template.node_tree.nodes['textures'].node_tree = original_textures_group
            bpy.data.materials.remove(genMat.material)
            template['bake'] = True
            template['glasses'] = True
            template.name = 'KK ' + genType + ' ' + c.get_name()
            genMat.material = template

        #special exception to clip the emblem image because I am tired of seeing it repeat at the edges
        if 'Edit cf_m_emblem ' in genMat.material.name:
            genMat.material.node_tree.nodes['textures'].node_tree.nodes['_ST_CT.png'].extension = 'CLIP'

        c.print_timer('link_textures_for_clothes')


    def image_load(self, material_name: str, image_suffix = '', image_override = None, node_override = None, group_override = None):
        '''Automatically load image into mat's texture slot'''
        #get the id from the material
        material_name = 'Edit ' + material_name
        material = bpy.data.materials[material_name]
        #get the image name using the id and the suffix
        image_name = image_override if image_override else material['id'] + image_suffix
        #then load the image into the texture slot
        if bpy.data.images.get(image_name):
            ha = image_name.replace(material['id'], '')
            c.kklog(f'loading file: {image_name} into {ha}')
            node = node_override if node_override else image_name.replace(material['id'], '')
            group = group_override if group_override else 'textures'
            bpy.data.materials[material_name].node_tree.nodes[group].node_tree.nodes[node].image = bpy.data.images[image_name]
            #also apply scaling and offset data to the image
            self.apply_texture_data_to_image(material_name, image_name, node, group)
        else:
            c.kklog('File wasnt found, skipping: ' + image_name)

    def create_dark_textures(self, new_material_name):
        """Creates dark versions of textures for body, hair, and outfit materials."""
        material = bpy.data.materials[new_material_name]
        if material.node_tree.nodes.get('textures'):
            if material.node_tree.nodes['textures'].node_tree.nodes.get('_ST_DT.png'):
                maintex = material.node_tree.nodes['textures'].node_tree.nodes['_ST_CT.png'].image
                #if this isn't a placeholder image, create a dark version of it
                if maintex.name != 'Template: Placeholder' and maintex.name != 'cf_m_tang_CM.png':
                    shadow_color = c.json_file_manager.get_shadow_color(material.name)
                    darktex = self.create_darktex(maintex, shadow_color)
                    material.node_tree.nodes['textures'].node_tree.nodes['_ST_DT.png'].image = darktex
        c.print_timer('create_dark_textures')

    def create_darktex(self, maintex: bpy.types.Image, shadow_color: float) -> bpy.types.Image:
        '''#accepts a bpy image and creates a dark alternate using a modified version of the darkening code above. Returns a new bpy image'''
        if not os.path.isfile(bpy.context.scene.kkbp.import_dir + '/dark_files/' + maintex.name[:-6] + 'DT.png'):
            ok = time.time()
            image_array = numpy.asarray(maintex.pixels,dtype=self.np_number_precision)
            image_length = len(image_array)
            image_row_length = int(image_length/4)
            image_array = image_array.reshape((image_row_length, 4))

            ################### variable setup
            _ambientshadowG = numpy.asarray([0.15, 0.15, 0.15, 0.15],dtype=self.np_number_precision) #constant from experimentation
            diffuse = image_array #maintex color
            _ShadowColor = numpy.asarray([shadow_color['r'],shadow_color['g'],shadow_color['b'], 1],dtype=self.np_number_precision) #the shadow color from material editor
            ##########################

            #start at line 344 because the other one is for outlines
            #shadingAdjustment = ShadeAdjustItemNumpy(diffuse, _ShadowColor)
            #start at line 63
            x=0;y=1;z=2;w=3;
            t0 = diffuse
            t1 = t0[:, [y, z, z, x]] * _ShadowColor[[y,z,z,x]]
            t2 = t1[:, [y,x]]
            t3 = t0[:, [y,z]] * _ShadowColor[[y,z]] + (-t2)
            tb30 = t2[:, [y]] >= t1[:, [y]]
            t30 = tb30.astype(int)
            t2 = numpy.hstack((t2[:, [x,y]], numpy.full((t2.shape[0], 1), -1, t2.dtype), numpy.full((t2.shape[0], 1), 0.666666687, t2.dtype)))
            t3 = numpy.hstack((t3[:, [x,y]], numpy.full((t3.shape[0], 1),  1, t3.dtype), numpy.full((t3.shape[0], 1), -1,          t3.dtype)))
            t2 = t30 * t3 + t2
            tb30 = t1[:, [w]] >= t1[:, [x]]
            t30 = tb30.astype(int)
            t1 = numpy.hstack((t2[:, [x, y, w]], t1[:, [w]]))
            t2 = numpy.hstack((t1[:, [w, y]], t2[:, [z]], t1[:, [x]]))
            t2 = -t1 + t2
            t1 = t30 * t2 + t1
            t30 = numpy.minimum(t1[:, [y]], t1[:, [w]])
            t30 = -t30 + t1[:, [x]]
            t2[:, [x]] = t30 * 6 + 1.00000001e-10
            t11 = -t1[:, [y]] + t1[:, [w]]
            t11 = t11 / t2[:, [x]];
            t11 = t11 + t1[:, [z]];
            t1[:, [x]] = t1[:, [x]] + 1.00000001e-10;
            t30 = t30 / t1[:, [x]];
            t30 = t30 * 0.5;
            #the w component of t1 is no longer used, so ignore it
            t1 = numpy.absolute(t11) + numpy.asarray([0.0, -0.333333343, 0.333333343, 1]); #90
            t1 = t1 - numpy.floor(t1)
            t1 = -t1 * 2 + 1
            t1 = numpy.absolute(t1) * 3 + (-1)
            t1 = numpy.clip(t1, 0, 1)
            t1 = t1 + (-1); #95
            t1 = (t30) * t1 + 1; #96

            shadingAdjustment = t1

            #skip to line 352
            diffuseShaded = shadingAdjustment * 0.899999976 - 0.5;
            diffuseShaded = -diffuseShaded * 2 + 1;

            compTest = 0.555555582 < shadingAdjustment;
            shadingAdjustment *= 1.79999995;
            diffuseShaded = -diffuseShaded * 0.7225 + 1; #invertfinalambient shadow is a constant 0.7225, so don't calc it

            hlslcc_movcTemp = shadingAdjustment;
            #reframe ifs as selects
            hlslcc_movcTemp[:, [x]] = numpy.select(condlist=[compTest[:, [x]], numpy.invert(compTest[:, [x]])], choicelist=[diffuseShaded[:, [x]], shadingAdjustment[:, [x]]])
            hlslcc_movcTemp[:, [y]] = numpy.select(condlist=[compTest[:, [y]], numpy.invert(compTest[:, [y]])], choicelist=[diffuseShaded[:, [y]], shadingAdjustment[:, [y]]])
            hlslcc_movcTemp[:, [z]] = numpy.select(condlist=[compTest[:, [z]], numpy.invert(compTest[:, [z]])], choicelist=[diffuseShaded[:, [z]], shadingAdjustment[:, [z]]])
            shadingAdjustment = numpy.clip(hlslcc_movcTemp, 0, 1) #374 the lerp result (and shadowCol) is going to be this because shadowColor's alpha is always 1 making shadowCol 1

            diffuseShadow = diffuse * shadingAdjustment;

            # lightCol is constant [1.0656, 1.0656, 1.0656, 1] calculated from the custom ambient of [0.666, 0.666, 0.666, 1] and sun light color [0.666, 0.666, 0.666, 1],
            # so ambientCol always results in lightCol after the max function
            ambientCol = numpy.asarray([1.0656, 1.0656, 1.0656, 1],dtype=self.np_number_precision);
            diffuseShadow = diffuseShadow * ambientCol;

            #make a new image and place the dark pixels into it
            dark_array = diffuseShadow
            darktex = bpy.data.images.new(maintex.name[:-7] + '_DT.png', width=maintex.size[0], height=maintex.size[1], alpha = True)
            darktex.file_format = 'PNG'
            darktex.pixels = dark_array.ravel()
            darktex.use_fake_user = True
            darktex_filename = maintex.filepath_raw[maintex.filepath_raw.find(maintex.name):][:-7]+ '_DT.png'
            darktex_filepath = bpy.context.scene.kkbp.import_dir + '/dark_files/' + darktex_filename
            darktex.filepath_raw = darktex_filepath
            darktex.pack()
            darktex.save()
            c.kklog('Created dark version of {} in {} seconds'.format(darktex.name, time.time() - ok))
            return darktex
        else:
            bpy.data.images.load(filepath=str(bpy.context.scene.kkbp.import_dir + '/dark_files/' + maintex.name[:-6] + 'DT.png'))
            darktex = bpy.data.images[maintex.name[:-6] + 'DT.png']
            c.kklog('Loading in existing dark version of {}'.format(darktex.name))
            try:
                darktex.pack()
                darktex.save()
            except:
                c.kklog('This image was not automatically loaded in because its name exceeds 64 characters: ' + darktex.name, type = 'error')
            return darktex

    def saturate_texture(self, index, slice_image, is_first_batch):
        '''The Secret Sauce. Accepts a bpy image and saturates it to match the in-game look.'''
        # Find the XY coordinates of the LUT image needed to saturate each pixel
        coord = slice_image[:, :, :3] * self.coord_scale + self.coord_offset
        coord_frac, coord_floor = numpy.modf(coord)
        coord_frac_z = coord_frac[:, :, 2:3]
        del coord_frac  # free temporary variables after they're used
        coord_bot = coord[:, :, :2] + coord_floor[:, :, 2:3] * self.texel_height_X0
        del coord
        del coord_floor

        #use those XY coordinates to find the saturated version of the color from the LUT image
        lutcol_bot = self.__bilinear_interpolation__(self.lut_pixels, coord_bot)

        lut_colors = lutcol_bot * (1 - coord_frac_z)
        del lutcol_bot
        coord_top = numpy.clip(coord_bot + self.texel_height_X0, 0, 1)
        lutcol_top = self.__bilinear_interpolation__(self.lut_pixels, coord_top)
        lut_colors += lutcol_top * coord_frac_z
        del lutcol_top
        del coord_top
        # slice_image[:, :, :3] = lut_colors[:,:,:3]
        if is_first_batch:
            slice_image[:, :, :3] = lut_colors[:,:,:3]
        else:
            slice_image[1:, :, :3] = lut_colors[1:, :, :3]
        with self.queue_lock:
            self.data_queue.put(index)

    def __bilinear_interpolation__(self, lut_pixels, coords):
        h, w, _ = lut_pixels.shape
        x = coords[:, :, 0] * (w - 1)
        # Fudge x coordinates based on x position. subtract -0.5 if at x position 0 and add 0.5 if at x position 1024 of the LUT.
        # this helps with some kind of overflow / underflow issue where it reads from the next LUT square when it's not supposed to
        x = x + (x / 1024 - 0.5)
        y = coords[:, :, 1] * (h - 1)
        # Get integer and fractional parts of each coordinate.
        # Also make sure each coordinate is clipped to the LUT image bounds
        x0 = numpy.clip(numpy.floor(x).astype(int), 0, w - 1)
        x1 = numpy.clip(x0 + 1, 0, w - 1)
        y0 = numpy.clip(numpy.floor(y).astype(int), 0, h - 1)
        y1 = numpy.clip(y0 + 1, 0, h - 1)
        x_frac = x - x0
        y_frac = y - y0
        # Get the pixel values at four corners of this coordinate
        f00 = lut_pixels[y0, x0]
        f01 = lut_pixels[y1, x0]
        f10 = lut_pixels[y0, x1]
        f11 = lut_pixels[y1, x1]
        del x0
        del x1
        del y0
        del y1
        # Perform the bilinear interpolation using the fractional part of each coordinate
        # This will ensure the LUT can provide the correct color every single time, even if that color isn't found in the LUT itself
        # If this isn't performed, the resulting image will look very blocky because it will snap to colors only found in the LUT.
        lut_col_bot = f00 * (1 - y_frac)[:, :, numpy.newaxis] + f01 * y_frac[:, :, numpy.newaxis]
        lut_col_top = f10 * (1 - y_frac)[:, :, numpy.newaxis] + f11 * y_frac[:, :, numpy.newaxis]
        interpolated_colors = lut_col_bot * (1 - x_frac)[:, :, numpy.newaxis] + lut_col_top * x_frac[:, :, numpy.newaxis]
        return interpolated_colors

    def load_json_colors(self, new_material_name, type):
        self.update_shaders('light', new_material_name, type) # Set light colors
        self.update_shaders('dark', new_material_name, type) # Set dark colors
        c.print_timer('load_json_colors')

    def update_shaders(self, light_pass: str, new_material_name, type):
        '''Set the colors for everything. This is run once for the light colors and again for the dark colors'''
        
        if type == 'body':
            for base_name in self.remap_dict:
                if base_name in new_material_name:
                    mat_name = f'Edit {base_name}'
                    match base_name:
                        case 'cf_m_face_00':
                            #face
                            #Note that some headmods have multiple face materials. This will only replace the first one
                            if c.get_material_names('cf_O_face'):
                                #setup the face material
                                shader_inputs = c.get_body().material_slots[mat_name].material.node_tree.nodes[light_pass].inputs
                                if light_pass == 'light':
                                    shader_inputs['Skin color'].default_value = self.saturate_color(c.json_file_manager.get_color('Edit cf_m_face_00', "_Color "), light_pass = 'light')
                                else:
                                    shader_inputs['Skin color'].default_value = self.saturate_color(self.skin_dark_color(c.json_file_manager.get_color('Edit cf_m_face_00', "_Color ")), light_pass = 'light')
                                shader_inputs['Detail color'].default_value =      self.saturate_color(c.json_file_manager.get_color('Edit cf_m_face_00', "_Color2 " ),                       light_pass, shadow_color = c.json_file_manager.get_shadow_color('Edit cf_m_face_00'))
                                shader_inputs['Light blush color'].default_value =      self.saturate_color(c.json_file_manager.get_color(mat_name, "_overcolor2 "  ),                light_pass, shadow_color = c.json_file_manager.get_shadow_color(mat_name))
                                shader_inputs['Lipstick multiplier'].default_value =    self.saturate_color(c.json_file_manager.get_color(mat_name, "_overcolor1 "  ),                light_pass, shadow_color = c.json_file_manager.get_shadow_color(mat_name))
                        
                        case 'cf_m_body':
                            #set body colors
                            if c.get_body():
                                if c.get_material_names('o_body_a'):
                                    shader_inputs = c.get_body().material_slots[mat_name].material.node_tree.nodes[light_pass].inputs
                                    if light_pass == 'light':
                                        shader_inputs['Skin color'].default_value = self.saturate_color(c.json_file_manager.get_color(mat_name, "_Color "), light_pass = 'light')
                                    else:
                                        shader_inputs['Skin color'].default_value = self.saturate_color(self.skin_dark_color(c.json_file_manager.get_color(mat_name, "_Color ")), light_pass = 'light')
                                    shader_inputs['Detail color'].default_value =               self.saturate_color(c.json_file_manager.get_color(mat_name, "_Color2 " ),  light_pass, shadow_color = c.json_file_manager.get_shadow_color(mat_name))
                                    shader_inputs['Line mask color'].default_value =            self.saturate_color(c.json_file_manager.get_color(mat_name, "_Color2 " ),  light_pass, shadow_color = c.json_file_manager.get_shadow_color(mat_name)) #use same color for both detail and line
                                    shader_inputs['Nail color (multiplied)'].default_value =    self.saturate_color(c.json_file_manager.get_color(mat_name, "_Color5 " ),  light_pass, shadow_color = c.json_file_manager.get_shadow_color(mat_name))
                                    if not bpy.context.scene.kkbp.sfw_mode:
                                        shader_inputs['Underhair color'].default_value =        [0, 0, 0, 1]

                        case 'cf_m_mayuge_00':
                            #eyebrows
                            if c.get_material_names('cf_O_mayuge'):
                                shader_inputs = c.get_body().material_slots[mat_name].material.node_tree.nodes['light'].inputs
                                shader_inputs['Eyebrow color'].default_value =       self.saturate_color(c.json_file_manager.get_color(mat_name, "_Color "))
                                shader_inputs['Eyebrow color dark'].default_value =  self.saturate_color(c.json_file_manager.get_color(mat_name, "_Color "),  'dark' , shadow_color = c.json_file_manager.get_shadow_color(mat_name))

                        case 'cf_O_eyeline_low':
                            if c.get_material_names('cf_O_eyeline_low'):
                                shader_inputs = c.get_body().material_slots[mat_name].material.node_tree.nodes['light'].inputs
                                shader_inputs['Eyeline down fade color'].default_value = self.saturate_color(c.json_file_manager.get_color(mat_name, "_Color "),  light_pass, shadow_color = c.json_file_manager.get_shadow_color(mat_name))
                        
                        case 'cf_O_eyeline':
                            if c.get_material_names('cf_O_eyeline'):
                                shader_inputs = c.get_body().material_slots[mat_name].material.node_tree.nodes['light'].inputs
                                shader_inputs['Eyeline fade color'].default_value = self.saturate_color(c.json_file_manager.get_color(mat_name, "_Color "),  light_pass, shadow_color = c.json_file_manager.get_shadow_color(mat_name))
                        
                        case 'o_tang':
                            #set the tongue colors if it exists
                            if c.get_material_names('o_tang') and (tongue := c.get_tongue()):
                                shader_inputs = tongue.material_slots[0].material.node_tree.nodes[light_pass].inputs
                                shader_inputs['Maintex Saturation'].default_value = 0.6
                                shader_inputs['Detail intensity (green)'].default_value = 0.01
                                shader_inputs['Color mask (base)'].default_value = [1, 1, 1, 1]
                                mat_name = tongue.material_slots[0].name
                                shader_inputs['Color mask (red)'].default_value =   self.saturate_color(c.json_file_manager.get_color(mat_name, "_Color "),  light_pass, shadow_color = c.json_file_manager.get_shadow_color(mat_name))
                                shader_inputs['Color mask (green)'].default_value = self.saturate_color(c.json_file_manager.get_color(mat_name, "_Color2 "), light_pass, shadow_color = c.json_file_manager.get_shadow_color(mat_name))
                                shader_inputs['Color mask (blue)'].default_value =  self.saturate_color(c.json_file_manager.get_color(mat_name, "_Color3 "), light_pass, shadow_color = c.json_file_manager.get_shadow_color(mat_name))

        elif type == 'hair':
            #set all of the hair colors
            hair_material = bpy.data.materials[new_material_name]
            shader_inputs = hair_material.node_tree.nodes[light_pass].inputs
            shader_inputs['Hair color'].default_value         = self.saturate_color(c.json_file_manager.get_color(hair_material.name, "_Color " ),  light_pass, shadow_color = c.json_file_manager.get_shadow_color(hair_material.name))
            shader_inputs['Color mask (root)'].default_value  = self.saturate_color(c.json_file_manager.get_color(hair_material.name, "_Color2 "),  light_pass, shadow_color = c.json_file_manager.get_shadow_color(hair_material.name))
            shader_inputs['Color mask (tip)'].default_value = self.saturate_color(c.json_file_manager.get_color(hair_material.name, "_Color3 "),  light_pass, shadow_color = c.json_file_manager.get_shadow_color(hair_material.name))

        elif type == 'outfit':
            #set the clothes colors
            material = bpy.data.materials[new_material_name]
            shader_inputs = material.node_tree.nodes[light_pass].inputs
            shader_inputs['Color mask (red)'].default_value =       self.saturate_color(c.json_file_manager.get_color(material.name, "_Color "),     light_pass, shadow_color = c.json_file_manager.get_shadow_color(material.name))
            shader_inputs['Color mask (green)'].default_value =     self.saturate_color(c.json_file_manager.get_color(material.name, "_Color2 "),    light_pass, shadow_color = c.json_file_manager.get_shadow_color(material.name))
            shader_inputs['Color mask (blue)'].default_value =      self.saturate_color(c.json_file_manager.get_color(material.name, "_Color3 "),    light_pass, shadow_color = c.json_file_manager.get_shadow_color(material.name))
            shader_inputs['Pattern color (red)'].default_value =    self.saturate_color(c.json_file_manager.get_color(material.name, "_Color1_2 "),  light_pass, shadow_color = c.json_file_manager.get_shadow_color(material.name))
            shader_inputs['Pattern color (green)'].default_value =  self.saturate_color(c.json_file_manager.get_color(material.name, "_Color2_2 "),  light_pass, shadow_color = c.json_file_manager.get_shadow_color(material.name))
            shader_inputs['Pattern color (blue)'].default_value =   self.saturate_color(c.json_file_manager.get_color(material.name, "_Color3_2 "),  light_pass, shadow_color = c.json_file_manager.get_shadow_color(material.name))

    def saturate_color(self, color: float, light_pass = 'light', shadow_color = {'r':0.764, 'g':0.880, 'b':1}) -> dict[str, float]:
        '''The Secret Sauce. Accepts a 0-1 float rgba color dict, saturates it to match the in-game look 
        and returns it in the form of a 0-1 float rgba array'''

        #fix the color if it does not have an alpha
        color['a'] = color.get('a', 1)

        #make the color a dark color if the light_pass is set to dark
        color = color if light_pass == 'light' else self.clothes_dark_color(color, shadow_color)
        width, height = 1,1

        # Load image and LUT image pixels into array
        image_pixels = numpy.array([color['r'], color['g'], color['b'], 1],dtype=self.np_number_precision).reshape(height, width, 4)

        # Find the XY coordinates of the LUT image needed to saturate each pixel
        coord = image_pixels[:, :, :3] * self.coord_scale + self.coord_offset
        coord_frac, coord_floor = numpy.modf(coord)
        coord_bot = coord[:, :, :2] + numpy.tile(coord_floor[:, :, 2].reshape(height, width, 1), (1, 1, 2)) * self.texel_height_X0
        coord_top = numpy.clip(coord_bot + self.texel_height_X0, 0, 1)

        lutcol_bot = self.__bilinear_interpolation__(self.lut_pixels, coord_bot)
        lutcol_top = self.__bilinear_interpolation__(self.lut_pixels, coord_top)
        #After the older gpu code uses the texture lookup the colorspace is converted from srgb to linear,
        # so replicate that behavior here.
        def srgb_to_linear(srgb):
            linear_rgb = numpy.where(
                srgb <= 0.04045,
                srgb / 12.92,
                numpy.power((srgb + 0.055) / 1.055, 2.4))
            return linear_rgb
        lutcol_bot = srgb_to_linear(lutcol_bot)
        lutcol_top = srgb_to_linear(lutcol_top)
        lut_colors = lutcol_bot * (1 - coord_frac[:, :, 2].reshape(height, width, 1)) + lutcol_top * coord_frac[:, :, 2].reshape(height, width, 1)
        image_pixels[:, :, :3] = lut_colors[:,:,:3]

        return image_pixels.flatten().tolist()[0:4]

    def MapValuesMain(self, color): #-> float4
        '''mapvaluesmain function is from https://github.com/xukmi/KKShadersPlus/blob/main/Shaders/Skin/KKPDiffuse.cginc'''
        t0 = color;
        tb30 = t0.y>=t0.z;
        t30 = 1 if tb30 else float(0.0);
        t1 = float4(t0.z, t0.y, t0.z, t0.w);
        t2 = float4(t0.y - t1.x,  t0.z - t1.y);
        t1.z = float(-1.0);
        t1.w = float(0.666666687);
        t2.z = float(1.0);
        t2.w = float(-1.0);
        t1 = float4(t30, t30, t30, t30) * float4(t2.x, t2.y, t2.w, t2.z) + float4(t1.x, t1.y, t1.w, t1.z);
        tb30 = t0.x>=t1.x;
        t30 = 1 if tb30 else 0.0;
        t2.z = t1.w;
        t1.w = t0.x;
        t2 = float4(t1.w, t1.y, t2.z, t1.x)
        t2 = (-t1) + t2;
        t1 = float4(t30, t30, t30, t30) * t2 + t1;
        t30 = min(t1.y, t1.w);
        t30 = (-t30) + t1.x;
        t2.x = t30 * 6.0 + 1.00000001e-10;
        t11 = (-t1.y) + t1.w;
        t11 = t11 / t2.x;
        t11 = t11 + t1.z;
        t1.x = t1.x + 1.00000001e-10;
        t30 = t30 / t1.x;
        t30 = t30 * 0.660000026;
        #w component isn't used anymore so ignore
        t2 = float4(t11, t11, t11).abs() + float4(-0.0799999982, -0.413333356, 0.25333333)
        t2 = t2.frac()
        t2 = (-t2) * float4(2.0, 2.0, 2.0) + float4(1.0, 1.0, 1.0);
        t2 = t2.abs() * float4(3.0, 3.0, 3.0) + float4(-1.0, -1.0, -1.0);
        t2 = t2.clamp()
        t2 = t2 + float4(-1.0, -1.0, -1.0);
        t2 = float4(t30, t30, t30) * t2 + float4(1.0, 1.0, 1.0);
        return float4(t2.x, t2.y, t2.z, 1);

    def adjust_pupil_highlight(self):
        data = c.json_file_manager.get_json_file('KK_CharacterInfoData.json')[0]
        if vec0 := data.get('pupilOffset'):
            bpy.data.node_groups[".Eye Textures positioning"].nodes["eye_scale"].inputs[3].default_value = vec0[0] * 50 + 25
            bpy.data.node_groups[".Eye Textures positioning"].nodes["eye_scale"].inputs[4].default_value = vec0[1] * 50 + 25

            vec = data['pupilScale']
            bpy.data.node_groups[".Eye Textures positioning"].nodes["eye_scale"].inputs[1].default_value = vec[0]
            bpy.data.node_groups[".Eye Textures positioning"].nodes["eye_scale"].inputs[2].default_value = vec[1]

            vec = data['highlightUpOffset']
            bpy.data.node_groups[".Eye Textures positioning"].nodes["Group"].inputs[3].default_value = (vec[0] - vec0[0]) * 50 + 25
            bpy.data.node_groups[".Eye Textures positioning"].nodes["Group"].inputs[4].default_value = (vec[1] - vec0[1]) * 50 + 25

            # vec = data['highlightUpScale']
            bpy.data.node_groups[".Eye Textures positioning"].nodes["Group"].inputs[1].default_value = 1
            bpy.data.node_groups[".Eye Textures positioning"].nodes["Group"].inputs[2].default_value = 1

            vec = data['highlightDownOffset']
            bpy.data.node_groups[".Eye Textures positioning"].nodes["Group.001"].inputs[3].default_value = (vec[0] - vec0[0]) * 50 + 25
            bpy.data.node_groups[".Eye Textures positioning"].nodes["Group.001"].inputs[4].default_value = (vec[1] - vec0[1]) * 50 + 25

            # vec = data['highlightDownScale']
            bpy.data.node_groups[".Eye Textures positioning"].nodes["Group.001"].inputs[1].default_value = 1
            bpy.data.node_groups[".Eye Textures positioning"].nodes["Group.001"].inputs[2].default_value = 1

            # No need to set rotation
            # vec = data['eyeRotation']
            # bpy.data.node_groups[".Eye Textures positioning"].nodes["eye_scale"].inputs[5].default_value = math.degrees(vec[0])

            name = c.get_name()
            vec0 = tuple(data['highlightUpColor'])
            vec = tuple(data['highlightDownColor'])
            if bpy.data.materials.get('Edit KK cf_m_hitomi_00_cf_Ohitomi_L02'):
                bpy.data.materials[f"Edit cf_m_hitomi_00_cf_Ohitomi_L02"].node_tree.nodes["light"].inputs[0].default_value = vec0
                bpy.data.materials[f"Edit cf_m_hitomi_00_cf_Ohitomi_L02"].node_tree.nodes["light"].inputs[1].default_value = vec
                bpy.data.materials[f"Edit cf_m_hitomi_00_cf_Ohitomi_L02"].node_tree.nodes["light"].inputs[2].default_value = vec0[3]
                bpy.data.materials[f"Edit cf_m_hitomi_00_cf_Ohitomi_L02"].node_tree.nodes["light"].inputs[3].default_value = vec[3]
            if bpy.data.materials.get('Edit KK KK cf_m_hitomi_00_cf_Ohitomi_R02'):
                bpy.data.materials[f"Edit cf_m_hitomi_00_cf_Ohitomi_R02"].node_tree.nodes["light"].inputs[0].default_value = vec0
                bpy.data.materials[f"Edit cf_m_hitomi_00_cf_Ohitomi_R02"].node_tree.nodes["light"].inputs[1].default_value = vec
                bpy.data.materials[f"Edit cf_m_hitomi_00_cf_Ohitomi_R02"].node_tree.nodes["light"].inputs[2].default_value = vec0[3]
                bpy.data.materials[f"Edit cf_m_hitomi_00_cf_Ohitomi_R02"].node_tree.nodes["light"].inputs[3].default_value = vec[3]
        c.print_timer('adjust pupil and highlight')

    def apply_texture_data_to_image(self, mat: str, image: str, node:str, group = 'textures'):
        '''Sets offset and scale of an image node using the TextureData.json '''
        json_tex_data = c.json_file_manager.get_json_file('KK_TextureData.json')
        if not json_tex_data:
            c.kklog('wow great')
            return
        texture_data = [t for t in json_tex_data if t["textureName"] == image]
        if texture_data and bpy.data.materials.get(mat):
            #Apply Offset and Scale
            bpy.data.materials[mat].node_tree.nodes[group].node_tree.nodes[node].texture_mapping.translation[0] = texture_data[0]["offset"]["x"]
            bpy.data.materials[mat].node_tree.nodes[group].node_tree.nodes[node].texture_mapping.translation[1] = texture_data[0]["offset"]["y"]
            bpy.data.materials[mat].node_tree.nodes[group].node_tree.nodes[node].texture_mapping.scale[0] = texture_data[0]["scale"]["x"]
            bpy.data.materials[mat].node_tree.nodes[group].node_tree.nodes[node].texture_mapping.scale[1] = texture_data[0]["scale"]["y"]
   
    def set_uv_type(self, mat: str, uvnode: str, uv_name: str, group = 'textures'):
        bpy.data.materials['Edit ' + mat].node_tree.nodes[group].node_tree.nodes['pos'].node_tree.nodes[uvnode].uv_map = uv_name


    def skin_dark_color(self, color) -> dict[str, float]:
        '''Takes a 1.0 max rgba dict and returns a 1.0 max rgba dict. skin is from https://github.com/xukmi/KKShadersPlus/blob/main/Shaders/Skin/KKPSkinFrag.cginc '''
        diffuse = float4(color['r'], color['g'], color['b'], 1)
        shadingAdjustment = self.MapValuesMain(diffuse);

        diffuseShaded = shadingAdjustment * 0.899999976 - 0.5;
        diffuseShaded = -diffuseShaded * 2 + 1;

        compTest = 0.555555582 < shadingAdjustment;
        shadingAdjustment *= 1.79999995;
        diffuseShaded = -diffuseShaded * 0.7225 + 1;
        hlslcc_movcTemp = shadingAdjustment;
        hlslcc_movcTemp.x = diffuseShaded.x if (compTest.x) else shadingAdjustment.x; #370
        hlslcc_movcTemp.y = diffuseShaded.y if (compTest.y) else shadingAdjustment.y; #371
        hlslcc_movcTemp.z = diffuseShaded.z if (compTest.z) else shadingAdjustment.z; #372
        shadingAdjustment = (hlslcc_movcTemp).saturate(); #374 the lerp result (and shadowCol) is going to be this because shadowColor's alpha is always 1 making shadowCol 1

        finalDiffuse = diffuse * shadingAdjustment;

        bodyShine = float4(1.0656, 1.0656, 1.0656, 1);
        finalDiffuse *= bodyShine;
        fudge_factor = float4(0.02, 0.05, 0, 0) #result is slightly off but it looks consistently off so add a fudge factor
        finalDiffuse += fudge_factor

        return {'r':finalDiffuse.x, 'g':finalDiffuse.y, 'b':finalDiffuse.z, 'a':1}

    def clothes_dark_color(self, color: dict, shadow_color: dict) -> dict[str, float]:
        '''Takes a 1.0 max rgba dict and returns a 1.0 max rgba dict.
        clothes is from https://github.com/xukmi/KKShadersPlus/blob/main/Shaders/Item/MainItemPlus.shader
        This was stripped down to just the shadow portion, and to remove all constants'''
        ################### variable setup
        _ambientshadowG = float4(0.15, 0.15, 0.15, 0.15) #constant from experimentation
        diffuse = float4(color['r'],color['g'],color['b'],1) #maintex color
        _ShadowColor = float4(shadow_color['r'],shadow_color['g'],shadow_color['b'],1) #the shadow color from material editor
        ##########################

        #start at line 344 because the other one is for outlines
        shadingAdjustment = self.ShadeAdjustItem(diffuse, _ShadowColor)

        #skip to line 352
        diffuseShaded = shadingAdjustment * 0.899999976 - 0.5;
        diffuseShaded = -diffuseShaded * 2 + 1;

        compTest = 0.555555582 < shadingAdjustment;
        shadingAdjustment *= 1.79999995;
        diffuseShaded = -diffuseShaded * 0.7225 + 1; #invertfinalambient shadow is a constant 0.7225, so don't calc it

        hlslcc_movcTemp = shadingAdjustment;
        hlslcc_movcTemp.x = diffuseShaded.x if (compTest.x) else shadingAdjustment.x; #370
        hlslcc_movcTemp.y = diffuseShaded.y if (compTest.y) else shadingAdjustment.y; #371
        hlslcc_movcTemp.z = diffuseShaded.z if (compTest.z) else shadingAdjustment.z; #372
        shadingAdjustment = (hlslcc_movcTemp).saturate(); #374 the lerp result (and shadowCol) is going to be this because shadowColor's alpha is always 1 making shadowCol 1

        diffuseShadow = diffuse * shadingAdjustment;

        # lightCol is constant [1.0656, 1.0656, 1.0656, 1] calculated from the custom ambient of [0.666, 0.666, 0.666, 1] and sun light color [0.666, 0.666, 0.666, 1],
        # so ambientCol always results in lightCol after the max function
        ambientCol = float4(1.0656, 1.0656, 1.0656, 1);
        diffuseShadow = diffuseShadow * ambientCol;

        return {'r':diffuseShadow.x, 'g':diffuseShadow.y, 'b':diffuseShadow.z, 'a':1}

    def ShadeAdjustItem(self, col, _ShadowColor): #-> float4
        '''#shadeadjust function is from https://github.com/xukmi/KKShadersPlus/blob/main/Shaders/Item/KKPItemDiffuse.cginc .
    lines with comments at the end have been translated from C# to python. lines without comments at the end have been copied verbatim from the C# source'''
        #start at line 63
        t0 = col
        t1 = float4(t0.y, t0.z, None, t0.x) * float4(_ShadowColor.y, _ShadowColor.z, None, _ShadowColor.x) #line 65
        t2 = float4(t1.y, t1.x) #66
        t3 = float4(t0.y, t0.z) * float4(_ShadowColor.y, _ShadowColor.z) + (-float4(t2.x, t2.y)); #67
        tb30 = t2.y >= t1.y;
        t30 = 1 if tb30 else 0;
        t2 = float4(t2.x, t2.y, -1.0, 0.666666687); #70-71
        t3 = float4(t3.x, t3.y, 1.0, -1); #72-73
        t2 = (t30) * t3 + t2;
        tb30 = t1.w >= t2.x;
        t30 = 1 if tb30 else float(0.0);
        t1 = float4(t2.x, t2.y, t2.w, t1.w) #77
        t2 = float4(t1.w, t1.y, t2.z, t1.x) #78
        t2 = (-t1) + t2;
        t1 = (t30) * t2 + t1;
        t30 = min(t1.y, t1.w);
        t30 = (-t30) + t1.x;
        t2.x = t30 * 6.0 + 1.00000001e-10;
        t11 = (-t1.y) + t1.w;
        t11 = t11 / t2.x;
        t11 = t11 + t1.z;
        t1.x = t1.x + 1.00000001e-10;
        t30 = t30 / t1.x;
        t30 = t30 * 0.5;
        #the w component of t1 is no longer used, so ignore it
        t1 = abs((t11)) + float4(0.0, -0.333333343, 0.333333343, 1); #90
        t1 = t1.frac(); #91
        t1 = -t1 * 2 + 1; #92
        t1 = t1.abs() * 3 + (-1) #93
        t1 = t1.clamp() #94
        t1 = t1 + (-1); #95
        t1 = (t30) * t1 + 1; #96
        return float4(t1.x, t1.y, t1.z, 1) #97

class revert_material(bpy.types.Operator):
    bl_idname = "kkbp.revertmaterial"
    bl_label = "Revert material"
    bl_description = 'Revert material'
    bl_options = {'REGISTER', 'UNDO'}

    def execute(self, context):

        #replace the Edit material with the original material without saving it
        edit_material = bpy.context.object.active_material.name
        original_material = [i for i in bpy.data.materials if i.get('id') == bpy.data.materials[edit_material].get('id') and i.name != edit_material]
        if original_material:
            bpy.context.object.material_slots[edit_material].material = original_material[0]
            #TODO: Why does this crash blender
            bpy.data.materials.remove(bpy.data.materials[edit_material])

        return {'FINISHED'}
    
class save_material(bpy.types.Operator):
    bl_idname = "kkbp.savematerial"
    bl_label = "Save material"
    bl_description = 'Save material'
    bl_options = {'REGISTER', 'UNDO'}

    def execute(self, context):

        return {'FINISHED'}

class float4:
    '''class to mimic part of float4 class in Unity
    multiplying things per element according to https://github.com/Unity-Technologies/Unity.Mathematics/blob/master/src/Unity.Mathematics/float4.gen.cs#L330
    returning things like float.XZW as [Xposition = X, Yposition = Z, Zposition = W] according to https://github.com/Unity-Technologies/Unity.Mathematics/blob/master/src/Unity.Mathematics/float4.gen.cs#L3056
    using the variable order x, y, z, w according to https://github.com/Unity-Technologies/Unity.Mathematics/blob/master/src/Unity.Mathematics/float4.gen.cs#L42'''
    def __init__(self, x = None, y = None, z = None, w = None):
        self.x = x
        self.y = y
        self.z = z
        self.w = w
    def __mul__ (self, vector):
        #if a float4, multiply piece by piece, else multiply full vector
        if type(vector) in [float, int]:
            vector = float4(vector, vector, vector, vector)
        x = self.x * vector.x if self.get('x') != None else None
        y = self.y * vector.y if self.get('y') != None else None
        z = self.z * vector.z if self.get('z') != None else None
        w = self.w * vector.w if self.get('w') != None else None
        return float4(x,y,z,w)
    __rmul__ = __mul__
    def __add__ (self, vector):
        #if a float4, add piece by piece, else add full vector
        if type(vector) in [float, int]:
            vector = float4(vector, vector, vector, vector)
        x = self.x + vector.x if self.get('x') != None else None
        y = self.y + vector.y if self.get('y') != None else None
        z = self.z + vector.z if self.get('z') != None else None
        w = self.w + vector.w if self.get('w') != None else None
        return float4(x,y,z,w)
    __radd__ = __add__
    def __sub__ (self, vector):
        #if a float4, subtract piece by piece, else subtract full vector
        if type(vector) in [float, int]:
            vector = float4(vector, vector, vector, vector)
        x = self.x - vector.x if self.get('x') != None else None
        y = self.y - vector.y if self.get('y') != None else None
        z = self.z - vector.z if self.get('z') != None else None
        w = self.w - vector.w if self.get('w') != None else None
        return float4(x,y,z,w)
    __rsub__ = __sub__
    def __gt__ (self, vector):
        #if a float4, compare piece by piece, else compare full vector
        if type(vector) in [float, int]:
            vector = float4(vector, vector, vector, vector)
        x = self.x > vector.x if self.get('x') != None else None
        y = self.y > vector.y if self.get('y') != None else None
        z = self.z > vector.z if self.get('z') != None else None
        w = self.w > vector.w if self.get('w') != None else None
        return float4(x,y,z,w)
    def __neg__ (self):
        x = -self.x if self.get('x') != None else None
        y = -self.y if self.get('y') != None else None
        z = -self.z if self.get('z') != None else None
        w = -self.w if self.get('w') != None else None
        return float4(x,y,z,w)
    def frac(self):
        x = self.x - math.floor (self.x) if self.get('x') != None else None
        y = self.y - math.floor (self.y) if self.get('y') != None else None
        z = self.z - math.floor (self.z) if self.get('z') != None else None
        w = self.w - math.floor (self.w) if self.get('w') != None else None
        return float4(x,y,z,w)
    def abs(self):
        x = abs(self.x) if self.get('x') != None else None
        y = abs(self.y) if self.get('y') != None else None
        z = abs(self.z) if self.get('z') != None else None
        w = abs(self.w) if self.get('w') != None else None
        return float4(x,y,z,w)
    def clamp(self):
        x = (0 if self.x < 0 else 1 if self.x > 1 else self.x) if self.get('x') != None else None
        y = (0 if self.y < 0 else 1 if self.y > 1 else self.y) if self.get('y') != None else None
        z = (0 if self.z < 0 else 1 if self.z > 1 else self.z) if self.get('z') != None else None
        w = (0 if self.w < 0 else 1 if self.w > 1 else self.w) if self.get('w') != None else None
        return float4(x,y,z,w)
    saturate = clamp
    def clamphalf(self):
        x = (0 if self.x < 0 else .5 if self.x > .5 else self.x) if self.get('x') != None else None
        y = (0 if self.y < 0 else .5 if self.y > .5 else self.y) if self.get('y') != None else None
        z = (0 if self.z < 0 else .5 if self.z > .5 else self.z) if self.get('z') != None else None
        w = (0 if self.w < 0 else .5 if self.w > .5 else self.w) if self.get('w') != None else None
        return float4(x,y,z,w)
    def get(self, var):
        if hasattr(self, var):
            return getattr(self, var)
        else:
            return None
    def __str__(self):
        return str([self.x, self.y, self.z, self.w])
    __repr__ = __str__

