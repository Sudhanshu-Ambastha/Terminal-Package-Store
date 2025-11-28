import subprocess
from dataclasses import dataclass
from typing import List

@dataclass
class Package:
    """Represents a single package entry returned by winget list/upgrade."""
    name: str
    id: str
    version: str
    available_version: str
    source: str

def get_upgradable_packages() -> List[Package]:
    """
    Executes 'winget upgrade' and parses the output into a list of Package objects.
    This is sensitive to changes in winget's output formatting.
    """
    try:
        # 1. Execute the winget command
        result = subprocess.run(
            ['winget', 'upgrade'], 
            capture_output=True, 
            text=True, 
            check=True
        )
        
        lines = result.stdout.strip().split('\n')
        packages = []

        try:
            start_index = lines.index("-----------------------------------------------------------------------------------------------------------------------") + 1
        except ValueError:
            return []
        
        for line in lines[start_index:]:
            if not line.strip():
                continue
            
            parts = line.split() 
            
            if len(parts) >= 5:
                source = parts[-1]
                available_version = parts[-2]
                version = parts[-3]
                pkg_id = parts[-4]
                
                name = " ".join(parts[:-4])
                
                packages.append(Package(
                    name=name.strip(),
                    id=pkg_id,
                    version=version,
                    available_version=available_version,
                    source=source
                ))
        
        return packages
        
    except subprocess.CalledProcessError as e:
        print(f"Error executing winget: {e.stderr}")
        return []
    except FileNotFoundError:
        print("Error: 'winget' command not found. Ensure Windows Package Manager is installed and in your PATH.")
        return []

if __name__ == "__main__":
    upgrades = get_upgradable_packages()
    print(f"Found {len(upgrades)} packages needing an upgrade:")
    for pkg in upgrades:
        print(f"  Name: {pkg.name} | ID: {pkg.id} | Current: {pkg.version} | Available: {pkg.available_version}")