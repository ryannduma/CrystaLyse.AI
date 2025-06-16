#!/usr/bin/env node

const { spawn } = require('child_process');
const path = require('path');

async function testBasicFunctionality() {
    console.log('🧪 Testing CrystaLyse CLI Basic Functionality');
    console.log('=' .repeat(50));
    
    // Test 1: Help command
    console.log('\n📋 Test 1: Help Command');
    try {
        const helpProcess = spawn('node', [path.join(__dirname, 'dist/index.js'), '--help'], {
            stdio: 'pipe'
        });
        
        let output = '';
        helpProcess.stdout.on('data', (data) => {
            output += data.toString();
        });
        
        await new Promise((resolve) => {
            helpProcess.on('close', (code) => {
                console.log(code === 0 ? '✅ Help command works' : '❌ Help command failed');
                if (output.includes('crystalyse')) {
                    console.log('✅ CLI identity correct');
                } else {
                    console.log('❌ CLI identity issue');
                }
                resolve();
            });
        });
    } catch (error) {
        console.log('❌ Help test failed:', error.message);
    }
    
    // Test 2: Version command  
    console.log('\n📋 Test 2: Version Command');
    try {
        const versionProcess = spawn('node', [path.join(__dirname, 'dist/index.js'), '--version'], {
            stdio: 'pipe'
        });
        
        let output = '';
        versionProcess.stdout.on('data', (data) => {
            output += data.toString();
        });
        
        await new Promise((resolve) => {
            versionProcess.on('close', (code) => {
                console.log(code === 0 ? '✅ Version command works' : '❌ Version command failed');
                if (output.trim().match(/\d+\.\d+\.\d+/)) {
                    console.log('✅ Version format correct');
                } else {
                    console.log('❌ Version format issue');
                }
                resolve();
            });
        });
    } catch (error) {
        console.log('❌ Version test failed:', error.message);
    }

    // Test 3: Bridge connectivity (quick test)
    console.log('\n📋 Test 3: Python Bridge Test');
    try {
        const fs = require('fs');
        const bridgeScript = path.join(__dirname, 'src/bridge/crystalyse_bridge.py');
        
        if (fs.existsSync(bridgeScript)) {
            console.log('✅ Python bridge script exists');
            
            // Test if Python can run the script
            const pythonProcess = spawn('python3', [bridgeScript], {
                stdio: 'pipe'
            });
            
            let output = '';
            pythonProcess.stdout.on('data', (data) => {
                output += data.toString();
            });
            
            // Send a simple test
            pythonProcess.stdin.write('{"type": "validate", "composition": "NaCl"}\n');
            pythonProcess.stdin.end();
            
            await new Promise((resolve) => {
                setTimeout(() => {
                    pythonProcess.kill();
                    
                    if (output.includes('"type": "ready"') || output.includes('"type": "complete"')) {
                        console.log('✅ Python bridge responds correctly');
                    } else if (output.includes('demo')) {
                        console.log('⚠️ Python bridge running in demo mode');
                    } else {
                        console.log('❌ Python bridge communication issue');
                        console.log('Bridge output:', output);
                    }
                    resolve();
                }, 3000);
            });
        } else {
            console.log('❌ Python bridge script missing');
        }
    } catch (error) {
        console.log('❌ Bridge test failed:', error.message);
    }

    // Test 4: HTML template test
    console.log('\n📋 Test 4: HTML Template Test');
    try {
        const fs = require('fs');
        const viewerTemplate = path.join(__dirname, 'assets/viewer.html');
        
        if (fs.existsSync(viewerTemplate)) {
            const content = fs.readFileSync(viewerTemplate, 'utf8');
            
            if (content.includes('3Dmol') && content.includes('viewport')) {
                console.log('✅ HTML viewer template is valid');
            } else {
                console.log('❌ HTML viewer template is incomplete');
            }
        } else {
            console.log('❌ HTML viewer template missing');
        }
        
        const compareTemplate = path.join(__dirname, 'assets/compare.html');
        if (fs.existsSync(compareTemplate)) {
            console.log('✅ HTML compare template exists');
        } else {
            console.log('❌ HTML compare template missing');
        }
    } catch (error) {
        console.log('❌ Template test failed:', error.message);
    }

    // Test 5: Directory structure
    console.log('\n📋 Test 5: Directory Structure Test');
    const expectedDirs = [
        'dist',
        'src/commands',
        'src/ui',
        'src/visualization',
        'src/bridge',
        'assets'
    ];
    
    const fs = require('fs');
    for (const dir of expectedDirs) {
        const dirPath = path.join(__dirname, dir);
        if (fs.existsSync(dirPath)) {
            console.log(`✅ ${dir} exists`);
        } else {
            console.log(`❌ ${dir} missing`);
        }
    }
    
    console.log('\n🎯 Basic functionality test complete!');
    console.log('=' .repeat(50));
}

// Run the test
testBasicFunctionality().catch(console.error);