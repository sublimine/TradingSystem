"""
Verify Build Integrity - Verifica reproducibilidad del build
"""
import json
import hashlib
from pathlib import Path

def compute_file_hash(file_path: Path) -> str:
    hasher = hashlib.sha256()
    with open(file_path, 'rb') as f:
        while chunk := f.read(8192):
            hasher.update(chunk)
    return hasher.hexdigest()

def verify_build():
    sbom_path = Path("SBOM.json")
    if not sbom_path.exists():
        print("ERROR: SBOM.json not found")
        return False
    
    with open(sbom_path, 'r') as f:
        sbom = json.load(f)
    
    print(f"Verifying: {sbom['project_name']} v{sbom['version']}")
    print(f"Modules to check: {len(sbom['modules'])}\n")
    
    valid = 0
    modified = 0
    missing = 0
    
    for module in sbom['modules']:
        path = Path(module['path'])
        expected = module['sha256']
        
        if not path.exists():
            print(f"MISSING: {module['path']}")
            missing += 1
        else:
            actual = compute_file_hash(path)
            if actual == expected:
                print(f"OK: {module['path']}")
                valid += 1
            else:
                print(f"MODIFIED: {module['path']}")
                modified += 1
    
    print(f"\nResults: {valid} OK, {modified} modified, {missing} missing")
    return modified == 0 and missing == 0

if __name__ == "__main__":
    verify_build()
