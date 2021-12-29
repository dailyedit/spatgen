from spatgen.parser import parse
import sys

if len(sys.argv) != 2:
    print("Usage: python -m spatgen <path_to_pattern_file>")
    sys.exit(1)

spec = parse(sys.argv[1])
for section, patterns in spec.items():
    print(section)
    print("".join("=" for _ in range(len(section))))
    for pattern in patterns:
        print(pattern)
    print()
