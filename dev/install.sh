#!/bin/bash

# CrystaLyse.AI Installation Script
# Automatically installs CrystaLyse.AI with proper Python 3.11+ environment setup

set -e  # Exit on any error

# Color codes for output
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
NC='\033[0m' # No Color

# Print functions
print_info() { echo -e "${BLUE}[INFO]${NC} $1"; }
print_success() { echo -e "${GREEN}[SUCCESS]${NC} $1"; }
print_warning() { echo -e "${YELLOW}[WARNING]${NC} $1"; }
print_error() { echo -e "${RED}[ERROR]${NC} $1"; }

# Default values
PYTHON_MIN_VERSION="3.11"
VENV_NAME="crystalyse-env"
INSTALL_METHOD="pip"
SKIP_VENV=false
EXTRAS=""

# Function to check if command exists
command_exists() {
    command -v "$1" >/dev/null 2>&1
}

# Function to compare version numbers
version_greater_equal() {
    printf '%s\n%s\n' "$2" "$1" | sort -V -C
}

# Function to get Python version
get_python_version() {
    python_cmd="$1"
    if command_exists "$python_cmd"; then
        $python_cmd -c "import sys; print('.'.join(map(str, sys.version_info[:2])))" 2>/dev/null || echo "0.0"
    else
        echo "0.0"
    fi
}

# Function to find suitable Python interpreter
find_python() {
    # List of Python commands to try
    python_commands=("python3.12" "python3.11" "python3" "python")
    
    for cmd in "${python_commands[@]}"; do
        version=$(get_python_version "$cmd")
        if version_greater_equal "$version" "$PYTHON_MIN_VERSION"; then
            echo "$cmd"
            return 0
        fi
    done
    
    return 1
}

# Function to detect operating system
detect_os() {
    if [[ "$OSTYPE" == "linux-gnu"* ]]; then
        if command_exists apt-get; then
            echo "ubuntu"
        elif command_exists yum; then
            echo "rhel"
        elif command_exists dnf; then
            echo "fedora"
        else
            echo "linux"
        fi
    elif [[ "$OSTYPE" == "darwin"* ]]; then
        echo "macos"
    elif [[ "$OSTYPE" == "msys" ]] || [[ "$OSTYPE" == "cygwin" ]]; then
        echo "windows"
    else
        echo "unknown"
    fi
}

# Function to install Python 3.11+ on different systems
install_python() {
    os=$(detect_os)
    
    case $os in
        "ubuntu")
            print_info "Installing Python 3.11 on Ubuntu/Debian..."
            sudo apt update
            sudo apt install -y software-properties-common
            sudo add-apt-repository -y ppa:deadsnakes/ppa
            sudo apt update
            sudo apt install -y python3.11 python3.11-pip python3.11-venv python3.11-dev
            ;;
        "rhel"|"fedora")
            print_info "Installing Python 3.11 on RHEL/Fedora..."
            if command_exists dnf; then
                sudo dnf install -y python3.11 python3.11-pip python3.11-devel
            else
                sudo yum install -y python3.11 python3.11-pip python3.11-devel
            fi
            ;;
        "macos")
            if command_exists brew; then
                print_info "Installing Python 3.11 using Homebrew..."
                brew install python@3.11
            else
                print_error "Homebrew not found. Please install Homebrew first:"
                print_info "  /bin/bash -c \"\$(curl -fsSL https://raw.githubusercontent.com/Homebrew/install/HEAD/install.sh)\""
                exit 1
            fi
            ;;
        *)
            print_error "Automatic Python installation not supported for your system."
            print_info "Please install Python 3.11+ manually from https://python.org"
            exit 1
            ;;
    esac
}

# Function to create virtual environment
create_venv() {
    python_cmd="$1"
    venv_path="$2"
    
    print_info "Creating virtual environment at $venv_path..."
    $python_cmd -m venv "$venv_path"
    
    # Activate virtual environment
    source "$venv_path/bin/activate"
    
    # Upgrade pip
    print_info "Upgrading pip..."
    pip install --upgrade pip
    
    print_success "Virtual environment created and activated"
}

# Function to install CrystaLyse.AI
install_crystalyse() {
    method="$1"
    extras="$2"
    
    package_spec="crystalyse-ai"
    if [[ -n "$extras" ]]; then
        package_spec="crystalyse-ai[$extras]"
    fi
    
    case $method in
        "pip")
            print_info "Installing CrystaLyse.AI using pip..."
            pip install "$package_spec"
            ;;
        "uv")
            if ! command_exists uv; then
                print_info "Installing uv..."
                pip install uv
            fi
            print_info "Installing CrystaLyse.AI using uv..."
            uv pip install "$package_spec"
            ;;
        *)
            print_error "Unknown installation method: $method"
            exit 1
            ;;
    esac
}

# Function to verify installation
verify_installation() {
    print_info "Verifying installation..."
    
    # Check if crystalyse command is available
    if command_exists crystalyse; then
        version=$(crystalyse --version 2>/dev/null || echo "unknown")
        print_success "CrystaLyse.AI installed successfully: $version"
    else
        print_error "CrystaLyse.AI command not found"
        return 1
    fi
    
    # Run system check
    print_info "Running system check..."
    if crystalyse check-system >/dev/null 2>&1; then
        print_success "System check passed"
    else
        print_warning "System check failed - some features may not work"
        print_info "Run 'crystalyse check-system' for detailed diagnostics"
    fi
}

# Function to setup configuration
setup_config() {
    print_info "Setting up initial configuration..."
    
    # Initialize configuration
    crystalyse init --quiet
    
    # Check for OpenAI API key
    if [[ -z "$OPENAI_API_KEY" ]]; then
        print_warning "OpenAI API key not found in environment"
        print_info "You'll need to set your API key later:"
        print_info "  export OPENAI_API_KEY='your-api-key-here'"
        print_info "  # or"
        print_info "  crystalyse config set openai.api_key 'your-api-key-here'"
    else
        print_success "OpenAI API key found in environment"
    fi
}

# Function to print usage instructions
print_usage() {
    cat << EOF
CrystaLyse.AI Installation Script

Usage: $0 [OPTIONS]

Options:
  -h, --help              Show this help message
  -m, --method METHOD     Installation method: pip or uv (default: pip)
  -e, --extras EXTRAS     Install with extras: visualization,quantum,all
  -v, --venv NAME         Virtual environment name (default: crystalyse-env)
  --skip-venv            Skip virtual environment creation
  --python COMMAND       Use specific Python command
  
Examples:
  $0                              # Basic installation
  $0 -m uv -e all                 # Install with uv and all extras
  $0 --skip-venv                  # Install in current environment
  $0 --python python3.11         # Use specific Python version

EOF
}

# Parse command line arguments
while [[ $# -gt 0 ]]; do
    case $1 in
        -h|--help)
            print_usage
            exit 0
            ;;
        -m|--method)
            INSTALL_METHOD="$2"
            shift 2
            ;;
        -e|--extras)
            EXTRAS="$2"
            shift 2
            ;;
        -v|--venv)
            VENV_NAME="$2"
            shift 2
            ;;
        --skip-venv)
            SKIP_VENV=true
            shift
            ;;
        --python)
            PYTHON_CMD="$2"
            shift 2
            ;;
        *)
            print_error "Unknown option: $1"
            print_usage
            exit 1
            ;;
    esac
done

# Main installation process
main() {
    print_info "Starting CrystaLyse.AI installation..."
    
    # Find or install Python
    if [[ -n "$PYTHON_CMD" ]]; then
        python_version=$(get_python_version "$PYTHON_CMD")
        if ! version_greater_equal "$python_version" "$PYTHON_MIN_VERSION"; then
            print_error "Specified Python version $python_version is less than required $PYTHON_MIN_VERSION"
            exit 1
        fi
        PYTHON_CMD="$PYTHON_CMD"
    else
        PYTHON_CMD=$(find_python)
        if [[ $? -ne 0 ]]; then
            print_warning "Python $PYTHON_MIN_VERSION+ not found. Attempting to install..."
            install_python
            PYTHON_CMD=$(find_python)
            if [[ $? -ne 0 ]]; then
                print_error "Failed to install or find Python $PYTHON_MIN_VERSION+"
                exit 1
            fi
        fi
    fi
    
    python_version=$(get_python_version "$PYTHON_CMD")
    print_success "Using Python $python_version at $(command -v $PYTHON_CMD)"
    
    # Create virtual environment (unless skipped)
    if [[ "$SKIP_VENV" == false ]]; then
        venv_path="$HOME/$VENV_NAME"
        create_venv "$PYTHON_CMD" "$venv_path"
    else
        print_info "Skipping virtual environment creation"
    fi
    
    # Install CrystaLyse.AI
    install_crystalyse "$INSTALL_METHOD" "$EXTRAS"
    
    # Verify installation
    verify_installation
    
    # Setup configuration
    setup_config
    
    # Print completion message
    print_success "Installation completed successfully!"
    print_info ""
    print_info "Next steps:"
    if [[ "$SKIP_VENV" == false ]]; then
        print_info "  1. Activate the virtual environment:"
        print_info "     source $HOME/$VENV_NAME/bin/activate"
    fi
    print_info "  2. Set your OpenAI API key (if not already set):"
    print_info "     export OPENAI_API_KEY='your-api-key-here'"
    print_info "  3. Try the quickstart:"
    print_info "     crystalyse --help"
    print_info "     crystalyse analyse 'CCO'"
    print_info "  4. Start an interactive session:"
    print_info "     crystalyse interactive"
    print_info ""
    print_info "For more information, visit: https://crystalyse-ai.readthedocs.io"
}

# Run main function
main "$@"