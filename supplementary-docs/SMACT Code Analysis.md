# SMACT Codebase Analysis

## High-Level Architecture

### Core Data Model
- **Element**: Central class storing elemental properties (electronegativity, oxidation states, radii, etc.)
- **Species**: Represents elements in specific oxidation states
- **Composition**: Handles chemical compositions and stoichiometry

### Key Modules and Their Relationships

1. **Data Loading Pipeline**
   - `data_loader.py` reads from CSV/JSON files in `data/` directory
   - Initializes Element and Species objects with properties
   - Data includes oxidation states, radii, electronegativities from multiple sources

2. **Screening Workflow**
   - `screening.py` provides filters (charge neutrality, electronegativity)
   - `oxidation_states.py` adds statistical filtering using ICSD data
   - Filters can be chained to progressively narrow search space

3. **Property Estimation**
   - `properties.py` calculates band gaps, solid-state energy scales
   - `metallicity.py` classifies metallic vs non-metallic character
   - Uses composition-based heuristics and element properties

4. **Structure Tools**
   - `lattice_parameters.py` estimates lattice constants from ionic radii
   - `builder.py` constructs common structure types (perovskite, spinel)
   - `structure_prediction/` submodule uses ML for structure prediction via ionic substitution

5. **Analysis Utilities**
   - `utils/composition.py` provides composition parsing and manipulation
   - `utils/crystal_space/` handles embedding and visualisation
   - `benchmarking/` compares performance with pymatgen

### Data Sources
The `data/` directory contains critical datasets:
- Multiple oxidation state sources (ICSD, Wikipedia, Pymatgen)
- Shannon and covalent radii databases
- Elemental properties (electronegativity, valence electrons)
- ML embeddings for structure prediction

### Integration Points
- ASE (Atomic Simulation Environment) for structure manipulation
- Pymatgen for materials analysis interoperability
- Materials Project API for downloading structures
- ElementEmbeddings for ML featurization

## Testing Approach
Tests are in `smact/tests/` and use pytest. Key test files:
- `test_core.py`: Element/Species functionality
- `test_structure.py`: Structure prediction
- `test_utils.py`: Utility functions
- `test_doper.py`: Dopant prediction
- `test_metallicity.py`: Metallicity classification

Test data files are stored in `smact/tests/files/`.

## Most Critical/Essential Functions

### Core Data & Classes

**1. `Element` and `Species` classes** (`smact/__init__.py`)
- Foundation of entire library - stores elemental properties
- Used by nearly every other module
- Provides oxidation states, electronegativity, radii, etc.

**2. `data_loader.lookup_element_data()`** (`smact/data_loader.py`)
- Critical data loading infrastructure
- Implements caching to avoid repeated I/O
- Feeds data to Element/Species initialization

### Screening & Filtering

**3. `smact_filter()`** (`smact/screening.py`)
- The primary composition screening function
- Implements charge neutrality and electronegativity checks
- Core to the library's main use case

**4. `neutral_ratios()`** (`smact/__init__.py`)
- Calculates charge-neutral stoichiometries
- Essential for generating valid compositions

**5. `pauling_test()`** (`smact/screening.py`)
- Electronegativity ordering filter
- Key chemical heuristic for screening

### Property Prediction

**6. `band_gap_*()` functions** (`smact/properties.py`)
- Estimates band gaps from composition
- Critical for semiconductor discovery

**7. `compound_electroneg()` and related** (`smact/properties.py`)
- Calculates composition-weighted properties
- Used throughout for property estimation

### Structure Prediction

**8. `predict_structure()`** (`smact/structure_prediction/prediction.py`)
- ML-based crystal structure prediction
- Key advanced functionality

**9. `build_*()` functions** (`smact/builder.py`)
- Constructs common structure types
- Essential for structure generation

### Utilities

**10. `parse_formula()`** (`smact/utils/composition.py`)
- Parses chemical formulas into usable data
- Fundamental utility used everywhere

**11. `get_sign()` and `oxidation_states_filter()`** (`smact/oxidation_states.py`)
- Statistical oxidation state validation
- Important for realistic screening

## Least Essential Modules & Functions

### Least Essential Modules

**1. `smact/benchmarking/`**
- Performance comparison tools with pymatgen
- Only useful for development/optimisation
- Not needed for core functionality

**2. `smact/metallicity.py`**
- Binary metallicity classification
- Limited use case (metal vs non-metal)
- Could be replaced with simpler heuristics

**3. `smact/utils/crystal_space/`**
- Visualisation and embedding tools
- Nice-to-have for analysis but not core
- Primarily for creating plots/visualisations

**4. `smact/mainpage.py`**
- Just contains documentation strings
- No functional code

### Least Essential Functions

**5. Visualisation functions**
- `plot_embedding()` in crystal_space
- `plot_dopability()` in doper.py
- Useful for papers but not essential

**6. File I/O utilities**
- `download_compounds_with_mp_api.py`
- `generate_composition_with_smact.py`
- Convenience scripts, not core functionality

**7. Specialized getters in Element class**
- `Element.num_valence_modified`
- `Element.dipol` (dipole polarizability)
- `Element.eig_s` (s-orbital eigenvalue)
- Rarely used properties

**8. Alternative oxidation state sources**
- `oxidation_states_wiki`
- `oxidation_states_sp`
- `oxidation_states_custom`
- Most users just need the default set

**9. Legacy/deprecated functions**
- `ordered_elements()` (returns element list in order)
- Some SSE variants that aren't commonly used

**10. Specialized lattice functions**
- `cubic_perovskite_tolerance_factor()`
- `cubic_perovskite_goldschmidt()`
- Very specific use cases

## Most Inefficient Parts of the Codebase

### 1. **Repeated Element Object Creation**
- Elements are recreated multiple times instead of being cached
- Each Element initialization triggers file I/O despite data_loader caching
- Could benefit from a singleton pattern or module-level cache

### 2. **Inefficient Combinatorial Generation**
- `enumerator()` in `screening.py` generates all combinations in memory
- For 4+ elements, this creates enormous lists before filtering
- Should use generators/iterators throughout

### 3. **String-based Formula Parsing**
- `parse_formula()` uses regex repeatedly
- Formula parsing happens multiple times for same formula
- No caching of parsed results

### 4. **Redundant Oxidation State Lookups**
- Multiple oxidation state lists stored per element
- Each access requires attribute lookup
- Could be optimised with better data structure

### 5. **Database Operations in Structure Prediction**
- `database.py` uses basic SQL without indexing strategy
- No connection pooling
- Repeated queries for same data

### 6. **JSON Loading for Embeddings**
- Large JSON files loaded repeatedly in `structure_prediction`
- Files like `skipspecies_20221028_319ion_dim200_cosine_similarity.json`
- Should be loaded once and cached

### 7. **Inefficient Charge Neutrality Checking**
- `neutral_ratios()` uses nested loops and GCD calculations
- Could be optimised with vectorised operations
- Generates many unnecessary combinations

### 8. **Multiple Data File Formats**
- Mix of CSV, JSON, TXT formats requiring different parsers
- Inconsistent data loading strategies
- Should standardise on one efficient format

### 9. **No Parallel Processing in Core Functions**
- `smact_filter()` processes combinations sequentially
- Could parallelise independent composition checks
- Only examples show multiprocessing usage

### 10. **Repeated Property Calculations**
- Properties like electronegativity calculated multiple times
- No memoization for expensive calculations
- Could cache at composition level

## Specific Code Examples of Inefficiencies

### 1. **Repeated File I/O Operations**

In `smact/data_loader.py`, multiple functions read the same data files repeatedly:
- Lines 92-93, 140-141, 186-187, 234-235, 283-284, 328-329: Each oxidation state lookup function opens and parses its data file on first call, but caching is per-function, not globally shared
- Lines 372-382 (`lookup_element_hhis`): Opens and parses `hhi.txt` file
- Lines 438-444 (`lookup_element_data`): Opens and parses `element_data.txt`
- Lines 512-537, 610-635: Shannon radii CSV files are parsed multiple times

**Issue**: If multiple Element objects are created in sequence, each triggers separate file reads even though they could share cached data.

### 2. **Inefficient Loops and Combinatorial Generation**

In `smact/screening.py`:
- Lines 205, 243 (`eneg_states_test` functions): Uses `combinations()` to generate all pairs for electronegativity testing, creating O(n²) comparisons
- Line 404: `itertools.product(*ox_combos)` generates all possible oxidation state combinations, which can be exponentially large
- Line 507: Another `itertools.product(*ox_combos)` in `smact_validity`

In `smact/__init__.py`:
- Line 504: `itertools.product(*stoichs)` generates all stoichiometry combinations up to threshold

**Issue**: These generate all combinations upfront rather than lazily evaluating or short-circuiting when a valid combination is found.

### 3. **Lack of Caching Where Beneficial**

In `smact/__init__.py`:
- Lines 294-297 (`Species.__init__`): Shannon radius data is looked up every time a Species object is created, even for the same element/oxidation/coordination
- Lines 335-339: SSE_2015 data lookup is repeated for each Species instance

In `smact/oxidation_states.py`:
- Lines 40-45: Probability table is loaded from JSON file each time an `Oxidation_state_probability_finder` is instantiated without a custom table

### 4. **Redundant Calculations**

In `smact/__init__.py`:
- Lines 182-183, 200-203: `oxidation_states_icsd24` is looked up twice (once for `oxidation_states` and once for `oxidation_states_icsd24`)
- Lines 305-306, 313-314: Shannon radius lookups iterate through all datasets twice (once for shannon_radius, once for ionic_radius)

In `smact/screening.py`:
- Lines 476-479: GCD calculation and stoichiometry normalization happens for every `smact_validity` call, even for the same composition

### 5. **Memory-Intensive Operations**

In `smact/data_loader.py`:
- Lines 879-906 (`lookup_element_magpie_data`): Loads entire Magpie CSV into pandas DataFrame and converts to dictionary, keeping all in memory
- Lines 946-951 (`lookup_element_valence_data`): Similar pandas DataFrame loading

In `smact/__init__.py`:
- Line 393: `element_dictionary` creates Element objects for all 103 elements even if only a few are needed

In `smact/structure_prediction/database.py`:
- Lines 160-165: Uses parallel processing with `pathos` but loads all data into memory before processing

## Summary of Key Inefficiencies

### Most Critical Performance Issues:

1. **Exponential Combinatorial Generation**: The biggest bottleneck - `smact_filter()` and related functions generate all combinations before filtering, limiting practical chemical space size

2. **No Shared Caching**: Each data_loader function maintains separate caches, causing redundant file parsing and memory usage

3. **Repeated Element Instantiation**: No caching of Element/Species objects leads to unnecessary overhead

4. **Sequential Processing**: Core functions don't leverage parallelization despite being embarrassingly parallel

5. **Inefficient Data Structures**: Using lists/dictionaries where numpy arrays or more efficient structures would be better

### Recommendations for Optimization:

1. **Implement Global Cache**: Single shared cache for all file data across data_loader functions
2. **Use Generators**: Replace `itertools.product()` with lazy generators that yield combinations
3. **Add Memoization**: Cache expensive calculations and object instantiations
4. **Parallelize Core Functions**: Built-in multiprocessing for screening operations
5. **Optimise Data Loading**: Standardise on efficient binary formats, use memory mapping for large files
6. **Early Termination**: Short-circuit combinatorial searches when valid combinations are found
7. **Vectorise Operations**: Use numpy for numerical operations instead of pure Python loops

### Recommendations for Future Development
1. **Refactor Element Class**: Implement singleton or caching for Element objects
2. **Use Iterators**: Replace list generation with iterators/generators
3. **Add Memoization**: Cache expensive calculations and object instantiations
4. **Parallelise Core Functions**: Built-in multiprocessing for screening operations
5. **Optimise Data Loading**: Standardise on efficient binary formats, use memory mapping for large files
6. **Early Termination**: Short-circuit combinatorial searches when valid combinations are found
7. **Vectorise Operations**: Use numpy for numerical operations instead of pure Python loops
8. **Standardise Data Formats**: Consolidate on a single, efficient data format like HDF5
9. **Improve Database Interactions**: Use an ORM or implement connection pooling and indexing
10. **Centralize Configuration**: Use a single config file for paths and parameters