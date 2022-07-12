import re
import numpy as np

with open(r"SPV-plan.txt",'r') as f:
    txt = f.read()

txt = txt.replace(",",".")
getCatchInfo = re.compile(r"\n([^ \n]+) [^ \n-]+ [^ \n]+ ([^ \n]+) ([^ \n]+) [^ \n]+ ([^ \n]+)")

match = getCatchInfo.findall(txt)

with open(r"SPV-plan.csv","w") as f:
    for m in match:
        f.write("%s,%s,%s,%s\n" % (m[0],m[1],m[2],m[3]))