from bpy.app.translations import locale
from .dictionary_jp import translation_dictionary as jp_translation
from .dictionary_zh import translation_dictionary as zh_translation

translation_dictionary = {

    'seams'     : "Fix body seams",
    'seams_tt'  : 'This performs a "Merge by Distance" operation on the body materials. Removing doubles screws with the weights around certain areas. Disabling this will preserve the weights, but may cause seams to appear around the neck and down the chest when the outline modifier is on',
    
    
    'keep_templates'        : "Keep material templates",
    'keep_templates_tt'     : "Keep enabled to set the KKBP material templates to fake user. This will keep them from being deleted when blender is closed. Useful if you want to apply them to other objects after your character is finished",

    'sfw_mode'          : 'SFW mode',
    'sfw_mode_tt'       : 'Attempts to cover up some NSFW things',

    'use_rigify'        : "Use Rigify Armature",
    'no_rigify'         : "Use FK Armature",
    'use_rigify_tt'     : "Choose between the Rigify armature and an FK armature. The Rigify armature is an advanced armature suitable for use in Blender. The FK armature is easier to use and better suited for exporting the model out of Blender",

    'cat_drop'      : 'Separation type',
    'no_separate'    : "One object per outfit",
    'cat_drop_A_tt' : "Import everything and get a single object containing all your model's clothes. Hides any alternate clothes by default",
    'separate'    : "Separate all clothing",
    'cat_drop_B_tt' : "Import everything and automatically separate every single piece of clothing into several objects",

    'prep_drop'         : 'Export type',
    'prep_drop_A'       : 'Unity - VRM compatible',
    'prep_drop_A_tt'    : 'This option will edit the bone hierarchy to allow Unity to automatically detect the right bones',
    'prep_drop_B'       : 'Generic FBX - No changes',
    'prep_drop_B_tt'    : 'Does not make any changes to the armature. This works best if you plan on re-implementing the bone drivers, bone constraints and other advanced features in another program',
    'prep_drop_D'       : 'Unity - VRChat compatible',
    'prep_drop_D_tt'    : 'This option will edit the bone hierarchy to allow Unity to automatically detect the right bones. It will also removed the "Upper Chest" bone from the armature',
    'prep_drop_E'       : 'Unreal Engine',
    'prep_drop_E_tt'    : """This option will edit the bone hierarchy to match Epic Mannequin skeleton""",

    'simp_drop'     : 'Armature simplification type',
    'simp_drop_A'   : 'Very simple (SLOW)',
    'simp_drop_A_tt': 'Use this option if you want a very low bone count. This will leave you with ~100 bones. It will simplify bones in the following bone collections: Junk, Charamaker bones, Deform bones, NSFW, Face, Face (MCH), Rigged Tongue',
    'simp_drop_B'   : 'Simple',
    'simp_drop_B_tt': 'This will leave you with ~500 bones. It will simplify the useless bones in the Junk bone collection',
    'simp_drop_C'   : 'No changes (FAST)',
    'simp_drop_C_tt': 'Does not simplify anything',

    'shader_A'       : 'Use Eevee',
    'shader_B'       : "Use Cycles (toon)",
    'shader_D'       : "Use Cycles (classic)",
    'shader_C'       : "Use Eevee mod",
    'shader_C_tt'    : "Uses a modified shader setup for Eevee",

    'import_export' : 'Importing and Exporting',
    'extras'        : 'KKBP Extras',
    'import_model'  : 'Import model',
    'prep'          : 'Prep for target application',

    'single_animation'          : 'Import single animation file',
    'single_animation_tt'       : 'Only available for the Rigify armature. Imports an exported Koikatsu .fbx animation file and applies it to your character. Mixamo .fbx files are also supported if you use the toggle below',
    'animation_koi'             : 'Import Koikatsu animation',
    'animation_mix'             : 'Import Mixamo animation',
    'animation_type_tt'         : 'Disable this if you are importing a Koikatsu .fbx animation. Enable this if you are importing a Mixamo .fbx animation',
    'animation_library'         : 'Create animation library',
    'animation_library_tt'      : "Only available for the Rigify Armature. Creates an animation library using the current file and current character. Will not save over the current file in case you want to reuse it. Open the folder containing the animation files exported with SB3Utility",
    'animation_library_scale'   : 'Scale arms',
    'animation_library_scale_tt': 'Check this to scale the arms on the y axis by 5%. This will make certain poses more accurate to the in-game one',

    'rigify_convert'            : "Convert to Rigify",
    'rigify_convert_tt'         : "Convert the FK armature into a Rigify armature (Warning: This is irreversible)",
    'sep_eye'                   : "Separate Eyes and Eyebrows",
    'sep_eye_tt'                : "Separates the Eyes and Eyebrows from the Body object and links the shapekeys to the Body object. Useful for when you want to make eyes or eyebrows appear through the hair using the Cryptomatte features in the compositor",
    'link_hair'                 : 'Update hair materials',
    'link_hair_tt'              : 'Click to copy the current colors, detail intensity, etc to the other hair materials on this object',

    'kkbp_import_tt'    : "Imports a Koikatsu model (.pmx format) and applies fixes to it",
    'export_prep_tt'    : "Only works if you import with the FK armature. Prepares your model for export to Unity, Unreal Engine, or other 3D applications",

    'use_atlas' : 'Create atlas',
    'dont_use_atlas' : 'Don\'t create Atlas',
    'atlas_no_eyes' : 'Create atlas (skip eyes)',
    'use_atlas_tt': 'Enable this to create a material atlas when finalizing materials. If you want to apply UV offsets to the eye materials in Unity, Unreal, etc then use the "skip eyes" option',

    'mat_comb_tt' : 'KKBP uses parts of Shotariya\'s Material Combiner addon to automatically merge your materials into an atlas. Click this if you want to manually combine your materials instead of letting KKBP do it for you (requires you to download the Material Combiner addon)',
    'matcomb' : 'Setup materials for Material Combiner',
    'mat_comb_switch' : 'Toggle light / dark for Material Combiner',
    'mat_comb_switch_tt' : 'Click this to toggle texture state to get both a light and dark atlas from Material Combiner',

    'pillow' : 'Install PIL to use the atlas feature',
    'pillow_tt':'Click to install Pillow from PyPI. This could take a while and might require you to run Blender as Admin',
    
    'max_thread_num' : 'Max threads',
    'max_image_num' : 'Max parallel images',
    'batch_rows' : 'Rows per batch',
    'max_thread_num_tt' : 'KKBP saturates your character\'s textures during model import. This option determines how many CPU cores you want to use to perform the saturation. If you have more cores to spare, you can set it higher. Default is 8.',
    'max_image_num_tt' : 'KKBP saturates your character\'s textures during model import. This option determines how many images can be saturated at once. This setting affects memory usage. For example, if the program loads two 4096 x 4096 images, the peak memory usage could reach 8 GB. If you don\'t have 8GB of free memory Blender could crash. Default is 2',
    'batch_rows_tt' : 'KKBP saturates your character\'s textures during model import. This option determines how many rows of pixels to process in one batch. For example, if this setting is set to 512 rows and the program is saturating a 1024 x 1024 image, it will be processed in two 512 x 1024 batches. Increasing this value can allow you to process the full image in a single batch, but will increase CPU and memory usage. Default is 512',

    'outline' : 'Use outlines',
    'no_outline' : 'Don\'t use outlines',
    'outline_tt'  : "If outlines are enabled, KKBP will create an outline material for each material on the model.",

    'use_rigify_tt' : 'Enable this to use Rigify as the default armature when importing models. Requires the Rigify addon to be enabled in Blender preferences',
    'dont_use_rigify_tt' : 'Disable this to use the FK armature as the default armature when importing models',

    'bad_prep': 'Import with the FK armature to use Export features!'
    }

def t(text_entry):
    try:
        if locale == 'ja_JP':
            return jp_translation[text_entry]
        elif locale in ['zh_HANS', 'zh_CN']:
            return zh_translation[text_entry]
        else:
            return translation_dictionary[text_entry]
    except KeyError:
        #default to english if not translated
        if translation_dictionary.get(text_entry):
            return translation_dictionary[text_entry] 
        else:
            return text_entry

