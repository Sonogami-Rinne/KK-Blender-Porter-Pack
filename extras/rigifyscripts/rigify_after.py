
#Switch to Object Mode and select Generated Rig

import bpy
import math
from . import commons as koikatsuCommons
from ... import common as c
from ...importing.modifyarmature import modify_armature
    
def main():		   
    generatedRig = bpy.context.active_object

    assert generatedRig.mode == "OBJECT", 'assert generated_rig.mode == "OBJECT"'
    assert generatedRig.type == "ARMATURE", 'assert generatedRig.type == "ARMATURE"'
    
    generatedRig.show_in_front = True
    generatedRig.display_type = 'TEXTURED'
        
    metarig = None
    for bone in generatedRig.pose.bones:
        if bone.name.startswith(koikatsuCommons.metarigIdBonePrefix):
            generatedRigIdBoneName = bone.name
            for object in bpy.data.objects:
                if object != generatedRig and object.type == "ARMATURE":
                    for objectBone in object.pose.bones:
                        if objectBone.name == generatedRigIdBoneName:
                            metarig = object
                            break
            break
    
    if metarig:
        metarig.name = 'Metarig ' + metarig['name']
        generatedRig.name = 'Rig ' + metarig['name']
        generatedRig['rig'] = True
        generatedRig['name'] = metarig['name']

        metarig.hide_set(True)
        for object in bpy.data.objects:
            if object.type == "MESH":
                if object.parent == metarig:
                    object.parent = generatedRig
                for modifier in object.modifiers:
                    if modifier.type == "ARMATURE" and modifier.object == metarig:
                        modifier.object = generatedRig
                    if modifier.type == "UV_WARP" and modifier.object_from == metarig:
                        if modifier.name == "Left Eye UV warp":
                            modifier.object_from = generatedRig
                            modifier.bone_from = koikatsuCommons.eyesXBoneName
                            modifier.object_to = generatedRig
                            modifier.bone_to = koikatsuCommons.leftEyeBoneName
                        elif modifier.name == "Right Eye UV warp":
                            modifier.object_from = generatedRig
                            modifier.bone_from = koikatsuCommons.eyesXBoneName
                            modifier.object_to = generatedRig
                            modifier.bone_to = koikatsuCommons.rightEyeBoneName

    koikatsuCommons.setBoneCustomShapeScale(generatedRig, koikatsuCommons.eyesTrackTargetBoneName, 1.5)
    koikatsuCommons.setBoneCustomShapeScale(generatedRig, koikatsuCommons.headTweakBoneName, 1.1)
    koikatsuCommons.setBoneCustomShapeScale(generatedRig, koikatsuCommons.leftBreastDeformBone1Name, 0.4)
    koikatsuCommons.setBoneCustomShapeScale(generatedRig, koikatsuCommons.rightBreastDeformBone1Name, 0.4)
    koikatsuCommons.setBoneCustomShapeScale(generatedRig, koikatsuCommons.leftBreastBone2Name, 3)
    koikatsuCommons.setBoneCustomShapeScale(generatedRig, koikatsuCommons.rightBreastBone2Name, 3)
    koikatsuCommons.setBoneCustomShapeScale(generatedRig, koikatsuCommons.leftBreastDeformBone2Name, 0.3)
    koikatsuCommons.setBoneCustomShapeScale(generatedRig, koikatsuCommons.rightBreastDeformBone2Name, 0.3)
    koikatsuCommons.setBoneCustomShapeScale(generatedRig, koikatsuCommons.leftBreastBone3Name, 2)
    koikatsuCommons.setBoneCustomShapeScale(generatedRig, koikatsuCommons.rightBreastBone3Name, 2)
    koikatsuCommons.setBoneCustomShapeScale(generatedRig, koikatsuCommons.leftBreastDeformBone3Name, 0.2)
    koikatsuCommons.setBoneCustomShapeScale(generatedRig, koikatsuCommons.rightBreastDeformBone3Name, 0.2)
    koikatsuCommons.setBoneCustomShapeScale(generatedRig, koikatsuCommons.leftNippleBone1Name, 1)
    koikatsuCommons.setBoneCustomShapeScale(generatedRig, koikatsuCommons.rightNippleBone1Name, 1)
    koikatsuCommons.setBoneCustomShapeScale(generatedRig, koikatsuCommons.leftNippleDeformBone1Name, 0.1)
    koikatsuCommons.setBoneCustomShapeScale(generatedRig, koikatsuCommons.rightNippleDeformBone1Name, 0.1)
    koikatsuCommons.setBoneCustomShapeScale(generatedRig, koikatsuCommons.leftNippleBone2Name, 0.5)
    koikatsuCommons.setBoneCustomShapeScale(generatedRig, koikatsuCommons.rightNippleBone2Name, 0.5)
    koikatsuCommons.setBoneCustomShapeScale(generatedRig, koikatsuCommons.leftNippleDeformBone2Name, 0.05)
    koikatsuCommons.setBoneCustomShapeScale(generatedRig, koikatsuCommons.rightNippleDeformBone2Name, 0.05)
    koikatsuCommons.setBoneCustomShapeScale(generatedRig, koikatsuCommons.leftShoulderBoneName, 1.25)
    koikatsuCommons.setBoneCustomShapeScale(generatedRig, koikatsuCommons.rightShoulderBoneName, 1.25)
    koikatsuCommons.setBoneCustomShapeScale(generatedRig, koikatsuCommons.leftThumbBone1Name, 1.3)
    koikatsuCommons.setBoneCustomShapeScale(generatedRig, koikatsuCommons.rightThumbBone1Name, 1.3)
    koikatsuCommons.setBoneCustomShapeScale(generatedRig, koikatsuCommons.leftThumbBone2Name, 1.3)
    koikatsuCommons.setBoneCustomShapeScale(generatedRig, koikatsuCommons.rightThumbBone2Name, 1.3)
    koikatsuCommons.setBoneCustomShapeScale(generatedRig, koikatsuCommons.leftThumbBone3Name, 1.2)
    koikatsuCommons.setBoneCustomShapeScale(generatedRig, koikatsuCommons.rightThumbBone3Name, 1.2)
    koikatsuCommons.setBoneCustomShapeScale(generatedRig, koikatsuCommons.leftIndexFingerBone2Name, 1.1)
    koikatsuCommons.setBoneCustomShapeScale(generatedRig, koikatsuCommons.rightIndexFingerBone2Name, 1.1)
    koikatsuCommons.setBoneCustomShapeScale(generatedRig, koikatsuCommons.leftIndexFingerBone3Name, 1.1)
    koikatsuCommons.setBoneCustomShapeScale(generatedRig, koikatsuCommons.rightIndexFingerBone3Name, 1.1)
    koikatsuCommons.setBoneCustomShapeScale(generatedRig, koikatsuCommons.leftMiddleFingerBone2Name, 1.1)
    koikatsuCommons.setBoneCustomShapeScale(generatedRig, koikatsuCommons.rightMiddleFingerBone2Name, 1.1)
    koikatsuCommons.setBoneCustomShapeScale(generatedRig, koikatsuCommons.leftMiddleFingerBone3Name, 1.1)
    koikatsuCommons.setBoneCustomShapeScale(generatedRig, koikatsuCommons.rightMiddleFingerBone3Name, 1.1)
    koikatsuCommons.setBoneCustomShapeScale(generatedRig, koikatsuCommons.leftRingFingerBone2Name, 1.1)
    koikatsuCommons.setBoneCustomShapeScale(generatedRig, koikatsuCommons.rightRingFingerBone2Name, 1.1)
    koikatsuCommons.setBoneCustomShapeScale(generatedRig, koikatsuCommons.leftRingFingerBone3Name, 1.1)
    koikatsuCommons.setBoneCustomShapeScale(generatedRig, koikatsuCommons.rightRingFingerBone3Name, 1.1)
    koikatsuCommons.setBoneCustomShapeScale(generatedRig, koikatsuCommons.leftLittleFingerPalmBoneName, 1.1)
    koikatsuCommons.setBoneCustomShapeScale(generatedRig, koikatsuCommons.rightLittleFingerPalmBoneName, 1.1)
    koikatsuCommons.setBoneCustomShapeScale(generatedRig, koikatsuCommons.leftLittleFingerPalmFkBoneName, 1.1)
    koikatsuCommons.setBoneCustomShapeScale(generatedRig, koikatsuCommons.rightLittleFingerPalmFkBoneName, 1.1)
    koikatsuCommons.setBoneCustomShapeScale(generatedRig, koikatsuCommons.leftLittleFingerBone2Name, 1.1)
    koikatsuCommons.setBoneCustomShapeScale(generatedRig, koikatsuCommons.rightLittleFingerBone2Name, 1.1)
    koikatsuCommons.setBoneCustomShapeScale(generatedRig, koikatsuCommons.leftLittleFingerBone3Name, 1.1)
    koikatsuCommons.setBoneCustomShapeScale(generatedRig, koikatsuCommons.rightLittleFingerBone3Name, 1.1)
    koikatsuCommons.setBoneCustomShapeScale(generatedRig, koikatsuCommons.rootBoneName, 0.25)
    
    for bone_name in modify_armature.face_bones + modify_armature.face_bones_mch:
        if bone := generatedRig.pose.bones.get(bone_name):
            bone.custom_shape_rotation_euler[0] = math.pi/2
    koikatsuCommons.setBoneCustomShapeScale(generatedRig, 'cf_j_kokan', 0.2)

    headBone = generatedRig.pose.bones[koikatsuCommons.originalBonePrefix + koikatsuCommons.headBoneName]
    koikatsuCommons.changeConstraintIndex(generatedRig, headBone.name, koikatsuCommons.transformationConstraintBaseName + koikatsuCommons.headConstraintSuffix + koikatsuCommons.rotationConstraintSuffix, len(headBone.constraints) - 1)
    koikatsuCommons.changeConstraintIndex(generatedRig, headBone.name, koikatsuCommons.limitRotationConstraintBaseName + koikatsuCommons.headConstraintSuffix, len(headBone.constraints) - 1)
    
    headTweakLimitRotationConstraint = koikatsuCommons.addLimitRotationConstraint(generatedRig, koikatsuCommons.headTweakBoneName, None, 'LOCAL', koikatsuCommons.limitRotationConstraintBaseName + koikatsuCommons.headConstraintSuffix, 
    True, math.radians(-180), math.radians(180), True, math.radians(-180), math.radians(180), True, math.radians(-180), math.radians(180))
    
    for driver in generatedRig.animation_data.drivers:
        if driver.data_path.startswith("pose.bones"):
            driverOwnerName = driver.data_path.split('"')[1]
            driverProperty = driver.data_path.rsplit('.', 1)[1]
            if driverOwnerName == headBone.name:
                constraintName = driver.data_path.split('"')[3]
                if constraintName == koikatsuCommons.limitRotationConstraintBaseName + koikatsuCommons.headConstraintSuffix:
                    variable = driver.driver.variables[0]
                    newVariable = koikatsuCommons.DriverVariable(variable.name, variable.type, generatedRig, variable.targets[0].bone_target, None, None, None, None, variable.targets[0].data_path, None, None)																																											  
                    koikatsuCommons.addDriver(headTweakLimitRotationConstraint, driverProperty, None, driver.driver.type, [newVariable], 
                    driver.driver.expression)
        
    for bone in generatedRig.pose.bones:
        for constraint in bone.constraints:
            if constraint.type == 'ARMATURE':
                for target in constraint.targets:
                    if target.subtarget:
                        target.target = generatedRig
                        if target.subtarget.endswith(koikatsuCommons.placeholderBoneSuffix):
                            target.subtarget = target.subtarget[:-len(koikatsuCommons.placeholderBoneSuffix)]
    
    for driver in bpy.data.objects[koikatsuCommons.bodyName()].data.shape_keys.animation_data.drivers:
        if driver.data_path.startswith("key_blocks"):
            ownerName = driver.data_path.split('"')[1]
            if ownerName == koikatsuCommons.eyelidsShapeKeyCopyName:
                for variable in driver.driver.variables:
                    for target in variable.targets:
                        if target.id == metarig:
                            target.id = generatedRig 
    
    for driver in generatedRig.animation_data.drivers:    
        if driver.data_path.startswith("pose.bones"):
            driverOwnerName = driver.data_path.split('"')[1]
            driverProperty = driver.data_path.rsplit('.', 1)[1]
            if driverOwnerName in koikatsuCommons.bonesWithDrivers and driverProperty == "location":
                for variable in driver.driver.variables:
                    for target in variable.targets:
                        for targetToChange in koikatsuCommons.targetsToChange:
                            if target.bone_target == koikatsuCommons.originalBonePrefix + targetToChange:
                                target.bone_target = koikatsuCommons.deformBonePrefix + targetToChange
                                
    bpy.ops.object.mode_set(mode='EDIT')

    for bone in generatedRig.data.edit_bones:
        if bone.collections.get(koikatsuCommons.getRigifyLayerIndexByName(koikatsuCommons.junkLayerName)):
            koikatsuCommons.deleteBone(generatedRig, bone.name)
            continue
        if bone.collections.get(koikatsuCommons.defLayerIndex) or bone.collections.get(koikatsuCommons.nsfwLayerName) or bone.name == 'cf_s_waist02':
            bone.use_deform = True

    #face bones deform
    for bone in generatedRig.data.edit_bones:
        if bone.collections.get(koikatsuCommons.faceLayerName):
            bone.use_deform = True
    
    #other bones deform
    for bone in metarig.data.bones:
        if bone.collections.get(koikatsuCommons.faceLayerName + koikatsuCommons.mchLayerSuffix) or bone.collections.get(koikatsuCommons.nsfwLayerName):
            koikatsuCommons.unlockAllPoseTransforms(metarig, bone.name)
            bone.use_deform = True

    generatedRig.data.edit_bones[koikatsuCommons.eyesTrackTargetParentBoneName].parent = None
    generatedRig.data.edit_bones[koikatsuCommons.headTrackTargetParentBoneName].parent = None

    bpy.ops.object.mode_set(mode='OBJECT')
        
    bpy.context.object.pose.bones["root"].color.palette = 'CUSTOM'
    #needs to be done for data and pose
    generatedRig.data.bones['root'].color.custom.normal = (0.956863, 0.788235, 0.047059)
    generatedRig.data.bones['root'].color.custom.select = (0.313989, 0.783538, 1.000000)
    generatedRig.data.bones['root'].color.custom.active = (0.552011, 1.000000, 1.000000)

    generatedRig.pose.bones['root'].color.custom.active = (0.552011, 1.000000, 1.000000)
    generatedRig.pose.bones['root'].color.custom.normal = (0.956863, 0.788235, 0.047059)
    generatedRig.pose.bones['root'].color.custom.select = (0.313989, 0.783538, 1.000000)

    #set layer visibility
    for collection in generatedRig.data.collections_all:
        collection.is_visible = False
    for layer in ['Torso', 'Arm.L IK', 'Arm.R IK', 'Leg.L IK', 'Leg.R IK', 'Root']:
        generatedRig.data.collections_all[layer].is_visible = True

    #Take the IDs from all org bones and copy them over to the generated / helper bones
    for bone in generatedRig.data.bones:
        if bone.get('id') and bone.name.startswith('ORG-'):
            bone_base_name = bone.name[4:]  # Remove 'ORG-' prefix
            for bone_name in [
                bone_base_name,
                'DEF-' + bone_base_name,
                bone_base_name + '_ik', 
                bone_base_name + '_ik.parent', 
                bone_base_name + '_master', 
                'MCH-' + bone_base_name,
                'MCH-' + bone_base_name + '_drv',
                ]:
                if generatedRig.data.bones.get(bone_name):
                    generatedRig.data.bones[bone_name]['id'] = bone['id']
                    #also add the id to the .001 tail bone that appears sometimes
                    if 'MCH-' in bone_name and '_drv' in bone_name:
                        if first_child := generatedRig.data.bones[bone_name].children:
                            if second_child := first_child[0].children:
                                second_child[0]['id'] = bone['id']

    #Finally, extract the accessory bones for different outfits to their own layers... 
    #I won't put these in the Rigify UI, but they'll still be accessible in the bone collection section
    clothes_and_hair = c.get_outfits()
    clothes_and_hair.extend(c.get_hairs())
    outfit_ids = (int(c['id']) for c in clothes_and_hair if c.get('id'))
    outfit_ids = list(set(outfit_ids))
    already_used = []
    for id in outfit_ids:
        if int(id) == min(outfit_ids):
            continue
        for bone in [bone for bone in generatedRig.data.bones if bone.name not in already_used]:
            if new_layer := bone.get('id'):
                if int(new_layer[0]) != min(outfit_ids):
                    if koikatsuCommons.hairLayerName in bone.collections[0].name:
                        koikatsuCommons.assignSingleBoneLayer(generatedRig, bone.name, bone.collections[0].name + f' {new_layer[0]}')
                        already_used.append(bone.name)
                        bone.collections[0].is_visible = False

class rigify_after(bpy.types.Operator):
    bl_idname = "kkbp.rigafter"
    bl_label = "After Each Rigify Generate - Public"
    bl_description = 'Performs cleanup after a Rigify generation'
    bl_options = {'REGISTER', 'UNDO'}

    def execute(self, context):
        main()
        return {'FINISHED'}

