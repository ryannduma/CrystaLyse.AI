#!/usr/bin/env python3
"""
Enhanced Materials Discovery Example

This example demonstrates the complete CrystaLyse.AI workflow including:
- Dual-mode operation (Creative vs Rigorous)
- Crystal structure prediction with Chemeleon
- Interactive 3D visualization
- Comprehensive file storage and organization
- HTML report generation

Usage:
    python enhanced_materials_discovery.py

Requirements:
    - OpenAI API key set in environment
    - py3dmol for visualization
    - Properly configured MCP servers (SMACT and Chemeleon)
"""

import asyncio
import os
from pathlib import Path
import sys

# Add parent directory to path for imports
sys.path.insert(0, str(Path(__file__).parent.parent))

async def demo_creative_mode():
    """Demonstrate creative mode with crystal structure generation."""
    print("🎨 Creative Mode Demo: Novel Photovoltaic Materials")
    print("=" * 60)
    
    from crystalyse import EnhancedCrystaLyseAgent
    
    # Initialize creative mode agent
    agent = EnhancedCrystaLyseAgent(
        model="gpt-4o-mini",  # Use cheaper model for demo
        temperature=0.7,      # Higher temperature for creativity
        use_chem_tools=False, # Creative mode - no SMACT validation
        storage_dir="demo_creative_results",
        auto_visualize=True,
        auto_store=True
    )
    
    query = """
    Design innovative lead-free perovskite materials for solar cells.
    Focus on compositions that could achieve high efficiency while being 
    environmentally friendly. Consider novel A-site and B-site substitutions.
    """
    
    try:
        print("  🔍 Generating novel compositions and crystal structures...")
        print("  ⏳ This may take a few minutes for structure generation...")
        
        result = await agent.analyze_with_visualization(
            query=query,
            num_structures_per_composition=3,  # Generate 3 structures per composition
            generate_report=True
        )
        
        print(f"\n  ✅ Analysis completed for session: {result['session_id']}")
        print(f"  📊 Processed {len(result['compositions'])} compositions")
        
        for comp in result['compositions']:
            if comp['success']:
                formula = comp['composition']
                num_structures = len(comp['structures'])
                print(f"    🔬 {formula}: {num_structures} crystal structures generated")
            else:
                print(f"    ❌ {comp['composition']}: Failed - {comp.get('error', 'Unknown error')}")
        
        if result['visualization_reports']:
            print(f"\n  📊 Generated {len(result['visualization_reports'])} HTML reports:")
            for report in result['visualization_reports']:
                print(f"    📄 {report}")
                print(f"       Open in browser: file://{Path(report).absolute()}")
        
        return result
        
    except Exception as e:
        print(f"  ❌ Creative mode demo failed: {e}")
        return None

async def demo_rigorous_mode():
    """Demonstrate rigorous mode with SMACT validation + crystal structures."""
    print("\n🔬 Rigorous Mode Demo: Validated Battery Materials")
    print("=" * 60)
    
    from crystalyse import EnhancedCrystaLyseAgent
    
    # Initialize rigorous mode agent
    agent = EnhancedCrystaLyseAgent(
        model="gpt-4o-mini",
        temperature=0.3,      # Lower temperature for precision
        use_chem_tools=True,  # Rigorous mode - with SMACT validation
        storage_dir="demo_rigorous_results",
        auto_visualize=True,
        auto_store=True
    )
    
    query = """
    Design and validate cathode materials for sodium-ion batteries.
    Requirements:
    - High specific capacity (>150 mAh/g)
    - Good structural stability during cycling
    - Use earth-abundant elements
    - Operating voltage 2.5-4.0V vs Na/Na+
    
    Validate all compositions with SMACT before generating structures.
    """
    
    try:
        print("  🔍 Generating compositions with SMACT validation...")
        print("  🧪 Followed by crystal structure prediction...")
        print("  ⏳ This may take several minutes...")
        
        result = await agent.analyze_with_visualization(
            query=query,
            num_structures_per_composition=5,  # Generate 5 structures per validated composition
            generate_report=True
        )
        
        print(f"\n  ✅ Rigorous analysis completed for session: {result['session_id']}")
        print(f"  📊 Processed {len(result['compositions'])} compositions")
        
        validated_count = 0
        for comp in result['compositions']:
            if comp['success']:
                formula = comp['composition']
                num_structures = len(comp['structures'])
                print(f"    ✅ {formula}: VALIDATED + {num_structures} structures")
                validated_count += 1
            else:
                print(f"    ❌ {comp['composition']}: {comp.get('error', 'Failed validation/generation')}")
        
        print(f"\n  🎯 Successfully validated and generated structures for {validated_count} compositions")
        
        if result['visualization_reports']:
            print(f"\n  📊 Generated {len(result['visualization_reports'])} HTML reports:")
            for report in result['visualization_reports']:
                print(f"    📄 {report}")
                print(f"       Open in browser: file://{Path(report).absolute()}")
        
        return result
        
    except Exception as e:
        print(f"  ❌ Rigorous mode demo failed: {e}")
        return None

async def demo_visualization_features():
    """Demonstrate advanced visualization features."""
    print("\n🎨 Advanced Visualization Features Demo")
    print("=" * 60)
    
    from crystalyse.visualization import CrystalVisualizer, StructureStorage
    
    # Initialize visualization system
    viz = CrystalVisualizer(backend="py3dmol")
    storage = StructureStorage("demo_visualization")
    
    print("  🔧 Testing visualization with sample structures...")
    
    # Create sample structure data
    sample_structures = [
        {
            'formula': 'CaTiO3',
            'structure': {
                "cell": [[3.84, 0.0, 0.0], [0.0, 3.84, 0.0], [0.0, 0.0, 3.84]],
                "positions": [[0.0, 0.0, 0.0], [1.92, 1.92, 1.92], [1.92, 1.92, 0.0], [1.92, 0.0, 1.92], [0.0, 1.92, 1.92]],
                "numbers": [20, 22, 8, 8, 8],  # Ca, Ti, O, O, O
                "pbc": [True, True, True]
            },
            'analysis': {
                'formula': 'CaTiO3',
                'volume': 56.7,
                'density': 4.04,
                'lattice': {
                    'a': 3.84, 'b': 3.84, 'c': 3.84,
                    'alpha': 90.0, 'beta': 90.0, 'gamma': 90.0
                },
                'symmetry': {
                    'space_group': 'Pm-3m',
                    'crystal_system': 'cubic',
                    'point_group': 'm-3m'
                }
            },
            'cif': '''data_CaTiO3
_cell_length_a 3.84
_cell_length_b 3.84
_cell_length_c 3.84
_space_group_name_H-M_alt 'P m -3 m'
loop_
_atom_site_label
_atom_site_fract_x
_atom_site_fract_y
_atom_site_fract_z
Ca1 0.0 0.0 0.0
Ti1 0.5 0.5 0.5
O1 0.5 0.5 0.0
O2 0.5 0.0 0.5
O3 0.0 0.5 0.5
'''
        }
    ]
    
    try:
        # Test individual visualization
        print("    🖼️ Creating individual structure visualization...")
        view = viz.visualize_structure(sample_structures[0]['structure'])
        
        # Save standalone interactive view
        standalone_path = Path("demo_CaTiO3_structure.html")
        viz.save_interactive_view(sample_structures[0]['structure'], standalone_path, "CaTiO3 Perovskite")
        print(f"    ✅ Standalone view saved: {standalone_path}")
        
        # Test multi-structure report
        print("    📋 Creating comprehensive HTML report...")
        html_report = viz.create_multi_structure_report(sample_structures, "CaTiO3")
        
        report_path = Path("demo_CaTiO3_report.html")
        report_path.write_text(html_report)
        print(f"    ✅ Comprehensive report saved: {report_path}")
        
        # Test storage features
        print("    💾 Testing storage and organization...")
        storage_info = storage.store_structures(
            composition="CaTiO3",
            structures=sample_structures,
            analysis_params={"demo": True, "method": "demonstration"}
        )
        
        print(f"    ✅ Stored {storage_info['num_structures']} structures")
        
        # Test MACE preparation
        print("    🔬 Preparing MACE input file...")
        mace_file = storage.prepare_mace_input("CaTiO3", max_structures=5)
        print(f"    ✅ MACE input prepared: {mace_file}")
        
        # Display storage stats
        stats = storage.get_storage_stats()
        print(f"    📈 Storage statistics:")
        print(f"       Compositions: {stats['total_compositions']}")
        print(f"       Structures: {stats['total_structures']}")
        print(f"       Files: {stats['total_cif_files']} CIF, {stats['total_json_files']} JSON")
        
        return True
        
    except Exception as e:
        print(f"    ❌ Visualization demo failed: {e}")
        return False

async def demo_session_management():
    """Demonstrate session management and export features."""
    print("\n📊 Session Management & Export Demo")
    print("=" * 60)
    
    from crystalyse import EnhancedCrystaLyseAgent
    
    agent = EnhancedCrystaLyseAgent(
        model="gpt-4o-mini",
        temperature=0.5,
        use_chem_tools=False,
        storage_dir="demo_session_management",
        auto_visualize=True,
        auto_store=True
    )
    
    try:
        print("  📚 Checking session history...")
        history = agent.get_session_history()
        print(f"    Found {len(history)} previous sessions")
        
        if history:
            latest_session = history[0]
            print(f"    Latest session: {latest_session['session_id']}")
            print(f"    Query: {latest_session['query'][:60]}...")
            print(f"    Compositions: {latest_session['compositions_processed']}")
            
            # Test export functionality
            print("  📤 Testing export functionality...")
            exported = agent.export_session_results(
                session_id=latest_session['session_id'],
                export_format="all"
            )
            
            total_exported = sum(len(files) for files in exported.values())
            print(f"    ✅ Exported {total_exported} files")
            print(f"       CIF files: {len(exported.get('cif', []))}")
            print(f"       JSON files: {len(exported.get('json', []))}")
            print(f"       HTML reports: {len(exported.get('html', []))}")
        
        return True
        
    except Exception as e:
        print(f"  ❌ Session management demo failed: {e}")
        return False

async def main():
    """Run the complete demonstration."""
    print("🚀 CrystaLyse.AI Enhanced Materials Discovery Demonstration")
    print("=" * 80)
    
    # Check environment
    if not os.getenv('OPENAI_MDG_API_KEY'):
        print("❌ OPENAI_MDG_API_KEY not set. Please set this environment variable.")
        print("   export OPENAI_MDG_API_KEY='your-mdg-key-here'")
        return
    
    # Demo sections
    demos = [
        ("Creative Mode", demo_creative_mode),
        ("Rigorous Mode", demo_rigorous_mode), 
        ("Visualization Features", demo_visualization_features),
        ("Session Management", demo_session_management),
    ]
    
    results = []
    
    for demo_name, demo_func in demos:
        try:
            print(f"\n🎯 Running {demo_name} Demo...")
            result = await demo_func()
            results.append((demo_name, result is not None and result is not False))
        except KeyboardInterrupt:
            print(f"\n⚠️ Demo interrupted: {demo_name}")
            break
        except Exception as e:
            print(f"❌ Demo crashed: {demo_name} - {e}")
            results.append((demo_name, False))
    
    # Summary
    print("\n" + "=" * 80)
    print("📊 Demonstration Summary")
    print("=" * 80)
    
    passed = 0
    for demo_name, success in results:
        status = "✅" if success else "❌"
        print(f"  {status} {demo_name}")
        if success:
            passed += 1
    
    print(f"\n🎯 Successfully completed {passed}/{len(results)} demonstrations")
    
    if passed == len(results):
        print("\n🎉 All demonstrations completed successfully!")
        
        print("\n📁 Generated Files:")
        print("  • Interactive HTML visualizations")
        print("  • Comprehensive structure reports")
        print("  • Organized CIF and JSON storage")
        print("  • MACE input files")
        print("  • Export packages")
        
        print("\n🚀 Next Steps:")
        print("  1. Open the HTML files in your browser to view 3D structures")
        print("  2. Use the CIF files with your favorite crystal structure software")
        print("  3. Import MACE files for force field calculations")
        print("  4. Explore the organized storage directories")
        
    else:
        print("\n⚠️ Some demonstrations had issues. Check the output above.")
        print("💡 Tip: Some features require proper MCP server setup.")

if __name__ == "__main__":
    try:
        asyncio.run(main())
    except KeyboardInterrupt:
        print("\n⚠️ Demonstration interrupted by user")
    except Exception as e:
        print(f"\n💥 Demonstration crashed: {e}")
        import traceback
        traceback.print_exc()