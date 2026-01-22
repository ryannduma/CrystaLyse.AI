#!/bin/bash
# Setup script for headless visualization

echo "Setting up headless visualization environment for Crystalyse..."

# Check if running in headless environment
if [ -z "$DISPLAY" ]; then
    echo "No DISPLAY detected - configuring headless environment"

    # Install virtual display for headless environments (if not already installed)
    if ! command -v Xvfb &> /dev/null; then
        echo "Installing Xvfb for virtual display..."
        sudo apt-get update
        sudo apt-get install -y xvfb
    fi

    # Start virtual display
    export DISPLAY=:99
    echo "Starting virtual display on $DISPLAY..."
    Xvfb :99 -screen 0 1024x768x24 -ac +extension GLX +render -noreset &
    XVFB_PID=$!

    # Wait a moment for Xvfb to start
    sleep 2

    echo "Virtual display started with PID $XVFB_PID"
else
    echo "DISPLAY already set to: $DISPLAY"
fi

# Set environment variables for headless rendering
echo "Configuring environment variables for headless rendering..."

export KALEIDO_CHROMIUM_ARGS="--disable-gpu --disable-software-rasterizer --no-sandbox --disable-dev-shm-usage"
export KALEIDO_CHROMIUM_DISABLE_FEATURES="VizDisplayCompositor,UseOzonePlatform,WebGL,WebGL2"
export CHROME_ARGS="--no-sandbox --disable-gpu --disable-dev-shm-usage --disable-software-rasterizer"
export TORCH_FORCE_NO_WEIGHTS_ONLY_LOAD=1

# Add to current session
echo "export DISPLAY=:99" >> ~/.bashrc
echo "export KALEIDO_CHROMIUM_ARGS=\"--disable-gpu --disable-software-rasterizer --no-sandbox --disable-dev-shm-usage\"" >> ~/.bashrc
echo "export KALEIDO_CHROMIUM_DISABLE_FEATURES=\"VizDisplayCompositor,UseOzonePlatform,WebGL,WebGL2\"" >> ~/.bashrc
echo "export CHROME_ARGS=\"--no-sandbox --disable-gpu --disable-dev-shm-usage --disable-software-rasterizer\"" >> ~/.bashrc
echo "export TORCH_FORCE_NO_WEIGHTS_ONLY_LOAD=1" >> ~/.bashrc

echo "Environment variables configured and saved to ~/.bashrc"

# Test the setup
echo "Testing the setup..."
if command -v python3 &> /dev/null; then
    python3 -c "
import os
print('DISPLAY:', os.environ.get('DISPLAY', 'Not set'))
print('KALEIDO_CHROMIUM_ARGS:', os.environ.get('KALEIDO_CHROMIUM_ARGS', 'Not set'))
print('TORCH_FORCE_NO_WEIGHTS_ONLY_LOAD:', os.environ.get('TORCH_FORCE_NO_WEIGHTS_ONLY_LOAD', 'Not set'))
"
fi

echo "✅ Headless visualization environment setup complete!"
echo ""
echo "To apply these changes in the current session, run:"
echo "source ~/.bashrc"
echo ""
echo "Or restart your terminal and the environment will be configured automatically."
