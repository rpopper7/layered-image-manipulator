# This is a script for the program Blender3D that can make an animation out of your
# images you sliced using LayeredImageManipulator. It does need to be copied and pasted into Blender3D

import os
import bpy
from bpy import context

# set the scene dimensions
scene = bpy.data.scenes["Scene"]
scene.render.resolution_x = 1080
scene.render.resolution_y = 1920
scene.render.resolution_percentage = 100

path = "/Users/RP/Desktop/layered-image-manipulator/video-outputs"
files = [f for f in os.listdir(path) if os.path.isfile(os.path.join(path, f))]
files.sort()
numOfFiles = len(files)

c = 2 # start on the second row to give room for audio & template below
panelCounter = 0
DURATION = 60
context.scene.sequence_editor_create()
for f in files:
    if f == "Thumbnail.png":
        break
    if f == f'Panel-{panelCounter + 1}':
        panelCounter += 1
        
    x1 = DURATION * (panelCounter - 1)
    x2 = x1 + DURATION

    seq = context.scene.sequence_editor.sequences.new_image(
        name = f,
        filepath = os.path.join(path, f),
        channel = c,
        frame_start = x1)
    seq.use_reverse_frames = False
    seq.blend_type = "ALPHA_OVER"
    seq.frame_final_duration = DURATION
    
    if "Bubble" in f:
        eff = context.scene.sequence_editor.sequences.new_effect(
            name = "Transform",
            type = "TRANSFORM",
            channel = (c + 1),
            frame_start = x1,
            frame_end = x2,
            seq1 = seq) # this last arg is target channel
        eff.blend_type = "ALPHA_OVER"
        c += 2
    else:
        c += 1

videoTemplatePath = "/Users/RP/Desktop/layered-image-manipulator/assets/video-template.png"
videoTemplateSeq = context.scene.sequence_editor.sequences.new_image(
    name = "template",
    filepath = videoTemplatePath,
    channel = c,
    frame_start = 0)
videoTemplateSeq.use_reverse_frames = False
videoTemplateSeq.blend_type = "ALPHA_OVER"
videoTemplateSeq.frame_final_duration = DURATION * panelCounter