"""
Generate requirements with hashes using pip download
"""
import subprocess
import tempfile
import hashlib
from pathlib import Path

def get_package_hash(package_spec):
    """Download package and compute SHA256 hash."""
    with tempfile.TemporaryDirectory() as tmpdir:
        # Download package
        result = subprocess.run(
            ["pip", "download", "--no-deps", "-d", tmpdir, package_spec],
            capture_output=True,
            text=True
        )
        
        if result.returncode != 0:
            return None
        
        # Find downloaded file
        files = list(Path(tmpdir).glob("*"))
        if not files:
            return None
        
        # Compute hash
        pkg_file = files[0]
        hasher = hashlib.sha256()
        
        with open(pkg_file, 'rb') as f:
            while chunk := f.read(8192):
                hasher.update(chunk)
        
        return hasher.hexdigest()

def generate_lockfile_with_hashes(requirements_file, output_file):
    """Generate lockfile with hashes."""
    with open(requirements_file, 'r') as f:
        packages = [line.strip() for line in f if line.strip() and not line.startswith('#')]
    
    lockfile_lines = [
        "# Generated lockfile with SHA256 hashes",
        "# To install: pip install --require-hashes -r requirements.lock",
        ""
    ]
    
    for package_spec in packages:
        print(f"Processing {package_spec}...")
        
        pkg_hash = get_package_hash(package_spec)
        
        if pkg_hash:
            lockfile_lines.append(f"{package_spec} \\")
            lockfile_lines.append(f"    --hash=sha256:{pkg_hash}")
        else:
            print(f"  WARNING: Could not get hash for {package_spec}")
            lockfile_lines.append(f"{package_spec}")
    
    with open(output_file, 'w') as f:
        f.write('\n'.join(lockfile_lines))
    
    print(f"\nLockfile generated: {output_file}")

if __name__ == "__main__":
    generate_lockfile_with_hashes("requirements.txt", "requirements.lock")
