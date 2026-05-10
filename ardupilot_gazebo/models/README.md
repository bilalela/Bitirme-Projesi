Models added: lightweight radar and SAM launcher

Files:
- radar_simple/model.config
- radar_simple/model.sdf
- sam_launcher/model.config
- sam_launcher/model.sdf

Spawn examples (while Gazebo is running):

1) Spawn radar at specific pose:
   gz model --spawn-file=$(pwd)/ardupilot_gazebo/models/radar_simple/model.sdf -y 0 -x 10 -z 0

2) Spawn SAM launcher:
   gz model --spawn-file=$(pwd)/ardupilot_gazebo/models/sam_launcher/model.sdf -y 5 -x 12 -z 0

Alternatively use `gz model --spawn-file <path>` with absolute paths.

These are lightweight SDF-only models (no external meshes) for quick testing.
