"""Generate the code reference pages and navigation."""
from pathlib import Path
import mkdocs_gen_files
import importlib
import inspect

nav = mkdocs_gen_files.Nav()

root = Path(__file__).parent.parent
src = root / "src"
generated_docs = root / "docs" / "generated_reference"
generated_docs.mkdir(parents=True, exist_ok=True)

def generate_markdown_content(module_name, obj):
    """Generate markdown documentation for a Python object."""
    content = [f"# {obj.__name__}\n"]
    
    # Add docstring if it exists
    if obj.__doc__:
        content.append(obj.__doc__.strip())
        content.append("\n")
    
    if inspect.isclass(obj):
        # Document methods
        for name, method in inspect.getmembers(obj, inspect.isfunction):
            if not name.startswith('_'):  # Skip private methods
                content.append(f"## {name}\n")
                if method.__doc__:
                    content.append(method.__doc__.strip())
                content.append("\n")
                
                # Get the method signature
                try:
                    signature = inspect.signature(method)
                    content.append(f"```python\n{name}{signature}\n```\n")
                except ValueError:
                    pass
                
                content.append("\n")
    
    return "\n".join(content)

for path in sorted(src.rglob("*.py")):
    module_path = path.relative_to(src).with_suffix("")
    if "rapidata_client" not in str(module_path):
        continue
    
    doc_path = path.relative_to(src).with_suffix(".md")
    full_doc_path = Path("reference", doc_path)
    permanent_doc_path = generated_docs / doc_path

    parts = tuple(module_path.parts)

    if parts[-1] == "__init__":
        parts = parts[:-1]
        doc_path = doc_path.with_name("index.md")
        full_doc_path = full_doc_path.with_name("index.md")
        permanent_doc_path = permanent_doc_path.with_name("index.md")
    elif parts[-1] == "__main__":
        continue

    nav[parts] = doc_path.as_posix()

    # Import the module and generate documentation
    module_name = ".".join(parts)
    try:
        module = importlib.import_module(module_name)
        
        # Generate markdown content for the module and its contents
        content = [f"# {module_name}\n"]
        
        if module.__doc__:
            content.append(module.__doc__.strip())
            content.append("\n")
        
        # Document classes in the module
        for name, obj in inspect.getmembers(module, inspect.isclass):
            if obj.__module__ == module_name:  # Only document classes defined in this module
                content.append(generate_markdown_content(module_name, obj))
        
        markdown_content = "\n".join(content)
        
        # For mkdocs processing
        with mkdocs_gen_files.open(full_doc_path, "w") as fd:
            fd.write(f"::: {module_name}")
        
        # Save detailed markdown content
        permanent_doc_path.parent.mkdir(parents=True, exist_ok=True)
        with open(permanent_doc_path, "w") as fd:
            fd.write(markdown_content)
            
    except ImportError as e:
        print(f"Warning: Could not import {module_name}: {e}")
        continue

    mkdocs_gen_files.set_edit_path(full_doc_path, path.relative_to(root))

with mkdocs_gen_files.open("reference/SUMMARY.md", "w") as nav_file:
    nav_file.writelines(nav.build_literate_nav())

# Also save SUMMARY.md permanently
summary_path = generated_docs / "SUMMARY.md"
with open(summary_path, "w") as nav_file:
    nav_file.writelines(nav.build_literate_nav())
