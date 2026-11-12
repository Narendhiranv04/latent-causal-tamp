#!/bin/bash
# after the laptop xy run: empty-sequence verification, then run gvlab's not-yet-done items from the END of its list (gvlab runs from the start)
V4=/home/naren/Desktop/boltzmann_lfd/final_dataset_generation/final3d_v4; cd $V4/work
while ! grep -q "^DONE" xy_final_laptop.log; do sleep 30; done
$V4/code/run.sh xy es_items.json es_verify.jsonl 20 0-19
scp -q gvlab:approachb_final_gen/final3d_v4/work/xy_final_gvlab.jsonl xy_final_gvlab.jsonl
python3 - <<'P'
import json
SRC="/home/naren/Desktop/rss3d_final_src/gh-yadu-iiith/shelf_6x6_open_sides/dataset_bd_classquota_without_home_position_no_overpass/raw/roots/"
GV="/home/nav/approachb_final_gen/final3d_v4/src/dataset_bd_classquota_without_home_position_no_overpass/raw/roots/"
it=json.load(open("xy_final_gvlab.json")); done={json.loads(l)["key"] for l in open("xy_final_gvlab.jsonl")}
rest=[dict(i,path=i["path"].replace(GV,SRC)) for i in it if i["key"] not in done][::-1]
json.dump(rest,open("xy_assist_laptop.json","w")); print("assist items",len(rest))
P
$V4/code/run.sh xy xy_assist_laptop.json xy_assist_laptop.jsonl 27 0-26
