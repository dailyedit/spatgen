from spatgen.parser import parse_file
import sys

if len(sys.argv) != 2:
    print("Usage: python -m spatgen <path_to_pattern_file>")
    sys.exit(1)

spec = parse_file(sys.argv[1])
print("definitions\n===========")
print(spec["definitions"])
print()
for section, patterns in spec["sections"].items():
    print(section)
    print("".join("=" for _ in range(len(section))))
    for pattern in patterns:
        print(pattern)
    print()
