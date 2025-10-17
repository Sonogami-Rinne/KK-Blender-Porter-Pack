#simplfies bone count using the merge weights function in CATS

import bpy, traceback, time
from .. import common as c
from ..interface.dictionary_en import t

def main(prep_type, simp_type):

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

        #TODO: Create the atlas here

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
            main(prep_type, simp_type)
            c.kklog('Finished in ' + str(time.time() - last_step)[0:4] + 's')
            c.toggle_console()
            return {'FINISHED'}
        except:
            c.kklog('Unknown python error occurred', type = 'error')
            c.kklog(traceback.format_exc())
            self.report({'ERROR'}, traceback.format_exc())
            return {"CANCELLED"}
    
