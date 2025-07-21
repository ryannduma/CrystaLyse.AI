# User Interface Components

## Overview

CrystaLyse.AI provides a sophisticated command-line interface designed specifically for materials design workflows. The UI combines intuitive interaction patterns with powerful crystal structure visualisation capabilities, offering both novice-friendly guidance and expert-level efficiency for materials researchers.

## UI Architecture

### Component Structure

```
CLI Interface
├── Command Parser
│   ├── Natural Language Processing
│   ├── Materials-aware Parsing
│   └── Context Understanding
├── Display Engine
│   ├── Crystal Structure Visualisation
│   ├── Data Presentation
│   └── Interactive Elements
├── Theme System
│   ├── Colour Schemes
│   ├── ASCII Art
│   └── Layout Templates
└── Session Management
    ├── History Tracking
    ├── Context Preservation
    └── Multi-session Support
```

## Command-Line Interface

### Interactive Mode

The primary interface for materials design analysis:

```bash
$ crystalyse interactive

═══════════════════════════════════════════════════════════
                    CRYSTALYSE.AI v1.0.0
                  Materials Design Platform
═══════════════════════════════════════════════════════════

Welcome to CrystaLyse.AI! Type 'help' for commands or ask any materials design question.

crystalyse> analyse LiFePO4
```

### Command Structure

CrystaLyse.AI supports multiple command patterns:

```bash
# Direct commands
crystalyse analyse "LiFePO4"
crystalyse visualise "CaTiO3" --output perovskite.png
crystalyse design "high capacity cathode" --target-material

# Natural language
crystalyse "What are the properties of LiCoO2?"
crystalyse "Show me materials similar to spinel oxides"
crystalyse "How can I design a stable electrolyte?"

# Interactive sessions
crystalyse interactive --session battery_materials
crystalyse resume session_id
```

## Display Components

### Crystal Structure Visualisation

#### 2D Structure Display

```
Material: Lithium Iron Phosphate (LiFePO4)
Formula: LiFePO4

Structure:
  Li⁺  Fe²⁺  [PO₄]³⁻
   │    │      │
  Olivine Structure
         
Structural Features:
• Olivine framework: [FeO6] octahedra
• Polyanion: [PO4] tetrahedra  
• Li channels: 1D diffusion paths
```

#### 3D Visualisation

Interactive 3D crystal structure viewer:
- Rotate, zoom, and pan
- Multiple rendering styles
- Atom/bond labelling
- Unit cell display
- Miller planes visualisation

### Data Presentation

#### Property Tables

```
═══════════════════════════════════════════════════════════
                    MATERIAL PROPERTIES
═══════════════════════════════════════════════════════════
Property                Value              Unit       
───────────────────────────────────────────────────────────
Formation Energy        -2.84              eV/atom    
Band Gap                3.8                eV         
Density                 3.6                g/cm³      
Space Group             Pnma               -          
Lattice a               10.33              Å          
Lattice b               6.01               Å          
═══════════════════════════════════════════════════════════
```

#### Analysis Summaries

```
┌─────────────────────────────────────────────────────────┐
│                    ANALYSIS SUMMARY                     │
├─────────────────────────────────────────────────────────┤
│ Material: Lithium Iron Phosphate                       │
│ Formula: LiFePO₄                                        │
│                                                         │
│ Key Findings:                                           │
│ ✓ Thermodynamically stable structure                   │
│ ✓ Suitable band gap for cathode application            │
│ ⚠ Lower ionic conductivity than alternatives           │
│                                                         │
│ Similarity: 8 similar olivine structures found         │
│ Applications: Battery cathode materials                 │
└─────────────────────────────────────────────────────────┘
```

### Interactive Elements

#### Progress Indicators

```
Analysing material... [████████████████████] 100%

Processing steps:
✓ Composition validation (SMACT)
✓ Structure generation (Chemeleon)
✓ Energy calculation (MACE)
⚠ Phase stability analysis (metastable)
✓ Property prediction (suitable for batteries)
```

#### Selection Menus

```
Multiple crystal structures found:

[1] Olivine structure (most stable, -2.84 eV/atom)
    Li diffusion: 1D channels
    Structural stability: High

[2] Spinel structure (metastable, -2.71 eV/atom)
    Li diffusion: 3D pathways
    Structural stability: Moderate

[3] Layered structure (unstable, -2.55 eV/atom)
    Li diffusion: 2D layers
    Structural stability: Low

Select structure [1-3] or 'all' for details: 
```

## Theme System

### Colour Schemes

#### Professional Theme (Default)

```python
theme = {
    "primary": "#2E86AB",      # Crystal blue
    "secondary": "#A23B72",    # Materials purple  
    "success": "#F18F01",      # Formation orange
    "warning": "#C73E1D",      # Alert red
    "info": "#03CEA4",         # Information teal
    "background": "#F5F5F5",   # Light grey
    "text": "#2C3E50"          # Dark blue-grey
}
```

#### Dark Theme

```python
dark_theme = {
    "primary": "#61DAFB",      # Bright blue
    "secondary": "#BB86FC",    # Purple
    "success": "#03DAC6",      # Teal
    "warning": "#CF6679",      # Pink
    "info": "#FFB74D",         # Orange
    "background": "#121212",   # Dark grey
    "text": "#FFFFFF"          # White
}
```

### Enhanced UI Components

#### Header Graphics

```
     ▄████▄   ██▀███ ▓██   ██▓  ██████ ▄▄▄█████▓ ▄▄▄       ██▓    ▓██   ██▓  ██████ ▓█████ 
    ▒██▀ ▀█  ▓██ ▒ ██▒▒██  ██▒▒██    ▒ ▓  ██▒ ▓▒▒████▄    ▓██▒     ▒██  ██▒▒██    ▒ ▓█   ▀ 
    ▒▓█    ▄ ▓██ ░▄█ ▒ ▒██ ██░░ ▓██▄   ▒ ▓██░ ▒░▒██  ▀█▄  ▒██░      ▒██ ██░░ ▓██▄   ▒███   
    ▒▓▓▄ ▄██▒▒██▀▀█▄   ░ ▐██▓░  ▒   ██▒░ ▓██▓ ░ ░██▄▄▄▄██ ▒██░      ░ ▐██▓░  ▒   ██▒▒▓█  ▄ 
    ▒ ▓███▀ ░░██▓ ▒██▒ ░ ██▒▓░▒██████▒▒  ▒██▒ ░  ▓█   ▓██▒░██████▒  ░ ██▒▓░▒██████▒▒░▒████▒
    ░ ░▒ ▒  ░░ ▒▓ ░▒▓░  ██▒▒▒ ▒ ▒▓▒ ▒ ░  ▒ ░░    ▒▒   ▓▒█░░ ▒░▓  ░   ██▒▒▒ ▒ ▒▓▒ ▒ ░░░ ▒░ ░
      ░  ▒     ░▒ ░ ▒░▓██ ░▒░ ░ ░▒  ░ ░    ░      ▒   ▒▒ ░░ ░ ▒  ░ ▓██ ░▒░ ░ ░▒  ░ ░ ░ ░  ░
    ░          ░░   ░ ▒ ▒ ░░  ░  ░  ░    ░        ░   ▒     ░ ░    ▒ ▒ ░░  ░  ░  ░     ░   
    ░ ░         ░     ░ ░           ░                 ░  ░    ░  ░ ░ ░           ░     ░  ░
    ░                 ░ ░                                          ░ ░                      
```

#### Crystal Structure Graphics

```
    Li⁺    Fe²⁺    [PO₄]³⁻
     │      │        │
     •------•--------•
           Olivine Framework

Material: Lithium Iron Phosphate
Space Group: Pnma (orthorhombic)
```

## Customisation Options

### User Preferences

```yaml
# ~/.crystalyse/preferences.yaml
ui:
  theme: "professional"
  show_ascii_art: true
  colour_output: true
  verbose_mode: false
  
display:
  structure_format: "3d_crystal"
  table_style: "grid"
  max_similar_materials: 10
  
interaction:
  confirm_destructive: true
  auto_save_sessions: true
  command_history_size: 1000
```

### Command Aliases

```yaml
# Custom command shortcuts
aliases:
  props: "analyse --properties-only"
  sim: "similarity-search"
  design: "design-material --target-properties"
  viz: "visualise --crystal-structure"
```

## Responsive Design

### Terminal Adaptation

The UI adapts to terminal capabilities:

```python
# Detect terminal features
terminal_info = {
    "width": 120,
    "height": 40,
    "colour_support": "256_colour",
    "unicode_support": True
}

# Adjust display accordingly
if terminal_info["width"] < 80:
    use_compact_layout()
if not terminal_info["colour_support"]:
    use_monochrome_theme()
```

### Mobile-Friendly Output

For narrow terminals:

```
Mat: LiFePO4
Ef: -2.84 eV/atom
Bg: 3.8 eV
SG: Pnma

✓ Stable cathode
⚠ Low conductivity
```

## Accessibility Features

### Screen Reader Support

```python
# Alternative text for molecular structures
alt_text = {
    "structure": "Benzene ring with attached acetyl and carboxyl groups",
    "properties": "Molecular weight 180.16, moderate lipophilicity",
    "warning": "Potential gastrointestinal toxicity alert"
}
```

### Keyboard Navigation

```
Navigation:
  Tab/Shift+Tab: Move between elements
  Enter: Select/confirm
  Esc: Cancel/back
  ↑/↓: Navigate lists
  Space: Toggle options
  ?: Show help
```

### High Contrast Mode

```python
# High contrast colour scheme
high_contrast = {
    "background": "#000000",
    "text": "#FFFFFF", 
    "highlight": "#FFFF00",
    "error": "#FF0000",
    "success": "#00FF00"
}
```

## Advanced Features

### Split-Screen Mode

```
┌─────────────────────────┬─────────────────────────┐
│     Input/Commands      │      Visualisation      │
├─────────────────────────┼─────────────────────────┤
│ > analyse aspirin       │         O              │
│                         │         ‖              │
│ Properties calculated:  │     H₃C-C-O-⬡-C-OH     │
│ MW: 180.16 g/mol       │             │   ‖       │
│ LogP: 1.19             │             ⬡   O       │
│                         │                         │
│ > similar compounds     │     [Rotate] [Zoom]     │
│                         │     [Measure] [Export]  │
└─────────────────────────┴─────────────────────────┘
```

### Workflow Visualisation

```
Analysis Pipeline:
┌─────────┐    ┌─────────┐    ┌─────────┐    ┌─────────┐
│ Input   │ → │ Validate│ → │ Analyse │ → │ Report  │
│ SMILES  │    │ Structure│   │Properties│   │ Results │
└─────────┘    └─────────┘    └─────────┘    └─────────┘
     ↓             ↓             ↓             ↓
  ✓ Valid      ✓ Processed   ✓ Calculated  ✓ Generated
```

### Context-Aware Help

```
crystalyse> analyse LiCoO2 ?

HELP: analyse command
Syntax: analyse <material> [options]

For 'LiCoO2':
  Common representations:
  • Formula: LiCoO2
  • Structure: Layered oxide
  • Space Group: R-3m

  Suggested analyses:
  • Basic properties: analyse LiCoO2 --properties
  • Phase stability: analyse LiCoO2 --phase-diagram
  • Electronic structure: analyse LiCoO2 --band-structure

crystalyse> 
```

## Integration Patterns

### Agent Communication

```python
class UIAgent:
    def display_analysis(self, result):
        # Format for optimal readability
        formatted = self.format_for_terminal(result)
        
        # Add interactive elements
        if result.has_alternatives:
            formatted += self.create_selection_menu(result.alternatives)
        
        # Display with appropriate theme
        self.renderer.display(formatted, theme=self.current_theme)
    
    def handle_user_input(self, input_text):
        # Parse natural language or commands
        parsed = self.parser.parse(input_text)
        
        # Provide immediate feedback
        self.show_processing_indicator()
        
        # Execute and display results
        result = self.agent.process(parsed)
        self.display_analysis(result)
```

### Plugin Architecture

```python
# Custom UI plugins
class CustomDisplayPlugin:
    def register_renderers(self):
        return {
            "spectra": SpectraRenderer(),
            "reactions": ReactionRenderer(),
            "pathways": PathwayRenderer()
        }
    
    def register_commands(self):
        return {
            "spectra": self.handle_spectra_command,
            "pathways": self.handle_pathway_command
        }

# Register plugin
ui_manager.register_plugin(CustomDisplayPlugin())
```

## Performance Optimisation

### Lazy Rendering

```python
class LazyMoleculeRenderer:
    def render_on_demand(self, molecule):
        # Only render when displayed
        if self.is_visible(molecule):
            return self.full_render(molecule)
        else:
            return self.placeholder_render(molecule)
```

### Streaming Output

```python
def stream_analysis_results(molecule):
    yield "Starting analysis..."
    
    for step in analysis_pipeline:
        yield f"Processing {step.name}..."
        result = step.execute(molecule)
        yield format_partial_result(result)
    
    yield "Analysis complete!"
```

## Best Practices

### 1. Information Hierarchy

- Most important information first
- Group related data
- Use visual cues for priority
- Maintain consistent spacing

### 2. User Feedback

```python
# Provide clear feedback
def execute_command(command):
    try:
        show_progress("Executing command...")
        result = process_command(command)
        show_success("Command completed successfully")
        return result
    except Exception as e:
        show_error(f"Error: {e}")
        suggest_alternatives(command)
```

### 3. Context Preservation

- Remember user preferences
- Maintain command history
- Preserve session state
- Provide undo functionality

### 4. Error Handling

```python
# Graceful error presentation
def handle_error(error):
    if error.type == "InvalidSMILES":
        return format_smiles_error(error)
    elif error.type == "NetworkTimeout":
        return format_network_error(error)
    else:
        return format_generic_error(error)
```

## Next Steps

- Learn about [Session Management](sessions.md) for persistent interfaces
- Explore [Tool Integration](tools.md) for extended functionality
- Check [API Reference](../reference/ui/) for detailed documentation
- Read [Customisation Guide](../guides/customisation.md) for personalisation