#!/usr/bin/env python3
"""
Universal CIF Visualization Demo for Crystalyse

This script demonstrates how to use the integrated universal CIF visualizer
capabilities in your Crystalyse workflow.
"""

from pathlib import Path

from crystalyse.output.universal_cif_visualizer import UniversalCIFVisualizer


def main():
    print("🔬 Universal CIF Visualizer Demo for Crystalyse")
    print("=" * 50)

    # Initialize the visualizer
    visualizer = UniversalCIFVisualizer()

    # Demo 1: Create universal viewer (like the user's scaffold)
    print("\n1️⃣ Creating Universal CIF Viewer...")
    viewer_path = "/tmp/crystalyse_universal_viewer.html"
    visualizer.create_universal_viewer(viewer_path)
    print(f"   📄 Universal viewer created: {viewer_path}")
    print("   🌐 Open this in a browser to load any CIF file!")

    # Demo 2: Check for existing CIF files to visualize
    print("\n2️⃣ Looking for CIF files to demonstrate individual conversion...")

    # Check recent query results
    query_results_dirs = ["/home/ryan/crystalyseai/test_perovskite", "/tmp"]

    cif_files_found = []
    for base_dir in query_results_dirs:
        if Path(base_dir).exists():
            cif_files = list(Path(base_dir).glob("**/cif_files/*.cif"))
            cif_files_found.extend(cif_files)

    if cif_files_found:
        print(f"   Found {len(cif_files_found)} CIF files")

        # Convert first CIF file to demonstrate individual conversion
        first_cif = cif_files_found[0]
        print(f"\\n3️⃣ Converting {first_cif.name} to HTML...")

        try:
            html_output = visualizer.convert_cif_to_html(str(first_cif), "/tmp/demo_structure.html")
            print(f"   ✅ Individual visualization created: {html_output}")
        except Exception as e:
            print(f"   ⚠️  Conversion failed: {e}")

        # Demo 3: Create gallery if we have multiple CIF files in same directory
        cif_dir = first_cif.parent
        cif_files_in_dir = list(cif_dir.glob("*.cif"))

        if len(cif_files_in_dir) > 1:
            print(f"\\n4️⃣ Creating gallery from {len(cif_files_in_dir)} CIF files in {cif_dir}...")
            try:
                gallery_output = visualizer.create_gallery(str(cif_dir), "/tmp/crystalyse_gallery")
                print(f"   ✅ Gallery created: {gallery_output}")
                print(f"   🌐 Open {gallery_output}/index.html to browse all structures!")
            except Exception as e:
                print(f"   ⚠️  Gallery creation failed: {e}")
    else:
        print("   No CIF files found to demonstrate conversion")

    print("\\n🎯 Summary of Available Capabilities:")
    print("   • Universal HTML viewer (load any CIF file)")
    print("   • Individual CIF → HTML conversion")
    print("   • Batch processing of CIF directories")
    print("   • Gallery generation with search functionality")
    print("   • Enhanced visualization with 3Dmol.js")
    print("   • Automatic structural analysis and parameter extraction")
    print("   • Responsive design for desktop and mobile")

    print("\\n📖 Command Line Usage:")
    print("   # Create universal viewer")
    print("   python -m crystalyse.output.universal_cif_visualizer create-viewer viewer.html")
    print("   ")
    print("   # Convert single CIF")
    print("   python -m crystalyse.output.universal_cif_visualizer convert structure.cif")
    print("   ")
    print("   # Create gallery")
    print("   python -m crystalyse.output.universal_cif_visualizer gallery /path/to/cif/files")


if __name__ == "__main__":
    main()
