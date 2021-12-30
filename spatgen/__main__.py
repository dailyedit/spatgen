from spatgen.parser import parse_file
import sys

if len(sys.argv) != 2:
    print("Usage: python -m spatgen <path_to_pattern_file>")
    sys.exit(1)

sections = parse_file(sys.argv[1])
for key in sections.keys():
    print(key)
    print("".join("=" for _ in range(len(key))))
    for pattern in sections[key]:
        print(pattern)
