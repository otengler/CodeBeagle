import re, sys

m = re.match("(\\d+)\\.(\\d+)", sys.version)
if not m:
    print("Unable to determine Python version")
    sys.exit(1)

print(f"{m.group(1)}{m.group(2)}")