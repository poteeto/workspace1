#!/usr/bin/env python3
"""Native DeepSeek monochrome brand integration guard.

Static tests only: does not imply that WebView/React styles or true-device
rendering has passed. Intentional semantic warning/error/success colors remain.
"""
from pathlib import Path
import xml.etree.ElementTree as ET

ROOT=Path(__file__).resolve().parents[1]
RES=ROOT/"app/src/main/res"
ANDROID="{http://schemas.android.com/apk/res/android}"

def parse(path):
    return ET.parse(path).getroot()

def colors(name):
    root=parse(RES/name/"colors.xml")
    return {x.attrib["name"]:(x.text or "").strip().upper() for x in root.findall("color")}

light=colors("values")
dark=colors("values-night")
assert light["primary"]=="#111111"
assert dark["primary"]=="#F5F5F5"
assert light["surface"]=="#FFFFFF"
assert dark["surface"]=="#000000"
for palette in (light,dark):
    assert all(palette[n] for n in ("ok","warn","err","text","text_secondary","primary"))
    assert len(set(palette[n] for n in ("ok","warn","err")))==3

foreground=parse(RES/"drawable/dsha_launcher_foreground.xml")
assert foreground.tag=="vector"
assert foreground.find("group/path").get(ANDROID+"fillColor")=="#FFFFFFFF"
assert len(foreground.find("group/path").get(ANDROID+"pathData",""))>3000

for name in ("bg_dsha_brand.xml","bg_ui2_mark.xml"):
    mark=parse(RES/"drawable"/name)
    assert mark.find("solid").attrib[ANDROID+"color"].upper()=="#FF000000",name

references={
    "layout/activity_main.xml":"dsha_launcher_foreground",
    "layout/activity_welcome.xml":"dsha_launcher_foreground",
    "layout/welcome_page1.xml":"dsha_launcher_foreground",
    "layout/dialog_about.xml":"dsha_launcher_foreground"
}
for path,drawable in references.items():
    root=parse(RES/path)
    images=[x for x in root.iter() if x.tag.endswith("ImageView") and x.get(ANDROID+"src")=="@drawable/"+drawable]
    assert len(images)==1,(path,len(images))
    image=images[0]
    assert image.get(ANDROID+"tint") is None,(path,"brand must not be tinted")

java=(ROOT/"app/src/main/java/com/deepseekharness/app/ui/AboutFragment.java").read_text()
assert "mark.setImageResource(R.drawable.dsha_launcher_foreground)" in java
assert "mark.setBackgroundResource(R.drawable.bg_dsha_brand)" in java

main=(ROOT/"app/src/main/java/com/deepseekharness/app/util/Constants.java").read_text()
import re,json
m=re.search(r'DSH_VERSION\s*=\s*"([^"]+)"',main)
assert m is not None
version=json.loads((ROOT/"tools/dsh-runtime/package.json").read_text())["dependencies"]["@deepseek-ai/dsh"]
assert m.group(1)==version,("Android version mismatch",m.group(1),version)

print("PASS: unified official DeepSeek monochrome vector across native main, welcome and About; semantic status colors intact; DSH versions aligned.")
